from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib.util
from io import StringIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Thread
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stomicsdb_round2_download.py"
SPEC = importlib.util.spec_from_file_location("stomicsdb_round2_download", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
downloader = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = downloader
SPEC.loader.exec_module(downloader)


class FileHandler(BaseHTTPRequestHandler):
    data = b"abcdefghij"
    ignore_range = False
    content_type = "application/octet-stream"
    ranges: list[str | None] = []
    required_cookie: str | None = None
    etag = '"test-etag"'
    last_modified = "Thu, 23 Jul 2026 00:00:00 GMT"

    def do_GET(self) -> None:
        if self.required_cookie is not None and self.headers.get("Cookie") != self.required_cookie:
            self.send_error(403)
            return
        requested_range = self.headers.get("Range")
        type(self).ranges.append(requested_range)
        start = 0
        end = len(self.data) - 1
        status = 200
        if requested_range and not self.ignore_range:
            range_value = requested_range.removeprefix("bytes=")
            start_text, end_text = range_value.split("-", 1)
            start = int(start_text)
            if end_text:
                end = int(end_text)
            status = 206
        body = self.data[start : end + 1]
        self.send_response(status)
        self.send_header("Content-Type", self.content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", self.etag)
        self.send_header("Last-Modified", self.last_modified)
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(self.data)}")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def file_server(
    *,
    ignore_range: bool = False,
    content_type: str = "application/octet-stream",
    required_cookie: str | None = None,
):
    handler = type(
        "ConfiguredFileHandler",
        (FileHandler,),
        {
            "ignore_range": ignore_range,
            "content_type": content_type,
            "ranges": [],
            "required_cookie": required_cookie,
        },
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/file", handler
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def plan_row(tmp_path: Path, url: str) -> object:
    root = tmp_path / "data"
    target = "raw_data/public_database/stomicsdb/datasets/STDS0000001/bundles/b/artifacts/data.h5ad"
    return downloader.PlanRow(2, url, target, root / target)


def config() -> object:
    return downloader.DownloadConfig(overwrite=False, timeout=5.0, retries=0, retry_backoff=0.0)


def write_resume_state(row: object, url: str, data: bytes) -> None:
    row.target.parent.mkdir(parents=True, exist_ok=True)
    part = row.target.with_name(row.target.name + ".part")
    part.write_bytes(data)
    downloader.write_part_metadata(
        downloader.part_metadata_path(part),
        downloader.RemoteIdentity(
            source_url=url,
            final_url=url,
            etag=FileHandler.etag,
            last_modified=FileHandler.last_modified,
            total_size=len(FileHandler.data),
        ),
    )


def test_parse_plan_validates_contract_and_containment(tmp_path: Path) -> None:
    root = tmp_path / "data"
    plan = tmp_path / "plan.tsv"
    target = "raw_data/public_database/stomicsdb/datasets/STDS0000001/bundles/b/artifacts/data.h5ad"
    plan.write_text(f"source_url\ttarget_path\nhttps://example.org/data.h5ad\t{target}\n")

    rows = downloader.parse_plan(plan, root)

    assert len(rows) == 1
    assert rows[0].target_path == target
    assert rows[0].target == root / target


def test_parse_plan_rejects_target_traversal(tmp_path: Path) -> None:
    plan = tmp_path / "plan.tsv"
    plan.write_text(
        "source_url\ttarget_path\n"
        "https://example.org/data.h5ad\t../artifacts/data.h5ad\n"
    )

    with pytest.raises(downloader.PlanError, match="unsafe target path"):
        downloader.parse_plan(plan, tmp_path / "data")


def test_response_identity_does_not_persist_redirect_query() -> None:
    class Response:
        headers = {"ETag": '"etag"', "Last-Modified": "today"}

        @staticmethod
        def geturl() -> str:
            return "https://objects.example.org/file?X-Amz-Signature=secret#fragment"

    row = downloader.PlanRow(2, "https://example.org/file", "target", Path("target"))

    identity = downloader.response_identity(row, Response(), 200, None, 10)

    assert identity.final_url == "https://objects.example.org/file"


def test_existing_final_file_is_skipped_without_network(tmp_path: Path) -> None:
    row = plan_row(tmp_path, "http://127.0.0.1:1/unreachable")
    row.target.parent.mkdir(parents=True)
    row.target.write_bytes(b"complete")

    result = downloader.download_row(row, config(), downloader.JsonlLogger(StringIO()))

    assert result.status == "skipped"
    assert row.target.read_bytes() == b"complete"


def test_validate_only_logs_plan_identity_and_runtime_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "data"
    plan = tmp_path / "plan.tsv"
    target = "raw_data/public_database/stomicsdb/datasets/STDS0000001/bundles/b/artifacts/data.h5ad"
    plan.write_text(f"source_url\ttarget_path\nhttps://example.org/data.h5ad\t{target}\n")
    output = StringIO()
    monkeypatch.setattr(downloader.sys, "stdout", output)
    monkeypatch.setattr(
        downloader.sys,
        "argv",
        [
            "stomicsdb_round2_download.py",
            "--plan",
            str(plan),
            "--data-root",
            str(root),
            "--workers",
            "3",
            "--validate-only",
        ],
    )

    assert downloader.main() == 0
    event = json.loads(output.getvalue())
    assert event["event"] == "plan_validated"
    assert event["plan_sha256"] == hashlib.sha256(plan.read_bytes()).hexdigest()
    assert event["row_count"] == 1
    assert event["workers"] == 3
    assert event["validate_only"] is True
    assert event["selected_row_count"] == 1


def test_target_path_filter_rejects_unknown_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "data"
    plan = tmp_path / "plan.tsv"
    target = "raw_data/public_database/stomicsdb/datasets/STDS0000001/bundles/b/artifacts/data.h5ad"
    plan.write_text(f"source_url\ttarget_path\nhttps://example.org/data.h5ad\t{target}\n")
    output = StringIO()
    monkeypatch.setattr(downloader.sys, "stdout", output)
    monkeypatch.setattr(
        downloader.sys,
        "argv",
        [
            "stomicsdb_round2_download.py",
            "--plan",
            str(plan),
            "--data-root",
            str(root),
            "--target-path",
            "raw_data/public_database/stomicsdb/datasets/STDS0000001/bundles/b/artifacts/missing.h5ad",
            "--validate-only",
        ],
    )

    assert downloader.main() == 2
    event = json.loads(output.getvalue())
    assert event["event"] == "plan_invalid"
    assert "unknown --target-path" in event["error"]


def test_resume_uses_range_and_atomically_finishes(tmp_path: Path) -> None:
    with file_server() as (url, handler):
        row = plan_row(tmp_path, url)
        write_resume_state(row, url, handler.data[:3])

        result = downloader.download_row(row, config(), downloader.JsonlLogger(StringIO()))

    assert result.status == "downloaded"
    assert row.target.read_bytes() == handler.data
    assert not row.target.with_name(row.target.name + ".part").exists()
    assert not downloader.part_metadata_path(
        row.target.with_name(row.target.name + ".part")
    ).exists()
    assert handler.ranges == ["bytes=0-0", "bytes=3-"]


def test_server_ignoring_range_restarts_from_zero(tmp_path: Path) -> None:
    with file_server(ignore_range=True) as (url, handler):
        row = plan_row(tmp_path, url)
        write_resume_state(row, url, b"old")

        downloader.download_row(row, config(), downloader.JsonlLogger(StringIO()))

    assert row.target.read_bytes() == handler.data
    assert handler.ranges == ["bytes=0-0", "bytes=3-"]


@pytest.mark.parametrize("metadata_contents", [None, "not-json"])
def test_missing_or_corrupt_partial_metadata_restarts_from_zero(
    tmp_path: Path, metadata_contents: str | None
) -> None:
    with file_server() as (url, handler):
        row = plan_row(tmp_path, url)
        row.target.parent.mkdir(parents=True)
        part = row.target.with_name(row.target.name + ".part")
        part.write_bytes(b"stale")
        metadata = downloader.part_metadata_path(part)
        if metadata_contents is not None:
            metadata.write_text(metadata_contents)

        downloader.download_row(row, config(), downloader.JsonlLogger(StringIO()))

    assert row.target.read_bytes() == handler.data
    assert handler.ranges == [None]
    assert not metadata.exists()


def test_changed_remote_identity_restarts_from_zero(tmp_path: Path) -> None:
    with file_server() as (url, handler):
        row = plan_row(tmp_path, url)
        write_resume_state(row, url, b"stale")
        metadata = downloader.part_metadata_path(row.target.with_name(row.target.name + ".part"))
        stored = json.loads(metadata.read_text())
        stored["etag"] = '"old-etag"'
        metadata.write_text(json.dumps(stored))

        downloader.download_row(row, config(), downloader.JsonlLogger(StringIO()))

    assert row.target.read_bytes() == handler.data
    assert handler.ranges == ["bytes=0-0", None]
    assert not metadata.exists()


def test_launcher_rejects_concurrent_run_for_same_plan(tmp_path: Path) -> None:
    launcher = SCRIPT.with_name("start_stomicsdb_round2_download.sh")
    data_root = tmp_path / "data"
    log_dir = data_root / "logs"
    plan = tmp_path / "plan.tsv"
    plan.write_text("source_url\ttarget_path\n")
    started = tmp_path / "started"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "for arg in \"$@\"; do\n"
        "  if [[ \"$arg\" == \"--validate-only\" ]]; then exit 0; fi\n"
        "done\n"
        "printf '%s\\n' \"$$\" > \"${FAKE_STARTED}\"\n"
        "exec sleep 30\n"
    )
    fake_python.chmod(0o755)
    environment = {
        **os.environ,
        "HYPOTRACE_DATA_ROOT": str(data_root),
        "STOMICSDB_ACQUISITION_PLAN": str(plan),
        "STOMICSDB_DOWNLOAD_LOG_DIR": str(log_dir),
        "PYTHON_BIN": str(fake_python),
        "FAKE_STARTED": str(started),
    }

    first = subprocess.run([str(launcher)], env=environment, text=True, capture_output=True, check=True)
    pid = int(first.stdout.split("pid=", 1)[1].split()[0])
    try:
        deadline = time.monotonic() + 5
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert started.exists()

        second = subprocess.run([str(launcher)], env=environment, text=True, capture_output=True)

        assert second.returncode == 1
        assert "download already running for plan=" in second.stderr
        assert list(log_dir.glob("*.lock"))
    finally:
        os.killpg(pid, signal.SIGTERM)


