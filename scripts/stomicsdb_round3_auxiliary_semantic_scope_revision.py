#!/usr/bin/env python3
"""Apply an evidence-backed semantic contraction to current Round 3 cases."""

from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
from typing import Any

import yaml

from stomicsdb_round3_auxiliary_scope_revision import (
    CASE_FILES,
    DEFAULT_DATA_ROOT,
    STOMICS_RELATIVE,
    TRANSACTION_ID_PATTERN,
    RevisionError,
    acquire_lock,
    atomic_write_yaml,
    data_relative,
    dump_yaml,
    excluded_auxiliary_references,
    file_records,
    fsync_directory,
    load_case,
    load_json,
    load_yaml,
    output_paths,
    ordered_union,
    prune_case,
    release_lock,
    require_list,
    require_mapping,
    resolve_data_path,
    result_link_map,
    serialize_case,
    sha256_path,
    utc_now,
    validate_case,
    validate_external_bindings,
    verify_record,
    write_case_tree,
)


REVISION_KIND = "round3_auxiliary_semantic_scope_contraction"
CHAIN_EXTRACTION_FILES = {
    "chain_manifest.yaml",
    "scientific_chain.jsonl",
    "execution_subchains.jsonl",
}
CHAIN_FINAL_FILES = CHAIN_EXTRACTION_FILES | {"independent_check.md"}


def _evidence_paths(record: dict[str, Any], context: str) -> None:
    evidence_paths = record.get("evidence_paths", [])
    if not isinstance(evidence_paths, list) or not all(
        isinstance(value, str) and value for value in evidence_paths
    ):
        raise RevisionError(f"evidence_paths must be a list of paths: {context}")


def load_published_case(case_directory: Path) -> dict[str, dict[str, Any]]:
    expected = {value.as_posix() for value in CASE_FILES}
    actual_files: set[str] = set()
    chain_files: dict[str, set[str]] = defaultdict(set)
    for path in case_directory.rglob("*"):
        relative = path.relative_to(case_directory)
        value = relative.as_posix()
        if path.is_symlink():
            raise RevisionError(f"published case contains a symlink: {path}")
        if path.is_dir():
            if value == "data" or value == "dual_chain":
                continue
            if (
                len(relative.parts) == 2
                and relative.parts[0] == "dual_chain"
                and relative.parts[1].startswith("chain_sha256_")
            ):
                continue
            raise RevisionError(f"published case contains an unexpected directory: {path}")
        if not path.is_file():
            raise RevisionError(f"published case contains a non-regular entry: {path}")
        if value in expected:
            actual_files.add(value)
            continue
        if (
            len(relative.parts) == 3
            and relative.parts[0] == "dual_chain"
            and relative.parts[1].startswith("chain_sha256_")
            and relative.parts[2] in CHAIN_FINAL_FILES
        ):
            chain_files[relative.parts[1]].add(relative.parts[2])
            continue
        raise RevisionError(f"published case contains an unexpected file: {path}")
    if actual_files != expected:
        raise RevisionError(
            f"published case manifest set is incomplete: {case_directory}: {sorted(actual_files)}"
        )
    for chain_id, files in chain_files.items():
        if files not in (CHAIN_EXTRACTION_FILES, CHAIN_FINAL_FILES):
            raise RevisionError(
                f"published case contains an incomplete dual chain: {chain_id}: {sorted(files)}"
            )
    paths = [case_directory.joinpath(*value.parts) for value in CASE_FILES]
    return {
        "source": require_mapping(
            load_yaml(paths[0]).get("source_manifest"), "source_manifest"
        ),
        "data": require_mapping(
            load_yaml(paths[1]).get("case_data_manifest"), "case_data_manifest"
        ),
        "case": require_mapping(
            load_yaml(paths[2]).get("case_manifest"), "case_manifest"
        ),
    }


def published_manifest_file_records(
    case_directory: Path, data_root: Path
) -> list[dict[str, Any]]:
    load_published_case(case_directory)
    manifest_paths = [case_directory.joinpath(*value.parts) for value in CASE_FILES]
    return [
        {
            "path": data_relative(path, data_root),
            "sha256": sha256_path(path),
            "size_bytes": path.stat().st_size,
        }
        for path in manifest_paths
    ]


def published_file_records(
    case_directory: Path, data_root: Path
) -> list[dict[str, Any]]:
    manifest_records = published_manifest_file_records(case_directory, data_root)
    manifest_paths = [case_directory.joinpath(*value.parts) for value in CASE_FILES]
    manifest_set = set(manifest_paths)
    chain_paths = sorted(
        value
        for value in case_directory.rglob("*")
        if value.is_file() and value not in manifest_set
    )
    return manifest_records + [
        {
            "path": data_relative(path, data_root),
            "sha256": sha256_path(path),
            "size_bytes": path.stat().st_size,
        }
        for path in chain_paths
    ]


