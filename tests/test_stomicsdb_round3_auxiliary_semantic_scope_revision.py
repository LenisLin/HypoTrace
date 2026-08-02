from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "stomicsdb_round3_auxiliary_semantic_scope_revision.py"
SPEC = importlib.util.spec_from_file_location(
    "stomicsdb_round3_auxiliary_semantic_scope_revision", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
revision = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = revision
SPEC.loader.exec_module(revision)


def case_objects() -> dict:
    return {
        "source": {
            "stds_id": "STDS0000001",
            "results": [
                {
                    "result_id": value,
                    "source_anchors": [{"type": "text", "locator": f"anchor {value}"}],
                    "scientific_question": f"question {value}",
                    "conclusion": f"conclusion {value}",
                    "analysis_steps": [{"input": "i", "method": "m", "output": "o"}],
                }
                for value in ("R01", "R02", "R03", "R04")
            ],
        },
        "data": {
            "stds_id": "STDS0000001",
            "dataset_binding": {},
            "data_objects": [{"data_id": "D01"}],
            "auxiliary_resources": [
                {
                    "resource_id": "A01",
                    "resource_name": "resource one",
                    "expected_content": "one old expected",
                    "source_url": "https://example.org/one",
                    "access_classification": "anonymous_direct",
                    "local_availability": "absent",
                    "access_notes": "one old notes",
                },
                {
                    "resource_id": "A02",
                    "resource_name": "resource two",
                    "expected_content": "two old expected",
                    "source_url": "https://example.org/two",
                    "access_classification": "anonymous_direct",
                    "local_availability": "absent",
                    "access_notes": "two old notes",
                },
            ],
            "result_data_links": [
                {
                    "result_id": "R01",
                    "data_inputs": [{"data_id": "D01", "input_role": "primary_spatial"}],
                    "auxiliary_resource_ids": ["A01"],
                },
                {
                    "result_id": "R02",
                    "data_inputs": [{"data_id": "D01", "input_role": "primary_spatial"}],
                    "auxiliary_resource_ids": ["A01"],
                },
                {
                    "result_id": "R03",
                    "data_inputs": [{"data_id": "D01", "input_role": "primary_spatial"}],
                    "auxiliary_resource_ids": ["A02"],
                },
                {
                    "result_id": "R04",
                    "data_inputs": [{"data_id": "D01", "input_role": "primary_spatial"}],
                    "auxiliary_resource_ids": ["A02"],
                },
            ],
        },
        "case": {
            "stds_id": "STDS0000001",
            "source_manifest_path": "source_manifest.yaml",
            "case_data_manifest_path": "data/case_data_manifest.yaml",
            "case_candidates": [
                {
                    "candidate_id": "C01",
                    "result_ids": ["R01", "R02"],
                    "result_order": ["R01", "R02"],
                    "spatial_data_ids": ["D01"],
                    "auxiliary_resource_ids": ["A01"],
                    "result_connections": [
                        {"from_result_id": "R01", "to_result_id": "R02"}
                    ],
                },
                {
                    "candidate_id": "C02",
                    "result_ids": ["R03", "R04"],
                    "result_order": ["R03", "R04"],
                    "spatial_data_ids": ["D01"],
                    "auxiliary_resource_ids": ["A02"],
                    "result_connections": [
                        {"from_result_id": "R03", "to_result_id": "R04"}
                    ],
                },
            ],
        },
    }


def inventory(scope: list[str]) -> dict:
    return {
        "scope_stds_ids": scope,
        "resources": [
            {
                "inventory_id": "INV01",
                "resource_name": "resource one",
                "source_url": "https://example.org/one",
                "expected_content": "one",
                "result_ids_by_case": {"STDS0000001": ["R01", "R02"]},
            },
            {
                "inventory_id": "INV02",
                "resource_name": "resource two",
                "source_url": "https://example.org/two",
                "expected_content": "two",
                "result_ids_by_case": {"STDS0000001": ["R03", "R04"]},
            },
        ],
    }


def exclusion(resource_ids: list[str]) -> list[dict]:
    return [
        {
            "inventory_id": value,
            "verdict": "incomplete",
            "missing_content": "required semantic content is absent",
            "evidence_paths": [f"audit/{value}.yaml"],
            "reconstruction_required": False,
        }
        for value in resource_ids
    ]


def test_identity_mapping_resolves_current_axx_and_direct_results() -> None:
    resolved, per_case = revision.resolve_excluded_resource_mappings(
        inventory(["STDS0000001"]), exclusion(["INV01"]), {"STDS0000001": case_objects()}
    )

    assert resolved[0]["current_case_mappings"] == [
        {
            "stds_id": "STDS0000001",
            "case_auxiliary_resource_ids": ["A01"],
            "direct_result_ids": ["R01", "R02"],
        }
    ]
    assert per_case["STDS0000001"]["inventory_ids"] == {"INV01"}
    assert per_case["STDS0000001"]["auxiliary_ids"] == {"A01"}


def test_transitive_pruning_preserves_the_other_candidate() -> None:
    revised, details = revision.revise_case_for_exclusions(case_objects(), {"R01"})

    assert revised is not None
    assert details["removed_result_ids"] == ["R01", "R02"]
    assert details["downstream_removed_result_ids"] == ["R02"]
    assert [value["candidate_id"] for value in revised["case"]["case_candidates"]] == [
        "C02"
    ]


def test_pruning_can_transition_to_no_candidate() -> None:
    revised, details = revision.revise_case_for_exclusions(
        case_objects(), {"R01", "R03"}
    )

    assert revised is None
    assert details["removed_result_ids"] == ["R01", "R02", "R03", "R04"]


def test_assigned_spatial_scope_exclusion_resolves_and_prunes() -> None:
    evidence = [
        {
            "stds_id": "STDS0000001",
            "result_ids": ["R03"],
            "criterion": "uses_assigned_spatial_data",
            "required_value": "yes",
            "observed_value": "no",
            "rationale": "The article-fixed route uses a different spatial sample.",
            "evidence_paths": ["audit/result_scope.yaml"],
        }
    ]
    per_case, details = revision.resolve_result_scope_exclusions(
        evidence, {"STDS0000001": case_objects()}
    )

    assert per_case == {"STDS0000001": {"R03"}}
    assert details == {"STDS0000001": evidence}
    revised, pruning = revision.revise_case_for_exclusions(
        case_objects(), per_case["STDS0000001"]
    )
    assert revised is not None
    assert pruning["removed_result_ids"] == ["R03", "R04"]
    assert [
        value["candidate_id"] for value in revised["case"]["case_candidates"]
    ] == ["C01"]


def test_published_case_loader_accepts_only_complete_dual_chain_subtrees(
    tmp_path: Path,
) -> None:
    case_directory = tmp_path / "stomicsdb_STDS0000001"
    revision.write_case_tree(case_directory, revision.serialize_case(case_objects()))
    chain = case_directory / "dual_chain/chain_sha256_0123456789abcdef"
    chain.mkdir(parents=True)
    for name in sorted(revision.CHAIN_EXTRACTION_FILES):
        (chain / name).write_text("synthetic\n", encoding="utf-8")

    assert revision.load_published_case(case_directory) == case_objects()

    (chain / "unexpected.txt").write_text("invalid\n", encoding="utf-8")
    with pytest.raises(revision.RevisionError, match="unexpected file"):
        revision.load_published_case(case_directory)


def test_allowlisted_field_detachment_and_anchor_corrections() -> None:
    objects = case_objects()
    old_anchor = objects["source"]["results"][3]["source_anchors"]
    new_anchor = [
        {"type": "figure", "locator": "Extended Data Fig. 5"},
        {"type": "text", "locator": "anchor R04"},
    ]
    evidence = {
        "resources": [],
        "resource_corrections": [
            {
                "inventory_id": "INV02",
                "stds_id": "STDS0000001",
                "resource_id": "A02",
                "prior_values": {
                    "expected_content": "two old expected",
                    "access_notes": "two old notes",
                },
                "new_values": {
                    "expected_content": "two narrowed expected",
                    "access_notes": "two corrected notes",
                },
                "evidence_paths": ["audit/two.yaml"],
            }
        ],
        "auxiliary_detachments": [
            {
                "inventory_id": "INV01",
                "stds_id": "STDS0000001",
                "resource_id": "A01",
                "result_ids": ["R01", "R02"],
                "independent_article_anchor_result_ids": ["R01", "R02"],
                "evidence_paths": ["audit/one.yaml"],
            }
        ],
        "source_anchor_corrections": [
            {
                "stds_id": "STDS0000001",
                "result_id": "R04",
                "prior_source_anchors": old_anchor,
                "new_source_anchors": new_anchor,
                "evidence_paths": ["audit/anchors.yaml"],
            }
        ],
        "result_scope_exclusions": [],
    }

    revised, details = revision.apply_allowlisted_corrections(
        inventory(["STDS0000001"]), evidence, {"STDS0000001": objects}
    )
    result = revised["STDS0000001"]

    assert [value["resource_id"] for value in result["data"]["auxiliary_resources"]] == [
        "A02"
    ]
    assert result["data"]["auxiliary_resources"][0]["resource_name"] == "resource two"
    assert result["data"]["auxiliary_resources"][0]["expected_content"] == "two narrowed expected"
    assert result["data"]["result_data_links"][0]["auxiliary_resource_ids"] == []
    assert result["case"]["case_candidates"][0]["auxiliary_resource_ids"] == []
    assert result["source"]["results"][3]["source_anchors"] == new_anchor
    assert details["STDS0000001"]["resource_corrections"][0]["prior_values"][
        "access_notes"
    ] == "two old notes"
    assert details["STDS0000001"]["auxiliary_detachments"][0]["new_resource"] is None


def make_current_receipt(data_root: Path, scope: list[str]) -> Path:
    stomics_root = data_root / "raw_data/public_database/stomicsdb"
    records = []
    for index, stds_id in enumerate(scope):
        status = "accepted" if index == 0 else "no_candidate"
        prior_terminal = {
            "path": f"terminals/{stds_id}.yaml",
            "sha256": "0" * 64,
            "round3_batch_id": "batch",
            "job_attempt_id": f"batch__{stds_id}",
            "review_rounds": 1,
        }
        records.append(
            {
                "stds_id": stds_id,
                "authoritative_status": status,
                "status_source": "prior",
                "prior_terminal": prior_terminal,
                "prior_review_rounds": 1,
                "revision_validation": None,
                "output_paths": revision.output_paths(
                    stds_id, status, stomics_root, data_root
                ),
            }
        )
    path = data_root / "current_revision_receipt.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "round3_case_revision_receipt": {
                    "transaction_id": "prior",
                    "scope_stds_ids": scope,
                    "cases": records,
                    "counts": {"accepted": 1, "no_candidate": 15},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_small_end_to_end_commit_and_verify(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data_root"
    stomics_root = data_root / "raw_data/public_database/stomicsdb"
    case_directory = stomics_root / "cases/stomicsdb_STDS0000001"
    case_directory.parent.mkdir(parents=True)
    revision.write_case_tree(case_directory, revision.serialize_case(case_objects()))
    prior_chain = case_directory / "dual_chain/chain_sha256_0123456789abcdef"
    prior_chain.mkdir(parents=True)
    for name in revision.CHAIN_EXTRACTION_FILES:
        (prior_chain / name).write_text(f"prior {name}\n", encoding="utf-8")
    scope = [f"STDS{i:07d}" for i in range(1, 17)]
    source_inventory = data_root / "source_inventory.json"
    source_inventory.parent.mkdir(parents=True, exist_ok=True)
    source_inventory.write_text(json.dumps(inventory(scope)), encoding="utf-8")
    current_receipt = make_current_receipt(data_root, scope)
    evidence_path = data_root / "evidence.yaml"
    evidence_path.write_text(
        yaml.safe_dump({"resources": exclusion(["INV01"])}), encoding="utf-8"
    )
    monkeypatch.setattr(revision, "validate_external_bindings", lambda objects, root: None)
    args = argparse.Namespace(
        data_root=data_root,
        source_inventory=source_inventory,
        current_revision_receipt=current_receipt,
        exclusion_evidence=evidence_path,
        transaction_id="semantic_test_transaction",
        commit=True,
    )

    transaction_root = revision.prepare_transaction(args)
    assert revision.load_yaml(transaction_root / "transaction.yaml")[
        "post_publication_transaction"
    ]["state"] == "PREPARED"
    revision.commit_transaction(transaction_root, data_root)
    revision.verify_committed(transaction_root, data_root)

    committed = revision.load_case(case_directory)
    assert [value["candidate_id"] for value in committed["case"]["case_candidates"]] == [
        "C02"
    ]
    transaction = revision.load_yaml(transaction_root / "transaction.yaml")[
        "post_publication_transaction"
    ]
    assert transaction["state"] == "COMMITTED"
    assert transaction["committed_stds_ids"] == ["STDS0000001"]
    receipt = revision.load_yaml(transaction_root / "revision_receipt.yaml")[
        "round3_case_revision_receipt"
    ]
    assert receipt["counts"] == {"accepted": 1, "no_candidate": 15}
    assert len(receipt["cases"]) == 16
    backup = transaction_root / "backups/stomicsdb_STDS0000001"
    assert backup.is_dir()
    assert sorted(
        value.name for value in backup.glob("dual_chain/chain_sha256_*/**/*") if value.is_file()
    ) == sorted(revision.CHAIN_EXTRACTION_FILES)

    downstream_chain = case_directory / "dual_chain/chain_sha256_fedcba9876543210"
    downstream_chain.mkdir(parents=True)
    for name in revision.CHAIN_EXTRACTION_FILES:
        (downstream_chain / name).write_text(f"downstream {name}\n", encoding="utf-8")
    revision.verify_committed(transaction_root, data_root)