def test_html_error_response_is_rejected_for_data_target(tmp_path: Path) -> None:
    with file_server(content_type="text/html") as (url, _handler):
        row = plan_row(tmp_path, url)

        with pytest.raises(downloader.DownloadError, match="HTML response"):
            downloader.download_row(row, config(), downloader.JsonlLogger(StringIO()))

    assert not row.target.exists()


def test_cookie_file_authenticates_without_logging_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "session=secret-value"
    with file_server(required_cookie=secret) as (url, _handler):
        row = plan_row(tmp_path, url)
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text(
            "# Netscape HTTP Cookie File\n"
            "127.0.0.1\tFALSE\t/\tFALSE\t0\tsession\tsecret-value\n"
        )
        os.chmod(cookie_file, 0o600)
        class StaticCookieJar:
            def add_cookie_header(self, request: object) -> None:
                request.add_unredirected_header("Cookie", secret)

            def extract_cookies(self, response: object, request: object) -> None:
                return

        monkeypatch.setattr(downloader, "load_cookie_jar", lambda _path: StaticCookieJar())
        output = StringIO()
        authenticated = downloader.DownloadConfig(False, 5.0, 0, 0.0, cookie_file)

        result = downloader.download_row(row, authenticated, downloader.JsonlLogger(output))

    assert result.status == "downloaded"
    assert row.target.read_bytes() == FileHandler.data
    assert "secret-value" not in output.getvalue()