def load_evidence(path: Path) -> dict[str, list[dict[str, Any]]]:
    document = load_yaml(path)
    raw_resources = require_list(document.get("resources"), "evidence resources")
    resources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_resources:
        resource = require_mapping(raw, "evidence resource")
        inventory_id = resource.get("inventory_id")
        if not isinstance(inventory_id, str) or not inventory_id or inventory_id in seen:
            raise RevisionError(f"duplicate or invalid evidence inventory_id: {inventory_id}")
        seen.add(inventory_id)
        if resource.get("verdict") != "incomplete":
            raise RevisionError(f"evidence verdict must be incomplete: {inventory_id}")
        missing = resource.get("missing_content")
        if not (
            isinstance(missing, str) and missing.strip()
            or isinstance(missing, list)
            and missing
            and all(isinstance(value, str) and value.strip() for value in missing)
        ):
            raise RevisionError(f"missing_content must be nonempty: {inventory_id}")
        _evidence_paths(resource, inventory_id)
        if not isinstance(resource.get("reconstruction_required"), bool):
            raise RevisionError(f"reconstruction_required must be boolean: {inventory_id}")
        resources.append(deepcopy(resource))
    corrections: list[dict[str, Any]] = []
    for raw in require_list(document.get("resource_corrections", []), "resource_corrections"):
        record = require_mapping(raw, "resource correction")
        context = f"{record.get('stds_id')}:{record.get('resource_id')}"
        if not all(
            isinstance(record.get(key), str) and record[key]
            for key in ("inventory_id", "stds_id", "resource_id")
        ):
            raise RevisionError(f"invalid resource correction identity: {context}")
        prior = require_mapping(record.get("prior_values"), f"prior_values {context}")
        new = require_mapping(record.get("new_values"), f"new_values {context}")
        allowed = {"expected_content", "access_notes"}
        if not prior or set(prior) != set(new) or not set(prior) <= allowed:
            raise RevisionError(f"resource correction fields are not allowlisted: {context}")
        if any(not isinstance(value, str) or not value.strip() for value in [*prior.values(), *new.values()]):
            raise RevisionError(f"resource correction values must be nonempty strings: {context}")
        if prior == new:
            raise RevisionError(f"resource correction makes no change: {context}")
        _evidence_paths(record, context)
        corrections.append(deepcopy(record))

    detachments: list[dict[str, Any]] = []
    for raw in require_list(document.get("auxiliary_detachments", []), "auxiliary_detachments"):
        record = require_mapping(raw, "auxiliary detachment")
        context = f"{record.get('stds_id')}:{record.get('resource_id')}"
        if not all(
            isinstance(record.get(key), str) and record[key]
            for key in ("inventory_id", "stds_id", "resource_id")
        ):
            raise RevisionError(f"invalid auxiliary detachment identity: {context}")
        result_ids = require_list(record.get("result_ids"), f"detachment result_ids {context}")
        independent = require_list(
            record.get("independent_article_anchor_result_ids"),
            f"independent article anchors {context}",
        )
        if (
            not result_ids
            or len(result_ids) != len(set(result_ids))
            or not all(isinstance(value, str) and value for value in result_ids)
            or set(independent) != set(result_ids)
        ):
            raise RevisionError(f"detachment must independently anchor every result: {context}")
        _evidence_paths(record, context)
        detachments.append(deepcopy(record))

    anchor_corrections: list[dict[str, Any]] = []
    for raw in require_list(
        document.get("source_anchor_corrections", []), "source_anchor_corrections"
    ):
        record = require_mapping(raw, "source anchor correction")
        context = f"{record.get('stds_id')}:{record.get('result_id')}"
        if not all(
            isinstance(record.get(key), str) and record[key]
            for key in ("stds_id", "result_id")
        ):
            raise RevisionError(f"invalid source anchor correction identity: {context}")
        prior = require_list(
            record.get("prior_source_anchors"), f"prior source anchors {context}"
        )
        new = require_list(record.get("new_source_anchors"), f"new source anchors {context}")
        if not prior or not new or prior == new or any(not isinstance(value, dict) for value in prior + new):
            raise RevisionError(f"source anchor correction must bind distinct nonempty anchors: {context}")
        _evidence_paths(record, context)
        anchor_corrections.append(deepcopy(record))

    result_scope_exclusions: list[dict[str, Any]] = []
    for raw in require_list(
        document.get("result_scope_exclusions", []), "result_scope_exclusions"
    ):
        record = require_mapping(raw, "result scope exclusion")
        stds_id = record.get("stds_id")
        result_ids = require_list(
            record.get("result_ids"), f"result scope exclusion {stds_id}"
        )
        if (
            not isinstance(stds_id, str)
            or not stds_id
            or not result_ids
            or len(result_ids) != len(set(result_ids))
            or not all(isinstance(value, str) and value for value in result_ids)
        ):
            raise RevisionError(f"invalid result scope exclusion identity: {stds_id}")
        if (
            record.get("criterion") != "uses_assigned_spatial_data"
            or record.get("required_value") != "yes"
            or record.get("observed_value") != "no"
        ):
            raise RevisionError(
                f"result scope exclusion is not an assigned-spatial eligibility failure: {stds_id}"
            )
        if not isinstance(record.get("rationale"), str) or not record["rationale"].strip():
            raise RevisionError(f"result scope exclusion lacks rationale: {stds_id}")
        _evidence_paths(record, f"result scope exclusion {stds_id}")
        result_scope_exclusions.append(deepcopy(record))

    if not any(
        (
            resources,
            corrections,
            detachments,
            anchor_corrections,
            result_scope_exclusions,
        )
    ):
        raise RevisionError("exclusion evidence contains no revisions")
    return {
        "resources": resources,
        "resource_corrections": corrections,
        "auxiliary_detachments": detachments,
        "source_anchor_corrections": anchor_corrections,
        "result_scope_exclusions": result_scope_exclusions,
    }


def resolve_result_scope_exclusions(
    evidence: list[dict[str, Any]],
    current_cases: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, set[str]], dict[str, list[dict[str, Any]]]]:
    per_case: dict[str, set[str]] = defaultdict(set)
    details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for record in evidence:
        stds_id = record["stds_id"]
        if stds_id not in current_cases:
            raise RevisionError(
                f"result scope exclusion targets a non-accepted case: {stds_id}"
            )
        available = {
            value["result_id"] for value in current_cases[stds_id]["source"]["results"]
        }
        requested = set(record["result_ids"])
        if not requested <= available:
            raise RevisionError(f"result scope exclusion is unresolved: {stds_id}")
        for result_id in requested:
            identity = (stds_id, result_id)
            if identity in seen:
                raise RevisionError(
                    f"duplicate result scope exclusion: {stds_id}:{result_id}"
                )
            seen.add(identity)
        per_case[stds_id].update(requested)
        details[stds_id].append(deepcopy(record))
    return dict(per_case), dict(details)


