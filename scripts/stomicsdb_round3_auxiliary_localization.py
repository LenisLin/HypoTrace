#!/usr/bin/env python3
"""Publish acquired Round 3 auxiliary resources and bind accepted cases."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from typing import Any, Iterable

import yaml

import stomicsdb_round3_auxiliary_scope_revision as revision


DEFAULT_DATA_ROOT = Path("/mnt/NAS_21T/ProjectData/HypoTrace_Data")
STOMICS_RELATIVE = PurePosixPath("raw_data/public_database/stomicsdb")
TRANSACTION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
COVERAGE_EVIDENCE = (
    "Operator-approved non-pending inventory mapping; each listed local artifact "
    "byte/size/hash verified."
)
REVISION_KIND = "round3_auxiliary_localization_binding"


class LocalizationError(RuntimeError):
    pass


def require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LocalizationError(f"{context} must be a mapping")
    return value


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise LocalizationError(f"{context} must be a list")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def data_relative(path: Path, data_root: Path) -> str:
    try:
        return path.resolve().relative_to(data_root.resolve()).as_posix()
    except ValueError as error:
        raise LocalizationError(f"path is outside data root: {path}") from error


def resolve_data_path(value: str, data_root: Path) -> Path:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise LocalizationError(f"unsafe data-root-relative path: {value}")
    path = data_root.joinpath(*relative.parts)
    try:
        path.resolve().relative_to(data_root.resolve())
    except ValueError as error:
        raise LocalizationError(f"path escapes data root: {value}") from error
    return path


def sha256_path(path: Path) -> str:
    return revision.sha256_path(path)


def file_record(path: Path, data_root: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise LocalizationError(f"expected a regular file: {path}")
    return {
        "path": data_relative(path, data_root),
        "sha256": sha256_path(path),
        "size_bytes": path.stat().st_size,
    }


def verify_file_record(record: dict[str, Any], data_root: Path, field: str = "path") -> Path:
    path = resolve_data_path(record[field], data_root)
    if (
        path.is_symlink()
        or not path.is_file()
        or not stat.S_ISREG(path.stat().st_mode)
        or path.stat().st_size != record["size_bytes"]
        or sha256_path(path) != record["sha256"]
    ):
        raise LocalizationError(f"file binding mismatch: {path}")
    return path


def load_json(path: Path) -> dict[str, Any]:
    try:
        return require_mapping(json.loads(path.read_bytes()), str(path))
    except (OSError, json.JSONDecodeError) as error:
        raise LocalizationError(f"cannot parse JSON {path}: {error}") from error


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        return require_mapping(yaml.safe_load(path.read_bytes()), str(path))
    except (OSError, yaml.YAMLError) as error:
        raise LocalizationError(f"cannot parse YAML {path}: {error}") from error


def atomic_write_yaml(path: Path, value: Any) -> None:
    revision.atomic_write_yaml(path, value)


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise LocalizationError(f"cannot read run log {path}: {error}") from error
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        try:
            events.append(require_mapping(json.loads(line), f"{path}:{line_number}"))
        except json.JSONDecodeError as error:
            raise LocalizationError(f"invalid JSONL at {path}:{line_number}: {error}") from error
    return events


def validate_inventory_run(inventory_path: Path, data_root: Path) -> dict[str, Any]:
    """Validate one acquisition inventory/run and hash every declared artifact."""
    inventory_path = inventory_path.resolve()
    inventory = load_json(inventory_path)
    run_log_path = inventory_path.with_name("run.jsonl")
    events = parse_jsonl(run_log_path)
    terminals = [value for value in events if value.get("event") == "auxiliary_run_completed"]
    if len(terminals) != 1 or not events or events[-1] is not terminals[0]:
        raise LocalizationError(f"expected one auxiliary_run_completed event: {run_log_path}")
    terminal = terminals[0]
    artifacts_raw = require_list(inventory.get("artifacts"), "inventory artifacts")
    if (
        terminal.get("download_failure_count") != 0
        or any(value.get("event") == "download_failed" for value in events)
        or terminal.get("artifact_count") != len(artifacts_raw)
        or terminal.get("completed_artifact_count") != len(artifacts_raw)
    ):
        raise LocalizationError(f"incomplete acquisition terminal: {run_log_path}")

    terminal_events: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.get("event") in {"download_completed", "download_skipped"}:
            target = event.get("target_path")
            if not isinstance(target, str):
                raise LocalizationError(f"download terminal lacks target_path: {run_log_path}")
            terminal_events.setdefault(target, []).append(event)

    artifacts: dict[str, dict[str, Any]] = {}
    targets: set[str] = set()
    for raw in artifacts_raw:
        artifact = require_mapping(raw, "inventory artifact")
        artifact_id = artifact.get("artifact_id")
        target = artifact.get("target_path")
        source_url = artifact.get("source_url")
        if not all(isinstance(value, str) and value for value in (artifact_id, target, source_url)):
            raise LocalizationError("inventory artifact identity fields must be nonempty strings")
        if artifact_id in artifacts or target in targets:
            raise LocalizationError(f"duplicate artifact ID or target: {artifact_id}:{target}")
        matching_events = terminal_events.get(target, [])
        if len(matching_events) != 1:
            raise LocalizationError(f"expected one download terminal for {target}")
        event = matching_events[0]
        if event["event"] == "download_skipped" and event.get("reason") != "existing_final_file":
            raise LocalizationError(f"unsupported skipped download reason for {target}")
        if event.get("source_url") not in (None, source_url):
            raise LocalizationError(f"artifact/event source URL mismatch: {target}")
        path = resolve_data_path(target, data_root)
        record = file_record(path, data_root)
        size = event.get("size_bytes")
        if not isinstance(size, int) or size != record["size_bytes"]:
            raise LocalizationError(f"artifact/event size mismatch: {target}")
        event_sha = event.get("sha256")
        if event["event"] == "download_completed" and (
            not isinstance(event_sha, str) or event_sha != record["sha256"]
        ):
            raise LocalizationError(f"artifact/event hash mismatch: {target}")
        if event["event"] == "download_skipped" and event_sha not in (None, record["sha256"]):
            raise LocalizationError(f"skipped artifact/event hash mismatch: {target}")
        artifacts[artifact_id] = {
            "artifact_id": artifact_id,
            "source_url": source_url,
            "source_path": target,
            "sha256": record["sha256"],
            "size_bytes": record["size_bytes"],
        }
        targets.add(target)

    resources: dict[str, dict[str, Any]] = {}
    for raw in require_list(inventory.get("resources"), "inventory resources"):
        resource = require_mapping(raw, "inventory resource")
        resource_id = resource.get("inventory_id")
        if not isinstance(resource_id, str) or not resource_id or resource_id in resources:
            raise LocalizationError(f"duplicate or invalid inventory resource: {resource_id}")
        for field in (
            "resource_name",
            "expected_content",
            "source_url",
            "access_classification",
        ):
            if not isinstance(resource.get(field), str) or not resource[field]:
                raise LocalizationError(f"invalid {field} for {resource_id}")
        artifact_ids = require_list(resource.get("artifact_ids"), f"{resource_id} artifact_ids")
        if len(artifact_ids) != len(set(artifact_ids)) or any(value not in artifacts for value in artifact_ids):
            raise LocalizationError(f"unresolved or duplicate artifacts for {resource_id}")
        resources[resource_id] = resource
    pending_ids: set[str] = set()
    for raw in require_list(inventory.get("pending"), "inventory pending"):
        pending = require_mapping(raw, "pending resource")
        resource_id = pending.get("inventory_id")
        if not isinstance(resource_id, str) or resource_id in pending_ids or resource_id not in resources:
            raise LocalizationError(f"invalid pending resource: {resource_id}")
        pending_ids.add(resource_id)
    terminal_inventory = terminal.get("inventory_path")
    if not isinstance(terminal_inventory, str):
        raise LocalizationError(f"terminal lacks inventory_path: {run_log_path}")
    terminal_inventory_path = Path(terminal_inventory)
    if not terminal_inventory_path.is_absolute():
        terminal_inventory_path = resolve_data_path(terminal_inventory, data_root)
    if (
        terminal_inventory_path.resolve() != inventory_path
        or terminal.get("resource_count") != len(resources)
        or terminal.get("pending_resource_count") != len(pending_ids)
    ):
        raise LocalizationError(f"acquisition terminal/inventory mismatch: {run_log_path}")
    return {
        "inventory": inventory,
        "inventory_record": file_record(inventory_path, data_root),
        "run_log_record": file_record(run_log_path, data_root),
        "resources": resources,
        "artifacts": artifacts,
        "pending_ids": pending_ids,
    }


def build_resource_index(inventories: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index exactly one eligible acquisition resource per frozen identity."""
    matches: dict[tuple[str, str], list[dict[str, Any]]] = {}
    canonical_ids: set[str] = set()
    for inventory in inventories:
        for resource_id, resource in inventory["resources"].items():
            if resource_id in inventory["pending_ids"]:
                continue
            name = resource.get("resource_name")
            url = resource.get("source_url")
            if not all(isinstance(value, str) and value for value in (name, url)):
                raise LocalizationError(f"invalid resource identity: {resource_id}")
            identity = (name, url)
            entry = {
                "canonical_resource_id": resource_id,
                "resource": resource,
                "inventory": inventory,
                "artifacts": [inventory["artifacts"][value] for value in resource["artifact_ids"]],
            }
            matches.setdefault(identity, []).append(entry)
            if resource_id in canonical_ids:
                raise LocalizationError(f"duplicate eligible canonical resource ID: {resource_id}")
            canonical_ids.add(resource_id)
    ambiguous = [identity for identity, values in matches.items() if len(values) != 1]
    if ambiguous:
        raise LocalizationError(f"ambiguous eligible resource identity: {ambiguous[0]}")
    return {identity: values[0] for identity, values in matches.items()}


