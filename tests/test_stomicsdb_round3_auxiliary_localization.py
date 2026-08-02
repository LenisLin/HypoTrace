from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "stomicsdb_round3_auxiliary_localization.py"
SPEC = importlib.util.spec_from_file_location("stomicsdb_round3_auxiliary_localization", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
localization = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = localization
SPEC.loader.exec_module(localization)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def write_inventory(
    data_root: Path,
    run_name: str,
    *,
    resources: list[dict],
    artifacts: list[dict],
    pending: list[dict] | None = None,
    skipped: bool = False,
    event_size_delta: int = 0,
) -> Path:
    run_root = (
        data_root
        / "raw_data/public_database/stomicsdb/staging/round3_auxiliary_downloads/runs"
        / run_name
    )
    run_root.mkdir(parents=True)
    inventory_path = run_root / "inventory.json"
    inventory_path.write_text(
        json.dumps(
            {
                "run_id": run_name,
                "scope_stds_ids": ["STDS0000001"],
                "resources": resources,
                "artifacts": artifacts,
                "pending": pending or [],
            }
        ),
        encoding="utf-8",
    )
    events: list[dict] = []
    for index, artifact in enumerate(artifacts, 1):
        path = data_root / artifact["target_path"]
        event = {
            "event": "download_skipped" if skipped else "download_completed",
            "row_number": index,
            "source_url": artifact["source_url"],
            "target_path": artifact["target_path"],
            "size_bytes": path.stat().st_size + event_size_delta,
        }
        if skipped:
            event["reason"] = "existing_final_file"
        else:
            event["sha256"] = sha256(path)
        events.append(event)
    events.append(
        {
            "event": "auxiliary_run_completed",
            "resource_count": len(resources),
            "artifact_count": len(artifacts),
            "completed_artifact_count": len(artifacts),
            "download_failure_count": 0,
            "pending_resource_count": len(pending or []),
            "inventory_path": str(inventory_path),
        }
    )
    (run_root / "run.jsonl").write_text(
        "".join(json.dumps(value) + "\n" for value in events), encoding="utf-8"
    )
    return inventory_path


def test_resource_mapping_rejects_ambiguous_non_pending_identity() -> None:
    resource = {"resource_name": "same", "source_url": "https://example.org/same"}
    inventories = [
        {
            "resources": {"R3AUX001": {"inventory_id": "R3AUX001", **resource, "artifact_ids": []}},
            "pending_ids": set(),
            "artifacts": {},
        },
        {
            "resources": {"R3AUX002": {"inventory_id": "R3AUX002", **resource, "artifact_ids": []}},
            "pending_ids": set(),
            "artifacts": {},
        },
    ]

    with pytest.raises(localization.LocalizationError, match="ambiguous"):
        localization.build_resource_index(inventories)


def test_coverage_decisions_require_exact_packages_and_nonempty_subset(tmp_path: Path) -> None:
    required = {
        "R3AUX001": {
            "resource": {"artifact_ids": ["R3FILE_001", "R3FILE_002"]}
        }
    }
    assert localization.coverage_selections(None, required) == {
        "R3AUX001": {
            "selected_artifact_ids": ["R3FILE_001", "R3FILE_002"],
            "evidence": localization.COVERAGE_EVIDENCE,
        }
    }
    decision_path = tmp_path / "coverage.yaml"
    write_yaml(
        decision_path,
        {
            "resources": [
                {
                    "package_id": "R3AUX001",
                    "selected_artifact_ids": ["R3FILE_002"],
                    "evidence": "Archive member selected by the operator.",
                }
            ]
        },
    )
    assert localization.coverage_selections(decision_path, required) == {
        "R3AUX001": {
            "selected_artifact_ids": ["R3FILE_002"],
            "evidence": "Archive member selected by the operator.",
        }
    }

    write_yaml(
        decision_path,
        {
            "resources": [
                {
                    "package_id": "R3AUX001",
                    "selected_artifact_ids": ["R3FILE_missing"],
                    "evidence": "invalid",
                }
            ]
        },
    )
    with pytest.raises(localization.LocalizationError, match="unresolved artifacts"):
        localization.coverage_selections(decision_path, required)

    assert localization.canonical_artifact_filenames(
        [
            {"artifact_id": "R3FILE_001", "source_path": "one/shared.tsv"},
            {"artifact_id": "R3FILE_002", "source_path": "two/shared.tsv"},
        ]
    ) == {
        "R3FILE_001": "R3FILE_001__shared.tsv",
        "R3FILE_002": "R3FILE_002__shared.tsv",
    }


def test_lock_owner_write_failure_does_not_leak_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / "publish.lock"

    def fail_owner_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("forced owner write failure")

    monkeypatch.setattr(localization, "atomic_write_yaml", fail_owner_write)
    with pytest.raises(OSError, match="forced owner write failure"):
        localization.acquire_lock(lock_path, {"transaction_id": "tx"})
    assert not lock_path.exists()


def test_inventory_accepts_existing_file_skip_and_checks_event_size(tmp_path: Path) -> None:
    artifact_path = tmp_path / "downloads/object/artifacts/resource.tsv"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"a\tb\n1\t2\n")
    artifact = {
        "artifact_id": "R3FILE_001",
        "source_url": "https://example.org/resource.tsv",
        "target_path": relative(artifact_path, tmp_path),
    }
    resource = {
        "inventory_id": "R3AUX001",
        "resource_name": "resource",
        "expected_content": "table",
        "source_url": "https://example.org/resource",
        "access_classification": "anonymous_direct",
        "artifact_ids": ["R3FILE_001"],
    }
    valid = write_inventory(
        tmp_path,
        "valid",
        resources=[resource],
        artifacts=[artifact],
        skipped=True,
    )
    binding = localization.validate_inventory_run(valid, tmp_path)
    assert binding["artifacts"]["R3FILE_001"]["sha256"] == sha256(artifact_path)

    contradictory = write_inventory(
        tmp_path,
        "contradictory",
        resources=[resource],
        artifacts=[artifact],
        skipped=False,
    )
    contradictory_log = contradictory.with_name("run.jsonl")
    contradictory_events = [
        json.loads(value)
        for value in contradictory_log.read_text(encoding="utf-8").splitlines()
    ]
    contradictory_events.insert(
        -1, {"event": "download_failed", "target_path": artifact["target_path"]}
    )
    contradictory_log.write_text(
        "".join(json.dumps(value) + "\n" for value in contradictory_events),
        encoding="utf-8",
    )
    with pytest.raises(localization.LocalizationError, match="incomplete acquisition"):
        localization.validate_inventory_run(contradictory, tmp_path)

    invalid = write_inventory(
        tmp_path,
        "invalid",
        resources=[resource],
        artifacts=[artifact],
        skipped=True,
        event_size_delta=1,
    )
    with pytest.raises(localization.LocalizationError, match="size mismatch"):
        localization.validate_inventory_run(invalid, tmp_path)