def inventory_resource_map(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for raw in require_list(inventory.get("resources"), "inventory resources"):
        resource = require_mapping(raw, "inventory resource")
        inventory_id = resource.get("inventory_id")
        if not isinstance(inventory_id, str) or not inventory_id or inventory_id in output:
            raise RevisionError(f"duplicate or invalid inventory resource: {inventory_id}")
        if not isinstance(resource.get("resource_name"), str) or not isinstance(
            resource.get("source_url"), str
        ):
            raise RevisionError(f"inventory resource lacks a stable identity: {inventory_id}")
        output[inventory_id] = resource
    return output


def accepted_case_objects(
    receipt: dict[str, Any], stomics_root: Path, data_root: Path
) -> tuple[list[str], dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, Any]]]:
    scope = require_list(receipt.get("scope_stds_ids"), "receipt scope_stds_ids")
    if len(scope) != 16 or len(set(scope)) != 16 or not all(isinstance(value, str) for value in scope):
        raise RevisionError("current revision receipt must bind exactly 16 unique STDS IDs")
    raw_cases = require_list(receipt.get("cases"), "receipt cases")
    by_id: dict[str, dict[str, Any]] = {}
    objects: dict[str, dict[str, dict[str, Any]]] = {}
    for raw in raw_cases:
        record = require_mapping(raw, "receipt case")
        stds_id = record.get("stds_id")
        if not isinstance(stds_id, str) or stds_id in by_id:
            raise RevisionError(f"duplicate or invalid receipt case: {stds_id}")
        by_id[stds_id] = record
    if set(by_id) != set(scope):
        raise RevisionError("receipt case IDs differ from its 16-case scope")
    for stds_id in scope:
        record = by_id[stds_id]
        status = record.get("authoritative_status")
        directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
        if status == "accepted":
            expected = output_paths(stds_id, status, stomics_root, data_root)
            if record.get("output_paths") != expected:
                raise RevisionError(f"receipt output paths are not canonical: {stds_id}")
            objects[stds_id] = load_published_case(directory)
            validate_case(objects[stds_id], stds_id)
        elif status == "no_candidate":
            if record.get("output_paths") != output_paths(stds_id, status, stomics_root, data_root):
                raise RevisionError(f"no_candidate output paths are not null: {stds_id}")
            if directory.exists():
                raise RevisionError(f"no_candidate has a current case directory: {stds_id}")
        else:
            raise RevisionError(f"invalid authoritative status: {stds_id}:{status}")
        prior = require_mapping(record.get("prior_terminal"), f"prior_terminal {stds_id}")
        if record.get("prior_review_rounds") != prior.get("review_rounds"):
            raise RevisionError(f"review-round binding mismatch: {stds_id}")
    expected_counts = {
        "accepted": sum(value["authoritative_status"] == "accepted" for value in by_id.values()),
        "no_candidate": sum(
            value["authoritative_status"] == "no_candidate" for value in by_id.values()
        ),
    }
    if receipt.get("counts") != expected_counts:
        raise RevisionError("current revision receipt counts mismatch")
    return list(scope), objects, by_id


def resolve_excluded_resource_mappings(
    inventory: dict[str, Any],
    evidence: list[dict[str, Any]],
    current_cases: dict[str, dict[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, set[str]]]]:
    resources = inventory_resource_map(inventory)
    per_case: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {
            "inventory_ids": set(),
            "auxiliary_ids": set(),
            "direct_result_ids": set(),
        }
    )
    resolved: list[dict[str, Any]] = []
    seen_identities: set[tuple[str, str]] = set()
    for evidence_record in evidence:
        inventory_id = evidence_record["inventory_id"]
        if inventory_id not in resources:
            raise RevisionError(f"evidence inventory_id is absent from source inventory: {inventory_id}")
        inventory_record = resources[inventory_id]
        identity = (inventory_record["resource_name"], inventory_record["source_url"])
        if identity in seen_identities:
            raise RevisionError(f"excluded inventory resources share an identity: {inventory_id}")
        seen_identities.add(identity)
        mappings: list[dict[str, Any]] = []
        for stds_id, objects in current_cases.items():
            auxiliary_ids = {
                value["resource_id"]
                for value in objects["data"]["auxiliary_resources"]
                if (value.get("resource_name"), value.get("source_url")) == identity
            }
            if not auxiliary_ids:
                continue
            links = result_link_map(objects["data"])
            direct = {
                result_id
                for result_id, link in links.items()
                if auxiliary_ids.intersection(link["auxiliary_resource_ids"])
            }
            if not direct:
                raise RevisionError(
                    f"excluded Axx is not linked to a current result: {inventory_id}:{stds_id}"
                )
            per_case[stds_id]["inventory_ids"].add(inventory_id)
            per_case[stds_id]["auxiliary_ids"].update(auxiliary_ids)
            per_case[stds_id]["direct_result_ids"].update(direct)
            mappings.append(
                {
                    "stds_id": stds_id,
                    "case_auxiliary_resource_ids": sorted(auxiliary_ids),
                    "direct_result_ids": sorted(direct),
                }
            )
        if not mappings:
            raise RevisionError(f"excluded resource does not map to any current Axx: {inventory_id}")
        resolved.append(
            {
                "inventory_id": inventory_id,
                "resource_name": identity[0],
                "source_url": identity[1],
                "expected_content": inventory_record.get("expected_content"),
                "inventory_result_ids_by_case": deepcopy(
                    inventory_record.get("result_ids_by_case", {})
                ),
                "evidence": deepcopy(evidence_record),
                "current_case_mappings": mappings,
            }
        )
    return resolved, dict(per_case)