def infer_format(filename: str) -> str:
    lower = filename.lower()
    for suffix in (".tar.gz", ".tar.bz2", ".csv.gz", ".tsv.gz", ".txt.gz", ".nii.gz"):
        if lower.endswith(suffix):
            return suffix[1:]
    suffix = PurePosixPath(filename).suffix
    return suffix[1:].lower() if suffix else "binary"


def canonical_artifact_filenames(artifacts: list[dict[str, Any]]) -> dict[str, str]:
    basenames = [Path(value["source_path"]).name for value in artifacts]
    if any(not value for value in basenames):
        raise LocalizationError("acquisition artifact has an empty filename")
    counts = Counter(basenames)
    output = {
        artifact["artifact_id"]: (
            basename
            if counts[basename] == 1
            else f"{artifact['artifact_id']}__{basename}"
        )
        for artifact, basename in zip(artifacts, basenames, strict=True)
    }
    if len(output) != len(artifacts) or len(set(output.values())) != len(artifacts):
        raise LocalizationError("canonical package filename collision")
    return output


def stream_copy_verified(source: Path, destination: Path, expected: dict[str, Any]) -> None:
    if destination.exists():
        raise LocalizationError(f"staging destination collision: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_handle, destination.open("xb") as output_handle:
        for block in iter(lambda: input_handle.read(1024 * 1024), b""):
            output_handle.write(block)
        output_handle.flush()
        os.fsync(output_handle.fileno())
    if destination.stat().st_size != expected["size_bytes"] or sha256_path(destination) != expected["sha256"]:
        raise LocalizationError(f"staged byte-stream copy mismatch: {destination}")


def localization_manifest(
    transaction_id: str,
    entry: dict[str, Any],
    artifact_records: list[dict[str, Any]],
) -> dict[str, Any]:
    resource = entry["resource"]
    resource_id = entry["canonical_resource_id"]
    return {
        "auxiliary_localization_manifest": {
            "package_id": resource_id,
            "generation_id": f"{transaction_id}__{resource_id}",
            "localization_status": "LOCALIZED",
            "resource_identity": {
                "resource_name": resource["resource_name"],
                "source_url": resource["source_url"],
            },
            "expected_content": resource["expected_content"],
            "acquisition_bindings": {
                "inventories": [
                    {
                        "path": entry["inventory"]["inventory_record"]["path"],
                        "sha256": entry["inventory"]["inventory_record"]["sha256"],
                        "inventory_resource_id": resource_id,
                    }
                ],
                "successful_runs": [
                    {
                        "run_id": entry["inventory"]["inventory"]["run_id"],
                        "events_path": entry["inventory"]["run_log_record"]["path"],
                        "sha256": entry["inventory"]["run_log_record"]["sha256"],
                    }
                ],
            },
            "artifacts": artifact_records,
            "validation": {
                "artifact_count": len(artifact_records),
                "acquisition_bindings_verified": True,
                "all_artifacts_regular_files": True,
                "all_artifacts_readable": True,
                "all_artifact_sizes_verified": True,
                "all_artifact_sha256_verified": True,
                "all_artifact_paths_canonical": True,
            },
        }
    }


def coverage_binding(
    auxiliary: dict[str, Any],
    manifest_record: dict[str, Any],
    manifest: dict[str, Any],
    coverage_evidence: str,
) -> dict[str, Any]:
    body = manifest["auxiliary_localization_manifest"]
    artifacts = [
        {
            key: value[key]
            for key in ("artifact_id", "path", "source_url", "size_bytes", "sha256")
        }
        for value in body["artifacts"]
    ]
    return {
        "package_manifest": {
            "package_id": body["package_id"],
            "path": manifest_record["path"],
            "sha256": manifest_record["sha256"],
            "generation_id": body["generation_id"],
        },
        "artifacts": artifacts,
        "expected_content_coverage": {
            "status": "complete",
            "items": [
                {
                    "requirement": auxiliary["expected_content"],
                    "artifact_ids": [value["artifact_id"] for value in artifacts],
                    "evidence": coverage_evidence,
                }
            ],
            "uncovered_requirements": [],
        },
    }


def localize_case(
    objects: dict[str, dict[str, Any]],
    resource_index: dict[tuple[str, str], dict[str, Any]],
    package_bindings: dict[
        str, tuple[dict[str, Any], dict[str, Any], str]
    ],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    revised = deepcopy(objects)
    used: set[str] = set()
    for auxiliary in revised["data"]["auxiliary_resources"]:
        if auxiliary.get("local_availability") != "absent" or auxiliary.get("localization_binding") not in (None, {}):
            raise LocalizationError(f"Axx is not an unbound absent resource: {auxiliary.get('resource_id')}")
        identity = (auxiliary.get("resource_name"), auxiliary.get("source_url"))
        entries = [resource_index[identity]] if identity in resource_index else []
        if len(entries) != 1:
            raise LocalizationError(f"missing acquisition mapping for Axx identity: {identity}")
        entry = entries[0]
        resource = entry["resource"]
        if resource.get("access_classification") != auxiliary.get("access_classification"):
            raise LocalizationError(f"access-classification mismatch for {identity}")
        resource_id = entry["canonical_resource_id"]
        manifest_record, manifest, evidence = package_bindings[resource_id]
        auxiliary["local_availability"] = "localized"
        auxiliary["localization_binding"] = coverage_binding(
            auxiliary, manifest_record, manifest, evidence
        )
        used.add(resource_id)
    return revised, used


def validate_localized_auxiliary_resources(
    objects: dict[str, dict[str, Any]],
    manifests: dict[str, dict[str, Any]],
    data_root: Path,
    artifact_locations: dict[str, Path] | None = None,
) -> None:
    """Validate localized Axx records against canonical package manifests and bytes."""
    artifact_locations = artifact_locations or {}
    for auxiliary in require_list(objects["data"].get("auxiliary_resources"), "auxiliary_resources"):
        availability = auxiliary.get("local_availability")
        binding = auxiliary.get("localization_binding")
        if availability == "absent":
            if binding is not None:
                raise LocalizationError(f"absent Axx has a localization binding: {auxiliary.get('resource_id')}")
            raise LocalizationError(f"accepted case retains absent Axx: {auxiliary.get('resource_id')}")
        if availability != "localized" or not isinstance(binding, dict):
            raise LocalizationError(f"invalid localized Axx state: {auxiliary.get('resource_id')}")
        package = require_mapping(binding.get("package_manifest"), "package_manifest")
        package_id = package.get("package_id")
        if package_id not in manifests:
            raise LocalizationError(f"unresolved package manifest: {package_id}")
        manifest_document = manifests[package_id]
        manifest = require_mapping(
            manifest_document.get("auxiliary_localization_manifest"), "auxiliary_localization_manifest"
        )
        if manifest.get("localization_status") != "LOCALIZED":
            raise LocalizationError(f"package is not LOCALIZED: {package_id}")
        identity = manifest.get("resource_identity")
        if identity != {
            "resource_name": auxiliary.get("resource_name"),
            "source_url": auxiliary.get("source_url"),
        }:
            raise LocalizationError(f"resource identity mismatch: {package_id}")
        if package.get("generation_id") != manifest.get("generation_id") or package_id != manifest.get("package_id"):
            raise LocalizationError(f"package identity/generation mismatch: {package_id}")
        manifest_path = resolve_data_path(package["path"], data_root)
        expected_manifest_relative = (
            STOMICS_RELATIVE
            / "auxiliary_resources"
            / package_id
            / "generations"
            / manifest["generation_id"]
            / "localization.yaml"
        )
        if PurePosixPath(package["path"]) != expected_manifest_relative:
            raise LocalizationError(f"package manifest path is not canonical: {package_id}")
        actual_manifest_path = artifact_locations.get(package["path"], manifest_path)
        if (
            not actual_manifest_path.is_file()
            or sha256_path(actual_manifest_path) != package.get("sha256")
            or load_yaml(actual_manifest_path) != manifest_document
        ):
            raise LocalizationError(f"package manifest binding mismatch: {package_id}")
        manifest_artifacts = require_list(manifest.get("artifacts"), "manifest artifacts")
        validation = require_mapping(manifest.get("validation"), "manifest validation")
        if (
            validation.get("artifact_count") != len(manifest_artifacts)
            or validation.get("acquisition_bindings_verified") is not True
            or validation.get("all_artifacts_regular_files") is not True
            or validation.get("all_artifacts_readable") is not True
            or validation.get("all_artifact_sizes_verified") is not True
            or validation.get("all_artifact_sha256_verified") is not True
            or validation.get("all_artifact_paths_canonical") is not True
        ):
            raise LocalizationError(f"package validation record mismatch: {package_id}")
        acquisition = require_mapping(manifest.get("acquisition_bindings"), "acquisition_bindings")
        inventories = require_list(acquisition.get("inventories"), "acquisition inventories")
        runs = require_list(acquisition.get("successful_runs"), "successful acquisition runs")
        if len(inventories) != 1 or len(runs) != 1:
            raise LocalizationError(f"package must bind one acquisition inventory/run: {package_id}")
        inventory_binding = require_mapping(inventories[0], "acquisition inventory binding")
        run_binding = require_mapping(runs[0], "acquisition run binding")
        if inventory_binding.get("inventory_resource_id") != package_id:
            raise LocalizationError(f"acquisition resource ID mismatch: {package_id}")
        for record, path_field in ((inventory_binding, "path"), (run_binding, "events_path")):
            evidence_path = resolve_data_path(record[path_field], data_root)
            if not evidence_path.is_file() or sha256_path(evidence_path) != record.get("sha256"):
                raise LocalizationError(f"acquisition evidence binding mismatch: {package_id}")
        inventory_document = load_json(resolve_data_path(inventory_binding["path"], data_root))
        inventory_matches = [
            value
            for value in require_list(inventory_document.get("resources"), "acquisition resources")
            if value.get("inventory_id") == package_id
        ]
        if len(inventory_matches) != 1:
            raise LocalizationError(f"package is unresolved in acquisition inventory: {package_id}")
        inventory_resource = inventory_matches[0]
        if (
            inventory_resource.get("resource_name") != auxiliary.get("resource_name")
            or inventory_resource.get("source_url") != auxiliary.get("source_url")
            or inventory_resource.get("expected_content")
            != manifest.get("expected_content")
        ):
            raise LocalizationError(f"acquisition resource identity mismatch: {package_id}")
        if run_binding.get("run_id") != inventory_document.get("run_id"):
            raise LocalizationError(f"acquisition run ID mismatch: {package_id}")
        bound_artifacts = require_list(binding.get("artifacts"), "bound artifacts")
        bindable_manifest_artifacts = [
            {
                key: value[key]
                for key in ("artifact_id", "path", "source_url", "size_bytes", "sha256")
            }
            for value in manifest_artifacts
        ]
        if not bound_artifacts or any(value not in bindable_manifest_artifacts for value in bound_artifacts):
            raise LocalizationError(f"Axx artifacts are not a nonempty manifest subset: {package_id}")
        artifact_ids: set[str] = set()
        for artifact in manifest_artifacts:
            artifact_id = artifact.get("artifact_id")
            if not isinstance(artifact_id, str) or artifact_id in artifact_ids:
                raise LocalizationError(f"invalid manifest artifact ID: {package_id}")
            artifact_ids.add(artifact_id)
            if not isinstance(artifact.get("format"), str) or artifact.get("role") != "required_resource_artifact":
                raise LocalizationError(f"invalid manifest artifact metadata: {package_id}:{artifact_id}")
            expected_artifact_parent = expected_manifest_relative.parent / "artifacts"
            if (
                PurePosixPath(artifact.get("path", "")).parent != expected_artifact_parent
                or not isinstance(artifact.get("source_url"), str)
                or not artifact["source_url"]
            ):
                raise LocalizationError(f"artifact path/source is not canonical: {package_id}:{artifact_id}")
            canonical = resolve_data_path(artifact["path"], data_root)
            actual = artifact_locations.get(artifact["path"], canonical)
            if (
                actual.is_symlink()
                or not actual.is_file()
                or not os.access(actual, os.R_OK)
                or actual.stat().st_size != artifact.get("size_bytes")
                or sha256_path(actual) != artifact.get("sha256")
            ):
                raise LocalizationError(f"artifact binding mismatch: {artifact.get('path')}")
        coverage = require_mapping(binding.get("expected_content_coverage"), "expected_content_coverage")
        if coverage.get("status") != "complete" or coverage.get("uncovered_requirements") != []:
            raise LocalizationError(f"incomplete expected-content coverage: {package_id}")
        items = require_list(coverage.get("items"), "coverage items")
        if len(items) != 1:
            raise LocalizationError(f"expected one frozen coverage requirement: {package_id}")
        item = require_mapping(items[0], "coverage item")
        if (
            item.get("requirement") != auxiliary.get("expected_content")
            or set(item.get("artifact_ids") or [])
            != {value["artifact_id"] for value in bound_artifacts}
            or not isinstance(item.get("evidence"), str)
            or not item["evidence"]
        ):
            raise LocalizationError(f"coverage evidence mismatch: {package_id}")


def validate_proposal_coverage(
    objects: dict[str, dict[str, Any]], resource_changes: list[dict[str, Any]]
) -> None:
    expected = {
        value["package_id"]: {
            "artifact_ids": value["selected_artifact_ids"],
            "evidence": value["coverage_evidence"],
        }
        for value in resource_changes
    }
    if len(expected) != len(resource_changes):
        raise LocalizationError("duplicate package in proposal coverage records")
    for auxiliary in objects["data"]["auxiliary_resources"]:
        binding = require_mapping(auxiliary.get("localization_binding"), "localization_binding")
        package = require_mapping(binding.get("package_manifest"), "package_manifest")
        package_id = package.get("package_id")
        if package_id not in expected:
            raise LocalizationError(f"case binds a package outside the proposal: {package_id}")
        bound_ids = [value.get("artifact_id") for value in binding["artifacts"]]
        coverage_items = binding["expected_content_coverage"]["items"]
        if (
            bound_ids != expected[package_id]["artifact_ids"]
            or len(coverage_items) != 1
            or coverage_items[0].get("evidence") != expected[package_id]["evidence"]
        ):
            raise LocalizationError(f"case coverage differs from proposal: {package_id}")


def write_case_tree_preserving_unmodified_bytes(
    current_directory: Path,
    proposed_directory: Path,
    revised: dict[str, dict[str, Any]],
) -> None:
    proposed_directory.mkdir(parents=True)
    (proposed_directory / "data").mkdir()
    for relative in (Path("source_manifest.yaml"), Path("case_manifest.yaml")):
        source = current_directory / relative
        target = proposed_directory / relative
        stream_copy_verified(
            source,
            target,
            {"size_bytes": source.stat().st_size, "sha256": sha256_path(source)},
        )
    atomic_write_yaml(
        proposed_directory / "data/case_data_manifest.yaml",
        {"case_data_manifest": revised["data"]},
    )
    loaded = revision.load_case(proposed_directory)
    if loaded != revised:
        raise LocalizationError(f"proposed case object equality failed: {current_directory.name}")


def accepted_cases(receipt_path: Path, data_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    authority_transaction_path = receipt_path.with_name("transaction.yaml")
    authority = require_mapping(
        load_yaml(authority_transaction_path).get("post_publication_transaction"),
        "current revision authority transaction",
    )
    receipt_binding = require_mapping(
        authority.get("revision_receipt"), "current revision receipt binding"
    )
    bound_receipt_path = Path(receipt_binding.get("path", ""))
    if not bound_receipt_path.is_absolute():
        bound_receipt_path = resolve_data_path(str(receipt_binding.get("path", "")), data_root)
    if (
        authority.get("state") != "COMMITTED"
        or bound_receipt_path.resolve() != receipt_path.resolve()
        or receipt_binding.get("sha256") != sha256_path(receipt_path)
    ):
        raise LocalizationError("revision receipt is not bound by a COMMITTED authority")
    document = load_yaml(receipt_path)
    receipt = require_mapping(document.get("round3_case_revision_receipt"), "round3 case revision receipt")
    cases = require_list(receipt.get("cases"), "revision receipt cases")
    seen: set[str] = set()
    accepted: list[dict[str, Any]] = []
    for case in cases:
        stds_id = case.get("stds_id")
        status = case.get("authoritative_status")
        if not isinstance(stds_id, str) or stds_id in seen or status not in {"accepted", "no_candidate"}:
            raise LocalizationError(f"invalid authoritative case record: {stds_id}")
        seen.add(stds_id)
        if status == "accepted":
            paths = require_mapping(case.get("output_paths"), f"{stds_id} output_paths")
            if any(not isinstance(paths.get(key), str) for key in ("source_manifest", "case_data_manifest", "case_manifest")):
                raise LocalizationError(f"accepted case lacks output paths: {stds_id}")
            source_path = PurePosixPath(paths["source_manifest"])
            if (
                source_path.name != "source_manifest.yaml"
                or PurePosixPath(paths["case_data_manifest"])
                != source_path.parent / "data/case_data_manifest.yaml"
                or PurePosixPath(paths["case_manifest"])
                != source_path.parent / "case_manifest.yaml"
            ):
                raise LocalizationError(f"accepted case output paths diverge: {stds_id}")
            accepted.append(case)
    counts = require_mapping(receipt.get("counts"), "revision receipt counts")
    actual = {
        "accepted": sum(value.get("authoritative_status") == "accepted" for value in cases),
        "no_candidate": sum(value.get("authoritative_status") == "no_candidate" for value in cases),
    }
    if counts != actual:
        raise LocalizationError("revision receipt status counts mismatch")
    return receipt, accepted


def coverage_selections(
    coverage_path: Path | None,
    required_entries: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if coverage_path is None:
        return {
            package_id: {
                "selected_artifact_ids": list(entry["resource"]["artifact_ids"]),
                "evidence": COVERAGE_EVIDENCE,
            }
            for package_id, entry in required_entries.items()
        }
    document = load_yaml(coverage_path)
    decisions: dict[str, dict[str, Any]] = {}
    for raw in require_list(document.get("resources"), "coverage decision resources"):
        decision = require_mapping(raw, "coverage decision")
        package_id = decision.get("package_id")
        if not isinstance(package_id, str) or package_id in decisions:
            raise LocalizationError(f"duplicate or invalid coverage package: {package_id}")
        selected = require_list(
            decision.get("selected_artifact_ids"),
            f"{package_id} selected_artifact_ids",
        )
        evidence = decision.get("evidence")
        if (
            not selected
            or len(selected) != len(set(selected))
            or not all(isinstance(value, str) and value for value in selected)
            or not isinstance(evidence, str)
            or not evidence.strip()
        ):
            raise LocalizationError(f"invalid coverage decision: {package_id}")
        decisions[package_id] = {
            "selected_artifact_ids": selected,
            "evidence": evidence,
        }
    if set(decisions) != set(required_entries):
        raise LocalizationError("coverage decision packages differ from required Axx packages")
    for package_id, decision in decisions.items():
        available = set(required_entries[package_id]["resource"]["artifact_ids"])
        if not set(decision["selected_artifact_ids"]) <= available:
            raise LocalizationError(f"coverage selects unresolved artifacts: {package_id}")
    return decisions


def prepare_transaction(args: argparse.Namespace) -> Path:
    data_root = args.data_root.resolve()
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    transaction_parent = stomics_root / "staging/post_publication_transactions"
    transaction_root = transaction_parent / args.transaction_id
    if transaction_root.exists():
        raise LocalizationError(f"transaction directory already exists: {transaction_root}")
    final_auxiliary_root = stomics_root / "auxiliary_resources"
    if final_auxiliary_root.exists():
        raise LocalizationError(f"canonical auxiliary root already exists: {final_auxiliary_root}")

    source_inventory = validate_inventory_run(args.source_inventory, data_root)
    retained_inventory = validate_inventory_run(args.retained_inventory, data_root)
    inventories = [source_inventory, retained_inventory]
    resource_index = build_resource_index(inventories)
    receipt_path = args.current_revision_receipt.resolve()
    revision_receipt, accepted = accepted_cases(receipt_path, data_root)

    transaction_parent.mkdir(parents=True, exist_ok=True)
    try:
        transaction_root.mkdir()
    except FileExistsError as error:
        raise LocalizationError(
            f"transaction directory already exists: {transaction_root}"
        ) from error
    atomic_write_yaml(
        transaction_root / "transaction.yaml",
        {
            "round3_auxiliary_localization_transaction": {
                "transaction_id": args.transaction_id,
                "revision_kind": REVISION_KIND,
                "state": "PREPARING",
                "proposal_path": data_relative(
                    transaction_root / "proposal.yaml", data_root
                ),
                "error": None,
            }
        },
    )
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{args.transaction_id}.preparing.", dir=transaction_parent))
    try:
        case_objects: dict[str, dict[str, dict[str, Any]]] = {}
        required_entries: dict[str, dict[str, Any]] = {}
        for record in accepted:
            stds_id = record["stds_id"]
            source_path = resolve_data_path(record["output_paths"]["source_manifest"], data_root)
            case_directory = source_path.parent
            if (case_directory / "dual_chain").exists():
                raise LocalizationError(
                    f"existing dual-chain generations require stale handling: {stds_id}"
                )
            objects = revision.load_case(case_directory)
            revision.validate_case(objects, stds_id)
            revision.validate_external_bindings(objects, data_root)
            case_objects[stds_id] = objects
            for auxiliary in objects["data"]["auxiliary_resources"]:
                identity = (auxiliary.get("resource_name"), auxiliary.get("source_url"))
                if identity not in resource_index:
                    raise LocalizationError(f"missing non-pending resource mapping: {stds_id}:{auxiliary.get('resource_id')}")
                entry = resource_index[identity]
                resource_id = entry["canonical_resource_id"]
                prior = required_entries.get(resource_id)
                if prior is not None and prior["resource"] != entry["resource"]:
                    raise LocalizationError(f"canonical resource collision: {resource_id}")
                required_entries[resource_id] = entry

        coverage_path_value = getattr(args, "coverage_decisions", None)
        coverage_path = coverage_path_value.resolve() if coverage_path_value is not None else None
        selections = coverage_selections(coverage_path, required_entries)

        proposed_auxiliary = temporary_root / "proposed_auxiliary_resources"
        package_bindings: dict[
            str, tuple[dict[str, Any], dict[str, Any], str]
        ] = {}
        artifact_locations: dict[str, Path] = {}
        resource_changes: list[dict[str, Any]] = []
        canonical_paths: set[str] = set()
        for resource_id in sorted(required_entries):
            entry = required_entries[resource_id]
            generation_id = f"{args.transaction_id}__{resource_id}"
            selection = selections[resource_id]
            selected_ids = set(selection["selected_artifact_ids"])
            package_relative = PurePosixPath(resource_id) / "generations" / generation_id
            proposed_package = proposed_auxiliary.joinpath(*package_relative.parts)
            artifact_records: list[dict[str, Any]] = []
            filenames: set[str] = set()
            selected_artifacts = [
                artifact
                for artifact in entry["artifacts"]
                if artifact["artifact_id"] in selected_ids
            ]
            selected_artifacts.sort(
                key=lambda value: selection["selected_artifact_ids"].index(value["artifact_id"])
            )
            canonical_names = canonical_artifact_filenames(selected_artifacts)
            for artifact in selected_artifacts:
                filename = canonical_names[artifact["artifact_id"]]
                if not filename or filename in filenames:
                    raise LocalizationError(f"package filename collision: {resource_id}:{filename}")
                filenames.add(filename)
                final_path = final_auxiliary_root.joinpath(*package_relative.parts) / "artifacts" / filename
                relative = data_relative(final_path, data_root)
                if relative in canonical_paths:
                    raise LocalizationError(f"canonical path collision: {relative}")
                canonical_paths.add(relative)
                proposed_path = proposed_package / "artifacts" / filename
                source_path = resolve_data_path(artifact["source_path"], data_root)
                stream_copy_verified(source_path, proposed_path, artifact)
                artifact_locations[relative] = proposed_path
                artifact_records.append(
                    {
                        "artifact_id": artifact["artifact_id"],
                        "path": relative,
                        "source_url": artifact["source_url"],
                        "format": infer_format(filename),
                        "role": "required_resource_artifact",
                        "size_bytes": artifact["size_bytes"],
                        "sha256": artifact["sha256"],
                    }
                )
            if not artifact_records:
                raise LocalizationError(f"eligible resource has no acquired artifacts: {resource_id}")
            manifest_document = localization_manifest(
                args.transaction_id,
                entry,
                artifact_records,
            )
            proposed_manifest = proposed_package / "localization.yaml"
            atomic_write_yaml(proposed_manifest, manifest_document)
            final_manifest = final_auxiliary_root.joinpath(*package_relative.parts) / "localization.yaml"
            manifest_record = {
                "path": data_relative(final_manifest, data_root),
                "sha256": sha256_path(proposed_manifest),
                "size_bytes": proposed_manifest.stat().st_size,
            }
            artifact_locations[manifest_record["path"]] = proposed_manifest
            package_bindings[resource_id] = (
                manifest_record,
                manifest_document,
                selection["evidence"],
            )
            resource_changes.append(
                {
                    "package_id": resource_id,
                    "generation_id": generation_id,
                    "resource_identity": manifest_document["auxiliary_localization_manifest"]["resource_identity"],
                    "selected_artifact_ids": selection["selected_artifact_ids"],
                    "coverage_evidence": selection["evidence"],
                    "manifest": manifest_record,
                    "artifacts": artifact_records,
                }
            )

        case_changes: list[dict[str, Any]] = []
        used_resources: set[str] = set()
        candidate_count = 0
        for stds_id in sorted(case_objects):
            current_directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
            objects = case_objects[stds_id]
            revised, used = localize_case(objects, resource_index, package_bindings)
            used_resources.update(used)
            revision.validate_case(revised, stds_id)
            revision.validate_external_bindings(revised, data_root)
            manifests = {value: package_bindings[value][1] for value in used}
            validate_localized_auxiliary_resources(revised, manifests, data_root, artifact_locations)
            proposed_directory = temporary_root / "proposed_cases" / f"stomicsdb_{stds_id}"
            write_case_tree_preserving_unmodified_bytes(current_directory, proposed_directory, revised)
            input_files = revision.file_records(current_directory, data_root)
            proposed_files: list[dict[str, Any]] = []
            for local in revision.file_records(proposed_directory, temporary_root):
                local_path = PurePosixPath(local["path"])
                suffix = local_path.relative_to(PurePosixPath("proposed_cases") / f"stomicsdb_{stds_id}")
                proposed_files.append(
                    {
                        "transaction_path": data_relative(
                            transaction_root
                            / "proposed_cases"
                            / f"stomicsdb_{stds_id}"
                            / Path(*suffix.parts),
                            data_root,
                        ),
                        "target_path": data_relative(current_directory.joinpath(*suffix.parts), data_root),
                        "sha256": local["sha256"],
                        "size_bytes": local["size_bytes"],
                    }
                )
            candidate_count += len(revised["case"]["case_candidates"])
            case_changes.append(
                {
                    "stds_id": stds_id,
                    "authoritative_status": "accepted",
                    "case_directory": data_relative(current_directory, data_root),
                    "backup_directory": data_relative(
                        transaction_root / "backups/cases" / f"stomicsdb_{stds_id}", data_root
                    ),
                    "input_files": input_files,
                    "proposed_files": proposed_files,
                    "candidate_count": len(revised["case"]["case_candidates"]),
                    "localized_package_ids": sorted(used),
                }
            )
        if used_resources != set(required_entries):
            raise LocalizationError("prepared packages differ from case-required resources")

        input_preconditions = {
            "source_inventory": source_inventory["inventory_record"],
            "source_run_log": source_inventory["run_log_record"],
            "retained_inventory": retained_inventory["inventory_record"],
            "retained_run_log": retained_inventory["run_log_record"],
            "current_revision_receipt": file_record(receipt_path, data_root),
        }
        if coverage_path is not None:
            input_preconditions["coverage_decisions"] = file_record(coverage_path, data_root)
        proposal = {
            "round3_auxiliary_localization_proposal": {
                "transaction_id": args.transaction_id,
                "created_utc": utc_now(),
                "operation": "round3_auxiliary_canonical_localization",
                "revision_kind": REVISION_KIND,
                "input_preconditions": input_preconditions,
                "current_revision_status_counts": revision_receipt.get("counts"),
                "accepted_case_count": len(case_changes),
                "localized_resource_count": len(resource_changes),
                "candidate_count": candidate_count,
                "coverage_decisions_supplied": coverage_path is not None,
                "canonical_auxiliary_root": data_relative(final_auxiliary_root, data_root),
                "proposed_auxiliary_root": data_relative(
                    transaction_root / "proposed_auxiliary_resources", data_root
                ),
                "resources": resource_changes,
                "cases": case_changes,
                "statuses_changed": False,
                "downstream_binding_scan": {
                    "case_dual_chain_paths": [],
                    "downstream_generations_made_stale": [],
                },
            }
        }
        atomic_write_yaml(temporary_root / "proposal.yaml", proposal)
        atomic_write_yaml(
            temporary_root / "transaction.yaml",
            {
                "round3_auxiliary_localization_transaction": {
                    "transaction_id": args.transaction_id,
                    "revision_kind": REVISION_KIND,
                    "state": "PREPARED",
                    "proposal_path": data_relative(transaction_root / "proposal.yaml", data_root),
                    "error": None,
                }
            },
        )
        revision.fsync_directory(temporary_root)
        for child in sorted(temporary_root.iterdir(), key=lambda value: value.name):
            os.replace(child, transaction_root / child.name)
        temporary_root.rmdir()
        revision.fsync_directory(transaction_root)
        revision.fsync_directory(transaction_parent)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        shutil.rmtree(transaction_root, ignore_errors=True)
        raise
    return transaction_root


def load_proposal(transaction_root: Path) -> dict[str, Any]:
    return require_mapping(
        load_yaml(transaction_root / "proposal.yaml").get("round3_auxiliary_localization_proposal"),
        "localization proposal",
    )


def prepared_manifests(
    proposal: dict[str, Any], data_root: Path, proposed_root: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    manifests: dict[str, dict[str, Any]] = {}
    locations: dict[str, Path] = {}
    final_root = resolve_data_path(proposal["canonical_auxiliary_root"], data_root)
    for resource in proposal["resources"]:
        package_id = resource["package_id"]
        manifest_target = resolve_data_path(resource["manifest"]["path"], data_root)
        relative = manifest_target.relative_to(final_root)
        proposed_manifest = proposed_root / relative
        if sha256_path(proposed_manifest) != resource["manifest"]["sha256"]:
            raise LocalizationError(f"proposed package manifest changed: {package_id}")
        manifests[package_id] = load_yaml(proposed_manifest)
        locations[resource["manifest"]["path"]] = proposed_manifest
        for artifact in resource["artifacts"]:
            target = resolve_data_path(artifact["path"], data_root)
            location = proposed_root / target.relative_to(final_root)
            verify_file_record({**artifact, "transaction_path": data_relative(location, data_root)}, data_root, "transaction_path")
            locations[artifact["path"]] = location
    return manifests, locations


def verify_ready(transaction_root: Path, data_root: Path) -> dict[str, Any]:
    transaction = require_mapping(
        load_yaml(transaction_root / "transaction.yaml").get("round3_auxiliary_localization_transaction"),
        "localization transaction",
    )
    if transaction.get("state") != "PREPARED":
        raise LocalizationError(f"transaction is not ready: {transaction.get('state')}")
    proposal = load_proposal(transaction_root)
    if proposal.get("transaction_id") != transaction.get("transaction_id"):
        raise LocalizationError("transaction/proposal identity mismatch")
    if (
        proposal.get("revision_kind") != REVISION_KIND
        or transaction.get("revision_kind") != REVISION_KIND
        or proposal.get("downstream_binding_scan")
        != {
            "case_dual_chain_paths": [],
            "downstream_generations_made_stale": [],
        }
    ):
        raise LocalizationError("localization revision kind/downstream scan mismatch")
    for record in proposal["input_preconditions"].values():
        verify_file_record(record, data_root)
    final_auxiliary_root = resolve_data_path(proposal["canonical_auxiliary_root"], data_root)
    if final_auxiliary_root.exists():
        raise LocalizationError(f"canonical auxiliary root exists: {final_auxiliary_root}")
    proposed_root = resolve_data_path(proposal["proposed_auxiliary_root"], data_root)
    manifests, locations = prepared_manifests(proposal, data_root, proposed_root)
    if proposal.get("coverage_decisions_supplied"):
        decision_record = proposal["input_preconditions"].get("coverage_decisions")
        if not isinstance(decision_record, dict):
            raise LocalizationError("proposal lacks the supplied coverage-decision binding")
        decision_document = load_yaml(resolve_data_path(decision_record["path"], data_root))
        raw_decisions = require_list(decision_document.get("resources"), "coverage decision resources")
        frozen = {
            value.get("package_id"): {
                "selected_artifact_ids": value.get("selected_artifact_ids"),
                "evidence": value.get("evidence"),
            }
            for value in raw_decisions
        }
        proposed = {
            value["package_id"]: {
                "selected_artifact_ids": value["selected_artifact_ids"],
                "evidence": value["coverage_evidence"],
            }
            for value in proposal["resources"]
        }
        if len(frozen) != len(raw_decisions) or frozen != proposed:
            raise LocalizationError("proposal differs from frozen coverage decisions")
    for change in proposal["cases"]:
        current = resolve_data_path(change["case_directory"], data_root)
        if revision.file_records(current, data_root) != change["input_files"]:
            raise LocalizationError(f"case input changed: {change['stds_id']}")
        for record in change["proposed_files"]:
            verify_file_record(record, data_root, "transaction_path")
        proposed = transaction_root / "proposed_cases" / f"stomicsdb_{change['stds_id']}"
        objects = revision.load_case(proposed)
        revision.validate_case(objects, change["stds_id"])
        revision.validate_external_bindings(objects, data_root)
        validate_localized_auxiliary_resources(
            objects,
            {value: manifests[value] for value in change["localized_package_ids"]},
            data_root,
            locations,
        )
        validate_proposal_coverage(objects, proposal["resources"])
    return proposal


def acquire_lock(path: Path, owner: dict[str, Any]) -> None:
    try:
        path.mkdir()
    except FileExistsError as error:
        raise LocalizationError(f"live lock contention: {path}") from error
    try:
        atomic_write_yaml(path / "owner.yaml", owner)
    except Exception:
        (path / "owner.yaml").unlink(missing_ok=True)
        path.rmdir()
        raise


def release_lock(path: Path) -> None:
    (path / "owner.yaml").unlink(missing_ok=True)
    path.rmdir()


def _replace_path(records: list[dict[str, Any]], old: str, new: str) -> list[dict[str, Any]]:
    return [{**record, "path": record["path"].replace(old, new, 1)} for record in records]


def validate_published(
    transaction_root: Path, proposal: dict[str, Any], data_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    final_root = resolve_data_path(proposal["canonical_auxiliary_root"], data_root)
    manifests, locations = prepared_manifests(proposal, data_root, final_root)
    resource_receipts: list[dict[str, Any]] = []
    for resource in proposal["resources"]:
        manifest_path = resolve_data_path(resource["manifest"]["path"], data_root)
        manifest_record = file_record(manifest_path, data_root)
        if manifest_record != resource["manifest"]:
            raise LocalizationError(f"published manifest differs: {resource['package_id']}")
        artifact_records = []
        for artifact in resource["artifacts"]:
            record = file_record(resolve_data_path(artifact["path"], data_root), data_root)
            if record != {key: artifact[key] for key in ("path", "sha256", "size_bytes")}:
                raise LocalizationError(f"published artifact differs: {artifact['path']}")
            artifact_records.append(record)
        resource_receipts.append(
            {
                "package_id": resource["package_id"],
                "generation_id": resource["generation_id"],
                "manifest": manifest_record,
                "artifacts": artifact_records,
            }
        )
    case_receipts: list[dict[str, Any]] = []
    for change in proposal["cases"]:
        case_directory = resolve_data_path(change["case_directory"], data_root)
        actual = revision.file_records(case_directory, data_root)
        expected = [
            {
                "path": value["target_path"],
                "sha256": value["sha256"],
                "size_bytes": value["size_bytes"],
            }
            for value in change["proposed_files"]
        ]
        if actual != expected:
            raise LocalizationError(f"published case differs: {change['stds_id']}")
        objects = revision.load_case(case_directory)
        revision.validate_case(objects, change["stds_id"])
        revision.validate_external_bindings(objects, data_root)
        validate_localized_auxiliary_resources(
            objects,
            {value: manifests[value] for value in change["localized_package_ids"]},
            data_root,
            locations,
        )
        validate_proposal_coverage(objects, proposal["resources"])
        actual_candidate_count = len(objects["case"]["case_candidates"])
        if actual_candidate_count != change["candidate_count"]:
            raise LocalizationError(f"candidate count changed: {change['stds_id']}")
        backup = resolve_data_path(change["backup_directory"], data_root)
        expected_backup = _replace_path(
            change["input_files"], change["case_directory"], change["backup_directory"]
        )
        if revision.file_records(backup, data_root) != expected_backup:
            raise LocalizationError(f"backup binding mismatch: {change['stds_id']}")
        case_receipts.append(
            {
                "stds_id": change["stds_id"],
                "authoritative_status": "accepted",
                "candidate_count": actual_candidate_count,
                "localized_package_ids": change["localized_package_ids"],
                "files": actual,
                "preserved_backup_directory": change["backup_directory"],
            }
        )
    return resource_receipts, case_receipts


def commit_transaction(transaction_root: Path, data_root: Path) -> None:
    transaction = require_mapping(
        load_yaml(transaction_root / "transaction.yaml").get("round3_auxiliary_localization_transaction"),
        "localization transaction",
    )
    if transaction.get("state") == "COMMITTED":
        verify_committed(transaction_root, data_root)
        return
    if transaction.get("state") != "PREPARED":
        raise LocalizationError(f"transaction is not committable: {transaction.get('state')}")
    proposal = verify_ready(transaction_root, data_root)
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    global_lock = transaction_root.parent / "locks/round3_auxiliary_publish.lock"
    case_lock_root = stomics_root / "staging/round3_case_construction/locks"
    global_lock.parent.mkdir(parents=True, exist_ok=True)
    case_lock_root.mkdir(parents=True, exist_ok=True)
    locks = [global_lock] + sorted(
        case_lock_root / f"stomicsdb_{value['stds_id']}.lock" for value in proposal["cases"]
    )
    owner = {
        "transaction_id": proposal["transaction_id"],
        "operation": "round3_auxiliary_canonical_localization",
    }
    acquired: list[Path] = []
    moved_cases: list[dict[str, Any]] = []
    auxiliary_published = False
    release_acquired = True
    try:
        for lock in locks:
            acquire_lock(lock, owner)
            acquired.append(lock)
        verify_ready(transaction_root, data_root)
        atomic_write_yaml(
            transaction_root / "transaction.yaml",
            {
                "round3_auxiliary_localization_transaction": {
                    "transaction_id": proposal["transaction_id"],
                    "revision_kind": REVISION_KIND,
                    "state": "PREPARED",
                    "proposal_path": data_relative(transaction_root / "proposal.yaml", data_root),
                    "error": None,
                }
            },
        )
        final_auxiliary = resolve_data_path(proposal["canonical_auxiliary_root"], data_root)
        proposed_auxiliary = resolve_data_path(proposal["proposed_auxiliary_root"], data_root)
        os.replace(proposed_auxiliary, final_auxiliary)
        revision.fsync_directory(final_auxiliary.parent)
        auxiliary_published = True
        (transaction_root / "backups/cases").mkdir(parents=True)
        for change in proposal["cases"]:
            current = resolve_data_path(change["case_directory"], data_root)
            backup = resolve_data_path(change["backup_directory"], data_root)
            proposed = transaction_root / "proposed_cases" / f"stomicsdb_{change['stds_id']}"
            if backup.exists():
                raise LocalizationError(f"backup already exists: {backup}")
            os.replace(current, backup)
            moved_cases.append(change)
            os.replace(proposed, current)
            revision.fsync_directory(current.parent)

        resource_receipts, case_receipts = validate_published(transaction_root, proposal, data_root)
        (transaction_root / "proposed_cases").rmdir()
        proposal_path = transaction_root / "proposal.yaml"
        proposal_binding = {
            "path": data_relative(proposal_path, data_root),
            "sha256": sha256_path(proposal_path),
        }
        localization_receipt_path = transaction_root / "localization_receipt.yaml"
        cleanup_receipt_path = transaction_root / "cleanup_receipt.yaml"
        atomic_write_yaml(
            localization_receipt_path,
            {
                "round3_auxiliary_localization_receipt": {
                    "transaction_id": proposal["transaction_id"],
                    "committed_utc": utc_now(),
                    "proposal": proposal_binding,
                    "accepted_case_count": proposal["accepted_case_count"],
                    "localized_resource_count": proposal["localized_resource_count"],
                    "candidate_count": proposal["candidate_count"],
                    "authoritative_status_counts": proposal["current_revision_status_counts"],
                    "statuses_changed": False,
                    "downstream_generations_made_stale": [],
                    "resources": resource_receipts,
                    "cases": case_receipts,
                }
            },
        )
        cleanup_targets = [
            {
                "stds_id": value["stds_id"],
                "preserved_backup_directory": value["backup_directory"],
                "files": _replace_path(
                    value["input_files"], value["case_directory"], value["backup_directory"]
                ),
                "cleanup_status": "complete",
            }
            for value in proposal["cases"]
        ]
        atomic_write_yaml(
            cleanup_receipt_path,
            {
                "post_publication_cleanup_receipt": {
                    "transaction_id": proposal["transaction_id"],
                    "created_utc": utc_now(),
                    "proposal": proposal_binding,
                    "targets": cleanup_targets,
                    "canonical_auxiliary_publication_completed": True,
                    "canonical_case_publication_completed": True,
                    "transaction_backups_retained": True,
                    "partial_staging_remaining": False,
                    "downstream_generations_made_stale": [],
                }
            },
        )
        atomic_write_yaml(
            transaction_root / "transaction.yaml",
            {
                "round3_auxiliary_localization_transaction": {
                    "transaction_id": proposal["transaction_id"],
                    "revision_kind": REVISION_KIND,
                    "state": "COMMITTED",
                    "proposal": proposal_binding,
                    "localization_receipt": {
                        "path": data_relative(localization_receipt_path, data_root),
                        "sha256": sha256_path(localization_receipt_path),
                    },
                    "cleanup_receipt": {
                        "path": data_relative(cleanup_receipt_path, data_root),
                        "sha256": sha256_path(cleanup_receipt_path),
                    },
                    "error": None,
                }
            },
        )
        verify_committed(transaction_root, data_root)
    except Exception as error:
        rollback_error: Exception | None = None
        try:
            for change in reversed(moved_cases):
                current = resolve_data_path(change["case_directory"], data_root)
                backup = resolve_data_path(change["backup_directory"], data_root)
                proposed = transaction_root / "proposed_cases" / f"stomicsdb_{change['stds_id']}"
                if not current.is_dir() or not backup.is_dir() or proposed.exists():
                    raise LocalizationError(
                        f"cannot prove rollback inputs: {change['stds_id']}"
                    )
                proposed.parent.mkdir(parents=True, exist_ok=True)
                os.replace(current, proposed)
                os.replace(backup, current)
                revision.fsync_directory(current.parent)
                revision.fsync_directory(backup.parent)
            if auxiliary_published:
                final_auxiliary = resolve_data_path(proposal["canonical_auxiliary_root"], data_root)
                proposed_auxiliary = resolve_data_path(proposal["proposed_auxiliary_root"], data_root)
                if not final_auxiliary.is_dir() or proposed_auxiliary.exists():
                    raise LocalizationError("cannot prove auxiliary rollback inputs")
                os.replace(final_auxiliary, proposed_auxiliary)
                revision.fsync_directory(final_auxiliary.parent)
            new_package_ids = {
                value["package_id"] for value in proposal["resources"]
            }
            for change in proposal["cases"]:
                current = resolve_data_path(change["case_directory"], data_root)
                if revision.file_records(current, data_root) != change["input_files"]:
                    raise LocalizationError(
                        f"case rollback verification failed: {change['stds_id']}"
                    )
                restored = revision.load_case(current)
                revision.validate_case(restored, change["stds_id"])
                for auxiliary in restored["data"]["auxiliary_resources"]:
                    binding = auxiliary.get("localization_binding")
                    if (
                        isinstance(binding, dict)
                        and binding.get("package_manifest", {}).get("package_id")
                        in new_package_ids
                    ):
                        raise LocalizationError(
                            f"restored case still references new package: {change['stds_id']}"
                        )
            if auxiliary_published:
                final_auxiliary = resolve_data_path(
                    proposal["canonical_auxiliary_root"], data_root
                )
                proposed_auxiliary = resolve_data_path(
                    proposal["proposed_auxiliary_root"], data_root
                )
                if final_auxiliary.exists() or not proposed_auxiliary.is_dir():
                    raise LocalizationError("auxiliary rollback verification failed")
                prepared_manifests(proposal, data_root, proposed_auxiliary)
            for name in ("localization_receipt.yaml", "cleanup_receipt.yaml"):
                (transaction_root / name).unlink(missing_ok=True)
            atomic_write_yaml(
                transaction_root / "transaction.yaml",
                {
                    "round3_auxiliary_localization_transaction": {
                        "transaction_id": proposal["transaction_id"],
                        "revision_kind": REVISION_KIND,
                        "state": "ROLLED_BACK",
                        "proposal_path": data_relative(transaction_root / "proposal.yaml", data_root),
                        "error": str(error),
                    }
                },
            )
        except Exception as nested:
            rollback_error = nested
        if rollback_error is not None:
            release_acquired = False
            raise LocalizationError(f"commit failed ({error}); rollback failed ({rollback_error})") from error
        raise
    finally:
        if release_acquired:
            for lock in reversed(acquired):
                release_lock(lock)


def verify_committed(transaction_root: Path, data_root: Path) -> None:
    transaction = require_mapping(
        load_yaml(transaction_root / "transaction.yaml").get("round3_auxiliary_localization_transaction"),
        "localization transaction",
    )
    if transaction.get("state") != "COMMITTED":
        raise LocalizationError(f"transaction is not committed: {transaction.get('state')}")
    for name in ("proposal", "localization_receipt", "cleanup_receipt"):
        record = transaction[name]
        path = resolve_data_path(record["path"], data_root)
        if sha256_path(path) != record["sha256"]:
            raise LocalizationError(f"transaction binding mismatch: {name}")
    proposal = load_proposal(transaction_root)
    transaction_id = transaction.get("transaction_id")
    if proposal.get("transaction_id") != transaction_id:
        raise LocalizationError("committed transaction/proposal identity mismatch")
    if (
        transaction.get("revision_kind") != REVISION_KIND
        or proposal.get("revision_kind") != REVISION_KIND
    ):
        raise LocalizationError("committed localization revision kind mismatch")
    for record in proposal["input_preconditions"].values():
        verify_file_record(record, data_root)
    localization_receipt = require_mapping(
        load_yaml(resolve_data_path(transaction["localization_receipt"]["path"], data_root)).get(
            "round3_auxiliary_localization_receipt"
        ),
        "localization receipt",
    )
    cleanup_receipt = require_mapping(
        load_yaml(resolve_data_path(transaction["cleanup_receipt"]["path"], data_root)).get(
            "post_publication_cleanup_receipt"
        ),
        "cleanup receipt",
    )
    if (
        localization_receipt.get("transaction_id") != transaction_id
        or cleanup_receipt.get("transaction_id") != transaction_id
        or localization_receipt.get("proposal") != transaction["proposal"]
        or cleanup_receipt.get("proposal") != transaction["proposal"]
    ):
        raise LocalizationError("receipts do not bind committed proposal")
    if (
        localization_receipt.get("downstream_generations_made_stale") != []
        or cleanup_receipt.get("downstream_generations_made_stale") != []
    ):
        raise LocalizationError("receipts report unexpected downstream staleness")
    resources, cases = validate_published(transaction_root, proposal, data_root)
    if localization_receipt.get("resources") != resources or localization_receipt.get("cases") != cases:
        raise LocalizationError("localization receipt output bindings mismatch")
    expected_counts = {
        "accepted_case_count": len(cases),
        "localized_resource_count": len(resources),
        "candidate_count": sum(value["candidate_count"] for value in cases),
    }
    if (
        any(localization_receipt.get(key) != value for key, value in expected_counts.items())
        or proposal.get("accepted_case_count") != expected_counts["accepted_case_count"]
        or proposal.get("localized_resource_count")
        != expected_counts["localized_resource_count"]
        or proposal.get("candidate_count") != expected_counts["candidate_count"]
    ):
        raise LocalizationError("localization receipt counts mismatch")
    revision_receipt_record = proposal["input_preconditions"]["current_revision_receipt"]
    current_revision_receipt = require_mapping(
        load_yaml(resolve_data_path(revision_receipt_record["path"], data_root)).get(
            "round3_case_revision_receipt"
        ),
        "current revision receipt",
    )
    authoritative_counts = require_mapping(
        current_revision_receipt.get("counts"), "current revision counts"
    )
    if (
        localization_receipt.get("authoritative_status_counts")
        != authoritative_counts
        or proposal.get("current_revision_status_counts") != authoritative_counts
    ):
        raise LocalizationError("authoritative status counts mismatch")
    if (
        localization_receipt.get("statuses_changed") is not False
        or proposal.get("statuses_changed") is not False
    ):
        raise LocalizationError("localization receipt reports status changes")
    expected_targets = [
        {
            "stds_id": value["stds_id"],
            "preserved_backup_directory": value["backup_directory"],
            "files": _replace_path(value["input_files"], value["case_directory"], value["backup_directory"]),
            "cleanup_status": "complete",
        }
        for value in proposal["cases"]
    ]
    if (
        cleanup_receipt.get("targets") != expected_targets
        or cleanup_receipt.get("canonical_auxiliary_publication_completed") is not True
        or cleanup_receipt.get("canonical_case_publication_completed") is not True
        or cleanup_receipt.get("transaction_backups_retained") is not True
        or cleanup_receipt.get("partial_staging_remaining") is not False
    ):
        raise LocalizationError("cleanup receipt mismatch")
    if (transaction_root / "proposed_auxiliary_resources").exists() or (transaction_root / "proposed_cases").exists():
        raise LocalizationError("committed transaction retains proposed staging")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--retained-inventory", type=Path, required=True)
    parser.add_argument("--current-revision-receipt", type=Path, required=True)
    parser.add_argument("--coverage-decisions", type=Path)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args(argv)
    if not TRANSACTION_ID_PATTERN.fullmatch(args.transaction_id):
        parser.error("--transaction-id must be filesystem-safe")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        transaction_root = prepare_transaction(args)
        if args.commit:
            commit_transaction(transaction_root, args.data_root.resolve())
        transaction = require_mapping(
            load_yaml(transaction_root / "transaction.yaml").get(
                "round3_auxiliary_localization_transaction"
            ),
            "localization transaction",
        )
        print(
            json.dumps(
                {
                    "transaction_id": args.transaction_id,
                    "state": transaction.get("state"),
                    "transaction_root": str(transaction_root),
                },
                sort_keys=True,
            )
        )
        return 0
    except (LocalizationError, revision.RevisionError, OSError, yaml.YAMLError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
