#!/usr/bin/env python3
"""Validate and atomically publish STOmicsDB case-derived dual chains."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any, Callable, Iterable

import yaml

try:
    import jsonschema
except ModuleNotFoundError:  # The coordinator has an equivalent built-in validator.
    jsonschema = None


DEFAULT_DATA_ROOT = Path("/mnt/NAS_21T/ProjectData/HypoTrace_Data")
STOMICS_REL = PurePosixPath("raw_data/public_database/stomicsdb")
CASE_FILENAMES = (
    PurePosixPath("case_manifest.yaml"),
    PurePosixPath("source_manifest.yaml"),
    PurePosixPath("data/case_data_manifest.yaml"),
)
EXTRACTION_FILENAMES = (
    "chain_manifest.yaml",
    "execution_subchains.jsonl",
    "scientific_chain.jsonl",
)
FINAL_FILENAMES = EXTRACTION_FILENAMES + ("independent_check.md",)
REVIEW_FILENAMES = ("chain_manifest.yaml", "independent_check.md")
MAX_REVISION_ROUNDS = 2
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
MAX_IDENTIFIER_LENGTH = 128
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
STDS_PATTERN = re.compile(r"STDS[0-9]{7}\Z")
PLACEHOLDER_PATTERN = re.compile(
    r"<[A-Za-z][A-Za-z0-9_. -]{1,80}>|\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b",
    re.IGNORECASE,
)
EXTERNAL_AUXILIARY_IDENTITY_FIELDS = (
    "resource_name",
    "expected_content",
    "source_url",
    "access_classification",
    "access_notes",
)


class CoordinatorError(RuntimeError):
    """A stable validation or publication boundary failure."""


class ReadinessError(CoordinatorError):
    """A structurally valid candidate is not yet downstream DATA_READY."""


class HandoffError(CoordinatorError):
    """The admitted Round 3 candidate is internally contradictory."""


def require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CoordinatorError(f"{context} must be a mapping")
    return value


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise CoordinatorError(f"{context} must be a list")
    return value


def require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise CoordinatorError(f"{context} must be a nonempty string")
    return value


def external_auxiliary_identity(resource: dict[str, Any]) -> dict[str, str]:
    """Return the exact case-declared identity of one unresolved Axx input."""
    resource_id = require_string(resource.get("resource_id"), "auxiliary resource_id")
    if resource.get("local_availability") != "absent":
        raise CoordinatorError(f"{resource_id} is not an absent auxiliary resource")
    if resource.get("localization_binding") is not None:
        raise CoordinatorError(f"{resource_id} absent resource has a localization binding")
    return {
        field: require_string(resource.get(field), f"{resource_id}.{field}")
        for field in EXTERNAL_AUXILIARY_IDENTITY_FIELDS
    }


def external_auxiliary_readiness_errors(context: dict[str, Any]) -> list[str]:
    return [
        f"{resource_id} is not localized (local_availability: absent)"
        for resource_id in context["unresolved_auxiliary_ids"]
    ]


def assignment_supports_specification_extraction(assignment: dict[str, Any]) -> bool:
    return (
        assignment.get("data_readiness") == "BLOCKED_EXTERNAL"
        and bool(assignment.get("unresolved_auxiliary_resource_ids"))
        and "used_data_object_ids" in assignment
        and "used_auxiliary_resource_ids" in assignment
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise CoordinatorError(f"cannot read {path}: {error}") from error
    return digest.hexdigest()


HashCache = dict[Path, tuple[int, int, int, int, str]]


def _sha256_cached(path: Path, cache: HashCache | None) -> str:
    try:
        stat = path.stat()
    except OSError as error:
        raise ReadinessError(f"cannot stat required input {path}: {error}") from error
    identity = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if cache is not None and path in cache and cache[path][:4] == identity:
        return cache[path][4]
    value = sha256_path(path)
    if cache is not None:
        cache[path] = (*identity, value)
    return value


def chain_id(case_id: str, candidate_id: str) -> str:
    value = hashlib.sha256(f"{case_id}\n{candidate_id}".encode("utf-8")).hexdigest()
    return f"chain_sha256_{value[:16]}"


def data_relative(path: Path, data_root: Path) -> str:
    try:
        return path.resolve().relative_to(data_root.resolve()).as_posix()
    except ValueError as error:
        raise CoordinatorError(f"path is outside data root: {path}") from error


def resolve_data_path(value: str, data_root: Path) -> Path:
    relative = PurePosixPath(require_string(value, "data-root-relative path"))
    if relative.is_absolute() or ".." in relative.parts:
        raise CoordinatorError(f"unsafe data-root-relative path: {value}")
    path = data_root.joinpath(*relative.parts)
    try:
        path.resolve().relative_to(data_root.resolve())
    except ValueError as error:
        raise CoordinatorError(f"path escapes data root: {value}") from error
    return path


def load_yaml(path: Path, wrapper: str | None = None) -> dict[str, Any]:
    try:
        content = path.read_bytes()
    except (OSError, yaml.YAMLError) as error:
        raise CoordinatorError(f"cannot parse YAML {path}: {error}") from error
    return load_yaml_bytes(content, str(path), wrapper)


def load_yaml_bytes(
    content: bytes, context: str, wrapper: str | None = None
) -> dict[str, Any]:
    try:
        value = require_mapping(yaml.safe_load(content), context)
    except yaml.YAMLError as error:
        raise CoordinatorError(f"cannot parse YAML {context}: {error}") from error
    if wrapper is not None:
        value = require_mapping(value.get(wrapper), f"{context}:{wrapper}")
    return value


def dump_yaml(value: Any) -> bytes:
    return yaml.safe_dump(
        value, allow_unicode=False, sort_keys=False, width=1_000_000
    ).encode("utf-8")


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_yaml(path: Path, value: Any) -> None:
    atomic_write(path, dump_yaml(value))


def exact_files(directory: Path, expected: Iterable[str]) -> None:
    if not directory.is_dir() or directory.is_symlink():
        raise CoordinatorError(f"invalid directory: {directory}")
    items = list(directory.rglob("*"))
    if any(not item.is_file() or item.is_symlink() for item in items):
        invalid = [item.relative_to(directory).as_posix() for item in items if not item.is_file() or item.is_symlink()]
        raise CoordinatorError(f"non-regular entries in {directory}: {invalid}")
    actual = sorted(item.relative_to(directory).as_posix() for item in items)
    wanted = sorted(expected)
    if actual != wanted:
        raise CoordinatorError(f"unexpected files in {directory}: {actual}; expected {wanted}")
    for name in wanted:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise CoordinatorError(f"chain file must be a regular file: {path}")


def unique_index(records: list[Any], field: str, context: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for raw in records:
        record = require_mapping(raw, context)
        identifier = require_string(record.get(field), f"{context}.{field}")
        if identifier in output:
            raise CoordinatorError(f"duplicate {context} {identifier}")
        output[identifier] = record
    return output


def load_case(case_directory: Path) -> dict[str, Any]:
    case_path = case_directory / "case_manifest.yaml"
    source_path = case_directory / "source_manifest.yaml"
    data_path = case_directory / "data/case_data_manifest.yaml"
    for path in (case_path, source_path, data_path):
        if not path.is_file() or path.is_symlink():
            raise CoordinatorError(f"missing regular Round 3 manifest: {path}")
    case = load_yaml(case_path, "case_manifest")
    source = load_yaml(source_path, "source_manifest")
    data = load_yaml(data_path, "case_data_manifest")
    stds_id = require_string(case.get("stds_id"), "case_manifest.stds_id")
    if not STDS_PATTERN.fullmatch(stds_id):
        raise CoordinatorError(f"invalid stds_id: {stds_id}")
    if source.get("stds_id") != stds_id or data.get("stds_id") != stds_id:
        raise CoordinatorError(f"manifest stds_id mismatch for {case_directory}")
    expected_case_id = f"stomicsdb_{stds_id}"
    if case_directory.name != expected_case_id:
        raise CoordinatorError(f"case directory identity mismatch: {case_directory}")
    if case.get("source_manifest_path") != "source_manifest.yaml":
        raise CoordinatorError(f"invalid source_manifest_path for {stds_id}")
    if case.get("case_data_manifest_path") != "data/case_data_manifest.yaml":
        raise CoordinatorError(f"invalid case_data_manifest_path for {stds_id}")
    return {
        "case_id": expected_case_id,
        "stds_id": stds_id,
        "case": case,
        "source": source,
        "data": data,
        "paths": {
            "case_manifest": case_path,
            "source_manifest": source_path,
            "case_data_manifest": data_path,
        },
    }


def _validate_relative_file(
    path_value: str,
    data_root: Path,
    expected_sha256: str | None,
    context: str,
    hash_cache: HashCache | None = None,
) -> Path:
    path = resolve_data_path(path_value, data_root)
    if not path.is_file() or path.is_symlink():
        raise ReadinessError(f"{context} is not a readable regular file: {path_value}")
    if expected_sha256 is not None:
        if not SHA256_PATTERN.fullmatch(expected_sha256):
            raise CoordinatorError(f"invalid SHA-256 for {context}: {expected_sha256}")
        try:
            actual = _sha256_cached(path, hash_cache)
        except CoordinatorError as error:
            raise ReadinessError(str(error)) from error
        if actual != expected_sha256:
            raise ReadinessError(
                f"SHA-256 mismatch for {context} {path_value}: {actual} != {expected_sha256}"
            )
    return path


def validate_auxiliary_resource(
    resource: dict[str, Any],
    data_root: Path,
    hash_cache: HashCache | None = None,
) -> list[str]:
    resource_id = require_string(resource.get("resource_id"), "auxiliary resource_id")
    if resource.get("local_availability") != "localized":
        raise ReadinessError(f"{resource_id} is not localized")
    binding = require_mapping(
        resource.get("localization_binding"), f"{resource_id}.localization_binding"
    )
    package = require_mapping(
        binding.get("package_manifest"), f"{resource_id}.package_manifest"
    )
    package_id = require_string(package.get("package_id"), f"{resource_id}.package_id")
    generation_id = require_string(
        package.get("generation_id"), f"{resource_id}.package_generation_id"
    )
    if not IDENTIFIER_PATTERN.fullmatch(package_id) or not IDENTIFIER_PATTERN.fullmatch(
        generation_id
    ):
        raise CoordinatorError(f"{resource_id} has unsafe package or generation identity")
    package_path = require_string(package.get("path"), f"{resource_id}.package_path")
    package_sha = require_string(package.get("sha256"), f"{resource_id}.package_sha256")
    localization_path = _validate_relative_file(
        package_path,
        data_root,
        package_sha,
        f"{resource_id}.package_manifest",
        hash_cache,
    )
    localization = load_yaml(localization_path, "auxiliary_localization_manifest")
    if localization.get("package_id") != package_id:
        raise CoordinatorError(f"{resource_id} package_id binding mismatch")
    if localization.get("generation_id") != generation_id:
        raise CoordinatorError(f"{resource_id} package generation binding mismatch")
    if localization.get("localization_status") != "LOCALIZED":
        raise ReadinessError(f"{resource_id} canonical package is not LOCALIZED")
    expected_manifest_path = (
        STOMICS_REL
        / "auxiliary_resources"
        / package_id
        / "generations"
        / generation_id
        / "localization.yaml"
    )
    if PurePosixPath(package_path) != expected_manifest_path:
        raise CoordinatorError(f"{resource_id} package manifest path is not canonical")
    resource_identity = require_mapping(
        localization.get("resource_identity"), f"{resource_id}.resource_identity"
    )
    if resource_identity != {
        "resource_name": resource.get("resource_name"),
        "source_url": resource.get("source_url"),
    }:
        raise CoordinatorError(f"{resource_id} canonical resource identity mismatch")
    require_string(
        localization.get("expected_content"),
        f"{resource_id}.canonical_expected_content",
    )
    acquisition = require_mapping(
        localization.get("acquisition_bindings"), f"{resource_id}.acquisition_bindings"
    )
    inventories = require_list(
        acquisition.get("inventories"), f"{resource_id}.acquisition.inventories"
    )
    successful_runs = require_list(
        acquisition.get("successful_runs"), f"{resource_id}.acquisition.successful_runs"
    )
    if not inventories or not successful_runs:
        raise CoordinatorError(f"{resource_id} has incomplete acquisition bindings")
    for raw_inventory in inventories:
        inventory = require_mapping(raw_inventory, f"{resource_id}.inventory_binding")
        if inventory.get("inventory_resource_id") != package_id:
            raise CoordinatorError(f"{resource_id} inventory resource binding mismatch")
        _validate_relative_file(
            require_string(inventory.get("path"), f"{resource_id}.inventory.path"),
            data_root,
            require_string(inventory.get("sha256"), f"{resource_id}.inventory.sha256"),
            f"{resource_id}.inventory",
            hash_cache,
        )
    for raw_run in successful_runs:
        run = require_mapping(raw_run, f"{resource_id}.run_binding")
        require_string(run.get("run_id"), f"{resource_id}.run_id")
        events_path = _validate_relative_file(
            require_string(run.get("events_path"), f"{resource_id}.events_path"),
            data_root,
            require_string(run.get("sha256"), f"{resource_id}.events_sha256"),
            f"{resource_id}.events",
            hash_cache,
        )
        try:
            event_lines = events_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            raise ReadinessError(
                f"{resource_id} acquisition event log is unreadable: {error}"
            ) from error
        if not event_lines:
            raise CoordinatorError(f"{resource_id} acquisition event log is empty")
        try:
            terminal = require_mapping(
                json.loads(event_lines[-1]), f"{resource_id}.acquisition_terminal"
            )
        except json.JSONDecodeError as error:
            raise CoordinatorError(f"{resource_id} acquisition terminal is invalid: {error}") from error
        if (
            terminal.get("event") != "auxiliary_run_completed"
            or terminal.get("download_failure_count") != 0
        ):
            raise CoordinatorError(f"{resource_id} acquisition run is not successful")
    manifest_artifacts = unique_index(
        require_list(localization.get("artifacts"), f"{resource_id}.manifest_artifacts"),
        "artifact_id",
        f"{resource_id}.manifest_artifact",
    )
    validation = require_mapping(
        localization.get("validation"), f"{resource_id}.validation"
    )
    if validation.get("artifact_count") != len(manifest_artifacts) or any(
        validation.get(field) is not True
        for field in (
            "acquisition_bindings_verified",
            "all_artifacts_regular_files",
            "all_artifacts_readable",
            "all_artifact_sizes_verified",
            "all_artifact_sha256_verified",
            "all_artifact_paths_canonical",
        )
    ):
        raise CoordinatorError(f"{resource_id} canonical validation record is incomplete")
    artifacts = require_list(binding.get("artifacts"), f"{resource_id}.artifacts")
    if not artifacts:
        raise CoordinatorError(f"{resource_id} has no required artifacts")
    artifact_paths: list[str] = []
    bound_artifacts = unique_index(artifacts, "artifact_id", f"{resource_id}.artifact")
    artifact_fields = ("artifact_id", "path", "source_url", "size_bytes", "sha256")
    for artifact_id, artifact in bound_artifacts.items():
        if not IDENTIFIER_PATTERN.fullmatch(artifact_id):
            raise CoordinatorError(f"{resource_id} has unsafe artifact identity: {artifact_id}")
        if set(artifact) != set(artifact_fields):
            raise CoordinatorError(
                f"{resource_id} case artifact must contain exactly five fields: {artifact_id}"
            )
        if artifact_id not in manifest_artifacts:
            raise CoordinatorError(f"{resource_id} artifact is absent from package: {artifact_id}")
        package_artifact = manifest_artifacts[artifact_id]
        if (
            not isinstance(package_artifact.get("format"), str)
            or not package_artifact["format"]
            or not isinstance(package_artifact.get("role"), str)
            or not package_artifact["role"]
        ):
            raise CoordinatorError(f"{resource_id} canonical artifact metadata is invalid")
        package_projection = {
            field: manifest_artifacts[artifact_id].get(field) for field in artifact_fields
        }
        case_projection = {field: artifact.get(field) for field in artifact_fields}
        if case_projection != package_projection:
            raise CoordinatorError(
                f"{resource_id} artifact binding differs from package manifest: {artifact_id}"
            )
    for artifact_id, artifact in bound_artifacts.items():
        path_value = require_string(artifact.get("path"), f"{artifact_id}.path")
        if PurePosixPath(path_value).parent != expected_manifest_path.parent / "artifacts":
            raise CoordinatorError(f"{resource_id} artifact path is not canonical: {path_value}")
        digest = require_string(artifact.get("sha256"), f"{artifact_id}.sha256")
        source_url = require_string(artifact.get("source_url"), f"{artifact_id}.source_url")
        size_bytes = artifact.get("size_bytes")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise CoordinatorError(f"{artifact_id}.size_bytes must be a nonnegative integer")
        path = _validate_relative_file(
            path_value, data_root, digest, f"{resource_id}.artifact", hash_cache
        )
        try:
            actual_size = path.stat().st_size
        except OSError as error:
            raise ReadinessError(
                f"cannot stat {resource_id} artifact {path_value}: {error}"
            ) from error
        if actual_size != size_bytes:
            raise ReadinessError(f"{resource_id} artifact size mismatch: {path_value}")
        if not source_url:
            raise CoordinatorError(f"{resource_id} artifact source_url is empty")
        artifact_paths.append(path_value)
    if len(artifact_paths) != len(set(artifact_paths)):
        raise CoordinatorError(f"duplicate required artifacts for {resource_id}")
    coverage = require_mapping(
        binding.get("expected_content_coverage"), f"{resource_id}.expected_content_coverage"
    )
    if coverage.get("status") != "complete":
        raise ReadinessError(f"{resource_id} expected-content coverage is not complete")
    coverage_items = require_list(coverage.get("items"), f"{resource_id}.coverage.items")
    if len(coverage_items) != 1:
        raise CoordinatorError(f"{resource_id} must have one frozen coverage requirement")
    if require_list(
        coverage.get("uncovered_requirements"), f"{resource_id}.uncovered_requirements"
    ):
        raise ReadinessError(f"{resource_id} retains uncovered requirements")
    covered_artifact_ids: set[str] = set()
    for raw_item in coverage_items:
        item = require_mapping(raw_item, f"{resource_id}.coverage.item")
        requirement = require_string(
            item.get("requirement"), f"{resource_id}.coverage.requirement"
        )
        if requirement != resource.get("expected_content"):
            raise CoordinatorError(f"{resource_id} coverage requirement mismatch")
        require_string(item.get("evidence"), f"{resource_id}.coverage.evidence")
        item_artifacts = require_list(
            item.get("artifact_ids"), f"{resource_id}.coverage.artifact_ids"
        )
        if not item_artifacts or any(value not in bound_artifacts for value in item_artifacts):
            raise CoordinatorError(f"{resource_id} coverage cites unresolved artifacts")
        covered_artifact_ids.update(item_artifacts)
    if covered_artifact_ids != set(bound_artifacts):
        raise ReadinessError(f"{resource_id} bound artifacts are not fully covered")
    return artifact_paths


def _candidate_context(case_bundle: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    case = case_bundle["case"]
    source = case_bundle["source"]
    data = case_bundle["data"]
    dataset_prefix = STOMICS_REL / "datasets" / case_bundle["stds_id"]
    article_path_value = require_string(source.get("article_path"), "source.article_path")
    if tuple(PurePosixPath(article_path_value).parts[: len(dataset_prefix.parts)]) != tuple(
        dataset_prefix.parts
    ):
        raise CoordinatorError("article path is outside the assigned dataset")
    _validate_relative_file(
        article_path_value,
        case_bundle["data_root"],
        require_string(source.get("article_sha256"), "source.article_sha256"),
        "article",
        case_bundle.get("hash_cache"),
    )
    candidates = unique_index(
        require_list(case.get("case_candidates"), "case_candidates"),
        "candidate_id",
        "candidate",
    )
    if candidate_id not in candidates:
        raise CoordinatorError(f"unknown candidate_id {candidate_id}")
    candidate = candidates[candidate_id]
    result_ids = require_list(candidate.get("result_ids"), f"{candidate_id}.result_ids")
    result_order = require_list(candidate.get("result_order"), f"{candidate_id}.result_order")
    if (
        not result_ids
        or len(result_ids) != len(set(result_ids))
        or len(result_order) != len(set(result_order))
        or set(result_ids) != set(result_order)
    ):
        raise CoordinatorError(f"invalid result boundary for {candidate_id}")
    source_results = unique_index(
        require_list(source.get("results"), "source results"), "result_id", "source result"
    )
    links = unique_index(
        require_list(data.get("result_data_links"), "result_data_links"),
        "result_id",
        "result data link",
    )
    for result_id in result_order:
        if result_id not in source_results or result_id not in links:
            raise CoordinatorError(f"unresolved result {result_id} in {candidate_id}")
        result = source_results[result_id]
        require_string(result.get("result_section"), f"{result_id}.result_section")
        if not require_list(result.get("source_anchors"), f"{result_id}.source_anchors"):
            raise CoordinatorError(f"{result_id} has no source anchors")
        if not require_list(result.get("analysis_steps"), f"{result_id}.analysis_steps"):
            raise CoordinatorError(f"{result_id} has no analysis steps")
    connections = require_list(
        candidate.get("result_connections"), f"{candidate_id}.connections"
    )
    edges: set[tuple[str, str]] = set()
    adjacency: dict[str, set[str]] = {result_id: set() for result_id in result_ids}
    order_index = {result_id: index for index, result_id in enumerate(result_order)}
    for raw in connections:
        connection = require_mapping(raw, f"{candidate_id}.connection")
        source_id = connection.get("from_result_id")
        target_id = connection.get("to_result_id")
        if source_id not in result_ids or target_id not in result_ids:
            raise CoordinatorError(f"connection escapes candidate {candidate_id}")
        edge = (source_id, target_id)
        if (
            source_id == target_id
            or edge in edges
            or order_index[source_id] >= order_index[target_id]
        ):
            raise CoordinatorError(f"cyclic, duplicate, or misordered connection in {candidate_id}")
        edges.add(edge)
        adjacency[source_id].add(target_id)
        adjacency[target_id].add(source_id)
        from_output = require_string(connection.get("from_output"), "connection.from_output")
        to_input = require_string(connection.get("to_input"), "connection.to_input")
        if from_output not in {
            require_string(step.get("output"), f"{source_id}.analysis_step.output")
            for step in map(require_mapping, source_results[source_id]["analysis_steps"], ["step"] * len(source_results[source_id]["analysis_steps"]))
        }:
            raise CoordinatorError(f"connection output does not resolve for {source_id}")
        if to_input not in {
            require_string(step.get("input"), f"{target_id}.analysis_step.input")
            for step in map(require_mapping, source_results[target_id]["analysis_steps"], ["step"] * len(source_results[target_id]["analysis_steps"]))
        }:
            raise CoordinatorError(f"connection input does not resolve for {target_id}")
    if len(result_ids) == 1 and connections:
        raise CoordinatorError(f"single-result candidate has connections: {candidate_id}")
    if len(result_ids) > 1:
        reached = {result_order[0]}
        pending = [result_order[0]]
        while pending:
            for neighbor in adjacency[pending.pop()]:
                if neighbor not in reached:
                    reached.add(neighbor)
                    pending.append(neighbor)
        if reached != set(result_ids):
            raise CoordinatorError(f"multi-result candidate route is disconnected: {candidate_id}")

    data_objects = unique_index(
        require_list(data.get("data_objects"), "data_objects"), "data_id", "data object"
    )
    auxiliary = unique_index(
        require_list(data.get("auxiliary_resources"), "auxiliary_resources"),
        "resource_id",
        "auxiliary resource",
    )
    dataset_binding = require_mapping(data.get("dataset_binding"), "dataset_binding")
    samples_binding = require_mapping(dataset_binding.get("samples"), "dataset_binding.samples")
    samples_path_value = require_string(samples_binding.get("path"), "samples.path")
    if tuple(PurePosixPath(samples_path_value).parts[: len(dataset_prefix.parts)]) != tuple(
        dataset_prefix.parts
    ):
        raise CoordinatorError("samples.jsonl binding is outside the assigned dataset")
    samples_path = _validate_relative_file(
        samples_path_value,
        case_bundle["data_root"],
        require_string(samples_binding.get("sha256"), "samples.sha256"),
        "samples.jsonl",
        case_bundle.get("hash_cache"),
    )
    sample_ids: set[str] = set()
    try:
        sample_lines = samples_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReadinessError(f"samples inventory is unreadable: {error}") from error
    for number, line in enumerate(sample_lines, 1):
        if not line.strip():
            raise CoordinatorError(f"blank samples.jsonl row {number}")
        try:
            sample = require_mapping(json.loads(line), f"samples.jsonl line {number}")
        except json.JSONDecodeError as error:
            raise CoordinatorError(f"invalid samples.jsonl line {number}: {error}") from error
        sample_id = require_string(sample.get("sample_id"), f"samples line {number}.sample_id")
        if sample_id in sample_ids or sample.get("stds_id") != case_bundle["stds_id"]:
            raise CoordinatorError(f"invalid or duplicate assigned sample {sample_id}")
        sample_ids.add(sample_id)
    used_data_ids: list[str] = []
    used_auxiliary_ids: list[str] = []
    candidate_sample_ids: set[str] = set()
    primary_sets: list[set[str]] = []
    required_paths: dict[str, set[str]] = {}
    required_hashes: dict[str, dict[str, str]] = {}
    for result_id in result_order:
        link = links[result_id]
        primary: set[str] = set()
        data_inputs = require_list(link.get("data_inputs"), f"{result_id}.data_inputs")
        if not data_inputs:
            raise CoordinatorError(f"{result_id} has no data inputs")
        result_data_ids: set[str] = set()
        for raw_input in data_inputs:
            data_input = require_mapping(raw_input, f"{result_id}.data_input")
            data_id = require_string(data_input.get("data_id"), f"{result_id}.data_id")
            if data_id in result_data_ids:
                raise CoordinatorError(f"duplicate data input {data_id} for {result_id}")
            result_data_ids.add(data_id)
            if data_id not in data_objects:
                raise CoordinatorError(f"unresolved data object {data_id}")
            if data_id not in used_data_ids:
                used_data_ids.append(data_id)
            if data_input.get("input_role") == "primary_spatial":
                primary.add(data_id)
            selected_samples = require_list(
                data_input.get("sample_ids"), f"{result_id}.{data_id}.sample_ids"
            )
            if (
                not selected_samples
                or len(selected_samples) != len(set(selected_samples))
                or any(value not in sample_ids for value in selected_samples)
            ):
                raise CoordinatorError(f"unresolved sample IDs for {result_id}.{data_id}")
            candidate_sample_ids.update(selected_samples)
            for raw_component in require_list(
                data_input.get("required_components"), f"{result_id}.{data_id}.components"
            ):
                component = require_mapping(raw_component, "required component")
                component_name = require_string(component.get("component"), "component.name")
                component_record = require_mapping(
                    data_objects[data_id].get(component_name), f"{data_id}.{component_name}"
                )
                files = unique_index(
                    require_list(component_record.get("files"), f"{data_id}.{component_name}.files"),
                    "path",
                    "component file",
                )
                for path_value in require_list(component.get("paths"), "component.paths"):
                    path_value = require_string(path_value, "required component path")
                    if tuple(
                        PurePosixPath(path_value).parts[: len(dataset_prefix.parts)]
                    ) != tuple(dataset_prefix.parts):
                        raise CoordinatorError(
                            f"required component path is outside assigned dataset: {path_value}"
                        )
                    if path_value not in files:
                        raise CoordinatorError(
                            f"required path is not a {data_id}.{component_name} file: {path_value}"
                        )
                    digest = require_string(files[path_value].get("sha256"), "component sha256")
                    _validate_relative_file(
                        path_value,
                        case_bundle["data_root"],
                        digest,
                        data_id,
                        case_bundle.get("hash_cache"),
                    )
                    required_paths.setdefault(data_id, set()).add(path_value)
                    previous = required_hashes.setdefault(data_id, {}).setdefault(
                        path_value, digest
                    )
                    if previous != digest:
                        raise CoordinatorError(
                            f"conflicting component SHA-256 for {data_id}: {path_value}"
                        )
        if not primary:
            raise CoordinatorError(f"{result_id} has no primary_spatial input")
        primary_sets.append(primary)
        link_auxiliary = require_list(
            link.get("auxiliary_resource_ids"), f"{result_id}.auxiliary"
        )
        if len(link_auxiliary) != len(set(link_auxiliary)):
            raise CoordinatorError(f"duplicate auxiliary resource for {result_id}")
        for aux_id in link_auxiliary:
            aux_id = require_string(aux_id, f"{result_id}.auxiliary_id")
            if aux_id not in auxiliary:
                raise CoordinatorError(f"unresolved auxiliary resource {aux_id}")
            if aux_id not in used_auxiliary_ids:
                used_auxiliary_ids.append(aux_id)
    common_primary = primary_sets[0]
    if any(value != common_primary for value in primary_sets[1:]):
        raise CoordinatorError(f"candidate {candidate_id} has inconsistent primary_spatial sets")
    candidate_spatial = require_list(
        candidate.get("spatial_data_ids"), f"{candidate_id}.spatial_data_ids"
    )
    if set(candidate_spatial) != common_primary or len(candidate_spatial) != len(common_primary):
        raise CoordinatorError(f"candidate {candidate_id} spatial_data_ids mismatch")
    candidate_auxiliary = require_list(
        candidate.get("auxiliary_resource_ids"), f"{candidate_id}.auxiliary_resource_ids"
    )
    if set(candidate_auxiliary) != set(used_auxiliary_ids) or len(candidate_auxiliary) != len(
        used_auxiliary_ids
    ):
        raise CoordinatorError(f"candidate {candidate_id} auxiliary_resource_ids mismatch")
    for data_id in used_data_ids:
        data_object = data_objects[data_id]
        root_value = require_string(data_object.get("path"), f"{data_id}.path")
        if tuple(PurePosixPath(root_value).parts[: len(dataset_prefix.parts)]) != tuple(
            dataset_prefix.parts
        ):
            raise CoordinatorError(f"data object root is outside assigned dataset: {data_id}")
        root = resolve_data_path(root_value, case_bundle["data_root"])
        if not root.exists() or root.is_symlink():
            raise ReadinessError(f"data object root is not readable: {data_id}")
        bindings = require_list(data_object.get("localization_bindings"), f"{data_id}.bindings")
        if not bindings:
            raise CoordinatorError(f"data object has no localization binding: {data_id}")
        localized_artifacts: dict[str, str] = {}
        for raw_binding in bindings:
            binding = require_mapping(raw_binding, f"{data_id}.binding")
            binding_path = require_string(binding.get("path"), f"{data_id}.binding.path")
            if tuple(
                PurePosixPath(binding_path).parts[: len(dataset_prefix.parts)]
            ) != tuple(dataset_prefix.parts):
                raise CoordinatorError(
                    f"data object localization is outside assigned dataset: {data_id}"
                )
            localization_path = _validate_relative_file(
                binding_path,
                case_bundle["data_root"],
                require_string(binding.get("sha256"), f"{data_id}.binding.sha256"),
                f"{data_id}.binding",
                case_bundle.get("hash_cache"),
            )
            binding_generation = require_string(
                binding.get("generation_id"), f"{data_id}.binding.generation_id"
            )
            localization = load_yaml(localization_path)
            if localization.get("generation_id") != binding_generation:
                raise CoordinatorError(f"invalid Dxx localization generation for {data_id}")
            if localization.get("localization_status") != "LOCALIZED":
                raise ReadinessError(f"Dxx localization is not LOCALIZED for {data_id}")
            bundle_record = require_mapping(
                localization.get("bundle"), f"{data_id}.localization.bundle"
            )
            if (
                bundle_record.get("owner_id") != case_bundle["stds_id"]
                or bundle_record.get("target_directory")
                != data_relative(localization_path.parent, case_bundle["data_root"])
            ):
                raise CoordinatorError(f"Dxx localization owner/target mismatch for {data_id}")
            for raw_artifact in require_list(
                localization.get("artifacts"), f"{data_id}.localization.artifacts"
            ):
                artifact = require_mapping(raw_artifact, f"{data_id}.localization.artifact")
                artifact_path = require_string(
                    artifact.get("path"), f"{data_id}.localization.artifact.path"
                )
                artifact_sha = require_string(
                    artifact.get("sha256"), f"{data_id}.localization.artifact.sha256"
                )
                if artifact_path in localized_artifacts and localized_artifacts[
                    artifact_path
                ] != artifact_sha:
                    raise CoordinatorError(
                        f"conflicting Dxx localization artifact for {data_id}: {artifact_path}"
                    )
                localized_artifacts[artifact_path] = artifact_sha
        for required_path, required_sha in required_hashes.get(data_id, {}).items():
            if localized_artifacts.get(required_path) != required_sha:
                raise CoordinatorError(
                    f"required component is not bound by Dxx localization: {data_id}:{required_path}"
                )
    unresolved_auxiliary_ids: list[str] = []
    for aux_id in used_auxiliary_ids:
        resource = auxiliary[aux_id]
        availability = resource.get("local_availability")
        if availability == "absent":
            external_auxiliary_identity(resource)
            unresolved_auxiliary_ids.append(aux_id)
        elif availability == "localized":
            validate_auxiliary_resource(
                resource, case_bundle["data_root"], case_bundle.get("hash_cache")
            )
        else:
            raise CoordinatorError(
                f"unsupported local_availability for {aux_id}: {availability}"
            )
    return {
        "candidate": candidate,
        "source_results": source_results,
        "links": links,
        "data_objects": data_objects,
        "auxiliary_resources": auxiliary,
        "used_data_ids": used_data_ids,
        "used_auxiliary_ids": used_auxiliary_ids,
        "unresolved_auxiliary_ids": unresolved_auxiliary_ids,
        "required_paths": {key: sorted(value) for key, value in required_paths.items()},
        "candidate_sample_ids": sorted(candidate_sample_ids),
    }


def candidate_context(case_bundle: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    """Validate one candidate and return its exact downstream object boundary."""
    try:
        return _candidate_context(case_bundle, candidate_id)
    except ReadinessError:
        raise
    except CoordinatorError as error:
        raise HandoffError(str(error)) from error
    except (KeyError, TypeError) as error:
        raise CoordinatorError(f"malformed candidate {candidate_id}: {error}") from error


def _case_bundle(case_directory: Path, data_root: Path) -> dict[str, Any]:
    bundle = load_case(case_directory)
    bundle["data_root"] = data_root
    return bundle


def _chain_resume_state(
    final_directory: Path,
    data_root: Path,
    repository_root: Path,
    hash_cache: HashCache | None = None,
) -> tuple[str, str, int, int]:
    identifier = final_directory.name
    committed = _committed_revision_count(data_root, identifier)
    remaining = max(0, MAX_REVISION_ROUNDS - committed)
    if not final_directory.exists():
        return "absent", "extract_initial", committed, remaining
    if not final_directory.is_dir() or final_directory.is_symlink():
        raise CoordinatorError(f"final chain path is not a regular directory: {final_directory}")
    names = sorted(path.name for path in final_directory.iterdir())
    if names == sorted(EXTRACTION_FILENAMES):
        validate_chain_directory(
            final_directory,
            data_root,
            repository_root,
            hash_cache=hash_cache,
        )
        return "draft", "review_draft", committed, remaining
    if names != sorted(FINAL_FILENAMES):
        raise CoordinatorError(f"invalid existing final chain file set: {names}")
    manifest = load_yaml(final_directory / "chain_manifest.yaml")
    status = require_mapping(
        manifest.get("independent_check"), "independent_check"
    ).get("status")
    if status == "confirmed":
        validate_chain_directory(
            final_directory,
            data_root,
            repository_root,
            final=True,
            hash_cache=hash_cache,
        )
        chain_status = manifest.get("chain_status")
        if chain_status not in {"comparison_ready", "specification_ready"}:
            raise CoordinatorError(f"unsupported confirmed chain status: {chain_status}")
        return chain_status, "verify_and_close", committed, remaining
    validate_chain_directory(
        final_directory,
        data_root,
        repository_root,
        reviewed=True,
        hash_cache=hash_cache,
    )
    if status == "blocked":
        return "blocked", "close_blocked", committed, remaining
    if status != "needs_revision":
        raise CoordinatorError(f"unsupported existing review status: {status}")
    scope = require_mapping(
        manifest.get("independent_check"), "independent_check"
    ).get("revision_scope")
    if scope == "round3_handoff":
        return "needs_revision", "close_round3_handoff", committed, remaining
    action = "revise_reviewed" if remaining else "close_failed"
    return "needs_revision", action, committed, remaining


def _validate_job_assignment_invariants(
    assignment: dict[str, Any],
    data_root: Path,
    repository_root: Path,
    *,
    revalidate_inputs: bool = True,
    revalidate_state: bool = True,
    hash_cache: HashCache | None = None,
) -> dict[str, Any]:
    schema = _load_schema(repository_root, "stomicsdb_dual_chain_job.schema.json")
    _validate_schema_value(assignment, schema, "stomicsdb dual-chain job assignment")
    attempt_id = require_string(assignment.get("attempt_id"), "attempt_id")
    job_attempt_id = require_string(assignment.get("job_attempt_id"), "job_attempt_id")
    if len(attempt_id) > MAX_IDENTIFIER_LENGTH or len(job_attempt_id) > MAX_IDENTIFIER_LENGTH:
        raise CoordinatorError("attempt identity exceeds 128 characters")
    stds_id = require_string(assignment.get("stds_id"), "stds_id")
    case_id = require_string(assignment.get("case_id"), "case_id")
    candidate_id = require_string(assignment.get("candidate_id"), "candidate_id")
    identifier = require_string(assignment.get("chain_id"), "chain_id")
    if case_id != f"stomicsdb_{stds_id}":
        raise CoordinatorError("assignment case_id/stds_id mismatch")
    if identifier != chain_id(case_id, candidate_id):
        raise CoordinatorError("assignment deterministic chain_id mismatch")
    if job_attempt_id != f"{attempt_id}__{identifier}":
        raise CoordinatorError("assignment job_attempt_id mismatch")
    binding = require_mapping(assignment.get("input_binding"), "input_binding")
    if binding.get("stds_id") != stds_id or binding.get("candidate_id") != candidate_id:
        raise CoordinatorError("assignment top-level/input_binding identity mismatch")
    case_directory = data_root.joinpath(*STOMICS_REL.parts, "cases", case_id)
    expected_manifest_paths = {
        "case_manifest_path": case_directory / "case_manifest.yaml",
        "source_manifest_path": case_directory / "source_manifest.yaml",
        "case_data_manifest_path": case_directory / "data/case_data_manifest.yaml",
    }
    binding_fields = {
        "case_manifest_path": "case_manifest",
        "source_manifest_path": "source_manifest",
        "case_data_manifest_path": "case_data_manifest",
    }
    for field, expected in expected_manifest_paths.items():
        supplied = Path(require_string(assignment.get(field), field))
        if supplied.resolve() != expected.resolve():
            raise CoordinatorError(f"assignment {field} is not canonical")
        record = require_mapping(binding.get(binding_fields[field]), f"input_binding.{binding_fields[field]}")
        if record.get("path") != data_relative(expected, data_root):
            raise CoordinatorError(f"assignment {field}/input_binding path mismatch")
    extraction = data_root.joinpath(
        *STOMICS_REL.parts, "staging/dual_chain/extraction", attempt_id, identifier
    )
    review = data_root.joinpath(
        *STOMICS_REL.parts, "staging/dual_chain/review", attempt_id, identifier
    )
    final = case_directory / "dual_chain" / identifier
    expected_paths = {
        "extraction_staging_directory": extraction,
        "review_staging_directory": review,
        "final_chain_directory": final,
    }
    for field, expected in expected_paths.items():
        if Path(require_string(assignment.get(field), field)).resolve() != expected.resolve():
            raise CoordinatorError(f"assignment {field} is not canonical")
    readiness = assignment.get("data_readiness")
    errors = require_list(assignment.get("readiness_errors"), "readiness_errors")
    has_data_ids = "used_data_object_ids" in assignment
    has_auxiliary_ids = "used_auxiliary_resource_ids" in assignment
    has_used = has_data_ids and has_auxiliary_ids
    if has_data_ids != has_auxiliary_ids:
        raise CoordinatorError("assignment must provide both used-ID lists or neither")
    unresolved_ids = assignment.get("unresolved_auxiliary_resource_ids")
    if readiness == "DATA_READY":
        if errors or not has_used or unresolved_ids not in (None, []):
            raise CoordinatorError("DATA_READY assignment has inconsistent readiness fields")
    elif readiness == "BLOCKED_EXTERNAL":
        extractable = assignment_supports_specification_extraction(assignment)
        if not errors or (has_used != extractable):
            raise CoordinatorError("BLOCKED_EXTERNAL assignment has inconsistent readiness fields")
        if not extractable and unresolved_ids is not None:
            raise CoordinatorError("physical blocker cannot declare unresolved Axx IDs")
    else:
        raise CoordinatorError(f"unsupported assignment data_readiness: {readiness}")
    cache = hash_cache if hash_cache is not None else {}
    context: dict[str, Any] | None = None
    if revalidate_inputs:
        try:
            _, context = _load_bound_case(assignment, data_root, cache)
        except ReadinessError:
            if readiness != "BLOCKED_EXTERNAL" or has_used:
                raise
        else:
            expected_unresolved = context["unresolved_auxiliary_ids"]
            expected_readiness = "BLOCKED_EXTERNAL" if expected_unresolved else "DATA_READY"
            if readiness != expected_readiness:
                raise CoordinatorError("assignment data_readiness does not match current inputs")
            if assignment["used_data_object_ids"] != context["used_data_ids"]:
                raise CoordinatorError("assignment used_data_object_ids mismatch")
            if assignment["used_auxiliary_resource_ids"] != context["used_auxiliary_ids"]:
                raise CoordinatorError("assignment used_auxiliary_resource_ids mismatch")
            if expected_unresolved:
                if unresolved_ids != expected_unresolved:
                    raise CoordinatorError(
                        "assignment unresolved_auxiliary_resource_ids mismatch"
                    )
                if errors != external_auxiliary_readiness_errors(context):
                    raise CoordinatorError("assignment external-Axx readiness errors mismatch")
    if revalidate_state:
        state, action, committed, remaining = _chain_resume_state(
            final, data_root, repository_root, cache
        )
        expected_state = {
            "current_chain_state": state,
            "next_action": (
                action
                if readiness == "DATA_READY"
                or assignment_supports_specification_extraction(assignment)
                else "close_blocked"
            ),
            "committed_revision_rounds": committed,
            "remaining_revision_rounds": remaining,
        }
        for field, expected in expected_state.items():
            if assignment.get(field) != expected:
                raise CoordinatorError(f"assignment {field} mismatch: {assignment.get(field)} != {expected}")
    else:
        expected_state = {
            field: assignment[field]
            for field in (
                "current_chain_state",
                "next_action",
                "committed_revision_rounds",
                "remaining_revision_rounds",
            )
        }
        if expected_state["committed_revision_rounds"] + expected_state["remaining_revision_rounds"] != MAX_REVISION_ROUNDS:
            raise CoordinatorError("assignment revision counters do not sum to the fixed limit")
    return {**expected_state, "input_context": context}


def validate_job_assignment(
    assignment: dict[str, Any],
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    result = _validate_job_assignment_invariants(
        assignment, data_root, repository_root, hash_cache={}
    )
    return {key: value for key, value in result.items() if key != "input_context"}


def validate_job_response(
    response_document: dict[str, Any],
    assignment: dict[str, Any],
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    _validate_job_assignment_invariants(
        assignment,
        data_root,
        repository_root,
        revalidate_inputs=False,
        revalidate_state=False,
    )
    schema = _load_schema(
        repository_root, "stomicsdb_dual_chain_job_response.schema.json"
    )
    _validate_schema_value(
        response_document, schema, "stomicsdb dual-chain job response"
    )
    response = require_mapping(
        response_document.get("stomicsdb_dual_chain_job_response"),
        "stomicsdb_dual_chain_job_response",
    )
    for field in ("attempt_id", "job_attempt_id", "stds_id", "candidate_id", "chain_id"):
        if response.get(field) != assignment.get(field):
            raise CoordinatorError(f"job response {field} does not match assignment")
    output_paths = require_mapping(response.get("output_paths"), "output_paths")
    status = response.get("status")
    error = response.get("error")
    if response["review_rounds"] > response["revision_rounds"] + 1:
        raise CoordinatorError("job response review_rounds exceeds the bounded lifecycle")
    final = Path(assignment["final_chain_directory"])
    expected_paths = {
        "chain_directory": str(final.resolve()),
        "chain_manifest": str((final / "chain_manifest.yaml").resolve()),
        "scientific_chain": str((final / "scientific_chain.jsonl").resolve()),
        "execution_subchains": str((final / "execution_subchains.jsonl").resolve()),
        "independent_check": str((final / "independent_check.md").resolve()),
    }
    if status in {"comparison_ready", "specification_ready"}:
        if error is not None or output_paths != expected_paths:
            raise CoordinatorError(f"{status} response has invalid error or output paths")
        validated = validate_chain_directory(
            final, data_root, repository_root, final=True, hash_cache={}
        )
        if validated["manifest"].get("chain_status") != status:
            raise CoordinatorError("ready response status does not match final chain")
        expected_status = (
            "specification_ready"
            if assignment_supports_specification_extraction(assignment)
            else "comparison_ready"
        )
        if status != expected_status:
            raise CoordinatorError("ready response status does not match assignment readiness")
    else:
        if not isinstance(error, str) or not error.strip():
            raise CoordinatorError("non-ready response must contain a bounded error")
        if any(value is not None for value in output_paths.values()):
            raise CoordinatorError("non-ready response must not claim published output paths")
        if status == "blocked":
            if assignment_supports_specification_extraction(assignment):
                raise CoordinatorError(
                    "blocked response cannot use an absent-Axx-only limitation"
                )
            if assignment.get("data_readiness") != "BLOCKED_EXTERNAL":
                try:
                    _load_bound_case(assignment, data_root, {})
                except ReadinessError:
                    pass
                else:
                    raise CoordinatorError(
                        "blocked response has no current physical input failure"
                    )
        if status == "round3_handoff_needs_revision":
            supported = assignment.get("next_action") == "close_round3_handoff"
            if not supported and final.is_dir():
                reviewed = validate_chain_directory(
                    final,
                    data_root,
                    repository_root,
                    reviewed=True,
                    hash_cache={},
                )
                check = require_mapping(
                    reviewed["manifest"].get("independent_check"),
                    "independent_check",
                )
                supported = (
                    check.get("status") == "needs_revision"
                    and check.get("revision_scope") == "round3_handoff"
                )
            if not supported:
                raise CoordinatorError("handoff response has no structured handoff finding")
    return response


def audit_cases(
    data_root: Path = DEFAULT_DATA_ROOT,
    attempt_id: str = "audit",
    *,
    hash_cache: HashCache | None = None,
    repository_root: Path | None = None,
) -> list[dict[str, Any]]:
    if not IDENTIFIER_PATTERN.fullmatch(attempt_id):
        raise CoordinatorError(f"unsafe attempt ID: {attempt_id}")
    cases_root = data_root.joinpath(*STOMICS_REL.parts, "cases")
    assignments: list[dict[str, Any]] = []
    if not cases_root.is_dir():
        raise CoordinatorError(f"cases root does not exist: {cases_root}")
    hash_cache = hash_cache if hash_cache is not None else {}
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    for case_directory in sorted(cases_root.glob("stomicsdb_STDS*"), key=lambda value: value.name):
        if not case_directory.is_dir() or case_directory.is_symlink():
            continue
        bundle = _case_bundle(case_directory, data_root)
        bundle["hash_cache"] = hash_cache
        candidates = unique_index(
            require_list(bundle["case"].get("case_candidates"), "case_candidates"),
            "candidate_id",
            "candidate",
        )
        for candidate_id in sorted(candidates):
            identifier = chain_id(bundle["case_id"], candidate_id)
            extraction_staging = data_root.joinpath(
                *STOMICS_REL.parts,
                "staging/dual_chain/extraction",
                attempt_id,
                identifier,
            )
            review_staging = data_root.joinpath(
                *STOMICS_REL.parts,
                "staging/dual_chain/review",
                attempt_id,
                identifier,
            )
            final_directory = case_directory / "dual_chain" / identifier
            assignment = {
                "case_route": "public_database_stomicsdb",
                "attempt_id": attempt_id,
                "job_attempt_id": f"{attempt_id}__{identifier}",
                "max_revision_rounds": MAX_REVISION_ROUNDS,
                "stds_id": bundle["stds_id"],
                "case_id": bundle["case_id"],
                "candidate_id": candidate_id,
                "chain_id": identifier,
                "case_manifest_path": str(bundle["paths"]["case_manifest"].resolve()),
                "source_manifest_path": str(bundle["paths"]["source_manifest"].resolve()),
                "case_data_manifest_path": str(
                    bundle["paths"]["case_data_manifest"].resolve()
                ),
                "extraction_staging_directory": str(extraction_staging.resolve()),
                "review_staging_directory": str(review_staging.resolve()),
                "final_chain_directory": str(final_directory.resolve()),
                "input_binding": {
                    "stds_id": bundle["stds_id"],
                    "candidate_id": candidate_id,
                    "case_manifest": {
                        "path": data_relative(bundle["paths"]["case_manifest"], data_root),
                        "sha256": _sha256_cached(
                            bundle["paths"]["case_manifest"], hash_cache
                        ),
                    },
                    "source_manifest": {
                        "path": data_relative(bundle["paths"]["source_manifest"], data_root),
                        "sha256": _sha256_cached(
                            bundle["paths"]["source_manifest"], hash_cache
                        ),
                    },
                    "case_data_manifest": {
                        "path": data_relative(bundle["paths"]["case_data_manifest"], data_root),
                        "sha256": _sha256_cached(
                            bundle["paths"]["case_data_manifest"], hash_cache
                        ),
                    },
                },
            }
            try:
                context = candidate_context(bundle, candidate_id)
            except ReadinessError as error:
                assignment["data_readiness"] = "BLOCKED_EXTERNAL"
                assignment["readiness_errors"] = [str(error)]
            else:
                assignment["used_data_object_ids"] = context["used_data_ids"]
                assignment["used_auxiliary_resource_ids"] = context["used_auxiliary_ids"]
                unresolved = context["unresolved_auxiliary_ids"]
                if unresolved:
                    assignment["data_readiness"] = "BLOCKED_EXTERNAL"
                    assignment["readiness_errors"] = external_auxiliary_readiness_errors(
                        context
                    )
                    assignment["unresolved_auxiliary_resource_ids"] = unresolved
                else:
                    assignment["data_readiness"] = "DATA_READY"
                    assignment["readiness_errors"] = []
            state, action, committed, remaining = _chain_resume_state(
                final_directory, data_root, repository_root, hash_cache
            )
            assignment.update(
                {
                    "current_chain_state": state,
                    "next_action": (
                        action
                        if assignment["data_readiness"] == "DATA_READY"
                        or assignment_supports_specification_extraction(assignment)
                        else "close_blocked"
                    ),
                    "committed_revision_rounds": committed,
                    "remaining_revision_rounds": remaining,
                }
            )
            _validate_job_assignment_invariants(
                assignment,
                data_root,
                repository_root,
                revalidate_inputs=False,
                hash_cache=hash_cache,
            )
            assignments.append(assignment)
    return assignments


def _load_bound_case(
    manifest: dict[str, Any],
    data_root: Path,
    hash_cache: HashCache | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = require_mapping(manifest.get("input_binding"), "input_binding")
    stds_id = require_string(binding.get("stds_id"), "input_binding.stds_id")
    candidate_id = require_string(binding.get("candidate_id"), "input_binding.candidate_id")
    expected_paths = {
        "case_manifest": ("case_manifest", "case_manifest.yaml"),
        "source_manifest": ("source_manifest", "source_manifest.yaml"),
        "case_data_manifest": ("case_data_manifest", "data/case_data_manifest.yaml"),
    }
    resolved: dict[str, Path] = {}
    for key, (binding_key, suffix) in expected_paths.items():
        record = require_mapping(binding.get(binding_key), f"input_binding.{binding_key}")
        path_value = require_string(record.get("path"), f"input_binding.{binding_key}.path")
        digest = require_string(record.get("sha256"), f"input_binding.{binding_key}.sha256")
        path = _validate_relative_file(
            path_value, data_root, digest, binding_key, hash_cache
        )
        if not path_value.endswith(suffix):
            raise CoordinatorError(f"unexpected {binding_key} path: {path_value}")
        resolved[key] = path
    case_directory = resolved["case_manifest"].parent
    if resolved["source_manifest"].parent != case_directory:
        raise CoordinatorError("source manifest is outside the bound case")
    if resolved["case_data_manifest"].parent.parent != case_directory:
        raise CoordinatorError("case data manifest is outside the bound case")
    bundle = _case_bundle(case_directory, data_root)
    bundle["hash_cache"] = hash_cache if hash_cache is not None else {}
    if bundle["stds_id"] != stds_id:
        raise CoordinatorError("bound stds_id does not match current manifests")
    context = candidate_context(bundle, candidate_id)
    return bundle, context


def _ids_from_manifest(records: Any, context: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
    values = require_list(records, context)
    index = unique_index(values, "id", context)
    return [require_string(require_mapping(value, context).get("id"), f"{context}.id") for value in values], index


def _validate_used_objects(manifest: dict[str, Any], context: dict[str, Any]) -> None:
    data_ids, data_entries = _ids_from_manifest(manifest.get("used_data_objects"), "used_data_objects")
    if set(data_ids) != set(context["used_data_ids"]) or len(data_ids) != len(
        context["used_data_ids"]
    ):
        raise CoordinatorError("used_data_objects does not equal the candidate Dxx boundary")
    for data_id, entry in data_entries.items():
        artifact_refs = require_list(entry.get("artifact_refs"), f"used_data_objects.{data_id}.artifact_refs")
        referenced_paths = {
            require_string(require_mapping(raw, "artifact_ref").get("path_or_locator"), "artifact_ref.path")
            for raw in artifact_refs
        }
        expected_paths = set(context["required_paths"].get(data_id, []))
        if len(artifact_refs) != len(referenced_paths) or referenced_paths != expected_paths:
            raise CoordinatorError(
                f"used_data_objects artifact refs do not exactly match required paths for {data_id}"
            )

    aux_ids, aux_entries = _ids_from_manifest(
        manifest.get("used_auxiliary_resources"), "used_auxiliary_resources"
    )
    if set(aux_ids) != set(context["used_auxiliary_ids"]) or len(aux_ids) != len(
        context["used_auxiliary_ids"]
    ):
        raise CoordinatorError(
            "used_auxiliary_resources does not equal the candidate Axx boundary"
        )
    for aux_id, entry in aux_entries.items():
        source = context["auxiliary_resources"][aux_id]
        if source.get("local_availability") == "absent":
            expected = {
                "id": aux_id,
                "role": entry.get("role"),
                **external_auxiliary_identity(source),
                "local_availability": "absent",
                "required_by_scientific_units": entry.get(
                    "required_by_scientific_units"
                ),
                "required_by_execution_subchains": entry.get(
                    "required_by_execution_subchains"
                ),
            }
            if entry != expected:
                raise CoordinatorError(
                    f"unresolved auxiliary wrapper differs from Round 3 for {aux_id}"
                )
            continue
        source_binding = require_mapping(
            source.get("localization_binding"), f"{aux_id}.localization_binding"
        )
        source_package = require_mapping(
            source_binding.get("package_manifest"), f"{aux_id}.package_manifest"
        )
        package_id = source_package.get("package_id")
        if entry.get("canonical_resource_id") != package_id:
            raise CoordinatorError(f"used auxiliary canonical resource ID mismatch for {aux_id}")
        if entry.get("package_id") != package_id:
            raise CoordinatorError(f"used auxiliary package ID mismatch for {aux_id}")
        entry_binding = require_mapping(
            entry.get("localization_binding"), f"used auxiliary {aux_id}.localization_binding"
        )
        if set(entry_binding) != {"package_manifest"}:
            raise CoordinatorError(f"used auxiliary package binding has extra fields for {aux_id}")
        if entry_binding.get("package_manifest") != source_package:
            raise CoordinatorError(f"used auxiliary package binding mismatch for {aux_id}")
        case_artifacts = require_list(source_binding.get("artifacts"), f"{aux_id}.artifacts")
        expected_refs = [
            {field: artifact.get(field) for field in ("artifact_id", "path", "sha256")}
            for artifact in case_artifacts
        ]
        if entry.get("artifact_refs") != expected_refs:
            raise CoordinatorError(f"used auxiliary artifact refs mismatch for {aux_id}")


def read_jsonl(path: Path, schema: dict[str, Any], context: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise CoordinatorError(f"cannot read JSONL {path}: {error}") from error
    if not lines or any(not line.strip() for line in lines):
        raise CoordinatorError(f"{context} must contain only nonempty JSONL rows")
    for number, line in enumerate(lines, 1):
        try:
            record = require_mapping(json.loads(line), f"{context} line {number}")
        except (json.JSONDecodeError, CoordinatorError) as error:
            raise CoordinatorError(f"invalid {context} line {number}: {error}") from error
        _validate_schema_value(record, schema, f"{context} line {number}")
        output.append(record)
    return output


def _validate_json_schema(
    value: Any, schema: dict[str, Any], root: dict[str, Any], context: str
) -> None:
    """Validate the JSON-Schema subset used by the two immutable row schemas."""
    if "$ref" in schema:
        reference = require_string(schema["$ref"], f"{context}.$ref")
        if not reference.startswith("#/"):
            raise CoordinatorError(f"unsupported schema reference {reference}")
        resolved: Any = root
        for part in reference[2:].split("/"):
            resolved = require_mapping(resolved, "schema reference").get(part)
        _validate_json_schema(value, require_mapping(resolved, reference), root, context)
        return
    if "oneOf" in schema:
        matches = 0
        for option in require_list(schema["oneOf"], f"{context}.oneOf"):
            try:
                _validate_json_schema(value, require_mapping(option, "oneOf option"), root, context)
            except CoordinatorError:
                continue
            matches += 1
        if matches != 1:
            raise CoordinatorError(f"{context} must match exactly one schema branch")
        return
    allowed_types = schema.get("type")
    if allowed_types is not None:
        types = allowed_types if isinstance(allowed_types, list) else [allowed_types]
        predicates = {
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "string": lambda item: isinstance(item, str),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "boolean": lambda item: isinstance(item, bool),
            "null": lambda item: item is None,
        }
        if not any(kind in predicates and predicates[kind](value) for kind in types):
            raise CoordinatorError(f"{context} has wrong type")
    def json_equal(left: Any, right: Any) -> bool:
        if isinstance(left, bool) or isinstance(right, bool):
            return isinstance(left, bool) and isinstance(right, bool) and left == right
        if left is None or right is None:
            return left is None and right is None
        return type(left) is type(right) and left == right

    if "const" in schema and not json_equal(value, schema["const"]):
        raise CoordinatorError(f"{context} does not equal its required constant")
    if "enum" in schema and not any(json_equal(value, option) for option in schema["enum"]):
        raise CoordinatorError(f"{context} is not an allowed value")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise CoordinatorError(f"{context} is too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise CoordinatorError(f"{context} does not match {schema['pattern']}")
    elif isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise CoordinatorError(f"{context} is below its minimum")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise CoordinatorError(f"{context} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise CoordinatorError(f"{context} has too many items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                raise CoordinatorError(f"{context} items are not unique")
        if "items" in schema:
            item_schema = require_mapping(schema["items"], f"{context}.items")
            for index, item in enumerate(value):
                _validate_json_schema(item, item_schema, root, f"{context}[{index}]")
    elif isinstance(value, dict):
        required = schema.get("required", [])
        if any(field not in value for field in required):
            missing = [field for field in required if field not in value]
            raise CoordinatorError(f"{context} is missing {missing}")
        properties = require_mapping(schema.get("properties", {}), f"{context}.properties")
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                raise CoordinatorError(f"{context} has extra fields {sorted(extras)}")
        for field, child in value.items():
            if field in properties:
                _validate_json_schema(
                    child,
                    require_mapping(properties[field], f"schema.{field}"),
                    root,
                    f"{context}.{field}",
                )


def _load_schema(repository_root: Path, name: str) -> dict[str, Any]:
    path = repository_root / "contracts/schemas" / name
    try:
        return require_mapping(json.loads(path.read_bytes()), str(path))
    except (OSError, json.JSONDecodeError) as error:
        raise CoordinatorError(f"cannot load schema {path}: {error}") from error


def _validate_schema_value(
    value: Any, schema: dict[str, Any], context: str
) -> None:
    if jsonschema is not None:
        errors = sorted(
            jsonschema.Draft202012Validator(schema).iter_errors(value),
            key=lambda error: list(error.path),
        )
        if errors:
            raise CoordinatorError(f"{context} schema failure: {errors[0].message}")
        return
    try:
        _validate_json_schema(value, schema, schema, context)
    except CoordinatorError as error:
        raise CoordinatorError(f"{context} schema failure: {error}") from error


def _reject_placeholders(value: Any, context: str) -> None:
    if PLACEHOLDER_PATTERN.search(json.dumps(value, ensure_ascii=False, sort_keys=True)):
        raise CoordinatorError(f"placeholder marker found in {context}")


def _validate_jsonl_invariants(
    scientific: list[dict[str, Any]], execution: list[dict[str, Any]]
) -> None:
    if len(scientific) < 2 or scientific[0].get("scientific_unit_id") != "S00":
        raise CoordinatorError("scientific chain must start with one S00 and at least one HVU")
    scientific_ids = [record["scientific_unit_id"] for record in scientific]
    expected_scientific = ["S00"] + [f"S{index:02d}" for index in range(1, len(scientific))]
    if scientific_ids != expected_scientific:
        raise CoordinatorError(f"scientific unit IDs are not unique and sequential: {scientific_ids}")
    hvu_by_id = {record["scientific_unit_id"]: record for record in scientific[1:]}
    seen: set[str] = set()
    for record in scientific[1:]:
        identifier = record["scientific_unit_id"]
        parents = record["parent_units"]
        if identifier in parents or any(parent not in hvu_by_id for parent in parents):
            raise CoordinatorError(f"unresolved parent link for {identifier}")
        if any(parent not in seen for parent in parents):
            raise CoordinatorError(f"parent link is not topologically ordered for {identifier}")
        seen.add(identifier)

    execution_ids = [record["execution_subchain_id"] for record in execution]
    expected_execution = [f"E{index:02d}" for index in range(1, len(execution) + 1)]
    if execution_ids != expected_execution or len(execution) != len(hvu_by_id):
        raise CoordinatorError("execution IDs must be unique, sequential, and one per HVU")
    execution_by_id = {record["execution_subchain_id"]: record for record in execution}
    linked_units: list[str] = []
    for scientific_id, record in hvu_by_id.items():
        links = record["experiment"]["execution_subchain_ids"]
        if len(links) != 1 or links[0] not in execution_by_id:
            raise CoordinatorError(f"{scientific_id} must link to exactly one execution subchain")
        linked = execution_by_id[links[0]]
        if linked["linked_scientific_unit_id"] != scientific_id:
            raise CoordinatorError(f"scientific/execution link mismatch for {scientific_id}")
        if linked["result_extraction"]["observations"] != record["result"]["observations"]:
            raise CoordinatorError(f"result observations differ for {scientific_id}")
        linked_units.append(scientific_id)
    if len(linked_units) != len(set(linked_units)):
        raise CoordinatorError("multiple primary execution routes link to one HVU")

    known_outputs: dict[str, dict[str, Any]] = {}
    for record in execution:
        execution_id = record["execution_subchain_id"]
        for index, step in enumerate(record["steps"], 1):
            if step["step_id"] != f"{execution_id}.{index}":
                raise CoordinatorError(f"nonsequential step ID in {execution_id}")
            for input_object in step["inputs"]:
                identifier = input_object["id"]
                if identifier in known_outputs and input_object != known_outputs[identifier]:
                    raise CoordinatorError(f"object continuity mismatch for {identifier}")
            for output_object in step["outputs"]:
                identifier = output_object["id"]
                if identifier in known_outputs and output_object != known_outputs[identifier]:
                    raise CoordinatorError(f"conflicting output object ID {identifier}")
                known_outputs[identifier] = output_object


def _validate_execution_source_references(
    execution: list[dict[str, Any]], context: dict[str, Any]
) -> None:
    locators: list[str] = []
    for result_id in context["candidate"]["result_order"]:
        result = context["source_results"][result_id]
        locators.append(require_string(result.get("result_section"), "result_section"))
        for raw_anchor in result["source_anchors"]:
            anchor = require_mapping(raw_anchor, "source anchor")
            locators.append(require_string(anchor.get("locator"), "source anchor locator"))
    for subchain in execution:
        for step in subchain["steps"]:
            source_ref = require_mapping(step.get("source_ref"), f"{step['step_id']}.source_ref")
            locator = require_string(source_ref.get("locator"), f"{step['step_id']}.locator")
            if not any(_locator_matches(locator, value) for value in locators):
                raise CoordinatorError(
                    f"execution source locator escapes selected candidate: {step['step_id']}"
                )


def _locator_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z]+|[0-9]+", value.lower())


def _locator_matches(observed: str, admitted: str) -> bool:
    observed_tokens = _locator_tokens(observed)
    admitted_tokens = _locator_tokens(admitted)
    if not observed_tokens or not admitted_tokens:
        return False
    shorter, longer = sorted((observed_tokens, admitted_tokens), key=len)
    return any(
        longer[index : index + len(shorter)] == shorter
        for index in range(len(longer) - len(shorter) + 1)
    )


def _validate_s00_data_context(
    scientific: list[dict[str, Any]], context: dict[str, Any]
) -> None:
    summary = require_mapping(scientific[0].get("data_summary"), "S00.data_summary")
    contexts = [
        require_mapping(
            context["data_objects"][data_id].get("data_context"),
            f"{data_id}.data_context",
        )
        for data_id in context["used_data_ids"]
    ]
    organisms = {
        require_string(value.get("organism"), "data_context.organism") for value in contexts
    }
    if len(organisms) == 1 and summary.get("organism") != next(iter(organisms)):
        raise CoordinatorError("S00 organism is not derived from candidate Dxx contexts")
    tissues = {
        require_string(value.get("tissue_or_context"), "data_context.tissue_or_context")
        for value in contexts
    }
    s00_tissue = require_string(summary.get("tissue"), "S00.data_summary.tissue")
    if len(tissues) == 1:
        tissue = next(iter(tissues))
        if tissue.lower() not in s00_tissue.lower() and s00_tissue.lower() not in tissue.lower():
            raise CoordinatorError("S00 tissue is not derived from candidate Dxx contexts")
    assays = {
        require_string(value.get("spatial_assay"), "data_context.spatial_assay")
        for value in contexts
    }
    data_types = require_list(summary.get("data_types"), "S00.data_types")
    if not any(
        isinstance(data_type, str)
        and (data_type.lower() in assay.lower() or assay.lower() in data_type.lower())
        for data_type in data_types
        for assay in assays
    ):
        raise CoordinatorError("S00 data types are not derived from candidate Dxx contexts")
    sample_count = summary.get("sample_count")
    if sample_count is not None:
        selected_count = len(context["candidate_sample_ids"])
        if context["used_auxiliary_ids"]:
            if sample_count < selected_count:
                raise CoordinatorError(
                    "S00 sample_count is smaller than selected Dxx sample IDs"
                )
        elif sample_count != selected_count:
            raise CoordinatorError("S00 sample_count differs from selected sample IDs")


def _validate_execution_object_resolution(
    manifest: dict[str, Any], execution: list[dict[str, Any]]
) -> None:
    resource_tokens: dict[str, set[str]] = {}
    for raw in manifest["used_data_objects"]:
        record = require_mapping(raw, "used_data_object")
        resource_id = record["id"]
        tokens = {resource_id}
        for raw_ref in record["artifact_refs"]:
            ref = require_mapping(raw_ref, f"{resource_id}.artifact_ref")
            tokens.add(require_string(ref.get("name"), f"{resource_id}.artifact_ref.name"))
            tokens.add(
                require_string(
                    ref.get("path_or_locator"), f"{resource_id}.artifact_ref.path"
                )
            )
        resource_tokens[resource_id] = tokens
    for raw in manifest["used_auxiliary_resources"]:
        record = require_mapping(raw, "used_auxiliary_resource")
        resource_id = record["id"]
        tokens = {resource_id}
        if record.get("local_availability") == "absent":
            tokens.add(
                require_string(record.get("resource_name"), f"{resource_id}.resource_name")
            )
        else:
            tokens.update(
                {
                    require_string(
                        record.get("canonical_resource_id"),
                        f"{resource_id}.canonical_id",
                    ),
                    require_string(record.get("package_id"), f"{resource_id}.package_id"),
                }
            )
            for raw_ref in record["artifact_refs"]:
                ref = require_mapping(raw_ref, f"{resource_id}.artifact_ref")
                tokens.add(
                    require_string(ref.get("artifact_id"), f"{resource_id}.artifact_id")
                )
                tokens.add(require_string(ref.get("path"), f"{resource_id}.artifact_path"))
        resource_tokens[resource_id] = tokens
    all_tokens = set().union(*resource_tokens.values()) if resource_tokens else set()
    execution_by_id = {value["execution_subchain_id"]: value for value in execution}
    external_by_execution: dict[str, set[str]] = {}
    produced: set[str] = set()
    for execution_id, subchain in execution_by_id.items():
        external: set[str] = set()
        for step in subchain["steps"]:
            for input_object in step["inputs"]:
                identifier = input_object["id"]
                if identifier not in produced:
                    if identifier not in all_tokens:
                        raise CoordinatorError(
                            f"unresolved external execution input {identifier} in {execution_id}"
                        )
                    external.add(identifier)
            produced.update(value["id"] for value in step["outputs"])
        external_by_execution[execution_id] = external
    for field in ("used_data_objects", "used_auxiliary_resources"):
        for record in manifest[field]:
            resource_id = record["id"]
            for execution_id in record["required_by_execution_subchains"]:
                if not external_by_execution[execution_id] & resource_tokens[resource_id]:
                    raise CoordinatorError(
                        f"{execution_id} does not consume declared resource {resource_id}"
                    )


def _validate_wrapper_unit_references(
    manifest: dict[str, Any],
    scientific: list[dict[str, Any]],
    execution: list[dict[str, Any]],
) -> None:
    scientific_ids = {value["scientific_unit_id"] for value in scientific[1:]}
    execution_ids = {value["execution_subchain_id"] for value in execution}
    execution_to_scientific = {
        value["execution_subchain_id"]: value["linked_scientific_unit_id"]
        for value in execution
    }
    for field in ("used_data_objects", "used_auxiliary_resources"):
        for raw in require_list(manifest.get(field), field):
            record = require_mapping(raw, field)
            identifier = require_string(record.get("id"), f"{field}.id")
            required_scientific = require_list(
                record.get("required_by_scientific_units"),
                f"{field}.{identifier}.required_by_scientific_units",
            )
            required_execution = require_list(
                record.get("required_by_execution_subchains"),
                f"{field}.{identifier}.required_by_execution_subchains",
            )
            if (
                not required_scientific
                or len(required_scientific) != len(set(required_scientific))
                or any(value not in scientific_ids for value in required_scientific)
            ):
                raise CoordinatorError(f"unresolved scientific-unit reference for {identifier}")
            if (
                not required_execution
                or len(required_execution) != len(set(required_execution))
                or any(value not in execution_ids for value in required_execution)
            ):
                raise CoordinatorError(f"unresolved execution-subchain reference for {identifier}")
            expected_scientific = {
                execution_to_scientific[value] for value in required_execution
            }
            if not expected_scientific.issubset(set(required_scientific)):
                raise CoordinatorError(
                    f"scientific wrapper omits the direct Sxx consumer for {identifier}"
                )


def _validate_round3_result_bindings(
    manifest: dict[str, Any],
    scientific: list[dict[str, Any]],
    execution: list[dict[str, Any]],
    context: dict[str, Any],
    *,
    allow_legacy_missing: bool,
) -> None:
    raw_bindings = manifest.get("round3_result_bindings")
    if raw_bindings is None:
        if allow_legacy_missing:
            return
        raise CoordinatorError("new extraction is missing round3_result_bindings")
    bindings = require_list(raw_bindings, "round3_result_bindings")
    expected_results = context["candidate"]["result_order"]
    result_ids = [
        require_string(require_mapping(value, "round3_result_binding").get("result_id"), "result_id")
        for value in bindings
    ]
    if result_ids != expected_results:
        raise CoordinatorError(
            f"round3_result_bindings must equal candidate result_order: {result_ids}"
        )
    scientific_by_id = {value["scientific_unit_id"]: value for value in scientific[1:]}
    execution_by_id = {value["execution_subchain_id"]: value for value in execution}
    seen_scientific: set[str] = set()
    seen_execution: set[str] = set()
    for raw in bindings:
        binding = require_mapping(raw, "round3_result_binding")
        result_id = binding["result_id"]
        scientific_ids = require_list(binding.get("scientific_unit_ids"), f"{result_id}.scientific_unit_ids")
        execution_ids = require_list(binding.get("execution_subchain_ids"), f"{result_id}.execution_subchain_ids")
        if seen_scientific.intersection(scientific_ids) or seen_execution.intersection(execution_ids):
            raise CoordinatorError("Sxx/Exx may belong to only one Round 3 result binding")
        seen_scientific.update(scientific_ids)
        seen_execution.update(execution_ids)
        if any(value not in scientific_by_id for value in scientific_ids):
            raise CoordinatorError(f"{result_id} has unresolved scientific-unit binding")
        if any(value not in execution_by_id for value in execution_ids):
            raise CoordinatorError(f"{result_id} has unresolved execution binding")
        for execution_id in execution_ids:
            linked = execution_by_id[execution_id]["linked_scientific_unit_id"]
            if linked not in scientific_ids:
                raise CoordinatorError(f"{result_id} binds {execution_id} outside its Sxx set")
            if execution_id not in scientific_by_id[linked]["experiment"]["execution_subchain_ids"]:
                raise CoordinatorError(f"{result_id} has a broken Sxx/Exx link")
        result = context["source_results"][result_id]
        admitted = [require_string(result.get("result_section"), f"{result_id}.result_section")]
        admitted.extend(
            require_string(require_mapping(anchor, f"{result_id}.source_anchor").get("locator"), f"{result_id}.source_anchor.locator")
            for anchor in result["source_anchors"]
        )
        for execution_id in execution_ids:
            for step in execution_by_id[execution_id]["steps"]:
                locator = require_string(
                    require_mapping(step.get("source_ref"), f"{step['step_id']}.source_ref").get("locator"),
                    f"{step['step_id']}.locator",
                )
                if not any(_locator_matches(locator, value) for value in admitted):
                    raise CoordinatorError(
                        f"{execution_id} source locator is not bound to {result_id}"
                    )
    if seen_scientific != set(scientific_by_id) or seen_execution != set(execution_by_id):
        raise CoordinatorError("round3_result_bindings do not cover every non-S00 Sxx and Exx")


def _validate_manifest_identity(
    manifest: dict[str, Any], bundle: dict[str, Any], context: dict[str, Any]
) -> None:
    candidate_id = context["candidate"]["candidate_id"]
    expected_chain_id = chain_id(bundle["case_id"], candidate_id)
    expected = {
        "case_id": bundle["case_id"],
        "chain_id": expected_chain_id,
        "case_route": "public_database_stomicsdb",
        "chain_origin": "case_derived",
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise CoordinatorError(f"chain manifest {field} mismatch")
    if manifest["input_binding"].get("stds_id") != bundle["stds_id"]:
        raise CoordinatorError("chain manifest stds_id mismatch")
    if manifest["input_binding"].get("candidate_id") != candidate_id:
        raise CoordinatorError("chain manifest candidate_id mismatch")
    if manifest.get("source_manifest") != manifest["input_binding"]["source_manifest"]["path"]:
        raise CoordinatorError("chain manifest source_manifest duplicate binding mismatch")
    if manifest.get("case_data_manifest") != manifest["input_binding"]["case_data_manifest"]["path"]:
        raise CoordinatorError("chain manifest case_data_manifest duplicate binding mismatch")
    readiness = require_mapping(manifest.get("data_readiness"), "data_readiness")
    unresolved = context["unresolved_auxiliary_ids"]
    expected_readiness = {
        "status": "BLOCKED_EXTERNAL" if unresolved else "DATA_READY",
        "required_data_objects_resolved": "no" if unresolved else "yes",
        "unresolved_data_objects": unresolved,
    }
    for field, expected_value in expected_readiness.items():
        if readiness.get(field) != expected_value:
            raise CoordinatorError(
                f"chain manifest data_readiness {field} does not match bound inputs"
            )
    _validate_used_objects(manifest, context)


def _validate_review_record(
    manifest: dict[str, Any],
    context: dict[str, Any],
    data_root: Path,
    *,
    require_source_coverage: bool,
) -> None:
    independent = require_mapping(manifest.get("independent_check"), "independent_check")
    status = independent.get("status")
    if status == "not_started":
        return
    if independent.get("reviewer_independence") != "independent_curator":
        raise CoordinatorError("STOmicsDB review must use an independent curator")
    expected_notes = f"dual_chain/{manifest['chain_id']}/independent_check.md"
    if independent.get("notes_location") != expected_notes:
        raise CoordinatorError("independent_check.notes_location is not canonical")
    checked_sources = require_list(independent.get("checked_sources"), "checked_sources")
    if not checked_sources:
        raise CoordinatorError("completed review must record checked_sources")
    if require_source_coverage:
        for result_id in context["candidate"]["result_order"]:
            result = context["source_results"][result_id]
            admitted = [require_string(result.get("result_section"), f"{result_id}.result_section")]
            admitted.extend(
                require_string(require_mapping(anchor, f"{result_id}.source_anchor").get("locator"), f"{result_id}.source_anchor.locator")
                for anchor in result["source_anchors"]
            )
            if not any(
                _locator_matches(
                    require_string(require_mapping(record, "checked_source").get("locator"), "checked_source.locator"),
                    locator,
                )
                for record in checked_sources
                for locator in admitted
            ):
                raise CoordinatorError(f"review does not record source coverage for {result_id}")
    checked_data = require_list(
        independent.get("checked_data_objects"), "checked_data_objects"
    )
    checked_ids = [
        require_string(require_mapping(record, "checked_data_object").get("id"), "checked_data_object.id")
        for record in checked_data
    ]
    localized_auxiliary_ids = [
        value
        for value in context["used_auxiliary_ids"]
        if value not in context["unresolved_auxiliary_ids"]
    ]
    expected_ids = context["used_data_ids"] + localized_auxiliary_ids
    if require_source_coverage:
        if set(checked_ids) != set(expected_ids) or len(checked_ids) != len(expected_ids):
            raise CoordinatorError("review checked_data_objects do not equal the Dxx/Axx boundary")
    elif (
        not set(context["used_data_ids"]).issubset(set(checked_ids))
        or not set(checked_ids).issubset(set(expected_ids))
        or len(checked_ids) != len(set(checked_ids))
    ):
        raise CoordinatorError("legacy review checked_data_objects are outside the bound inputs")
    checked_unresolved = independent.get("checked_unresolved_auxiliary_resource_ids", [])
    checked_unresolved = require_list(
        checked_unresolved, "checked_unresolved_auxiliary_resource_ids"
    )
    if require_source_coverage and checked_unresolved != context["unresolved_auxiliary_ids"]:
        raise CoordinatorError(
            "review checked unresolved Axx IDs do not equal the external boundary"
        )
    if not require_source_coverage and not set(checked_unresolved).issubset(
        set(context["unresolved_auxiliary_ids"])
    ):
        raise CoordinatorError("legacy review checked unresolved Axx IDs are out of scope")
    for record in checked_data:
        value = require_mapping(record, "checked_data_object")
        path = resolve_data_path(
            require_string(value.get("local_or_prepared_path"), "checked_data_object.path"),
            data_root,
        )
        if not path.exists() or path.is_symlink() or not os.access(path, os.R_OK):
            raise CoordinatorError(f"review checked path is not readable: {path}")


def validate_chain_directory(
    directory: Path,
    data_root: Path,
    repository_root: Path,
    *,
    final: bool = False,
    reviewed: bool = False,
    allow_legacy_result_bindings: bool = False,
    hash_cache: HashCache | None = None,
) -> dict[str, Any]:
    if final and reviewed:
        raise CoordinatorError("final and reviewed validation modes are mutually exclusive")
    hash_cache = hash_cache if hash_cache is not None else {}
    exact_files(directory, FINAL_FILENAMES if final or reviewed else EXTRACTION_FILENAMES)
    manifest = load_yaml(directory / "chain_manifest.yaml")
    manifest_schema = _load_schema(
        repository_root, "stomicsdb_dual_chain_manifest.schema.json"
    )
    _validate_schema_value(manifest, manifest_schema, "chain_manifest")
    bundle, context = _load_bound_case(manifest, data_root, hash_cache)
    _validate_manifest_identity(manifest, bundle, context)
    if final or reviewed:
        independent = require_mapping(manifest.get("independent_check"), "independent_check")
        ready_status = (
            "specification_ready"
            if context["unresolved_auxiliary_ids"]
            else "comparison_ready"
        )
        compatible = {
            "confirmed": ready_status,
            "needs_revision": "needs_revision",
            "blocked": "blocked",
        }
        review_status = independent.get("status")
        if review_status not in compatible or manifest.get("chain_status") != compatible[review_status]:
            raise CoordinatorError("review status and chain_status are incompatible")
        if final and review_status != "confirmed":
            raise CoordinatorError("final independent check must be confirmed")
        expected_notes = f"dual_chain/{manifest['chain_id']}/independent_check.md"
        if independent.get("notes_location") != expected_notes:
            raise CoordinatorError("independent_check.notes_location is not canonical")
        scope = independent.get("revision_scope")
        if review_status == "needs_revision" and scope not in {
            "extraction",
            "round3_handoff",
        }:
            raise CoordinatorError("needs_revision review must declare revision_scope")
        if review_status != "needs_revision" and scope is not None:
            raise CoordinatorError("revision_scope is only valid for needs_revision")
        notes = (directory / "independent_check.md").read_text(encoding="utf-8")
        if not notes.strip():
            raise CoordinatorError("independent_check.md is empty")
        _reject_placeholders(notes, "independent_check.md")
        _validate_review_record(
            manifest, context, data_root, require_source_coverage=False
        )
    else:
        if manifest.get("chain_status") != "draft":
            raise CoordinatorError("extraction chain_status must be draft")
        independent = require_mapping(manifest.get("independent_check"), "independent_check")
        if independent.get("status") != "not_started":
            raise CoordinatorError("extraction independent check must be not_started")
    scientific_schema = _load_schema(repository_root, "scientific_chain.schema.json")
    execution_schema = _load_schema(repository_root, "execution_subchains.schema.json")
    scientific = read_jsonl(
        directory / "scientific_chain.jsonl", scientific_schema, "scientific_chain"
    )
    execution = read_jsonl(
        directory / "execution_subchains.jsonl", execution_schema, "execution_subchains"
    )
    _validate_jsonl_invariants(scientific, execution)
    _validate_execution_source_references(execution, context)
    _validate_s00_data_context(scientific, context)
    _validate_execution_object_resolution(manifest, execution)
    _validate_wrapper_unit_references(manifest, scientific, execution)
    _validate_round3_result_bindings(
        manifest,
        scientific,
        execution,
        context,
        allow_legacy_missing=(
            allow_legacy_result_bindings
            or bool(final and manifest.get("chain_status") == "comparison_ready")
        ),
    )
    _reject_placeholders(manifest, "chain_manifest")
    _reject_placeholders(scientific, "scientific_chain")
    _reject_placeholders(execution, "execution_subchains")
    return {
        "manifest": manifest,
        "bundle": bundle,
        "context": context,
        "scientific": scientific,
        "execution": execution,
    }


def validate_extraction_staging(
    staging_directory: Path,
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
    hash_cache: HashCache | None = None,
) -> dict[str, Any]:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    _require_staging_directory(staging_directory, data_root)
    validated = validate_chain_directory(
        staging_directory,
        data_root,
        repository_root,
        final=False,
        hash_cache=hash_cache,
    )
    _require_attempt_directory(
        staging_directory, data_root, "extraction", validated["manifest"]["chain_id"]
    )
    return validated


def _require_staging_directory(directory: Path, data_root: Path) -> None:
    relative = PurePosixPath(data_relative(directory, data_root))
    prefix = STOMICS_REL / "staging"
    if tuple(relative.parts[: len(prefix.parts)]) != tuple(prefix.parts):
        raise CoordinatorError(f"directory is outside STOmicsDB staging: {relative}")


def _require_attempt_directory(
    directory: Path, data_root: Path, kind: str, chain_identifier: str
) -> None:
    relative = PurePosixPath(data_relative(directory, data_root))
    prefix = STOMICS_REL / "staging" / "dual_chain" / kind
    if (
        tuple(relative.parts[: len(prefix.parts)]) != tuple(prefix.parts)
        or len(relative.parts) != len(prefix.parts) + 2
        or relative.parts[-1] != chain_identifier
        or not IDENTIFIER_PATTERN.fullmatch(relative.parts[-2])
    ):
        raise CoordinatorError(
            f"{kind} staging is outside its canonical assigned attempt root: {relative}"
        )


class ChainLock:
    def __init__(
        self,
        data_root: Path,
        chain_identifier: str,
        operation_id: str,
        *,
        recover_stale: bool = False,
    ):
        if not IDENTIFIER_PATTERN.fullmatch(chain_identifier) or len(chain_identifier) > MAX_IDENTIFIER_LENGTH:
            raise CoordinatorError(f"unsafe chain ID: {chain_identifier}")
        if not IDENTIFIER_PATTERN.fullmatch(operation_id) or len(operation_id) > MAX_IDENTIFIER_LENGTH:
            raise CoordinatorError(f"unsafe operation ID: {operation_id}")
        self.data_root = data_root
        self.path = data_root.joinpath(
            *STOMICS_REL.parts, "staging/dual_chain/locks", f"{chain_identifier}.lock"
        )
        self.operation_id = operation_id
        self.recover_stale = recover_stale

    @staticmethod
    def _process_start_time(pid: int) -> str | None:
        try:
            return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()[21]
        except (OSError, IndexError):
            return None

    def _remove_proven_stale_lock(self) -> None:
        owner_path = self.path / "owner.yaml"
        owner = load_yaml(owner_path)
        if owner.get("chain_id") != self.path.name.removesuffix(".lock"):
            raise CoordinatorError(f"stale lock owner identity mismatch: {self.path}")
        pid = owner.get("pid")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise CoordinatorError(f"stale lock has invalid PID: {self.path}")
        recorded_start = owner.get("process_start_time")
        current_start = self._process_start_time(pid)
        if current_start is None:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            except PermissionError as error:
                raise CoordinatorError(f"live chain lock exists: {self.path}") from error
            else:
                raise CoordinatorError(
                    f"cannot prove existing chain lock is stale: {self.path}"
                )
        else:
            if not isinstance(recorded_start, str):
                raise CoordinatorError(f"cannot prove existing chain lock is stale: {self.path}")
            if current_start == recorded_start:
                raise CoordinatorError(f"live chain lock exists: {self.path}")
        exact_files(self.path, ("owner.yaml",))
        owner_path.unlink()
        self.path.rmdir()
        fsync_directory(self.path.parent)

    def __enter__(self) -> "ChainLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.mkdir()
        except FileExistsError as error:
            if not self.recover_stale:
                raise CoordinatorError(f"live or orphan chain lock exists: {self.path}") from error
            self._remove_proven_stale_lock()
            self.path.mkdir()
        pid = os.getpid()
        owner = {
            "chain_id": self.path.name.removesuffix(".lock"),
            "operation_id": self.operation_id,
            "pid": pid,
            "process_start_time": self._process_start_time(pid),
            "created_at": utc_now(),
            "lock_path": data_relative(self.path, self.data_root),
        }
        try:
            atomic_write_yaml(self.path / "owner.yaml", owner)
        except Exception:
            self.path.rmdir()
            raise
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        (self.path / "owner.yaml").unlink(missing_ok=True)
        try:
            self.path.rmdir()
        except FileNotFoundError:
            pass


def _require_target_chain(
    final_directory: Path,
    data_root: Path,
    identifier: str,
    case_id: str,
) -> None:
    expected = STOMICS_REL / "cases" / case_id / "dual_chain" / identifier
    relative = PurePosixPath(data_relative(final_directory, data_root))
    if relative != expected:
        raise CoordinatorError(f"final chain path does not match bound case: {relative}")


def _assigned_stage_for_round(
    assignment: dict[str, Any], kind: str, round_index: int
) -> Path:
    if kind not in {"extraction", "review"} or round_index not in range(3):
        raise CoordinatorError(f"invalid assigned stage round: {kind} r{round_index}")
    field = f"{kind}_staging_directory"
    initial = Path(require_string(assignment.get(field), field))
    if round_index == 0:
        return initial
    return initial.parent.parent / f"{assignment['job_attempt_id']}.r{round_index}" / assignment["chain_id"]


def _validate_publication_assignment(
    assignment: dict[str, Any],
    staging_directory: Path,
    final_directory: Path,
    kind: str,
    round_index: int,
    data_root: Path,
    repository_root: Path,
) -> None:
    _validate_job_assignment_invariants(
        assignment,
        data_root,
        repository_root,
        revalidate_inputs=False,
        revalidate_state=False,
    )
    if staging_directory.resolve() != _assigned_stage_for_round(
        assignment, kind, round_index
    ).resolve():
        raise CoordinatorError("publication staging path does not match assignment round")
    if final_directory.resolve() != Path(assignment["final_chain_directory"]).resolve():
        raise CoordinatorError("publication final path does not match assignment")


def publish_initial(
    staging_directory: Path,
    final_directory: Path,
    operation_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
    assignment: dict[str, Any] | None = None,
) -> None:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    staged_manifest = load_yaml(staging_directory / "chain_manifest.yaml")
    identifier = require_string(staged_manifest.get("chain_id"), "chain_id")
    case_id = require_string(staged_manifest.get("case_id"), "case_id")
    if assignment is not None:
        _validate_publication_assignment(
            assignment,
            staging_directory,
            final_directory,
            "extraction",
            0,
            data_root,
            repository_root,
        )
        if assignment.get("next_action") != "extract_initial":
            raise CoordinatorError("assignment does not authorize initial extraction")
    _require_attempt_directory(staging_directory, data_root, "extraction", identifier)
    _require_target_chain(final_directory, data_root, identifier, case_id)
    if staging_directory.stat().st_dev != final_directory.parent.parent.stat().st_dev:
        raise CoordinatorError("staging and final chain are not on the same filesystem")
    hash_cache: HashCache = {}
    with ChainLock(data_root, identifier, operation_id):
        validated = validate_extraction_staging(
            staging_directory, data_root, repository_root, hash_cache
        )
        if (
            validated["manifest"]["chain_id"] != identifier
            or validated["manifest"]["case_id"] != case_id
        ):
            raise CoordinatorError("staged chain identity changed before publication")
        if final_directory.exists():
            raise CoordinatorError(f"final chain already exists: {final_directory}")
        final_directory.parent.mkdir(parents=True, exist_ok=True)
        if staging_directory.stat().st_dev != final_directory.parent.stat().st_dev:
            raise CoordinatorError("staging and final chain are not on the same filesystem")
        os.replace(staging_directory, final_directory)
        fsync_directory(final_directory.parent)
        try:
            validate_chain_directory(
                final_directory,
                data_root,
                repository_root,
                final=False,
                hash_cache=hash_cache,
            )
        except Exception:
            os.replace(final_directory, staging_directory)
            fsync_directory(final_directory.parent)
            raise


def _validate_review_staging(
    review_staging: Path,
    chain_directory: Path,
    data_root: Path,
    repository_root: Path,
    hash_cache: HashCache | None = None,
) -> dict[str, Any]:
    exact_files(review_staging, REVIEW_FILENAMES)
    exact_files(chain_directory, EXTRACTION_FILENAMES)
    original = validate_chain_directory(
        chain_directory,
        data_root,
        repository_root,
        final=False,
        hash_cache=hash_cache,
    )
    replacement_bytes = (review_staging / "chain_manifest.yaml").read_bytes()
    notes_bytes = (review_staging / "independent_check.md").read_bytes()
    replacement = load_yaml_bytes(
        replacement_bytes, str(review_staging / "chain_manifest.yaml")
    )
    _validate_schema_value(
        replacement,
        _load_schema(repository_root, "stomicsdb_dual_chain_manifest.schema.json"),
        "review chain_manifest",
    )
    bundle, context = _load_bound_case(replacement, data_root, hash_cache)
    _validate_manifest_identity(replacement, bundle, context)
    _validate_review_record(
        replacement, context, data_root, require_source_coverage=True
    )
    status = require_mapping(replacement.get("independent_check"), "independent_check").get(
        "status"
    )
    ready_status = (
        "specification_ready"
        if context["unresolved_auxiliary_ids"]
        else "comparison_ready"
    )
    compatible = {
        "confirmed": ready_status,
        "needs_revision": "needs_revision",
        "blocked": "blocked",
    }
    if status not in compatible or replacement.get("chain_status") != compatible[status]:
        raise CoordinatorError("review status and chain_status are incompatible")
    original_without_review = deepcopy(original["manifest"])
    replacement_without_review = deepcopy(replacement)
    for value in (original_without_review, replacement_without_review):
        value.pop("chain_status", None)
        value.pop("independent_check", None)
    if replacement_without_review != original_without_review:
        raise CoordinatorError("Stage 4 may only replace review fields in chain_manifest.yaml")
    try:
        notes = notes_bytes.decode("utf-8")
    except UnicodeError as error:
        raise CoordinatorError(f"independent_check.md is not UTF-8: {error}") from error
    if not notes.strip():
        raise CoordinatorError("independent_check.md is empty")
    _reject_placeholders(notes, "independent_check.md")
    expected_chain_status = compatible[status]
    overall = re.search(
        r"(?mi)^-\s*Overall result:\s*(confirmed|needs_revision|blocked)\s*$", notes
    )
    recommendation = re.search(
        r"(?mi)^-\s*Chain status recommendation:\s*"
        r"(comparison_ready|specification_ready|needs_revision|blocked)\s*$",
        notes,
    )
    if overall is None or overall.group(1) != status:
        raise CoordinatorError("independent_check.md overall result disagrees with manifest")
    if recommendation is None or recommendation.group(1) != expected_chain_status:
        raise CoordinatorError("independent_check.md chain recommendation disagrees with manifest")
    findings = require_mapping(
        require_mapping(replacement.get("independent_check"), "independent_check").get(
            "findings_summary"
        ),
        "findings_summary",
    )
    blocking = require_list(findings.get("blocking"), "findings_summary.blocking")
    revisions = require_list(
        findings.get("needs_revision"), "findings_summary.needs_revision"
    )
    if status == "confirmed" and (blocking or revisions):
        raise CoordinatorError("confirmed review retains blocking or revision findings")
    if status == "needs_revision" and not revisions:
        raise CoordinatorError("needs_revision review has no revision finding")
    if status == "blocked" and not blocking:
        raise CoordinatorError("blocked review has no blocking finding")
    scope = require_mapping(
        replacement.get("independent_check"), "independent_check"
    ).get("revision_scope")
    if status == "needs_revision" and scope not in {"extraction", "round3_handoff"}:
        raise CoordinatorError("needs_revision review must declare revision_scope")
    if status != "needs_revision" and scope is not None:
        raise CoordinatorError("revision_scope is only valid for needs_revision")
    return {
        "manifest": replacement,
        "status": status,
        "manifest_bytes": replacement_bytes,
        "notes_bytes": notes_bytes,
    }


def _transaction_root(data_root: Path, transaction_id: str) -> Path:
    if not IDENTIFIER_PATTERN.fullmatch(transaction_id) or len(transaction_id) > MAX_IDENTIFIER_LENGTH:
        raise CoordinatorError(f"unsafe transaction ID: {transaction_id}")
    return data_root.joinpath(
        *STOMICS_REL.parts, "staging/dual_chain/transactions", transaction_id
    )


def _file_hashes(directory: Path, names: Iterable[str]) -> dict[str, str]:
    return {name: sha256_path(directory / name) for name in sorted(names)}


def _validate_hash_binding(value: dict[str, str], context: str) -> None:
    if set(value) != set(EXTRACTION_FILENAMES):
        raise CoordinatorError(f"{context} must bind exactly the three extraction files")
    for name, digest in value.items():
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise CoordinatorError(f"invalid {context} SHA-256 for {name}")


def _validate_mode(
    directory: Path,
    data_root: Path,
    repository_root: Path,
    mode: str,
    hash_cache: HashCache | None = None,
) -> None:
    if mode not in {"extraction", "reviewed", "final"}:
        raise CoordinatorError(f"invalid chain validation mode: {mode}")
    validate_chain_directory(
        directory,
        data_root,
        repository_root,
        final=mode == "final",
        reviewed=mode == "reviewed",
        hash_cache=hash_cache,
    )


def _rollback_transaction_locked(
    *,
    transaction: Path,
    record: dict[str, Any],
    chain_directory: Path,
    data_root: Path,
    repository_root: Path,
    hash_cache: HashCache | None = None,
 ) -> None:
    chain_identifier = require_string(record.get("chain_id"), "transaction.chain_id")
    prior_hashes = require_mapping(record.get("prior_file_hashes"), "prior_file_hashes")
    prior_mode = require_string(record.get("prior_validation_mode"), "prior_validation_mode")
    if prior_mode not in {"extraction", "reviewed", "final"}:
        raise CoordinatorError(f"invalid transaction prior mode: {prior_mode}")
    expected_prior_names = (
        FINAL_FILENAMES
        if prior_mode in {"reviewed", "final"}
        else EXTRACTION_FILENAMES
    )
    if set(prior_hashes) != set(expected_prior_names):
        raise CoordinatorError("transaction prior-file binding is invalid")
    for name, digest in prior_hashes.items():
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise CoordinatorError(f"invalid transaction prior SHA-256 for {name}")
    backup = transaction / "backup" / chain_identifier
    failed = transaction / "failed_replacement" / chain_identifier
    if backup.exists():
        if chain_directory.exists():
            failed.parent.mkdir(parents=True, exist_ok=True)
            if failed.exists():
                raise CoordinatorError(f"failed replacement path already exists: {failed}")
            os.replace(chain_directory, failed)
        os.replace(backup, chain_directory)
        fsync_directory(chain_directory.parent)
    if _file_hashes(chain_directory, prior_hashes) != prior_hashes:
        raise CoordinatorError("rollback did not restore the prior chain bytes")
    _validate_mode(
        chain_directory,
        data_root,
        repository_root,
        prior_mode,
        hash_cache,
    )
    record["state"] = "ROLLED_BACK"
    record["phase"] = "rollback_verified"
    record["rolled_back_at"] = utc_now()
    atomic_write_yaml(transaction / "transaction.yaml", record)


def _execute_replacement_locked(
    *,
    chain_directory: Path,
    chain_identifier: str,
    case_id: str,
    transaction_id: str,
    operation: str,
    data_root: Path,
    repository_root: Path,
    prior_validation_mode: str,
    replacement_validation_mode: str,
    populate_replacement: Callable[[Path], None],
    transaction_metadata: dict[str, Any] | None = None,
    hash_cache: HashCache | None = None,
) -> Path:
    hash_cache = hash_cache if hash_cache is not None else {}
    transaction = _transaction_root(data_root, transaction_id)
    if transaction.exists():
        raise CoordinatorError(f"transaction already exists: {transaction}")
    prior_names = (
        FINAL_FILENAMES
        if prior_validation_mode in {"reviewed", "final"}
        else EXTRACTION_FILENAMES
    )
    prior_hashes = _file_hashes(chain_directory, prior_names)
    transaction.parent.mkdir(parents=True, exist_ok=True)
    transaction.mkdir()
    prepared = transaction / "replacement" / chain_identifier
    backup = transaction / "backup" / chain_identifier
    record: dict[str, Any] = {
        "transaction_id": transaction_id,
        "operation": operation,
        "chain_id": chain_identifier,
        "case_id": case_id,
        "state": "PREPARING",
        "phase": "replacement_pending",
        "prepared_at": utc_now(),
        "chain_directory": data_relative(chain_directory, data_root),
        "replacement_directory": data_relative(prepared, data_root),
        "backup_directory": data_relative(backup, data_root),
        "prior_validation_mode": prior_validation_mode,
        "replacement_validation_mode": replacement_validation_mode,
        "prior_file_hashes": prior_hashes,
    }
    if transaction_metadata:
        record["operation_binding"] = transaction_metadata
    atomic_write_yaml(transaction / "transaction.yaml", record)
    try:
        prepared.parent.mkdir(parents=True)
        backup.parent.mkdir(parents=True)
        populate_replacement(prepared)
        prepared_manifest = load_yaml(prepared / "chain_manifest.yaml")
        if (
            prepared_manifest.get("chain_id") != chain_identifier
            or prepared_manifest.get("case_id") != case_id
        ):
            raise CoordinatorError("replacement identity differs from locked chain")
        replacement_names = (
            FINAL_FILENAMES
            if replacement_validation_mode in {"reviewed", "final"}
            else EXTRACTION_FILENAMES
        )
        exact_files(prepared, replacement_names)
        _validate_mode(
            prepared,
            data_root,
            repository_root,
            replacement_validation_mode,
            hash_cache,
        )
        record["replacement_file_hashes"] = _file_hashes(prepared, replacement_names)
        record["state"] = "PREPARED"
        record["phase"] = "replacement_validated"
        atomic_write_yaml(transaction / "transaction.yaml", record)
        if prepared.stat().st_dev != chain_directory.stat().st_dev:
            raise CoordinatorError("replacement and final chain are not on the same filesystem")
        os.replace(chain_directory, backup)
        record["phase"] = "prior_chain_backed_up"
        atomic_write_yaml(transaction / "transaction.yaml", record)
        os.replace(prepared, chain_directory)
        fsync_directory(chain_directory.parent)
        record["phase"] = "replacement_installed"
        atomic_write_yaml(transaction / "transaction.yaml", record)
        _validate_mode(
            chain_directory,
            data_root,
            repository_root,
            replacement_validation_mode,
            hash_cache,
        )
        if _file_hashes(chain_directory, replacement_names) != record["replacement_file_hashes"]:
            raise CoordinatorError("published replacement bytes differ from prepared bytes")
        record["state"] = "COMMITTED"
        record["phase"] = "publication_verified"
        record["committed_at"] = utc_now()
        atomic_write_yaml(transaction / "transaction.yaml", record)
    except Exception as error:
        record["error"] = str(error)
        try:
            atomic_write_yaml(transaction / "transaction.yaml", record)
        except Exception as record_error:
            record["error_record_write_failure"] = str(record_error)
        try:
            _rollback_transaction_locked(
                transaction=transaction,
                record=record,
                chain_directory=chain_directory,
                data_root=data_root,
                repository_root=repository_root,
                hash_cache=hash_cache,
            )
        except Exception as rollback_error:
            record["phase"] = "rollback_failed"
            record["rollback_error"] = str(rollback_error)
            atomic_write_yaml(transaction / "transaction.yaml", record)
            raise CoordinatorError(
                f"transaction failed and rollback verification failed: {error}; {rollback_error}"
            ) from error
        raise
    return transaction


def recover_transaction(
    transaction: Path,
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    if (
        not IDENTIFIER_PATTERN.fullmatch(transaction.name)
        or transaction.resolve() != _transaction_root(data_root, transaction.name).resolve()
    ):
        raise CoordinatorError(f"transaction path is not canonical: {transaction}")
    record = load_yaml(transaction / "transaction.yaml")
    if record.get("transaction_id") != transaction.name:
        raise CoordinatorError("transaction identity does not match its directory")
    if record.get("state") in {"COMMITTED", "ROLLED_BACK"}:
        return record
    if record.get("state") not in {"PREPARING", "PREPARED"}:
        raise CoordinatorError(f"unsupported transaction recovery state: {record.get('state')}")
    chain_identifier = require_string(record.get("chain_id"), "transaction.chain_id")
    case_id = require_string(record.get("case_id"), "transaction.case_id")
    chain_directory = resolve_data_path(
        require_string(record.get("chain_directory"), "transaction.chain_directory"),
        data_root,
    )
    _require_target_chain(chain_directory, data_root, chain_identifier, case_id)
    expected_backup = transaction / "backup" / chain_identifier
    expected_replacement = transaction / "replacement" / chain_identifier
    if record.get("backup_directory") != data_relative(expected_backup, data_root):
        raise CoordinatorError("transaction backup binding is not canonical")
    if record.get("replacement_directory") != data_relative(expected_replacement, data_root):
        raise CoordinatorError("transaction replacement binding is not canonical")
    with ChainLock(
        data_root,
        chain_identifier,
        f"recover_{transaction.name}",
        recover_stale=True,
    ):
        record = load_yaml(transaction / "transaction.yaml")
        if record.get("state") in {"COMMITTED", "ROLLED_BACK"}:
            return record
        if record.get("state") not in {"PREPARING", "PREPARED"}:
            raise CoordinatorError(
                f"unsupported transaction recovery state: {record.get('state')}"
            )
        _rollback_transaction_locked(
            transaction=transaction,
            record=record,
            chain_directory=chain_directory,
            data_root=data_root,
            repository_root=repository_root,
        )
    return load_yaml(transaction / "transaction.yaml")


def _committed_revision_count(data_root: Path, chain_identifier: str) -> int:
    transactions = data_root.joinpath(*STOMICS_REL.parts, "staging/dual_chain/transactions")
    if not transactions.is_dir():
        return 0
    count = 0
    for transaction in transactions.iterdir():
        record_path = transaction / "transaction.yaml"
        if not transaction.is_dir() or transaction.is_symlink() or not record_path.is_file():
            continue
        record = load_yaml(record_path)
        if (
            record.get("operation") == "extraction_revision"
            and record.get("chain_id") == chain_identifier
            and record.get("state") == "COMMITTED"
        ):
            count += 1
    return count


def publish_review(
    review_staging: Path,
    chain_directory: Path,
    transaction_id: str,
    reviewer_input_hashes: dict[str, str],
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
    assignment: dict[str, Any] | None = None,
    review_round: int = 0,
) -> Path:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    proposed = load_yaml(review_staging / "chain_manifest.yaml")
    chain_identifier = require_string(proposed.get("chain_id"), "chain_id")
    case_id = require_string(proposed.get("case_id"), "case_id")
    if assignment is not None:
        _validate_publication_assignment(
            assignment,
            review_staging,
            chain_directory,
            "review",
            review_round,
            data_root,
            repository_root,
        )
    _require_attempt_directory(review_staging, data_root, "review", chain_identifier)
    _require_target_chain(chain_directory, data_root, chain_identifier, case_id)
    _validate_hash_binding(reviewer_input_hashes, "reviewer_input_hashes")
    hash_cache: HashCache = {}
    with ChainLock(data_root, chain_identifier, transaction_id):
        if _file_hashes(chain_directory, EXTRACTION_FILENAMES) != reviewer_input_hashes:
            raise CoordinatorError("reviewer input hashes do not match the current final chain")
        review = _validate_review_staging(
            review_staging,
            chain_directory,
            data_root,
            repository_root,
            hash_cache,
        )
        if (
            review["manifest"].get("chain_id") != chain_identifier
            or review["manifest"].get("case_id") != case_id
        ):
            raise CoordinatorError("review proposal identity changed before validation")

        def populate(prepared: Path) -> None:
            prepared.mkdir()
            atomic_write(
                prepared / "chain_manifest.yaml",
                review["manifest_bytes"],
            )
            atomic_write(
                prepared / "independent_check.md",
                review["notes_bytes"],
            )
            for name in ("scientific_chain.jsonl", "execution_subchains.jsonl"):
                os.link(chain_directory / name, prepared / name)

        transaction = _execute_replacement_locked(
            chain_directory=chain_directory,
            chain_identifier=chain_identifier,
            case_id=case_id,
            transaction_id=transaction_id,
            operation="independent_review",
            data_root=data_root,
            repository_root=repository_root,
            prior_validation_mode="extraction",
            replacement_validation_mode=(
                "final"
                if review["status"] == "confirmed"
                else "reviewed"
            ),
            populate_replacement=populate,
            transaction_metadata={"reviewer_input_hashes": reviewer_input_hashes},
            hash_cache=hash_cache,
        )
    try:
        shutil.rmtree(review_staging)
    except OSError as error:
        raise CoordinatorError(
            f"review transaction committed but staging cleanup remains: {review_staging}: {error}"
        ) from error
    return transaction


def publish_revision(
    revision_staging: Path,
    chain_directory: Path,
    transaction_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
    repository_root: Path | None = None,
    assignment: dict[str, Any] | None = None,
    revision_round: int = 1,
) -> Path:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    proposed = load_yaml(revision_staging / "chain_manifest.yaml")
    chain_identifier = require_string(proposed.get("chain_id"), "chain_id")
    case_id = require_string(proposed.get("case_id"), "case_id")
    if assignment is not None:
        _validate_publication_assignment(
            assignment,
            revision_staging,
            chain_directory,
            "extraction",
            revision_round,
            data_root,
            repository_root,
        )
    _require_attempt_directory(revision_staging, data_root, "extraction", chain_identifier)
    _require_target_chain(chain_directory, data_root, chain_identifier, case_id)
    hash_cache: HashCache = {}
    with ChainLock(data_root, chain_identifier, transaction_id):
        validated = validate_extraction_staging(
            revision_staging, data_root, repository_root, hash_cache
        )
        current = validate_chain_directory(
            chain_directory,
            data_root,
            repository_root,
            reviewed=True,
            hash_cache=hash_cache,
        )
        current_status = require_mapping(
            current["manifest"].get("independent_check"), "current independent_check"
        ).get("status")
        if (
            current_status != "needs_revision"
            or current["manifest"].get("chain_status") != "needs_revision"
        ):
            raise CoordinatorError("extraction replacement requires a needs_revision chain")
        if current["manifest"].get("chain_id") != validated["manifest"].get("chain_id"):
            raise CoordinatorError("revision chain identity mismatch")
        if (
            validated["manifest"].get("chain_id") != chain_identifier
            or validated["manifest"].get("case_id") != case_id
            or current["manifest"].get("case_id") != case_id
        ):
            raise CoordinatorError("revision case identity mismatch")
        committed_revisions = _committed_revision_count(data_root, chain_identifier)
        if committed_revisions >= MAX_REVISION_ROUNDS:
            raise CoordinatorError(
                f"revision limit reached for {chain_identifier}: {MAX_REVISION_ROUNDS}"
            )

        def populate(prepared: Path) -> None:
            if revision_staging.stat().st_dev != prepared.parent.stat().st_dev:
                raise CoordinatorError("revision and transaction are not on the same filesystem")
            os.replace(revision_staging, prepared)

        return _execute_replacement_locked(
            chain_directory=chain_directory,
            chain_identifier=chain_identifier,
            case_id=case_id,
            transaction_id=transaction_id,
            operation="extraction_revision",
            data_root=data_root,
            repository_root=repository_root,
            prior_validation_mode="reviewed",
            replacement_validation_mode="extraction",
            populate_replacement=populate,
            transaction_metadata={
                "revision_round": committed_revisions + 1,
                "max_revision_rounds": MAX_REVISION_ROUNDS,
            },
            hash_cache=hash_cache,
        )


def verify_all(
    data_root: Path = DEFAULT_DATA_ROOT, repository_root: Path | None = None
) -> list[dict[str, str]]:
    repository_root = repository_root or Path(__file__).resolve().parents[1]
    hash_cache: HashCache = {}
    assignments = audit_cases(
        data_root, hash_cache=hash_cache, repository_root=repository_root
    )
    blocked = [
        value
        for value in assignments
        if value["data_readiness"] != "DATA_READY"
        and not assignment_supports_specification_extraction(value)
    ]
    if blocked:
        raise CoordinatorError(
            "current candidates have physical input failures: "
            f"{[value['chain_id'] for value in blocked]}"
        )
    output: list[dict[str, str]] = []
    expected_directories: set[Path] = set()
    for assignment in assignments:
        directory = Path(assignment["final_chain_directory"])
        data_relative(directory, data_root)
        expected_directories.add(directory.resolve())
        validated = validate_chain_directory(
            directory,
            data_root,
            repository_root,
            final=True,
            hash_cache=hash_cache,
        )
        if (
            validated["manifest"].get("chain_id") != assignment["chain_id"]
            or validated["manifest"].get("case_id") != assignment["case_id"]
        ):
            raise CoordinatorError(
                f"final chain identity mismatch for {assignment['chain_id']}"
            )
        expected_status = (
            "specification_ready"
            if assignment_supports_specification_extraction(assignment)
            else "comparison_ready"
        )
        if validated["manifest"].get("chain_status") != expected_status:
            raise CoordinatorError(
                f"final chain status mismatch for {assignment['chain_id']}"
            )
        output.append(
            {
                "stds_id": assignment["stds_id"],
                "candidate_id": assignment["candidate_id"],
                "chain_id": assignment["chain_id"],
                "status": expected_status,
            }
        )
    cases_root = data_root.joinpath(*STOMICS_REL.parts, "cases")
    actual = {
        value.resolve()
        for value in cases_root.glob("stomicsdb_STDS*/dual_chain/chain_sha256_*")
        if value.is_dir() and not value.is_symlink()
    }
    if actual != expected_directories:
        raise CoordinatorError(
            f"unexpected or missing final chains: expected {len(expected_directories)}, found {len(actual)}"
        )
    locks = data_root.joinpath(*STOMICS_REL.parts, "staging/dual_chain/locks")
    if locks.exists() and any(locks.iterdir()):
        raise CoordinatorError(f"orphan or live dual-chain locks remain under {locks}")
    staging_root = data_root.joinpath(*STOMICS_REL.parts, "staging/dual_chain")
    if staging_root.exists():
        allowed = {"locks", "transactions", "extraction", "review"}
        unexpected = [value for value in staging_root.iterdir() if value.name not in allowed]
        if unexpected:
            raise CoordinatorError(f"current partial dual-chain staging remains: {unexpected}")
        for kind in ("extraction", "review"):
            kind_root = staging_root / kind
            if not kind_root.exists():
                continue
            partial = [
                value
                for attempt in kind_root.iterdir()
                if attempt.is_dir()
                for value in attempt.iterdir()
            ]
            if partial:
                raise CoordinatorError(f"current partial {kind} staging remains: {partial}")
        transactions = staging_root / "transactions"
        if transactions.exists():
            for transaction in transactions.iterdir():
                if not transaction.is_dir() or transaction.is_symlink():
                    raise CoordinatorError(f"invalid dual-chain transaction entry: {transaction}")
                record_path = transaction / "transaction.yaml"
                state = load_yaml(record_path).get("state") if record_path.is_file() else None
                if state not in {"COMMITTED", "ROLLED_BACK"}:
                    raise CoordinatorError(
                        f"nonterminal dual-chain transaction {transaction.name}: {state}"
                    )
    return output


def _load_assignment_document(path: Path) -> dict[str, Any]:
    document = load_yaml(path)
    if set(document) == {"stomicsdb_dual_chain_job"}:
        return require_mapping(
            document["stomicsdb_dual_chain_job"], "stomicsdb_dual_chain_job"
        )
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--repository-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--attempt-id", default="audit")
    preflight = subparsers.add_parser("preflight-job")
    preflight.add_argument("assignment", type=Path)
    response = subparsers.add_parser("validate-job-response")
    response.add_argument("assignment", type=Path)
    response.add_argument("response", type=Path)
    validate = subparsers.add_parser("validate-extraction")
    validate.add_argument("staging_directory", type=Path)
    initial = subparsers.add_parser("publish-initial")
    initial.add_argument("staging_directory", type=Path)
    initial.add_argument("final_directory", type=Path)
    initial.add_argument("operation_id")
    initial.add_argument("--assignment", type=Path, required=True)
    review = subparsers.add_parser("publish-review")
    review.add_argument("review_staging", type=Path)
    review.add_argument("chain_directory", type=Path)
    review.add_argument("transaction_id")
    review.add_argument("--chain-manifest-sha256", required=True)
    review.add_argument("--scientific-chain-sha256", required=True)
    review.add_argument("--execution-subchains-sha256", required=True)
    review.add_argument("--assignment", type=Path, required=True)
    review.add_argument("--review-round", type=int, choices=range(3), default=0)
    revision = subparsers.add_parser("publish-revision")
    revision.add_argument("revision_staging", type=Path)
    revision.add_argument("chain_directory", type=Path)
    revision.add_argument("transaction_id")
    revision.add_argument("--assignment", type=Path, required=True)
    revision.add_argument("--revision-round", type=int, choices=(1, 2), required=True)
    recover = subparsers.add_parser("recover-transaction")
    recover.add_argument("transaction", type=Path)
    subparsers.add_parser("verify-all")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        result: Any = audit_cases(
            args.data_root, args.attempt_id, repository_root=args.repository_root
        )
    elif args.command == "preflight-job":
        result = {
            "status": "valid",
            **validate_job_assignment(
                _load_assignment_document(args.assignment),
                args.data_root,
                args.repository_root,
            ),
        }
    elif args.command == "validate-job-response":
        result = validate_job_response(
            load_yaml(args.response),
            _load_assignment_document(args.assignment),
            args.data_root,
            args.repository_root,
        )
    elif args.command == "validate-extraction":
        validated = validate_extraction_staging(
            args.staging_directory, args.data_root, args.repository_root
        )
        result = {
            "chain_id": validated["manifest"]["chain_id"],
            "status": "valid",
        }
    elif args.command == "publish-initial":
        publish_initial(
            args.staging_directory,
            args.final_directory,
            args.operation_id,
            args.data_root,
            args.repository_root,
            _load_assignment_document(args.assignment),
        )
        result = {"status": "published", "path": data_relative(args.final_directory, args.data_root)}
    elif args.command == "publish-review":
        path = publish_review(
            args.review_staging,
            args.chain_directory,
            args.transaction_id,
            {
                "chain_manifest.yaml": args.chain_manifest_sha256,
                "scientific_chain.jsonl": args.scientific_chain_sha256,
                "execution_subchains.jsonl": args.execution_subchains_sha256,
            },
            data_root=args.data_root,
            repository_root=args.repository_root,
            assignment=_load_assignment_document(args.assignment),
            review_round=args.review_round,
        )
        result = {"status": "committed", "transaction": data_relative(path, args.data_root)}
    elif args.command == "publish-revision":
        path = publish_revision(
            args.revision_staging,
            args.chain_directory,
            args.transaction_id,
            args.data_root,
            args.repository_root,
            _load_assignment_document(args.assignment),
            args.revision_round,
        )
        result = {"status": "committed", "transaction": data_relative(path, args.data_root)}
    elif args.command == "recover-transaction":
        result = recover_transaction(
            args.transaction, args.data_root, args.repository_root
        )
    else:
        result = verify_all(args.data_root, args.repository_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReadinessError as error:
        print(f"error: blocked: {error}", file=os.sys.stderr)
        raise SystemExit(2)
    except HandoffError as error:
        print(f"error: round3_handoff_needs_revision: {error}", file=os.sys.stderr)
        raise SystemExit(2)
    except CoordinatorError as error:
        print(f"error: {error}", file=os.sys.stderr)
        raise SystemExit(2)