def apply_allowlisted_corrections(
    inventory: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    current_cases: dict[str, dict[str, dict[str, Any]]],
) -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, dict[str, list[dict[str, Any]]]],
]:
    resources = inventory_resource_map(inventory)
    revised_cases = deepcopy(current_cases)
    per_case: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {
            "resource_corrections": [],
            "auxiliary_detachments": [],
            "source_anchor_corrections": [],
        }
    )
    touched_resources: set[tuple[str, str]] = set()
    touched_results: set[tuple[str, str]] = set()

    for correction in evidence["source_anchor_corrections"]:
        stds_id = correction["stds_id"]
        result_id = correction["result_id"]
        target = (stds_id, result_id)
        if target in touched_results:
            raise RevisionError(f"duplicate source-anchor correction: {stds_id}:{result_id}")
        touched_results.add(target)
        if stds_id not in revised_cases:
            raise RevisionError(f"source-anchor correction targets a non-accepted case: {stds_id}")
        results = {
            value["result_id"]: value
            for value in revised_cases[stds_id]["source"]["results"]
        }
        if result_id not in results:
            raise RevisionError(f"source-anchor correction has unresolved result: {stds_id}:{result_id}")
        result = results[result_id]
        if result.get("source_anchors") != correction["prior_source_anchors"]:
            raise RevisionError(f"source-anchor prior value mismatch: {stds_id}:{result_id}")
        prior_result = deepcopy(result)
        result["source_anchors"] = deepcopy(correction["new_source_anchors"])
        if {key: value for key, value in result.items() if key != "source_anchors"} != {
            key: value for key, value in prior_result.items() if key != "source_anchors"
        }:
            raise RevisionError(f"source-anchor correction changed other fields: {stds_id}:{result_id}")
        per_case[stds_id]["source_anchor_corrections"].append(
            {
                "result_id": result_id,
                "prior_source_anchors": deepcopy(correction["prior_source_anchors"]),
                "new_source_anchors": deepcopy(correction["new_source_anchors"]),
                "evidence_paths": deepcopy(correction.get("evidence_paths", [])),
            }
        )

    for correction in evidence["resource_corrections"]:
        inventory_id = correction["inventory_id"]
        stds_id = correction["stds_id"]
        resource_id = correction["resource_id"]
        target = (stds_id, resource_id)
        if target in touched_resources:
            raise RevisionError(f"duplicate Axx correction/detachment: {stds_id}:{resource_id}")
        touched_resources.add(target)
        if inventory_id not in resources or stds_id not in revised_cases:
            raise RevisionError(f"resource correction target is unresolved: {inventory_id}:{stds_id}")
        inventory_record = resources[inventory_id]
        matches = [
            value
            for value in revised_cases[stds_id]["data"]["auxiliary_resources"]
            if value.get("resource_id") == resource_id
        ]
        if len(matches) != 1:
            raise RevisionError(f"resource correction does not resolve one Axx: {stds_id}:{resource_id}")
        resource = matches[0]
        if (resource.get("resource_name"), resource.get("source_url")) != (
            inventory_record["resource_name"],
            inventory_record["source_url"],
        ):
            raise RevisionError(f"resource correction identity mismatch: {inventory_id}:{stds_id}")
        frozen_identity = {
            key: resource.get(key)
            for key in (
                "resource_id",
                "resource_name",
                "source_url",
                "access_classification",
            )
        }
        for field, prior_value in correction["prior_values"].items():
            if resource.get(field) != prior_value:
                raise RevisionError(f"resource correction prior value mismatch: {stds_id}:{resource_id}:{field}")
        for field, new_value in correction["new_values"].items():
            resource[field] = new_value
        if any(resource.get(key) != value for key, value in frozen_identity.items()):
            raise RevisionError(f"resource correction changed identity: {stds_id}:{resource_id}")
        per_case[stds_id]["resource_corrections"].append(
            {
                "inventory_id": inventory_id,
                "resource_id": resource_id,
                "prior_values": deepcopy(correction["prior_values"]),
                "new_values": deepcopy(correction["new_values"]),
                "evidence_paths": deepcopy(correction.get("evidence_paths", [])),
            }
        )

    for detachment in evidence["auxiliary_detachments"]:
        inventory_id = detachment["inventory_id"]
        stds_id = detachment["stds_id"]
        resource_id = detachment["resource_id"]
        target = (stds_id, resource_id)
        if target in touched_resources:
            raise RevisionError(f"duplicate Axx correction/detachment: {stds_id}:{resource_id}")
        touched_resources.add(target)
        if inventory_id not in resources or stds_id not in revised_cases:
            raise RevisionError(f"detachment target is unresolved: {inventory_id}:{stds_id}")
        objects = revised_cases[stds_id]
        inventory_record = resources[inventory_id]
        matches = [
            value
            for value in objects["data"]["auxiliary_resources"]
            if value.get("resource_id") == resource_id
        ]
        if len(matches) != 1 or (
            matches[0].get("resource_name"), matches[0].get("source_url")
        ) != (inventory_record["resource_name"], inventory_record["source_url"]):
            raise RevisionError(f"detachment resource identity mismatch: {inventory_id}:{stds_id}")
        links = result_link_map(objects["data"])
        linked_results = {
            result_id
            for result_id, link in links.items()
            if resource_id in link["auxiliary_resource_ids"]
        }
        requested_results = set(detachment["result_ids"])
        if linked_results != requested_results:
            raise RevisionError(f"detachment does not cover all and only linked results: {stds_id}:{resource_id}")
        source_results = {
            value["result_id"]: value for value in objects["source"]["results"]
        }
        for result_id in requested_results:
            if not source_results.get(result_id, {}).get("source_anchors"):
                raise RevisionError(f"detached result lacks independent article anchors: {stds_id}:{result_id}")
            links[result_id]["auxiliary_resource_ids"] = [
                value
                for value in links[result_id]["auxiliary_resource_ids"]
                if value != resource_id
            ]
        if any(
            resource_id in link["auxiliary_resource_ids"] for link in links.values()
        ):
            raise RevisionError(f"detached Axx remains referenced: {stds_id}:{resource_id}")
        objects["data"]["auxiliary_resources"] = [
            value
            for value in objects["data"]["auxiliary_resources"]
            if value["resource_id"] != resource_id
        ]
        for candidate in objects["case"]["case_candidates"]:
            candidate["auxiliary_resource_ids"] = ordered_union(
                links[result_id]["auxiliary_resource_ids"]
                for result_id in candidate["result_ids"]
            )
        per_case[stds_id]["auxiliary_detachments"].append(
            {
                "inventory_id": inventory_id,
                "resource_id": resource_id,
                "detached_result_ids": sorted(requested_results),
                "prior_resource": deepcopy(matches[0]),
                "new_resource": None,
                "independent_article_anchors": {
                    result_id: deepcopy(source_results[result_id]["source_anchors"])
                    for result_id in sorted(requested_results)
                },
                "evidence_paths": deepcopy(detachment.get("evidence_paths", [])),
            }
        )

    for stds_id in per_case:
        validate_case(revised_cases[stds_id], stds_id)
    return revised_cases, dict(per_case)