def test_localized_axx_requires_complete_coverage_and_verified_artifacts(tmp_path: Path) -> None:
    artifact_path = (
        tmp_path
        / "raw_data/public_database/stomicsdb/auxiliary_resources/R3AUX001/generations/tx__R3AUX001/artifacts/table.tsv"
    )
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"gene\tvalue\nA\t1\n")
    artifact = {
        "artifact_id": "R3FILE_001",
        "path": relative(artifact_path, tmp_path),
        "source_url": "https://example.org/table.tsv",
        "format": "tsv",
        "role": "required_resource_artifact",
        "size_bytes": artifact_path.stat().st_size,
        "sha256": sha256(artifact_path),
    }
    acquisition_root = tmp_path / "acquisition"
    acquisition_root.mkdir()
    acquisition_inventory = acquisition_root / "inventory.json"
    acquisition_inventory.write_text(
        json.dumps(
            {
                "run_id": "run1",
                "resources": [
                    {
                        "inventory_id": "R3AUX001",
                        "resource_name": "resource",
                        "source_url": "https://example.org/resource",
                        "expected_content": "required table",
                        "artifact_ids": ["R3FILE_001"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    acquisition_run = acquisition_root / "run.jsonl"
    acquisition_run.write_text("{}\n", encoding="utf-8")
    manifest_path = artifact_path.parents[1] / "localization.yaml"
    manifest = {
        "auxiliary_localization_manifest": {
            "package_id": "R3AUX001",
            "generation_id": "tx__R3AUX001",
            "localization_status": "LOCALIZED",
            "resource_identity": {
                "resource_name": "resource",
                "source_url": "https://example.org/resource",
            },
            "expected_content": "required table",
            "acquisition_bindings": {
                "inventories": [
                    {
                        "path": relative(acquisition_inventory, tmp_path),
                        "sha256": sha256(acquisition_inventory),
                        "inventory_resource_id": "R3AUX001",
                    }
                ],
                "successful_runs": [
                    {
                        "run_id": "run1",
                        "events_path": relative(acquisition_run, tmp_path),
                        "sha256": sha256(acquisition_run),
                    }
                ],
            },
            "artifacts": [artifact],
            "validation": {
                "artifact_count": 1,
                "acquisition_bindings_verified": True,
                "all_artifacts_regular_files": True,
                "all_artifacts_readable": True,
                "all_artifact_sizes_verified": True,
                "all_artifact_sha256_verified": True,
                "all_artifact_paths_canonical": True,
            },
        }
    }
    write_yaml(manifest_path, manifest)
    bound_artifact = {
        key: artifact[key]
        for key in ("artifact_id", "path", "source_url", "size_bytes", "sha256")
    }
    objects = {
        "data": {
            "auxiliary_resources": [
                {
                    "resource_id": "A01",
                    "resource_name": "resource",
                    "expected_content": "required table",
                    "source_url": "https://example.org/resource",
                    "access_classification": "anonymous_direct",
                    "local_availability": "localized",
                    "localization_binding": {
                        "package_manifest": {
                            "package_id": "R3AUX001",
                            "path": relative(manifest_path, tmp_path),
                            "sha256": sha256(manifest_path),
                            "generation_id": "tx__R3AUX001",
                        },
                        "artifacts": [bound_artifact],
                        "expected_content_coverage": {
                            "status": "complete",
                            "items": [
                                {
                                    "requirement": "required table",
                                    "artifact_ids": ["R3FILE_001"],
                                    "evidence": localization.COVERAGE_EVIDENCE,
                                }
                            ],
                            "uncovered_requirements": [],
                        },
                    },
                }
            ]
        }
    }
    localization.validate_localized_auxiliary_resources(
        objects, {"R3AUX001": manifest}, tmp_path
    )

    objects["data"]["auxiliary_resources"][0]["localization_binding"][
        "expected_content_coverage"
    ]["status"] = "partial"
    with pytest.raises(localization.LocalizationError, match="incomplete expected-content coverage"):
        localization.validate_localized_auxiliary_resources(
            objects, {"R3AUX001": manifest}, tmp_path
        )


def build_external_case(data_root: Path) -> Path:
    stomics = data_root / "raw_data/public_database/stomicsdb"
    external = stomics / "fixture"
    external.mkdir(parents=True)
    article = external / "article.pdf"
    article.write_bytes(b"article")
    article_manifest = external / "article_manifest.yaml"
    write_yaml(article_manifest, {"generation_id": "article_gen"})
    dataset_manifest = external / "dataset_manifest.yaml"
    write_yaml(dataset_manifest, {"generation_id": "dataset_gen"})
    dataset_source = external / "source_manifest.yaml"
    write_yaml(dataset_source, {"generation_id": "dataset_gen"})
    samples = external / "samples.jsonl"
    samples.write_text('{"sample_id":"S1"}\n', encoding="utf-8")
    files = external / "files.jsonl"
    files.write_text("{}\n", encoding="utf-8")
    component = external / "matrix.tsv"
    component.write_bytes(b"gene\tS1\nA\t1\n")
    data_localization = external / "localization.yaml"
    write_yaml(
        data_localization,
        {
            "generation_id": "data_gen",
            "artifacts": [
                {"path": relative(component, data_root), "sha256": sha256(component)}
            ],
        },
    )

    case_directory = stomics / "cases/stomicsdb_STDS0000001"
    source = {
        "stds_id": "STDS0000001",
        "article_manifest_path": relative(article_manifest, data_root),
        "article_manifest_sha256": sha256(article_manifest),
        "article_generation_id": "article_gen",
        "article_path": relative(article, data_root),
        "article_sha256": sha256(article),
        "results": [{"result_id": "R01"}],
    }
    data = {
        "stds_id": "STDS0000001",
        "dataset_binding": {
            "dataset_manifest": {
                "path": relative(dataset_manifest, data_root),
                "sha256": sha256(dataset_manifest),
                "generation_id": "dataset_gen",
            },
            "source_manifest": {
                "path": relative(dataset_source, data_root),
                "sha256": sha256(dataset_source),
                "generation_id": "dataset_gen",
            },
            "samples": {"path": relative(samples, data_root), "sha256": sha256(samples)},
            "files": {"path": relative(files, data_root), "sha256": sha256(files)},
        },
        "data_objects": [
            {
                "data_id": "D01",
                "localization_bindings": [
                    {
                        "path": relative(data_localization, data_root),
                        "sha256": sha256(data_localization),
                        "generation_id": "data_gen",
                    }
                ],
                "expression_matrix": {
                    "files": [
                        {
                            "path": relative(component, data_root),
                            "sha256": sha256(component),
                        }
                    ]
                },
            }
        ],
        "auxiliary_resources": [
            {
                "resource_id": "A01",
                "resource_name": "reference table",
                "expected_content": "gene reference table",
                "source_url": "https://example.org/reference",
                "access_classification": "anonymous_direct",
                "local_availability": "absent",
            }
        ],
        "result_data_links": [
            {
                "result_id": "R01",
                "data_inputs": [
                    {
                        "data_id": "D01",
                        "input_role": "primary_spatial",
                        "required_components": [
                            {
                                "component": "expression_matrix",
                                "paths": [relative(component, data_root)],
                            }
                        ],
                    }
                ],
                "auxiliary_resource_ids": ["A01"],
            }
        ],
    }
    case = {
        "stds_id": "STDS0000001",
        "source_manifest_path": "source_manifest.yaml",
        "case_data_manifest_path": "data/case_data_manifest.yaml",
        "case_candidates": [
            {
                "candidate_id": "C01",
                "result_ids": ["R01"],
                "result_order": ["R01"],
                "spatial_data_ids": ["D01"],
                "auxiliary_resource_ids": ["A01"],
                "result_connections": [],
            }
        ],
    }
    write_yaml(case_directory / "source_manifest.yaml", {"source_manifest": source})
    write_yaml(case_directory / "data/case_data_manifest.yaml", {"case_data_manifest": data})
    write_yaml(case_directory / "case_manifest.yaml", {"case_manifest": case})
    return case_directory


def test_prepare_rollback_then_commit_verify_small_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_directory = build_external_case(tmp_path)
    original_source = (case_directory / "source_manifest.yaml").read_bytes()
    original_case = (case_directory / "case_manifest.yaml").read_bytes()
    download = (
        tmp_path
        / "raw_data/public_database/stomicsdb/staging/round3_auxiliary_downloads/objects/R3FILE_001/artifacts/reference.tsv"
    )
    download.parent.mkdir(parents=True)
    download.write_bytes(b"gene\tlabel\nA\talpha\n")
    artifact = {
        "artifact_id": "R3FILE_001",
        "source_url": "https://example.org/reference.tsv",
        "target_path": relative(download, tmp_path),
    }
    resource = {
        "inventory_id": "R3AUX001",
        "resource_name": "reference table",
        "expected_content": "gene reference table",
        "source_url": "https://example.org/reference",
        "access_classification": "anonymous_direct",
        "artifact_ids": ["R3FILE_001"],
    }
    source_inventory = write_inventory(
        tmp_path, "source", resources=[resource], artifacts=[artifact], skipped=True
    )
    retained_inventory = write_inventory(
        tmp_path, "retained", resources=[], artifacts=[], skipped=False
    )
    receipt_path = (
        tmp_path
        / "raw_data/public_database/stomicsdb/staging/post_publication_transactions/current/revision_receipt.yaml"
    )
    write_yaml(
        receipt_path,
        {
            "round3_case_revision_receipt": {
                "transaction_id": "current",
                "cases": [
                    {
                        "stds_id": "STDS0000001",
                        "authoritative_status": "accepted",
                        "output_paths": {
                            "source_manifest": relative(
                                case_directory / "source_manifest.yaml", tmp_path
                            ),
                            "case_data_manifest": relative(
                                case_directory / "data/case_data_manifest.yaml", tmp_path
                            ),
                            "case_manifest": relative(
                                case_directory / "case_manifest.yaml", tmp_path
                            ),
                        },
                    }
                ],
                "counts": {"accepted": 1, "no_candidate": 0},
            }
        },
    )
    write_yaml(
        receipt_path.with_name("transaction.yaml"),
        {
            "post_publication_transaction": {
                "transaction_id": "current",
                "state": "COMMITTED",
                "revision_receipt": {
                    "path": relative(receipt_path, tmp_path),
                    "sha256": sha256(receipt_path),
                },
            }
        },
    )
    coverage_path = receipt_path.parent / "coverage_decisions.yaml"
    coverage_evidence = "Operator selected the verified tabular artifact."
    write_yaml(
        coverage_path,
        {
            "resources": [
                {
                    "package_id": "R3AUX001",
                    "selected_artifact_ids": ["R3FILE_001"],
                    "evidence": coverage_evidence,
                }
            ]
        },
    )
    args = argparse.Namespace(
        data_root=tmp_path,
        source_inventory=source_inventory,
        retained_inventory=retained_inventory,
        current_revision_receipt=receipt_path,
        coverage_decisions=coverage_path,
        transaction_id="localize_test",
        commit=False,
    )

    transaction_root = localization.prepare_transaction(args)
    assert not (tmp_path / "raw_data/public_database/stomicsdb/auxiliary_resources").exists()
    assert (case_directory / "data/case_data_manifest.yaml").read_text().find(
        "local_availability: absent"
    ) != -1

    validate_published = localization.validate_published

    def force_final_validation_failure(*_args: object, **_kwargs: object) -> None:
        raise localization.LocalizationError("forced final validation failure")

    monkeypatch.setattr(
        localization, "validate_published", force_final_validation_failure
    )
    with pytest.raises(localization.LocalizationError, match="forced final validation"):
        localization.commit_transaction(transaction_root, tmp_path)
    rolled_back = yaml.safe_load((transaction_root / "transaction.yaml").read_text())[
        "round3_auxiliary_localization_transaction"
    ]
    assert rolled_back["state"] == "ROLLED_BACK"
    assert (case_directory / "source_manifest.yaml").read_bytes() == original_source
    assert (case_directory / "case_manifest.yaml").read_bytes() == original_case
    assert not (tmp_path / "raw_data/public_database/stomicsdb/auxiliary_resources").exists()
    assert (transaction_root / "proposed_auxiliary_resources").is_dir()
    assert (transaction_root / "proposed_cases/stomicsdb_STDS0000001").is_dir()
    assert not (
        transaction_root.parent / "locks/round3_auxiliary_publish.lock"
    ).exists()

    monkeypatch.setattr(localization, "validate_published", validate_published)
    args.transaction_id = "localize_test_commit"
    transaction_root = localization.prepare_transaction(args)
    localization.commit_transaction(transaction_root, tmp_path)
    localization.verify_committed(transaction_root, tmp_path)

    assert (case_directory / "source_manifest.yaml").read_bytes() == original_source
    assert (case_directory / "case_manifest.yaml").read_bytes() == original_case
    data = yaml.safe_load((case_directory / "data/case_data_manifest.yaml").read_text())[
        "case_data_manifest"
    ]
    auxiliary = data["auxiliary_resources"][0]
    assert auxiliary["local_availability"] == "localized"
    assert auxiliary["localization_binding"]["expected_content_coverage"]["status"] == "complete"
    assert auxiliary["localization_binding"]["expected_content_coverage"]["items"][0][
        "evidence"
    ] == coverage_evidence
    manifest_path = (
        tmp_path
        / auxiliary["localization_binding"]["package_manifest"]["path"]
    )
    assert manifest_path.is_file()
    assert not (transaction_root / "proposed_auxiliary_resources").exists()
    assert not (transaction_root / "proposed_cases").exists()