def test_probe_only_does_not_write_artifact(tmp_path: Path) -> None:
    with file_server() as (url, _handler):
        row = plan_row(tmp_path, url)
        output = StringIO()

        downloader.probe_row(row, config(), downloader.JsonlLogger(output))

    assert not row.target.exists()
    assert json.loads(output.getvalue().splitlines()[-1])["event"] == "probe_completed"


def test_cookie_file_rejects_non_cngb_domain(tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".example.org\tTRUE\t/\tTRUE\t0\tsession\tsecret-value\n"
    )
    os.chmod(cookie_file, 0o600)

    with pytest.raises(downloader.DownloadError, match="non-CNGB domain"):
        downloader.load_cookie_jar(cookie_file)


def test_cookie_file_rejects_lookalike_cngb_domain(tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".notcngb.org\tTRUE\t/\tTRUE\t0\tsession\tsecret-value\n"
    )
    os.chmod(cookie_file, 0o600)

    with pytest.raises(downloader.DownloadError, match="non-CNGB domain"):
        downloader.load_cookie_jar(cookie_file)


def test_cookie_file_accepts_only_cngb_domains(tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".cngb.org\tTRUE\t/\tTRUE\t0\tsession\tredacted\n"
        "#HttpOnly_db.cngb.org\tFALSE\t/\tTRUE\t0\tauth\tredacted\n"
    )
    os.chmod(cookie_file, 0o600)

    jar = downloader.load_cookie_jar(cookie_file)

    assert sorted(cookie.domain for cookie in jar) == [".cngb.org", "db.cngb.org"]