def revise_case_for_exclusions(
    objects: dict[str, dict[str, Any]], direct_result_ids: set[str]
) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any]]:
    revised, details = prune_case(objects, direct_result_ids)
    if revised is None:
        return None, details
    validate_case(revised, revised["case"]["stds_id"])
    original_results = {value["result_id"]: value for value in objects["source"]["results"]}
    original_links = {
        value["result_id"]: value for value in objects["data"]["result_data_links"]
    }
    for value in revised["source"]["results"]:
        if value != original_results.get(value["result_id"]):
            raise RevisionError("surviving source-result content changed during contraction")
    for value in revised["data"]["result_data_links"]:
        if value != original_links.get(value["result_id"]):
            raise RevisionError("surviving result-link content changed during contraction")
    return revised, details


def write_proposed_case(
    temporary_root: Path,
    transaction_root: Path,
    case_directory: Path,
    stds_id: str,
    objects: dict[str, dict[str, Any]],
    data_root: Path,
) -> list[dict[str, Any]]:
    proposed_directory = temporary_root / "proposed" / f"stomicsdb_{stds_id}"
    write_case_tree(proposed_directory, serialize_case(objects))
    if load_case(proposed_directory) != objects:
        raise RevisionError(f"proposed parsed-object equality failed: {stds_id}")
    records: list[dict[str, Any]] = []
    for local_record in file_records(proposed_directory, temporary_root):
        suffix = PurePosixPath(local_record.pop("path")).relative_to(
            PurePosixPath("proposed") / f"stomicsdb_{stds_id}"
        )
        records.append(
            {
                **local_record,
                "transaction_path": data_relative(
                    transaction_root / "proposed" / f"stomicsdb_{stds_id}" / Path(*suffix.parts),
                    data_root,
                ),
                "target_path": data_relative(case_directory / Path(*suffix.parts), data_root),
            }
        )
    return records


