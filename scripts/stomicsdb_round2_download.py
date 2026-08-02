#!/usr/bin/env python3
"""Download a validated STOmicsDB acquisition plan without starting later rounds."""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from http.cookiejar import LoadError, MozillaCookieJar
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from http.client import HTTPException
from io import StringIO
from itertools import chain
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from threading import Lock
import time
from typing import IO, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


DEFAULT_DATA_ROOT = Path("/mnt/NAS_21T/ProjectData/HypoTrace_Data")
DEFAULT_PLAN = DEFAULT_DATA_ROOT / "raw_data/public_database/stomicsdb/registry/acquisition_plan.tsv"
CHUNK_SIZE = 1024 * 1024
USER_AGENT = "HypoTrace-STOmicsDB-Round2A/1.0"


class PlanError(ValueError):
    pass


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlanRow:
    row_number: int
    source_url: str
    target_path: str
    target: Path


@dataclass(frozen=True)
class DownloadConfig:
    overwrite: bool
    timeout: float
    retries: int
    retry_backoff: float
    cookie_file: Path | None = None


@dataclass(frozen=True)
class DownloadResult:
    row_number: int
    status: str
    target_path: str
    size_bytes: int
    sha256: str | None


@dataclass(frozen=True)
class RemoteIdentity:
    source_url: str
    final_url: str
    etag: str | None
    last_modified: str | None
    total_size: int | None

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "source_url": self.source_url,
            "final_url": self.final_url,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "total_size": self.total_size,
        }


