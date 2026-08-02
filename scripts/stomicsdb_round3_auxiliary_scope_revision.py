#!/usr/bin/env python3
"""Apply an operator-approved Round 3 auxiliary-resource scope contraction."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable

import yaml


DEFAULT_DATA_ROOT = Path("/mnt/NAS_21T/ProjectData/HypoTrace_Data")
STOMICS_RELATIVE = PurePosixPath("raw_data/public_database/stomicsdb")
CASE_FILES = (
    PurePosixPath("source_manifest.yaml"),
    PurePosixPath("data/case_data_manifest.yaml"),
    PurePosixPath("case_manifest.yaml"),
)
TRANSACTION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class RevisionError(RuntimeError):
    pass


def require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RevisionError(f"{context} must be a mapping")
    return value


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise RevisionError(f"{context} must be a list")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def dump_yaml(value: Any) -> bytes:
    return yaml.safe_dump(
        value, allow_unicode=False, sort_keys=False, width=1_000_000
    ).encode("utf-8")


def atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_yaml(path: Path, value: Any) -> None:
    atomic_write(path, dump_yaml(value))


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        return require_mapping(yaml.safe_load(path.read_bytes()), str(path))
    except (OSError, yaml.YAMLError) as error:
        raise RevisionError(f"cannot parse YAML {path}: {error}") from error


def load_json(path: Path) -> dict[str, Any]:
    try:
        return require_mapping(json.loads(path.read_bytes()), str(path))
    except (OSError, json.JSONDecodeError) as error:
        raise RevisionError(f"cannot parse JSON {path}: {error}") from error


def data_relative(path: Path, data_root: Path) -> str:
    try:
        return path.resolve().relative_to(data_root.resolve()).as_posix()
    except ValueError as error:
        raise RevisionError(f"path is outside data root: {path}") from error


def resolve_data_path(value: str, data_root: Path) -> Path:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise RevisionError(f"unsafe data-root-relative path: {value}")
    path = data_root.joinpath(*relative.parts)
    try:
        path.resolve().relative_to(data_root.resolve())
    except ValueError as error:
        raise RevisionError(f"path escapes data root: {value}") from error
    return path


def case_file_paths(case_directory: Path) -> list[Path]:
    if not case_directory.is_dir() or case_directory.is_symlink():
        raise RevisionError(f"invalid case directory: {case_directory}")
    actual = sorted(
        value.relative_to(case_directory).as_posix()
        for value in case_directory.rglob("*")
        if value.is_file()
    )
    expected = sorted(value.as_posix() for value in CASE_FILES)
    if actual != expected:
        raise RevisionError(f"case must contain exactly three files: {case_directory}: {actual}")
    return [case_directory.joinpath(*value.parts) for value in CASE_FILES]


def load_case(case_directory: Path) -> dict[str, dict[str, Any]]:
    paths = case_file_paths(case_directory)
    return {
        "source": require_mapping(load_yaml(paths[0]).get("source_manifest"), "source_manifest"),
        "data": require_mapping(load_yaml(paths[1]).get("case_data_manifest"), "case_data_manifest"),
        "case": require_mapping(load_yaml(paths[2]).get("case_manifest"), "case_manifest"),
    }


def serialize_case(objects: dict[str, dict[str, Any]]) -> dict[PurePosixPath, bytes]:
    return {
        CASE_FILES[0]: dump_yaml({"source_manifest": objects["source"]}),
        CASE_FILES[1]: dump_yaml({"case_data_manifest": objects["data"]}),
        CASE_FILES[2]: dump_yaml({"case_manifest": objects["case"]}),
    }


def result_link_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for raw in require_list(data.get("result_data_links"), "result_data_links"):
        link = require_mapping(raw, "result link")
        result_id = link.get("result_id")
        if not isinstance(result_id, str) or result_id in output:
            raise RevisionError(f"duplicate or invalid result link: {result_id}")
        output[result_id] = link
    return output


def candidate_adjacency(case: dict[str, Any]) -> dict[str, set[str]]:
    output: dict[str, set[str]] = defaultdict(set)
    for raw_candidate in require_list(case.get("case_candidates"), "case_candidates"):
        candidate = require_mapping(raw_candidate, "case candidate")
        for raw_connection in require_list(candidate.get("result_connections"), "connections"):
            connection = require_mapping(raw_connection, "connection")
            source = connection.get("from_result_id")
            target = connection.get("to_result_id")
            if not isinstance(source, str) or not isinstance(target, str):
                raise RevisionError("connection result IDs must be strings")
            output[source].add(target)
    return output


def downstream_closure(direct: Iterable[str], adjacency: dict[str, set[str]]) -> set[str]:
    removed = set(direct)
    queue: deque[str] = deque(sorted(removed))
    while queue:
        for target in sorted(adjacency.get(queue.popleft(), set())):
            if target not in removed:
                removed.add(target)
                queue.append(target)
    return removed


def ordered_union(groups: Iterable[Iterable[str]]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            if value not in seen:
                seen.add(value)
                output.append(value)
    return output


def prune_case(
    objects: dict[str, dict[str, Any]], direct_result_ids: set[str]
) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any]]:
    revised = deepcopy(objects)
    source = revised["source"]
    data = revised["data"]
    case = revised["case"]
    current_results = require_list(source.get("results"), "source results")
    current_ids = [require_mapping(value, "source result").get("result_id") for value in current_results]
    if any(not isinstance(value, str) for value in current_ids):
        raise RevisionError("source result IDs must be strings")
    current_set = set(current_ids)
    if not direct_result_ids or not direct_result_ids <= current_set:
        raise RevisionError("direct removal contains no results or unresolved results")
    removed = downstream_closure(direct_result_ids, candidate_adjacency(case)) & current_set
    retained = current_set - removed
    source["results"] = [value for value in current_results if value["result_id"] in retained]
    data["result_data_links"] = [
        value for value in data["result_data_links"] if value["result_id"] in retained
    ]
    candidates: list[dict[str, Any]] = []
    for raw in case["case_candidates"]:
        candidate = deepcopy(raw)
        candidate["result_ids"] = [value for value in candidate["result_ids"] if value in retained]
        candidate["result_order"] = [value for value in candidate["result_order"] if value in retained]
        candidate["result_connections"] = [
            value
            for value in candidate["result_connections"]
            if value["from_result_id"] in retained and value["to_result_id"] in retained
        ]
        if candidate["result_ids"]:
            candidates.append(candidate)
    case["case_candidates"] = candidates
    details = {
        "direct_removed_result_ids": sorted(direct_result_ids),
        "downstream_removed_result_ids": sorted(removed - direct_result_ids),
        "removed_result_ids": sorted(removed),
        "retained_result_ids": [value for value in current_ids if value in retained],
        "retained_candidate_ids": [value["candidate_id"] for value in candidates],
    }
    if not candidates:
        return None, details

    links = result_link_map(data)
    used_data_ids = {
        require_mapping(value, "data input").get("data_id")
        for link in links.values()
        for value in require_list(link.get("data_inputs"), "data_inputs")
    }
    used_auxiliary_ids = {
        value
        for link in links.values()
        for value in require_list(link.get("auxiliary_resource_ids"), "auxiliary_resource_ids")
    }
    data["data_objects"] = [
        value for value in data["data_objects"] if value["data_id"] in used_data_ids
    ]
    data["auxiliary_resources"] = [
        value
        for value in data["auxiliary_resources"]
        if value["resource_id"] in used_auxiliary_ids
    ]
    for candidate in candidates:
        member_links = [links[value] for value in candidate["result_ids"]]
        candidate["auxiliary_resource_ids"] = ordered_union(
            link["auxiliary_resource_ids"] for link in member_links
        )
        primary_sets = [
            {
                value["data_id"]
                for value in link["data_inputs"]
                if value["input_role"] == "primary_spatial"
            }
            for link in member_links
        ]
        if not primary_sets or any(value != primary_sets[0] for value in primary_sets):
            raise RevisionError(f"primary-spatial set diverged: {candidate['candidate_id']}")
        candidate["spatial_data_ids"] = [
            value for value in candidate["spatial_data_ids"] if value in primary_sets[0]
        ]
    return revised, details


def validate_case(objects: dict[str, dict[str, Any]], stds_id: str) -> None:
    source, data, case = objects["source"], objects["data"], objects["case"]
    if {source.get("stds_id"), data.get("stds_id"), case.get("stds_id")} != {stds_id}:
        raise RevisionError(f"stds_id mismatch: {stds_id}")
    if case.get("source_manifest_path") != "source_manifest.yaml":
        raise RevisionError(f"source manifest path mismatch: {stds_id}")
    if case.get("case_data_manifest_path") != "data/case_data_manifest.yaml":
        raise RevisionError(f"case data manifest path mismatch: {stds_id}")
    source_ids = [value["result_id"] for value in source["results"]]
    links = result_link_map(data)
    data_ids = {value["data_id"] for value in data["data_objects"]}
    auxiliary_ids = {value["resource_id"] for value in data["auxiliary_resources"]}
    candidate_result_ids: list[str] = []
    used_data_ids: set[str] = set()
    used_auxiliary_ids: set[str] = set()
    candidate_ids: set[str] = set()
    for candidate in case["case_candidates"]:
        candidate_id = candidate["candidate_id"]
        if candidate_id in candidate_ids:
            raise RevisionError(f"duplicate candidate: {stds_id}:{candidate_id}")
        candidate_ids.add(candidate_id)
        members = candidate["result_ids"]
        if not members or len(members) != len(set(members)) or set(members) != set(candidate["result_order"]):
            raise RevisionError(f"invalid candidate membership: {stds_id}:{candidate_id}")
        if any(value not in links for value in members):
            raise RevisionError(f"unresolved candidate result: {stds_id}:{candidate_id}")
        candidate_result_ids.extend(members)
        indegree = {value: 0 for value in members}
        adjacency: dict[str, set[str]] = defaultdict(set)
        weak = {value: set() for value in members}
        for connection in candidate["result_connections"]:
            source_id = connection["from_result_id"]
            target_id = connection["to_result_id"]
            if source_id not in indegree or target_id not in indegree or source_id == target_id:
                raise RevisionError(f"invalid connection: {stds_id}:{candidate_id}")
            if target_id not in adjacency[source_id]:
                adjacency[source_id].add(target_id)
                indegree[target_id] += 1
            weak[source_id].add(target_id)
            weak[target_id].add(source_id)
        queue = deque(value for value, count in indegree.items() if count == 0)
        visited = 0
        while queue:
            source_id = queue.popleft()
            visited += 1
            for target_id in adjacency.get(source_id, set()):
                indegree[target_id] -= 1
                if indegree[target_id] == 0:
                    queue.append(target_id)
        if visited != len(members):
            raise RevisionError(f"cyclic candidate: {stds_id}:{candidate_id}")
        if len(members) == 1 and candidate["result_connections"]:
            raise RevisionError(f"singleton has connection: {stds_id}:{candidate_id}")
        if len(members) > 1:
            connected = {members[0]}
            queue = deque([members[0]])
            while queue:
                source_id = queue.popleft()
                for target_id in weak[source_id]:
                    if target_id not in connected:
                        connected.add(target_id)
                        queue.append(target_id)
            if connected != set(members):
                raise RevisionError(f"disconnected candidate: {stds_id}:{candidate_id}")
        primary_sets: list[set[str]] = []
        candidate_auxiliary: set[str] = set()
        for result_id in members:
            link = links[result_id]
            primary = {
                value["data_id"]
                for value in link["data_inputs"]
                if value["input_role"] == "primary_spatial"
            }
            if not primary or not primary <= data_ids:
                raise RevisionError(f"invalid primary input: {stds_id}:{result_id}")
            primary_sets.append(primary)
            for value in link["data_inputs"]:
                if value["data_id"] not in data_ids:
                    raise RevisionError(f"unresolved Dxx: {stds_id}:{result_id}")
                used_data_ids.add(value["data_id"])
            result_auxiliary = set(link["auxiliary_resource_ids"])
            if not result_auxiliary <= auxiliary_ids:
                raise RevisionError(f"unresolved Axx: {stds_id}:{result_id}")
            candidate_auxiliary.update(result_auxiliary)
            used_auxiliary_ids.update(result_auxiliary)
        if any(value != primary_sets[0] for value in primary_sets):
            raise RevisionError(f"candidate spatial inputs diverge: {stds_id}:{candidate_id}")
        if set(candidate["spatial_data_ids"]) != primary_sets[0]:
            raise RevisionError(f"candidate spatial_data_ids mismatch: {stds_id}:{candidate_id}")
        if set(candidate["auxiliary_resource_ids"]) != candidate_auxiliary:
            raise RevisionError(f"candidate auxiliary IDs mismatch: {stds_id}:{candidate_id}")
    if len(candidate_result_ids) != len(set(candidate_result_ids)):
        raise RevisionError(f"result appears in multiple candidates: {stds_id}")
    if set(source_ids) != set(links) or set(source_ids) != set(candidate_result_ids):
        raise RevisionError(f"source/link/candidate result mismatch: {stds_id}")
    if used_data_ids != data_ids or used_auxiliary_ids != auxiliary_ids:
        raise RevisionError(f"unused formal record: {stds_id}")


def validate_external_bindings(objects: dict[str, dict[str, Any]], data_root: Path) -> None:
    source, data = objects["source"], objects["data"]
    cache: dict[Path, str] = {}

    def verify(record: dict[str, Any]) -> Path:
        path = resolve_data_path(record["path"], data_root)
        if not path.is_file():
            raise RevisionError(f"bound file is absent: {path}")
        actual = cache.setdefault(path, sha256_path(path))
        if actual != record["sha256"]:
            raise RevisionError(f"hash mismatch: {path}")
        return path

    article_manifest = verify(
        {"path": source["article_manifest_path"], "sha256": source["article_manifest_sha256"]}
    )
    verify({"path": source["article_path"], "sha256": source["article_sha256"]})
    if load_yaml(article_manifest).get("generation_id") != source["article_generation_id"]:
        raise RevisionError("article generation mismatch")
    binding = data["dataset_binding"]
    for name in ("dataset_manifest", "source_manifest"):
        path = verify(binding[name])
        if load_yaml(path).get("generation_id") != binding[name]["generation_id"]:
            raise RevisionError(f"dataset generation mismatch: {path}")
    for name in ("samples", "files"):
        verify(binding[name])
    for data_object in data["data_objects"]:
        localized: dict[str, set[str]] = defaultdict(set)
        for record in data_object["localization_bindings"]:
            path = verify(record)
            manifest = load_yaml(path)
            if manifest.get("generation_id") != record["generation_id"]:
                raise RevisionError(f"localization generation mismatch: {path}")
            for entry in (manifest.get("artifacts") or []) + (manifest.get("extracted_paths") or []):
                localized[entry["path"]].add(entry["sha256"])
        for component_name in ("expression_matrix", "coordinates", "image", "metadata"):
            component = data_object.get(component_name)
            if component is None:
                continue
            for record in component["files"]:
                if record["sha256"] not in localized.get(record["path"], set()):
                    raise RevisionError(f"component not declared by localization: {record['path']}")
                verify(record)
    objects_by_id = {value["data_id"]: value for value in data["data_objects"]}
    for link in data["result_data_links"]:
        for data_input in link["data_inputs"]:
            data_object = objects_by_id[data_input["data_id"]]
            for required in data_input["required_components"]:
                declared = {value["path"] for value in data_object[required["component"]]["files"]}
                if not set(required["paths"]) <= declared:
                    raise RevisionError("required component paths are not a subset")


def file_records(case_directory: Path, data_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": data_relative(path, data_root),
            "sha256": sha256_path(path),
            "size_bytes": path.stat().st_size,
        }
        for path in case_file_paths(case_directory)
    ]


def inventory_resource_map(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for resource in require_list(inventory.get("resources"), "inventory resources"):
        resource_id = resource.get("inventory_id")
        if not isinstance(resource_id, str) or resource_id in output:
            raise RevisionError(f"duplicate inventory resource: {resource_id}")
        output[resource_id] = resource
    return output


def excluded_resource_identities(
    proposal: dict[str, Any], data_root: Path
) -> set[tuple[str, str]]:
    source_record = proposal["input_preconditions"]["source_auxiliary_inventory"]
    source_inventory = load_json(resolve_data_path(source_record["path"], data_root))
    resources = inventory_resource_map(source_inventory)
    excluded_ids = set(proposal["decision"]["excluded_pending_resource_ids"])
    if not excluded_ids <= set(resources):
        raise RevisionError("excluded resource IDs no longer resolve in the bound inventory")
    return {
        (resources[value]["resource_name"], resources[value]["source_url"])
        for value in excluded_ids
    }


def excluded_auxiliary_references(
    objects: dict[str, dict[str, Any]], identities: set[tuple[str, str]]
) -> list[str]:
    return sorted(
        value["resource_id"]
        for value in objects["data"]["auxiliary_resources"]
        if (value["resource_name"], value["source_url"]) in identities
    )


def validate_retained_downloads(inventory_path: Path, data_root: Path) -> dict[str, Any]:
    inventory = load_json(inventory_path)
    run_log = inventory_path.with_name("run.jsonl")
    completed: dict[str, dict[str, Any]] = {}
    final: dict[str, Any] | None = None
    try:
        lines = run_log.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RevisionError(f"cannot read retained run log: {error}") from error
    for line in lines:
        event = require_mapping(json.loads(line), "run event")
        if event.get("event") == "download_completed":
            completed[event["target_path"]] = event
        elif event.get("event") == "auxiliary_run_completed":
            final = event
    if not final or final.get("all_resources_localized") is not True or inventory.get("pending"):
        raise RevisionError("retained-resource run is not complete")
    artifacts: list[dict[str, Any]] = []
    for artifact in inventory["artifacts"]:
        target = artifact["target_path"]
        event = completed.get(target)
        if event is None:
            raise RevisionError(f"missing completion event: {target}")
        path = resolve_data_path(target, data_root)
        if path.stat().st_size != event["size_bytes"] or sha256_path(path) != event["sha256"]:
            raise RevisionError(f"retained artifact mismatch: {target}")
        artifacts.append(
            {
                "target_path": target,
                "sha256": event["sha256"],
                "size_bytes": event["size_bytes"],
                "source_url": artifact["source_url"],
            }
        )
    return {"inventory": inventory, "run_log": run_log, "artifacts": artifacts}


def find_terminal_binding(stds_id: str, stomics_root: Path, data_root: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    pattern = f"*/jobs/{stds_id}/terminal.yaml"
    for terminal_path in sorted((stomics_root / "round3_runs").glob(pattern)):
        terminal = require_mapping(load_yaml(terminal_path).get("round3_job_terminal"), "terminal")
        if terminal.get("status") != "accepted":
            continue
        receipt_path = terminal_path.parents[2] / "receipt.yaml"
        receipt = require_mapping(load_yaml(receipt_path).get("round3_receipt"), "receipt")
        relative = data_relative(terminal_path, data_root)
        digest = sha256_path(terminal_path)
        records = [value for value in receipt["terminal_records"] if value["stds_id"] == stds_id]
        if (
            len(records) != 1
            or not terminal_record_path_matches(
                records[0]["path"], terminal_path, data_root
            )
            or records[0]["sha256"] != digest
        ):
            raise RevisionError(f"receipt does not bind terminal: {terminal_path}")
        matches.append(
            {
                "path": relative,
                "sha256": digest,
                "round3_batch_id": terminal["round3_batch_id"],
                "job_attempt_id": terminal["job_attempt_id"],
                "review_rounds": terminal["review_rounds"],
            }
        )
    if len(matches) != 1:
        raise RevisionError(f"expected one accepted terminal for {stds_id}, found {len(matches)}")
    return matches[0]


def scan_downstream_bindings(data_root: Path, stds_ids: Iterable[str]) -> list[str]:
    roots = [data_root / value for value in ("results", "trajectories", "runs")]
    roots = [value for value in roots if value.exists()]
    if not roots:
        return []
    pattern = "stomicsdb_(?:" + "|".join(re.escape(value) for value in sorted(stds_ids)) + ")"
    result = subprocess.run(
        ["rg", "-l", pattern, *(str(value) for value in roots)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RevisionError(f"downstream scan failed: {result.stderr.strip()}")
    return [data_relative(Path(value), data_root) for value in result.stdout.splitlines() if value]


def write_case_tree(directory: Path, serialized: dict[PurePosixPath, bytes]) -> None:
    directory.mkdir(parents=True)
    (directory / "data").mkdir()
    for relative in CASE_FILES:
        target = directory.joinpath(*relative.parts)
        target.write_bytes(serialized[relative])
    fsync_directory(directory / "data")
    fsync_directory(directory)


def terminal_record_path_matches(
    recorded_path: str, terminal_path: Path, data_root: Path
) -> bool:
    recorded = Path(recorded_path)
    if recorded.is_absolute():
        return recorded.resolve() == terminal_path.resolve()
    return recorded_path == data_relative(terminal_path, data_root)


def prepare_transaction(args: argparse.Namespace) -> Path:
    data_root = args.data_root.resolve()
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    transaction_root = stomics_root / "staging/post_publication_transactions" / args.transaction_id
    if transaction_root.exists():
        return transaction_root
    source_path = args.source_inventory.resolve()
    retained_path = args.retained_inventory.resolve()
    source = load_json(source_path)
    retained = validate_retained_downloads(retained_path, data_root)
    retained_inventory = retained["inventory"]
    pending_ids = {value["inventory_id"] for value in source["pending"]}
    retained_ids = set(retained_inventory["selected_resource_ids"])
    if not retained_ids or not retained_ids <= pending_ids:
        raise RevisionError("retained IDs are not a nonempty subset of the source pending set")
    if set(inventory_resource_map(retained_inventory)) != retained_ids:
        raise RevisionError("retained resources differ from selected_resource_ids")
    excluded_ids = pending_ids - retained_ids
    resources = inventory_resource_map(source)
    if not excluded_ids or not excluded_ids <= set(resources):
        raise RevisionError("excluded pending resources are empty or unresolved")

    case_objects: dict[str, dict[str, dict[str, Any]]] = {}
    direct_results: dict[str, set[str]] = defaultdict(set)
    excluded_inventory: dict[str, list[str]] = defaultdict(list)
    excluded_auxiliary: dict[str, set[str]] = defaultdict(set)
    for inventory_id in sorted(excluded_ids):
        resource = resources[inventory_id]
        for stds_id, result_ids_value in resource["result_ids_by_case"].items():
            result_ids = set(result_ids_value)
            case_directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
            objects = case_objects.setdefault(stds_id, load_case(case_directory))
            matching = [
                value
                for value in objects["data"]["auxiliary_resources"]
                if value["resource_name"] == resource["resource_name"]
                and value["source_url"] == resource["source_url"]
            ]
            if len(matching) != 1:
                raise RevisionError(f"cannot map {inventory_id} to one Axx in {stds_id}")
            auxiliary_id = matching[0]["resource_id"]
            linked = {
                result_id
                for result_id, link in result_link_map(objects["data"]).items()
                if auxiliary_id in link["auxiliary_resource_ids"]
            }
            if linked != result_ids:
                raise RevisionError(f"inventory/case result mismatch: {inventory_id}:{stds_id}")
            direct_results[stds_id].update(result_ids)
            excluded_inventory[stds_id].append(inventory_id)
            excluded_auxiliary[stds_id].add(auxiliary_id)

    affected_ids = sorted(case_objects)
    downstream = scan_downstream_bindings(data_root, affected_ids)
    if downstream:
        raise RevisionError("downstream bindings exist and must be marked stale: " + ", ".join(downstream))
    intake_path = stomics_root / "registry/intake_manifest.yaml"
    intake = load_yaml(intake_path)
    scope_ids = intake["selected_stds_ids"]
    if set(scope_ids) != set(source["scope_stds_ids"]):
        raise RevisionError("source inventory scope differs from frozen intake")

    parent = transaction_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{args.transaction_id}.preparing.", dir=parent))
    try:
        prior_terminals = {
            stds_id: find_terminal_binding(stds_id, stomics_root, data_root) for stds_id in scope_ids
        }
        changes: list[dict[str, Any]] = []
        for stds_id in affected_ids:
            objects = case_objects[stds_id]
            validate_case(objects, stds_id)
            revised, details = prune_case(objects, direct_results[stds_id])
            status = "accepted" if revised is not None else "no_candidate"
            proposed_files: list[dict[str, Any]] = []
            if revised is not None:
                validate_case(revised, stds_id)
                proposed_directory = temporary_root / "proposed" / f"stomicsdb_{stds_id}"
                write_case_tree(proposed_directory, serialize_case(revised))
                if load_case(proposed_directory) != revised:
                    raise RevisionError(f"serialized-object equality failed: {stds_id}")
                for local_record in file_records(proposed_directory, temporary_root):
                    suffix = PurePosixPath(local_record.pop("path")).relative_to(
                        PurePosixPath("proposed") / f"stomicsdb_{stds_id}"
                    )
                    local_record["transaction_path"] = data_relative(
                        transaction_root / "proposed" / f"stomicsdb_{stds_id}" / Path(*suffix.parts),
                        data_root,
                    )
                    local_record["target_path"] = data_relative(
                        stomics_root / "cases" / f"stomicsdb_{stds_id}" / Path(*suffix.parts),
                        data_root,
                    )
                    proposed_files.append(local_record)
            case_directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
            changes.append(
                {
                    "stds_id": stds_id,
                    "prior_status": "accepted",
                    "proposed_status": status,
                    "prior_terminal": prior_terminals[stds_id],
                    "case_directory": data_relative(case_directory, data_root),
                    "backup_directory": data_relative(
                        transaction_root / "backups" / f"stomicsdb_{stds_id}", data_root
                    ),
                    "input_files": file_records(case_directory, data_root),
                    "excluded_inventory_resource_ids": sorted(excluded_inventory[stds_id]),
                    "excluded_case_auxiliary_resource_ids": sorted(excluded_auxiliary[stds_id]),
                    **details,
                    "proposed_files": proposed_files,
                }
            )
        proposal = {
            "post_publication_transaction_proposal": {
                "transaction_id": args.transaction_id,
                "created_utc": utc_now(),
                "purpose": "Apply the operator-approved exclusion of unresolved Round 3 auxiliary resources while retaining the two successfully localized current-version substitutes.",
                "revision_kind": "round3_auxiliary_scope_contraction",
                "input_preconditions": {
                    "intake_manifest": {"path": data_relative(intake_path, data_root), "sha256": sha256_path(intake_path)},
                    "source_auxiliary_inventory": {"path": data_relative(source_path, data_root), "sha256": sha256_path(source_path)},
                    "retained_current_version_inventory": {"path": data_relative(retained_path, data_root), "sha256": sha256_path(retained_path)},
                    "retained_current_version_run_log": {"path": data_relative(retained["run_log"], data_root), "sha256": sha256_path(retained["run_log"])},
                },
                "decision": {
                    "retained_current_version_resource_ids": sorted(retained_ids),
                    "excluded_pending_resource_ids": sorted(excluded_ids),
                    "retained_artifacts": retained["artifacts"],
                    "rule": "Remove each result directly requiring an excluded resource and the transitive downstream closure of explicit result_connections; add no content.",
                },
                "scope_stds_ids": scope_ids,
                "changes": changes,
                "downstream_binding_scan": {
                    "roots": ["results", "trajectories", "runs"],
                    "matches": [],
                    "downstream_generations_made_stale": [],
                },
            }
        }
        atomic_write_yaml(temporary_root / "proposal.yaml", proposal)
        atomic_write_yaml(
            temporary_root / "transaction.yaml",
            {
                "post_publication_transaction": {
                    "transaction_id": args.transaction_id,
                    "state": "PREPARED",
                    "proposal_path": data_relative(transaction_root / "proposal.yaml", data_root),
                    "error": None,
                }
            },
        )
        fsync_directory(temporary_root)
        os.replace(temporary_root, transaction_root)
        fsync_directory(parent)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return transaction_root


def verify_record(record: dict[str, Any], data_root: Path, path_field: str = "path") -> None:
    path = resolve_data_path(record[path_field], data_root)
    if not path.is_file() or path.stat().st_size != record["size_bytes"] or sha256_path(path) != record["sha256"]:
        raise RevisionError(f"file precondition failed: {path}")


def verify_prepared(transaction_root: Path, data_root: Path) -> dict[str, Any]:
    proposal = require_mapping(
        load_yaml(transaction_root / "proposal.yaml").get("post_publication_transaction_proposal"),
        "proposal",
    )
    for record in proposal["input_preconditions"].values():
        path = resolve_data_path(record["path"], data_root)
        if sha256_path(path) != record["sha256"]:
            raise RevisionError(f"input precondition changed: {path}")
    for change in proposal["changes"]:
        if file_records(resolve_data_path(change["case_directory"], data_root), data_root) != change["input_files"]:
            raise RevisionError(f"case precondition changed: {change['stds_id']}")
        if change["proposed_status"] == "accepted":
            for record in change["proposed_files"]:
                verify_record(record, data_root, "transaction_path")
            proposed_directory = transaction_root / "proposed" / f"stomicsdb_{change['stds_id']}"
            validate_case(load_case(proposed_directory), change["stds_id"])
        elif change["proposed_status"] != "no_candidate":
            raise RevisionError(f"invalid proposed status: {change['proposed_status']}")
    return proposal


def acquire_lock(path: Path, owner: dict[str, Any]) -> None:
    try:
        path.mkdir()
    except FileExistsError as error:
        raise RevisionError(f"live lock contention: {path}") from error
    atomic_write_yaml(path / "owner.yaml", owner)


def release_lock(path: Path) -> None:
    (path / "owner.yaml").unlink(missing_ok=True)
    path.rmdir()


def output_paths(stds_id: str, status: str, stomics_root: Path, data_root: Path) -> dict[str, str | None]:
    if status == "no_candidate":
        return {"source_manifest": None, "case_data_manifest": None, "case_manifest": None}
    case_directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
    return {
        "source_manifest": data_relative(case_directory / "source_manifest.yaml", data_root),
        "case_data_manifest": data_relative(case_directory / "data/case_data_manifest.yaml", data_root),
        "case_manifest": data_relative(case_directory / "case_manifest.yaml", data_root),
    }


def commit_transaction(transaction_root: Path, data_root: Path) -> None:
    transaction = require_mapping(
        load_yaml(transaction_root / "transaction.yaml").get("post_publication_transaction"),
        "transaction",
    )
    if transaction.get("state") == "COMMITTED":
        verify_committed(transaction_root, data_root)
        return
    if transaction.get("state") != "PREPARED":
        raise RevisionError(f"transaction is not committable: {transaction.get('state')}")
    proposal = verify_prepared(transaction_root, data_root)
    transaction_id = proposal["transaction_id"]
    excluded_identities = excluded_resource_identities(proposal, data_root)
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    changes = proposal["changes"]
    lock_root = stomics_root / "staging/round3_case_construction/locks"
    transaction_lock_root = transaction_root.parent / "locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    transaction_lock_root.mkdir(parents=True, exist_ok=True)
    locks = [transaction_lock_root / f"{transaction_id}.lock"] + [
        lock_root / f"stomicsdb_{value['stds_id']}.lock" for value in changes
    ]
    acquired: list[Path] = []
    moved: list[dict[str, Any]] = []
    owner = {"transaction_id": transaction_id, "operation": "round3_auxiliary_scope_contraction"}
    try:
        for lock in locks:
            acquire_lock(lock, owner)
            acquired.append(lock)
        verify_prepared(transaction_root, data_root)
        (transaction_root / "backups").mkdir()
        for change in changes:
            case_directory = resolve_data_path(change["case_directory"], data_root)
            backup_directory = resolve_data_path(change["backup_directory"], data_root)
            if backup_directory.exists():
                raise RevisionError(f"backup exists: {backup_directory}")
            os.replace(case_directory, backup_directory)
            fsync_directory(case_directory.parent)
            moved.append(change)
            if change["proposed_status"] == "accepted":
                proposed_directory = transaction_root / "proposed" / f"stomicsdb_{change['stds_id']}"
                os.replace(proposed_directory, case_directory)
                fsync_directory(case_directory.parent)

        changes_by_id = {value["stds_id"]: value for value in changes}
        cases: list[dict[str, Any]] = []
        cleanup_targets: list[dict[str, Any]] = []
        counts = {"accepted": 0, "no_candidate": 0}
        for stds_id in proposal["scope_stds_ids"]:
            change = changes_by_id.get(stds_id)
            if change is None:
                prior = find_terminal_binding(stds_id, stomics_root, data_root)
                status = "accepted"
                status_source = "retained_round3_terminal"
                details: dict[str, Any] = {}
            else:
                prior = change["prior_terminal"]
                status = change["proposed_status"]
                status_source = "committed_post_publication_revision"
                details = {
                    "excluded_inventory_resource_ids": change["excluded_inventory_resource_ids"],
                    "direct_removed_result_ids": change["direct_removed_result_ids"],
                    "downstream_removed_result_ids": change["downstream_removed_result_ids"],
                    "retained_result_ids": change["retained_result_ids"],
                    "retained_candidate_ids": change["retained_candidate_ids"],
                }
                backup_directory = resolve_data_path(change["backup_directory"], data_root)
                backup_records = file_records(backup_directory, data_root)
                expected_backup = [
                    {
                        **record,
                        "path": record["path"].replace(
                            change["case_directory"], change["backup_directory"], 1
                        ),
                    }
                    for record in change["input_files"]
                ]
                if backup_records != expected_backup:
                    raise RevisionError(f"backup bytes changed: {stds_id}")
                cleanup_targets.append(
                    {
                        "stds_id": stds_id,
                        "superseded_case_directory": change["case_directory"],
                        "preserved_backup_directory": change["backup_directory"],
                        "files": backup_records,
                        "canonical_namespace_status": "replaced" if status == "accepted" else "removed_no_candidate",
                        "backup_disposition": "retained_for_recovery",
                        "cleanup_status": "complete",
                    }
                )
            counts[status] += 1
            case_directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
            if status == "accepted":
                current_objects = load_case(case_directory)
                validate_case(current_objects, stds_id)
                residual = excluded_auxiliary_references(
                    current_objects, excluded_identities
                )
                if residual:
                    raise RevisionError(
                        f"retained case still references excluded resources: {stds_id}: {residual}"
                    )
                if change is not None:
                    validate_external_bindings(current_objects, data_root)
            elif case_directory.exists():
                raise RevisionError(f"no_candidate still has case directory: {stds_id}")
            cases.append(
                {
                    "stds_id": stds_id,
                    "authoritative_status": status,
                    "status_source": status_source,
                    "prior_terminal": prior,
                    "prior_review_rounds": prior["review_rounds"],
                    "revision_validation": "deterministic_scope_pruning" if change else None,
                    "output_paths": output_paths(stds_id, status, stomics_root, data_root),
                    **details,
                }
            )
        proposal_path = transaction_root / "proposal.yaml"
        proposal_binding = {"path": data_relative(proposal_path, data_root), "sha256": sha256_path(proposal_path)}
        revision_receipt_path = transaction_root / "revision_receipt.yaml"
        cleanup_receipt_path = transaction_root / "cleanup_receipt.yaml"
        atomic_write_yaml(
            revision_receipt_path,
            {
                "round3_case_revision_receipt": {
                    "transaction_id": transaction_id,
                    "committed_utc": utc_now(),
                    "proposal": proposal_binding,
                    "scope_stds_ids": proposal["scope_stds_ids"],
                    "retained_current_version_resource_ids": proposal["decision"]["retained_current_version_resource_ids"],
                    "excluded_pending_resource_ids": proposal["decision"]["excluded_pending_resource_ids"],
                    "cases": cases,
                    "counts": counts,
                }
            },
        )
        atomic_write_yaml(
            cleanup_receipt_path,
            {
                "post_publication_cleanup_receipt": {
                    "transaction_id": transaction_id,
                    "created_utc": utc_now(),
                    "proposal": proposal_binding,
                    "targets": cleanup_targets,
                    "retained_manifest_references_to_excluded_resources": [],
                    "downstream_generations_made_stale": [],
                    "canonical_namespace_cleanup_completed": True,
                    "transaction_backups_retained": True,
                }
            },
        )
        atomic_write_yaml(
            transaction_root / "transaction.yaml",
            {
                "post_publication_transaction": {
                    "transaction_id": transaction_id,
                    "state": "COMMITTED",
                    "proposal": proposal_binding,
                    "revision_receipt": {"path": data_relative(revision_receipt_path, data_root), "sha256": sha256_path(revision_receipt_path)},
                    "cleanup_receipt": {"path": data_relative(cleanup_receipt_path, data_root), "sha256": sha256_path(cleanup_receipt_path)},
                    "committed_stds_ids": sorted(changes_by_id),
                    "error": None,
                }
            },
        )
    except Exception as error:
        rollback_error: Exception | None = None
        try:
            for change in reversed(moved):
                case_directory = resolve_data_path(change["case_directory"], data_root)
                backup_directory = resolve_data_path(change["backup_directory"], data_root)
                if change["proposed_status"] == "accepted" and case_directory.exists():
                    proposed_directory = transaction_root / "proposed" / f"stomicsdb_{change['stds_id']}"
                    os.replace(case_directory, proposed_directory)
                if backup_directory.exists():
                    os.replace(backup_directory, case_directory)
            atomic_write_yaml(
                transaction_root / "transaction.yaml",
                {
                    "post_publication_transaction": {
                        "transaction_id": transaction_id,
                        "state": "ROLLED_BACK",
                        "proposal_path": data_relative(transaction_root / "proposal.yaml", data_root),
                        "error": str(error),
                    }
                },
            )
        except Exception as nested:
            rollback_error = nested
        if rollback_error:
            raise RevisionError(f"commit failed ({error}); rollback failed ({rollback_error})") from error
        raise
    finally:
        for lock in reversed(acquired):
            release_lock(lock)


def verify_committed(transaction_root: Path, data_root: Path) -> None:
    transaction = require_mapping(
        load_yaml(transaction_root / "transaction.yaml").get("post_publication_transaction"),
        "transaction",
    )
    if transaction.get("state") != "COMMITTED":
        raise RevisionError(f"transaction is not committed: {transaction.get('state')}")
    for name in ("proposal", "revision_receipt", "cleanup_receipt"):
        record = transaction[name]
        if sha256_path(resolve_data_path(record["path"], data_root)) != record["sha256"]:
            raise RevisionError(f"transaction binding mismatch: {name}")
    proposal = require_mapping(
        load_yaml(resolve_data_path(transaction["proposal"]["path"], data_root)).get(
            "post_publication_transaction_proposal"
        ),
        "proposal",
    )
    receipt = require_mapping(
        load_yaml(resolve_data_path(transaction["revision_receipt"]["path"], data_root)).get(
            "round3_case_revision_receipt"
        ),
        "revision receipt",
    )
    cleanup = require_mapping(
        load_yaml(resolve_data_path(transaction["cleanup_receipt"]["path"], data_root)).get(
            "post_publication_cleanup_receipt"
        ),
        "cleanup receipt",
    )
    if receipt.get("proposal") != transaction["proposal"] or cleanup.get("proposal") != transaction["proposal"]:
        raise RevisionError("transaction receipts do not bind the committed proposal")
    excluded_identities = excluded_resource_identities(proposal, data_root)
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    counts = {"accepted": 0, "no_candidate": 0}
    for case in receipt["cases"]:
        stds_id = case["stds_id"]
        status = case["authoritative_status"]
        counts[status] += 1
        directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
        if status == "accepted":
            objects = load_case(directory)
            validate_case(objects, stds_id)
            residual = excluded_auxiliary_references(objects, excluded_identities)
            if residual:
                raise RevisionError(
                    f"retained case still references excluded resources: {stds_id}: {residual}"
                )
        elif status == "no_candidate":
            if directory.exists():
                raise RevisionError(f"no_candidate has case directory: {stds_id}")
        else:
            raise RevisionError(f"invalid status: {status}")
    if counts != receipt["counts"]:
        raise RevisionError("revision receipt counts mismatch")
    if cleanup.get("retained_manifest_references_to_excluded_resources") != []:
        raise RevisionError("cleanup receipt reports retained excluded-resource references")
    if cleanup.get("canonical_namespace_cleanup_completed") is not True:
        raise RevisionError("cleanup receipt is not complete")
    for target in require_list(cleanup.get("targets"), "cleanup targets"):
        backup = resolve_data_path(target["preserved_backup_directory"], data_root)
        if file_records(backup, data_root) != target["files"]:
            raise RevisionError(f"cleanup backup binding mismatch: {target['stds_id']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--retained-inventory", type=Path, required=True)
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
            load_yaml(transaction_root / "transaction.yaml").get("post_publication_transaction"),
            "transaction",
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
    except (OSError, RevisionError, yaml.YAMLError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