def prepare_transaction(args: argparse.Namespace) -> Path:
    data_root = args.data_root.resolve()
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    transaction_root = (
        stomics_root / "staging/post_publication_transactions" / args.transaction_id
    )
    if transaction_root.exists():
        raise RevisionError(f"transaction already exists: {transaction_root}")
    source_path = args.source_inventory.resolve()
    receipt_path = args.current_revision_receipt.resolve()
    evidence_path = args.exclusion_evidence.resolve()
    source = load_json(source_path)
    receipt = require_mapping(
        load_yaml(receipt_path).get("round3_case_revision_receipt"),
        "current revision receipt",
    )
    evidence = load_evidence(evidence_path)
    scope, current_cases, receipt_cases = accepted_case_objects(
        receipt, stomics_root, data_root
    )
    if source.get("scope_stds_ids") != scope:
        raise RevisionError("source inventory scope differs from current revision receipt")
    corrected_cases, correction_details = apply_allowlisted_corrections(
        source, evidence, current_cases
    )
    resources, per_case = resolve_excluded_resource_mappings(
        source, evidence["resources"], corrected_cases
    )
    scope_result_ids, scope_details = resolve_result_scope_exclusions(
        evidence["result_scope_exclusions"], corrected_cases
    )
    for stds_id, result_ids in scope_result_ids.items():
        mapping = per_case.setdefault(
            stds_id,
            {
                "inventory_ids": set(),
                "auxiliary_ids": set(),
                "direct_result_ids": set(),
            },
        )
        mapping["direct_result_ids"].update(result_ids)

    parent = transaction_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{args.transaction_id}.preparing.", dir=parent))
    try:
        changes: list[dict[str, Any]] = []
        for stds_id in scope:
            prior = receipt_cases[stds_id]
            prior_status = prior["authoritative_status"]
            case_directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
            common: dict[str, Any] = {
                "stds_id": stds_id,
                "prior_status": prior_status,
                "prior_terminal": deepcopy(prior["prior_terminal"]),
                "prior_review_rounds": prior["prior_review_rounds"],
                "case_directory": data_relative(case_directory, data_root),
                "excluded_inventory_resource_ids": [],
                "excluded_case_auxiliary_resource_ids": [],
                "direct_removed_result_ids": [],
                "downstream_removed_result_ids": [],
                "removed_result_ids": [],
                "retained_result_ids": [],
                "retained_candidate_ids": [],
                "input_files": [],
                "proposed_files": [],
                "backup_directory": None,
                "resource_corrections": [],
                "auxiliary_detachments": [],
                "source_anchor_corrections": [],
                "result_scope_exclusions": deepcopy(scope_details.get(stds_id, [])),
            }
            if prior_status == "no_candidate":
                changes.append({**common, "action": "retain", "proposed_status": "no_candidate"})
                continue
            objects = corrected_cases[stds_id]
            common["input_files"] = published_file_records(case_directory, data_root)
            mapping = per_case.get(stds_id)
            corrections = correction_details.get(stds_id)
            if corrections is not None:
                common.update(deepcopy(corrections))
            if mapping is None and corrections is None:
                changes.append(
                    {
                        **common,
                        "action": "retain",
                        "proposed_status": "accepted",
                        "retained_result_ids": [
                            value["result_id"] for value in objects["source"]["results"]
                        ],
                        "retained_candidate_ids": [
                            value["candidate_id"]
                            for value in objects["case"]["case_candidates"]
                        ],
                    }
                )
                continue
            if mapping is None:
                revised = objects
                details = {
                    "direct_removed_result_ids": [],
                    "downstream_removed_result_ids": [],
                    "removed_result_ids": [],
                    "retained_result_ids": [
                        value["result_id"] for value in objects["source"]["results"]
                    ],
                    "retained_candidate_ids": [
                        value["candidate_id"]
                        for value in objects["case"]["case_candidates"]
                    ],
                }
                mapping = {
                    "inventory_ids": set(),
                    "auxiliary_ids": set(),
                    "direct_result_ids": set(),
                }
            else:
                revised, details = revise_case_for_exclusions(
                    objects, mapping["direct_result_ids"]
                )
            proposed_status = "accepted" if revised is not None else "no_candidate"
            action = "replace" if revised is not None else "remove_no_candidate"
            backup_directory = transaction_root / "backups" / f"stomicsdb_{stds_id}"
            proposed_files = (
                write_proposed_case(
                    temporary_root,
                    transaction_root,
                    case_directory,
                    stds_id,
                    revised,
                    data_root,
                )
                if revised is not None
                else []
            )
            changes.append(
                {
                    **common,
                    "action": action,
                    "proposed_status": proposed_status,
                    "backup_directory": data_relative(backup_directory, data_root),
                    "excluded_inventory_resource_ids": sorted(mapping["inventory_ids"]),
                    "excluded_case_auxiliary_resource_ids": sorted(mapping["auxiliary_ids"]),
                    **details,
                    "proposed_files": proposed_files,
                }
            )

        proposal = {
            "post_publication_transaction_proposal": {
                "transaction_id": args.transaction_id,
                "created_utc": utc_now(),
                "revision_kind": REVISION_KIND,
                "purpose": "Remove result chains whose required inputs are semantically incomplete or whose assigned-spatial eligibility is disproved; add no content.",
                "input_preconditions": {
                    "source_inventory": {
                        "path": data_relative(source_path, data_root),
                        "sha256": sha256_path(source_path),
                    },
                    "current_revision_receipt": {
                        "path": data_relative(receipt_path, data_root),
                        "sha256": sha256_path(receipt_path),
                    },
                    "exclusion_evidence": {
                        "path": data_relative(evidence_path, data_root),
                        "sha256": sha256_path(evidence_path),
                    },
                },
                "scope_stds_ids": scope,
                "decision": {
                    "rule": "Remove directly dependent Rxx and the transitive downstream closure of explicit result_connections; preserve surviving IDs and content without additions or renumbering.",
                    "excluded_resources": resources,
                    "resource_corrections": deepcopy(evidence["resource_corrections"]),
                    "auxiliary_detachments": deepcopy(evidence["auxiliary_detachments"]),
                    "source_anchor_corrections": deepcopy(
                        evidence["source_anchor_corrections"]
                    ),
                    "result_scope_exclusions": deepcopy(
                        evidence["result_scope_exclusions"]
                    ),
                },
                "changes": changes,
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
        if transaction_root.exists():
            raise RevisionError(f"transaction already exists: {transaction_root}")
        os.rename(temporary_root, transaction_root)
        fsync_directory(parent)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return transaction_root


def excluded_identities(proposal: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (value["resource_name"], value["source_url"])
        for value in proposal["decision"]["excluded_resources"]
    }


def verify_prepared(transaction_root: Path, data_root: Path) -> dict[str, Any]:
    proposal = require_mapping(
        load_yaml(transaction_root / "proposal.yaml").get(
            "post_publication_transaction_proposal"
        ),
        "proposal",
    )
    if proposal.get("revision_kind") != REVISION_KIND:
        raise RevisionError("unexpected revision kind")
    for record in proposal["input_preconditions"].values():
        path = resolve_data_path(record["path"], data_root)
        if not path.is_file() or sha256_path(path) != record["sha256"]:
            raise RevisionError(f"input precondition changed: {path}")
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    for change in proposal["changes"]:
        directory = resolve_data_path(change["case_directory"], data_root)
        if change["prior_status"] == "accepted":
            if published_file_records(directory, data_root) != change["input_files"]:
                raise RevisionError(f"case precondition changed: {change['stds_id']}")
        elif directory.exists():
            raise RevisionError(f"prior no_candidate reappeared: {change['stds_id']}")
        action = change["action"]
        if action == "replace":
            if change["prior_status"] != "accepted" or change["proposed_status"] != "accepted":
                raise RevisionError(f"replace action has invalid statuses: {change['stds_id']}")
            proposed = transaction_root / "proposed" / f"stomicsdb_{change['stds_id']}"
            for record in change["proposed_files"]:
                verify_record(record, data_root, "transaction_path")
            validate_case(load_case(proposed), change["stds_id"])
            actual = file_records(proposed, data_root)
            expected = [
                {
                    "path": value["transaction_path"],
                    "sha256": value["sha256"],
                    "size_bytes": value["size_bytes"],
                }
                for value in change["proposed_files"]
            ]
            if actual != expected:
                raise RevisionError(f"proposed file binding mismatch: {change['stds_id']}")
        elif action == "remove_no_candidate":
            if (
                change["prior_status"] != "accepted"
                or change["proposed_status"] != "no_candidate"
                or change["proposed_files"]
            ):
                raise RevisionError("no_candidate proposal contains files")
        elif action == "retain":
            if change["proposed_status"] != change["prior_status"] or change["proposed_files"]:
                raise RevisionError(f"retain action changes status or files: {change['stds_id']}")
        else:
            raise RevisionError(f"invalid case action: {action}")
    if len(proposal["changes"]) != 16:
        raise RevisionError("proposal does not cover all 16 cases")
    return proposal


def expected_backup_records(change: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **record,
            "path": record["path"].replace(
                change["case_directory"], change["backup_directory"], 1
            ),
        }
        for record in change["input_files"]
    ]


def verify_current_case(
    stds_id: str,
    status: str,
    stomics_root: Path,
    data_root: Path,
    identities: set[tuple[str, str]],
) -> None:
    directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
    if status == "no_candidate":
        if directory.exists():
            raise RevisionError(f"no_candidate has a case directory: {stds_id}")
        return
    objects = load_published_case(directory)
    validate_case(objects, stds_id)
    validate_external_bindings(objects, data_root)
    residual = excluded_auxiliary_references(objects, identities)
    if residual:
        raise RevisionError(f"current case retains excluded identities: {stds_id}:{residual}")


def commit_transaction(transaction_root: Path, data_root: Path) -> None:
    transaction_path = transaction_root / "transaction.yaml"
    transaction = require_mapping(
        load_yaml(transaction_path).get("post_publication_transaction"), "transaction"
    )
    if transaction.get("state") == "COMMITTED":
        verify_committed(transaction_root, data_root)
        return
    if transaction.get("state") != "PREPARED":
        raise RevisionError(f"transaction is not committable: {transaction.get('state')}")
    proposal = verify_prepared(transaction_root, data_root)
    transaction_id = proposal["transaction_id"]
    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    affected = sorted(
        (value for value in proposal["changes"] if value["action"] != "retain"),
        key=lambda value: value["stds_id"],
    )
    lock_root = stomics_root / "staging/round3_case_construction/locks"
    transaction_lock_root = transaction_root.parent / "locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    transaction_lock_root.mkdir(parents=True, exist_ok=True)
    locks = [transaction_lock_root / f"{transaction_id}.lock"] + [
        lock_root / f"stomicsdb_{value['stds_id']}.lock" for value in affected
    ]
    acquired: list[Path] = []
    moved: list[dict[str, Any]] = []
    owner = {"transaction_id": transaction_id, "operation": REVISION_KIND}
    try:
        for lock in locks:
            acquire_lock(lock, owner)
            acquired.append(lock)
        proposal = verify_prepared(transaction_root, data_root)
        backups = transaction_root / "backups"
        backups.mkdir()
        for change in affected:
            current = resolve_data_path(change["case_directory"], data_root)
            backup = resolve_data_path(change["backup_directory"], data_root)
            if backup.exists():
                raise RevisionError(f"backup already exists: {backup}")
            os.replace(current, backup)
            fsync_directory(current.parent)
            moved.append(change)
            if change["action"] == "replace":
                proposed = transaction_root / "proposed" / f"stomicsdb_{change['stds_id']}"
                os.replace(proposed, current)
                fsync_directory(current.parent)

        identities = excluded_identities(proposal)
        cleanup_targets: list[dict[str, Any]] = []
        cases: list[dict[str, Any]] = []
        counts = {"accepted": 0, "no_candidate": 0}
        for change in proposal["changes"]:
            stds_id = change["stds_id"]
            status = change["proposed_status"]
            verify_current_case(stds_id, status, stomics_root, data_root, identities)
            counts[status] += 1
            details = {
                key: deepcopy(change[key])
                for key in (
                    "excluded_inventory_resource_ids",
                    "excluded_case_auxiliary_resource_ids",
                    "direct_removed_result_ids",
                    "downstream_removed_result_ids",
                    "removed_result_ids",
                    "retained_result_ids",
                    "retained_candidate_ids",
                    "resource_corrections",
                    "auxiliary_detachments",
                    "source_anchor_corrections",
                    "result_scope_exclusions",
                )
            }
            cases.append(
                {
                    "stds_id": stds_id,
                    "authoritative_status": status,
                    "status_source": (
                        "committed_post_publication_revision"
                        if change["action"] != "retain"
                        else "retained_prior_revision"
                    ),
                    "prior_terminal": deepcopy(change["prior_terminal"]),
                    "prior_review_rounds": change["prior_review_rounds"],
                    "revision_validation": (
                        "deterministic_semantic_scope_pruning"
                        if change["action"] != "retain"
                        else None
                    ),
                    "output_paths": output_paths(
                        stds_id, status, stomics_root, data_root
                    ),
                    **details,
                }
            )
            if change["action"] != "retain":
                backup = resolve_data_path(change["backup_directory"], data_root)
                records = published_file_records(backup, data_root)
                if records != expected_backup_records(change):
                    raise RevisionError(f"backup bytes changed: {stds_id}")
                cleanup_targets.append(
                    {
                        "stds_id": stds_id,
                        "superseded_case_directory": change["case_directory"],
                        "preserved_backup_directory": change["backup_directory"],
                        "files": records,
                        "canonical_namespace_status": (
                            "replaced"
                            if status == "accepted"
                            else "removed_no_candidate"
                        ),
                        "backup_disposition": "retained_for_recovery",
                        "cleanup_status": "complete",
                    }
                )

        proposal_path = transaction_root / "proposal.yaml"
        proposal_binding = {
            "path": data_relative(proposal_path, data_root),
            "sha256": sha256_path(proposal_path),
        }
        revision_receipt_path = transaction_root / "revision_receipt.yaml"
        cleanup_receipt_path = transaction_root / "cleanup_receipt.yaml"
        atomic_write_yaml(
            revision_receipt_path,
            {
                "round3_case_revision_receipt": {
                    "transaction_id": transaction_id,
                    "committed_utc": utc_now(),
                    "proposal": proposal_binding,
                    "prior_revision_receipt": deepcopy(
                        proposal["input_preconditions"]["current_revision_receipt"]
                    ),
                    "scope_stds_ids": proposal["scope_stds_ids"],
                    "excluded_inventory_resource_ids": [
                        value["inventory_id"]
                        for value in proposal["decision"]["excluded_resources"]
                    ],
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
                    "canonical_namespace_cleanup_completed": True,
                    "transaction_backups_retained": True,
                }
            },
        )
        atomic_write_yaml(
            transaction_path,
            {
                "post_publication_transaction": {
                    "transaction_id": transaction_id,
                    "state": "COMMITTED",
                    "proposal": proposal_binding,
                    "revision_receipt": {
                        "path": data_relative(revision_receipt_path, data_root),
                        "sha256": sha256_path(revision_receipt_path),
                    },
                    "cleanup_receipt": {
                        "path": data_relative(cleanup_receipt_path, data_root),
                        "sha256": sha256_path(cleanup_receipt_path),
                    },
                    "committed_stds_ids": [value["stds_id"] for value in affected],
                    "error": None,
                }
            },
        )
        verify_committed(transaction_root, data_root)
    except Exception as error:
        rollback_error: Exception | None = None
        try:
            for change in reversed(moved):
                current = resolve_data_path(change["case_directory"], data_root)
                backup = resolve_data_path(change["backup_directory"], data_root)
                if change["action"] == "replace" and current.exists():
                    proposed = transaction_root / "proposed" / f"stomicsdb_{change['stds_id']}"
                    os.replace(current, proposed)
                if backup.exists():
                    os.replace(backup, current)
            for name in ("revision_receipt.yaml", "cleanup_receipt.yaml"):
                (transaction_root / name).unlink(missing_ok=True)
            atomic_write_yaml(
                transaction_path,
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
        if rollback_error is not None:
            raise RevisionError(
                f"commit failed ({error}); rollback failed ({rollback_error})"
            ) from error
        raise
    finally:
        for lock in reversed(acquired):
            release_lock(lock)


def verify_committed(transaction_root: Path, data_root: Path) -> None:
    transaction = require_mapping(
        load_yaml(transaction_root / "transaction.yaml").get(
            "post_publication_transaction"
        ),
        "transaction",
    )
    if transaction.get("state") != "COMMITTED":
        raise RevisionError(f"transaction is not committed: {transaction.get('state')}")
    documents: dict[str, dict[str, Any]] = {}
    wrappers = {
        "proposal": "post_publication_transaction_proposal",
        "revision_receipt": "round3_case_revision_receipt",
        "cleanup_receipt": "post_publication_cleanup_receipt",
    }
    for name, wrapper in wrappers.items():
        record = transaction[name]
        path = resolve_data_path(record["path"], data_root)
        if not path.is_file() or sha256_path(path) != record["sha256"]:
            raise RevisionError(f"transaction binding mismatch: {name}")
        documents[name] = require_mapping(load_yaml(path).get(wrapper), name)
    proposal = documents["proposal"]
    receipt = documents["revision_receipt"]
    cleanup = documents["cleanup_receipt"]
    if proposal.get("revision_kind") != REVISION_KIND:
        raise RevisionError("committed proposal has an unexpected revision kind")
    if receipt.get("proposal") != transaction["proposal"] or cleanup.get("proposal") != transaction["proposal"]:
        raise RevisionError("committed receipts do not bind the proposal")
    for record in proposal["input_preconditions"].values():
        path = resolve_data_path(record["path"], data_root)
        if not path.is_file() or sha256_path(path) != record["sha256"]:
            raise RevisionError(f"committed input binding mismatch: {path}")
    if receipt.get("prior_revision_receipt") != proposal["input_preconditions"]["current_revision_receipt"]:
        raise RevisionError("revision receipt does not carry the prior receipt binding")
    if receipt.get("excluded_inventory_resource_ids") != [
        value["inventory_id"] for value in proposal["decision"]["excluded_resources"]
    ]:
        raise RevisionError("revision receipt excluded-resource list differs from proposal")

    stomics_root = data_root.joinpath(*STOMICS_RELATIVE.parts)
    identities = excluded_identities(proposal)
    cases = require_list(receipt.get("cases"), "revision receipt cases")
    if len(cases) != 16 or [value["stds_id"] for value in cases] != proposal["scope_stds_ids"]:
        raise RevisionError("committed receipt does not cover the ordered 16-case scope")
    changes_by_id = {value["stds_id"]: value for value in proposal["changes"]}
    counts = {"accepted": 0, "no_candidate": 0}
    for record in cases:
        stds_id = record["stds_id"]
        status = record["authoritative_status"]
        if status not in counts:
            raise RevisionError(f"invalid committed status: {stds_id}:{status}")
        counts[status] += 1
        if record.get("output_paths") != output_paths(stds_id, status, stomics_root, data_root):
            raise RevisionError(f"committed output paths mismatch: {stds_id}")
        if record.get("prior_review_rounds") != record.get("prior_terminal", {}).get(
            "review_rounds"
        ):
            raise RevisionError(f"committed terminal/review binding mismatch: {stds_id}")
        verify_current_case(stds_id, status, stomics_root, data_root, identities)
        change = changes_by_id[stds_id]
        for key in (
            "resource_corrections",
            "auxiliary_detachments",
            "source_anchor_corrections",
            "result_scope_exclusions",
        ):
            if record.get(key) != change.get(key):
                raise RevisionError(f"receipt correction binding mismatch: {stds_id}:{key}")
        directory = stomics_root / "cases" / f"stomicsdb_{stds_id}"
        if change["action"] == "replace":
            expected = [
                {
                    "path": value["target_path"],
                    "sha256": value["sha256"],
                    "size_bytes": value["size_bytes"],
                }
                for value in change["proposed_files"]
            ]
            if published_manifest_file_records(directory, data_root) != expected:
                raise RevisionError(f"committed case differs from proposal: {stds_id}")
        elif change["action"] == "retain" and status == "accepted":
            if published_manifest_file_records(directory, data_root) != change[
                "input_files"
            ][: len(CASE_FILES)]:
                raise RevisionError(f"retained case bytes changed: {stds_id}")
    if counts != receipt.get("counts"):
        raise RevisionError("committed receipt counts mismatch")
    if cleanup.get("retained_manifest_references_to_excluded_resources") != []:
        raise RevisionError("cleanup receipt reports residual excluded resources")
    if cleanup.get("canonical_namespace_cleanup_completed") is not True:
        raise RevisionError("cleanup receipt is incomplete")
    targets = require_list(cleanup.get("targets"), "cleanup targets")
    affected_ids = {
        value["stds_id"] for value in proposal["changes"] if value["action"] != "retain"
    }
    if {value["stds_id"] for value in targets} != affected_ids:
        raise RevisionError("cleanup targets differ from affected cases")
    for target in targets:
        backup = resolve_data_path(target["preserved_backup_directory"], data_root)
        if published_file_records(backup, data_root) != target["files"]:
            raise RevisionError(f"backup binding mismatch: {target['stds_id']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--current-revision-receipt", type=Path, required=True)
    parser.add_argument("--exclusion-evidence", type=Path, required=True)
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
                "post_publication_transaction"
            ),
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