class JsonlLogger:
    def __init__(self, stream: IO[str]) -> None:
        self.stream = stream
        self.lock = Lock()

    def emit(self, event: str, *, level: str = "info", row: PlanRow | None = None, **fields: Any) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": level,
            "event": event,
        }
        if row is not None:
            record.update(
                {
                    "row_number": row.row_number,
                    "source_url": row.source_url,
                    "target_path": row.target_path,
                }
            )
        record.update(fields)
        line = json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        with self.lock:
            self.stream.write(line + "\n")
            self.stream.flush()


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def parse_plan_bytes(plan_bytes: bytes, data_root: Path) -> list[PlanRow]:
    root_resolved = data_root.resolve()
    rows: list[PlanRow] = []
    seen_targets: set[str] = set()
    try:
        plan_text = plan_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PlanError("acquisition plan is not valid UTF-8") from exc
    reader = csv.reader(StringIO(plan_text, newline=""), delimiter="\t", strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise PlanError("acquisition plan is empty") from exc
    if header != ["source_url", "target_path"]:
        raise PlanError("acquisition plan header must be exactly source_url<TAB>target_path")
    for row_number, fields in enumerate(reader, 2):
        if len(fields) != 2:
            raise PlanError(f"plan row {row_number} must contain exactly two columns")
        source_url, target_path = fields
        if not is_http_url(source_url):
            raise PlanError(f"plan row {row_number} has an invalid HTTP(S) URL")
        if any(token in source_url or token in target_path for token in ("<", ">", "{", "}")):
            raise PlanError(f"plan row {row_number} contains an unresolved placeholder")
        relative = PurePosixPath(target_path)
        if not target_path or relative.is_absolute() or ".." in relative.parts:
            raise PlanError(f"plan row {row_number} has an unsafe target path")
        if "artifacts" not in relative.parts or relative.parts[-1] == "artifacts":
            raise PlanError(f"plan row {row_number} target is not under an artifacts directory")
        if target_path in seen_targets:
            raise PlanError(f"plan row {row_number} duplicates target_path {target_path}")
        seen_targets.add(target_path)
        target = data_root / Path(*relative.parts)
        try:
            target.resolve(strict=False).relative_to(root_resolved)
        except ValueError as exc:
            raise PlanError(f"plan row {row_number} escapes the data root") from exc
        rows.append(PlanRow(row_number, source_url, target_path, target))
    if not rows:
        raise PlanError("acquisition plan contains no download rows")
    return rows


def load_plan(plan_path: Path, data_root: Path) -> tuple[list[PlanRow], str]:
    plan_bytes = plan_path.read_bytes()
    return parse_plan_bytes(plan_bytes, data_root), hashlib.sha256(plan_bytes).hexdigest()


def parse_plan(plan_path: Path, data_root: Path) -> list[PlanRow]:
    return load_plan(plan_path, data_root)[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        length = int(value)
    except ValueError as exc:
        raise DownloadError(f"invalid Content-Length header: {value}") from exc
    if length < 0:
        raise DownloadError(f"negative Content-Length header: {value}")
    return length


def parse_content_range(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    match = re.fullmatch(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)", value.strip())
    if not match:
        raise DownloadError(f"invalid Content-Range header: {value}")
    start, end, total = (int(part) for part in match.groups())
    if start > end or end >= total:
        raise DownloadError(f"inconsistent Content-Range header: {value}")
    return start, end, total


def response_is_html(content_type: str, first_block: bytes, target: Path) -> bool:
    if target.suffix.lower() in {".html", ".htm"}:
        return False
    if "text/html" in content_type.lower() or "application/xhtml" in content_type.lower():
        return True
    prefix = first_block[:512].lstrip().lower()
    return prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")


def load_cookie_jar(cookie_file: Path) -> MozillaCookieJar:
    if cookie_file.is_symlink() or not cookie_file.is_file():
        raise DownloadError("cookie file must be a regular file and not a symlink")
    if cookie_file.stat().st_mode & 0o077:
        raise DownloadError("cookie file permissions must be 0600 or stricter")
    jar = MozillaCookieJar(str(cookie_file))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except (LoadError, OSError) as exc:
        raise DownloadError(f"cannot load Netscape cookie file: {exc}") from exc
    cookies = list(jar)
    if not cookies:
        raise DownloadError("cookie file contains no cookies")
    def is_cngb_domain(domain: str) -> bool:
        normalized = domain.lstrip(".").lower()
        return normalized == "cngb.org" or normalized.endswith(".cngb.org")

    invalid_domain = next((cookie.domain for cookie in cookies if not is_cngb_domain(cookie.domain)), None)
    if invalid_domain is not None:
        raise DownloadError(f"cookie file contains a non-CNGB domain: {invalid_domain}")
    return jar


def open_request(row: PlanRow, headers: dict[str, str], timeout: float, cookie_file: Path | None):
    request = Request(row.source_url, headers=headers)
    opener = build_opener()
    if cookie_file is not None:
        opener = build_opener(HTTPCookieProcessor(load_cookie_jar(cookie_file)))
    try:
        return opener.open(request, timeout=timeout)
    except HTTPError as exc:
        raise DownloadError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise DownloadError(f"transport error: {exc.reason}") from exc


def open_response(row: PlanRow, offset: int, timeout: float, cookie_file: Path | None = None):
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    try:
        return open_request(row, headers, timeout, cookie_file)
    except DownloadError as exc:
        cause = exc.__cause__
        if isinstance(cause, HTTPError) and cause.code == 416 and offset:
            total_match = re.fullmatch(r"bytes \*/([0-9]+)", cause.headers.get("Content-Range", "").strip())
            if total_match and int(total_match.group(1)) == offset:
                return None
        raise


def probe_row(row: PlanRow, config: DownloadConfig, logger: JsonlLogger) -> None:
    logger.emit("probe_started", row=row, authenticated_session=config.cookie_file is not None)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "identity",
        "Range": "bytes=0-0",
    }
    with open_request(row, headers, config.timeout, config.cookie_file) as response:
        status = getattr(response, "status", response.getcode())
        if status not in {200, 206}:
            raise DownloadError(f"unexpected HTTP status {status}")
        content_encoding = response.headers.get("Content-Encoding", "identity").lower()
        if content_encoding not in {"", "identity"}:
            raise DownloadError(f"unsupported Content-Encoding: {content_encoding}")
        first_block = response.read(512)
        if response_is_html(response.headers.get("Content-Type", ""), first_block, row.target):
            raise DownloadError("HTML response rejected for non-HTML target")
        logger.emit(
            "probe_completed",
            row=row,
            http_status=status,
            content_type=response.headers.get("Content-Type", ""),
            bytes_inspected=len(first_block),
        )


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def part_metadata_path(part: Path) -> Path:
    return part.with_name(part.name + ".json")


def load_part_metadata(path: Path) -> RemoteIdentity:
    if path.is_symlink() or not path.is_file():
        raise DownloadError("partial metadata is missing or not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DownloadError("partial metadata is unreadable or invalid JSON") from exc
    if not isinstance(value, dict):
        raise DownloadError("partial metadata must be a JSON object")
    required = {"source_url", "final_url", "etag", "last_modified", "total_size"}
    if not required.issubset(value):
        raise DownloadError("partial metadata is missing required identity fields")
    if not isinstance(value["source_url"], str) or not is_http_url(value["source_url"]):
        raise DownloadError("partial metadata source_url is invalid")
    if not isinstance(value["final_url"], str) or not is_http_url(value["final_url"]):
        raise DownloadError("partial metadata final_url is invalid")
    for field in ("etag", "last_modified"):
        if value[field] is not None and not isinstance(value[field], str):
            raise DownloadError(f"partial metadata {field} is invalid")
    total_size = value["total_size"]
    if total_size is not None and (type(total_size) is not int or total_size < 0):
        raise DownloadError("partial metadata total_size is invalid")
    return RemoteIdentity(
        source_url=value["source_url"],
        final_url=value["final_url"],
        etag=value["etag"],
        last_modified=value["last_modified"],
        total_size=total_size,
    )


def write_part_metadata(path: Path, identity: RemoteIdentity) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(identity.as_dict(), handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def remove_state_file(path: Path, description: str) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        raise DownloadError(f"{description} is not a regular file")


def discard_partial(part: Path, metadata: Path) -> None:
    remove_state_file(part, "partial target")
    remove_state_file(metadata, "partial metadata")
    fsync_directory(part.parent)


def response_identity(
    row: PlanRow,
    response: Any,
    status: int,
    content_range: tuple[int, int, int] | None,
    content_length: int | None,
) -> RemoteIdentity:
    total_size = content_range[2] if content_range is not None else content_length
    final_url = urlparse(response.geturl())._replace(query="", fragment="").geturl()
    return RemoteIdentity(
        source_url=row.source_url,
        # Redirect queries may contain short-lived signatures and are not durable identity.
        final_url=final_url,
        etag=response.headers.get("ETag"),
        last_modified=response.headers.get("Last-Modified"),
        total_size=total_size,
    )


def probe_remote_identity(row: PlanRow, config: DownloadConfig) -> RemoteIdentity:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "identity",
        "Range": "bytes=0-0",
    }
    with open_request(row, headers, config.timeout, config.cookie_file) as response:
        status = getattr(response, "status", response.getcode())
        if status not in {200, 206}:
            raise DownloadError(f"unexpected HTTP status {status} during resume probe")
        content_encoding = response.headers.get("Content-Encoding", "identity").lower()
        if content_encoding not in {"", "identity"}:
            raise DownloadError(f"unsupported Content-Encoding: {content_encoding}")
        content_range = parse_content_range(response.headers.get("Content-Range"))
        if status == 206 and (content_range is None or content_range[0] != 0):
            raise DownloadError("resume probe returned an invalid partial response")
        content_length = parse_content_length(response.headers.get("Content-Length"))
        first_block = response.read(512)
        if response_is_html(response.headers.get("Content-Type", ""), first_block, row.target):
            raise DownloadError("HTML response rejected for non-HTML target")
        return response_identity(row, response, status, content_range, content_length)


def finalize_part(row: PlanRow, part: Path, metadata: Path) -> DownloadResult:
    size = part.stat().st_size
    digest = sha256_file(part)
    os.replace(part, row.target)
    remove_state_file(metadata, "partial metadata")
    fsync_directory(row.target.parent)
    return DownloadResult(row.row_number, "downloaded", row.target_path, size, digest)


def download_attempt(row: PlanRow, config: DownloadConfig, logger: JsonlLogger) -> DownloadResult:
    target = row.target
    part = target.with_name(target.name + ".part")
    metadata_path = part_metadata_path(part)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise DownloadError("existing target is not a regular file")
        if not config.overwrite:
            size = target.stat().st_size
            logger.emit("download_skipped", row=row, reason="existing_final_file", size_bytes=size)
            return DownloadResult(row.row_number, "skipped", row.target_path, size, None)
    resume_identity: RemoteIdentity | None = None
    if part.exists() or part.is_symlink():
        if part.is_symlink() or not part.is_file():
            raise DownloadError("partial target is not a regular file")
        try:
            stored_identity = load_part_metadata(metadata_path)
        except DownloadError as exc:
            discard_partial(part, metadata_path)
            logger.emit("range_restarted", row=row, reason="invalid_partial_metadata", error=str(exc))
            offset = 0
        else:
            if stored_identity.source_url != row.source_url:
                discard_partial(part, metadata_path)
                logger.emit("range_restarted", row=row, reason="source_url_changed")
                offset = 0
            else:
                current_identity = probe_remote_identity(row, config)
                offset = part.stat().st_size
                if stored_identity != current_identity:
                    discard_partial(part, metadata_path)
                    logger.emit("range_restarted", row=row, reason="remote_identity_changed")
                    offset = 0
                elif current_identity.total_size is not None and offset > current_identity.total_size:
                    discard_partial(part, metadata_path)
                    logger.emit("range_restarted", row=row, reason="partial_size_exceeds_total")
                    offset = 0
                elif current_identity.total_size is not None and offset == current_identity.total_size:
                    result = finalize_part(row, part, metadata_path)
                    logger.emit(
                        "download_completed", row=row, size_bytes=result.size_bytes, sha256=result.sha256
                    )
                    return result
                else:
                    resume_identity = current_identity
    else:
        offset = 0
        remove_state_file(metadata_path, "orphaned partial metadata")

    logger.emit("download_started", row=row, resume_offset=offset)
    response = open_response(row, offset, config.timeout, config.cookie_file)
    if response is None:
        discard_partial(part, metadata_path)
        logger.emit("range_restarted", row=row, reason="range_not_satisfiable", resume_offset=offset)
        return download_fresh(row, part, config, logger)

    with response:
        status = getattr(response, "status", response.getcode())
        content_range = parse_content_range(response.headers.get("Content-Range"))
        content_length = parse_content_length(response.headers.get("Content-Length"))
        actual_identity = response_identity(row, response, status, content_range, content_length)
        if resume_identity is not None and actual_identity != resume_identity:
            response.close()
            discard_partial(part, metadata_path)
            logger.emit("range_restarted", row=row, reason="remote_identity_changed_during_resume")
            return download_fresh(row, part, config, logger)
        write_offset = offset
        if offset and status == 206:
            if content_range is None or content_range[0] != offset:
                response.close()
                logger.emit("range_restarted", row=row, reason="misreported_content_range", resume_offset=offset)
                return download_fresh(row, part, config, logger)
        elif offset and status == 200:
            write_offset = 0
            logger.emit("range_restarted", row=row, reason="server_ignored_range", resume_offset=offset)
        elif not offset and status == 206:
            if content_range is None or content_range[0] != 0:
                raise DownloadError("unexpected partial response for a fresh download")
        elif status != 200:
            raise DownloadError(f"unexpected HTTP status {status}")

        content_encoding = response.headers.get("Content-Encoding", "identity").lower()
        if content_encoding not in {"", "identity"}:
            raise DownloadError(f"unsupported Content-Encoding: {content_encoding}")
        first_block = response.read(CHUNK_SIZE)
        if response_is_html(response.headers.get("Content-Type", ""), first_block, target):
            raise DownloadError("HTML response rejected for non-HTML target")

        write_part_metadata(metadata_path, actual_identity)
        bytes_received = 0
        mode = "ab" if write_offset else "wb"
        with part.open(mode) as handle:
            for block in chain((first_block,), iter(lambda: response.read(CHUNK_SIZE), b"")):
                if not block:
                    continue
                handle.write(block)
                bytes_received += len(block)
            handle.flush()
            os.fsync(handle.fileno())
        if content_length is not None and bytes_received != content_length:
            raise DownloadError(
                f"response length mismatch: expected {content_length}, received {bytes_received}"
            )
        if content_range is not None and bytes_received != content_range[1] - content_range[0] + 1:
            raise DownloadError("response length does not match Content-Range")
        if content_range is not None and part.stat().st_size != content_range[2]:
            raise DownloadError(
                f"completed size mismatch: expected {content_range[2]}, found {part.stat().st_size}"
            )

    result = finalize_part(row, part, metadata_path)
    logger.emit("download_completed", row=row, size_bytes=result.size_bytes, sha256=result.sha256)
    return result


def download_fresh(row: PlanRow, part: Path, config: DownloadConfig, logger: JsonlLogger) -> DownloadResult:
    metadata_path = part_metadata_path(part)
    if part.exists() and (part.is_symlink() or not part.is_file()):
        raise DownloadError("partial target is not a regular file")
    with open_response(row, 0, config.timeout, config.cookie_file) as response:
        status = getattr(response, "status", response.getcode())
        if status not in {200, 206}:
            raise DownloadError(f"unexpected HTTP status {status}")
        content_range = parse_content_range(response.headers.get("Content-Range"))
        if content_range is not None and content_range[0] != 0:
            raise DownloadError("fresh response starts at a nonzero offset")
        content_encoding = response.headers.get("Content-Encoding", "identity").lower()
        if content_encoding not in {"", "identity"}:
            raise DownloadError(f"unsupported Content-Encoding: {content_encoding}")
        content_length = parse_content_length(response.headers.get("Content-Length"))
        identity = response_identity(row, response, status, content_range, content_length)
        first_block = response.read(CHUNK_SIZE)
        if response_is_html(response.headers.get("Content-Type", ""), first_block, row.target):
            raise DownloadError("HTML response rejected for non-HTML target")
        write_part_metadata(metadata_path, identity)
        received = 0
        with part.open("wb") as handle:
            for block in chain((first_block,), iter(lambda: response.read(CHUNK_SIZE), b"")):
                if not block:
                    continue
                handle.write(block)
                received += len(block)
            handle.flush()
            os.fsync(handle.fileno())
        if content_length is not None and received != content_length:
            raise DownloadError(f"response length mismatch: expected {content_length}, received {received}")
        if content_range is not None and received != content_range[1] - content_range[0] + 1:
            raise DownloadError("response length does not match Content-Range")
        if content_range is not None and part.stat().st_size != content_range[2]:
            raise DownloadError(
                f"completed size mismatch: expected {content_range[2]}, found {part.stat().st_size}"
            )
    result = finalize_part(row, part, metadata_path)
    logger.emit("download_completed", row=row, size_bytes=result.size_bytes, sha256=result.sha256)
    return result


def download_row(row: PlanRow, config: DownloadConfig, logger: JsonlLogger) -> DownloadResult:
    for attempt in range(config.retries + 1):
        try:
            return download_attempt(row, config, logger)
        except (DownloadError, HTTPException, OSError) as exc:
            if attempt >= config.retries:
                if isinstance(exc, DownloadError):
                    raise
                raise DownloadError(str(exc)) from exc
            delay = config.retry_backoff * (2**attempt)
            logger.emit(
                "download_retry",
                level="warning",
                row=row,
                attempt=attempt + 1,
                delay_seconds=delay,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            if delay:
                time.sleep(delay)
    raise AssertionError("retry loop terminated unexpectedly")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--workers", type=positive_int, default=4)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=nonnegative_int, default=3)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="test one selected URL without writing an artifact",
    )
    parser.add_argument(
        "--cookie-file",
        type=Path,
        help="0600 Netscape cookie file containing only cngb.org cookies",
    )
    parser.add_argument(
        "--target-path",
        action="append",
        default=[],
        help="download only this exact target_path; may be repeated",
    )
    args = parser.parse_args()
    if args.timeout <= 0 or args.retry_backoff < 0:
        parser.error("timeout must be positive and retry-backoff must be nonnegative")
    if args.validate_only and args.probe_only:
        parser.error("--validate-only and --probe-only are mutually exclusive")

    logger = JsonlLogger(sys.stdout)
    try:
        rows, plan_sha256 = load_plan(args.plan, args.data_root)
    except (OSError, PlanError, csv.Error) as exc:
        logger.emit("plan_invalid", level="error", error_type=type(exc).__name__, error=str(exc))
        return 2
    requested_targets = set(args.target_path)
    if len(requested_targets) != len(args.target_path):
        logger.emit(
            "plan_invalid",
            level="error",
            error_type="PlanError",
            error="duplicate --target-path value",
        )
        return 2
    rows_by_target = {row.target_path: row for row in rows}
    unknown_targets = sorted(requested_targets - rows_by_target.keys())
    if unknown_targets:
        logger.emit(
            "plan_invalid",
            level="error",
            error_type="PlanError",
            error=f"unknown --target-path value: {unknown_targets[0]}",
        )
        return 2
    selected_rows = [row for row in rows if not requested_targets or row.target_path in requested_targets]
    if args.probe_only and len(selected_rows) != 1:
        logger.emit(
            "plan_invalid",
            level="error",
            error_type="PlanError",
            error="--probe-only requires exactly one --target-path",
        )
        return 2
    if args.cookie_file is not None:
        try:
            load_cookie_jar(args.cookie_file)
        except DownloadError as exc:
            logger.emit(
                "authentication_invalid",
                level="error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return 2
    logger.emit(
        "plan_validated",
        plan_path=str(args.plan),
        plan_sha256=plan_sha256,
        data_root=str(args.data_root),
        row_count=len(rows),
        validate_only=args.validate_only,
        workers=args.workers,
        timeout_seconds=args.timeout,
        retries=args.retries,
        retry_backoff_seconds=args.retry_backoff,
        overwrite=args.overwrite,
        selected_row_count=len(selected_rows),
        probe_only=args.probe_only,
        authenticated_session=args.cookie_file is not None,
    )
    if args.validate_only:
        return 0

    config = DownloadConfig(
        args.overwrite,
        args.timeout,
        args.retries,
        args.retry_backoff,
        args.cookie_file,
    )
    if args.probe_only:
        row = selected_rows[0]
        try:
            probe_row(row, config, logger)
        except (DownloadError, HTTPException, OSError) as exc:
            logger.emit(
                "probe_failed",
                level="error",
                row=row,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return 1
        return 0
    results: list[DownloadResult] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="stomicsdb-download") as executor:
        futures: dict[Future[DownloadResult], PlanRow] = {
            executor.submit(download_row, row, config, logger): row for row in selected_rows
        }
        for future in as_completed(futures):
            row = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures += 1
                logger.emit(
                    "download_failed",
                    level="error",
                    row=row,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
    status_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
    logger.emit(
        "run_completed",
        row_count=len(selected_rows),
        plan_row_count=len(rows),
        completed_count=len(results),
        failure_count=failures,
        status_counts=dict(sorted(status_counts.items())),
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
