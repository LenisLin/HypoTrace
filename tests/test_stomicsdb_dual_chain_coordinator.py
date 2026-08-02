from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stomicsdb_dual_chain_coordinator",
    ROOT / "scripts/stomicsdb_dual_chain_coordinator.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path, data_root: Path) -> str:
    return path.relative_to(data_root).as_posix()


def fixture(tmp_path: Path, *, localized: bool = True) -> dict[str, object]:
    data_root = tmp_path / "data_root"
    stomics = data_root / "raw_data/public_database/stomicsdb"
    case_id = "stomicsdb_STDS0000001"
    candidate_id = "C01"
    case_dir = stomics / "cases" / case_id
    dataset = stomics / "datasets/STDS0000001"
    data_root_object = dataset / "bundle"
    data_root_object.mkdir(parents=True)
    data_file = data_root_object / "matrix.h5ad"
    data_file.write_bytes(b"matrix")
    data_localization = data_root_object / "localization.yaml"
    write_yaml(
        data_localization,
        {
            "generation_id": "data-generation",
            "localization_status": "LOCALIZED",
            "bundle": {
                "owner_id": "STDS0000001",
                "target_directory": relative(data_root_object, data_root),
            },
            "artifacts": [
                {
                    "path": relative(data_file, data_root),
                    "sha256": digest(data_file),
                }
            ],
        },
    )
    samples_path = dataset / "samples.jsonl"
    write_jsonl(
        samples_path,
        [{"sample_id": "SAMPLE01", "stds_id": "STDS0000001"}],
    )
    article_path = dataset / "article.pdf"
    article_path.write_bytes(b"synthetic article")

    package_dir = stomics / "auxiliary_resources/R3AUX001/generations/aux-generation"
    artifact = package_dir / "artifacts/reference.tsv"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"gene\tcell\n")
    artifact_record = {
        "artifact_id": "A01_ART01",
        "path": relative(artifact, data_root),
        "source_url": "https://example.org/reference.tsv",
        "size_bytes": artifact.stat().st_size,
        "sha256": digest(artifact),
    }
    acquisition_dir = stomics / "staging/round3_auxiliary_downloads/runs/synthetic_run"
    inventory_path = acquisition_dir / "inventory.json"
    inventory_path.parent.mkdir(parents=True)
    inventory_path.write_text(
        json.dumps({"resources": [{"inventory_id": "R3AUX001"}]}) + "\n",
        encoding="utf-8",
    )
    events_path = acquisition_dir / "run.jsonl"
    write_jsonl(
        events_path,
        [
            {
                "event": "auxiliary_run_completed",
                "download_failure_count": 0,
                "artifact_count": 1,
            }
        ],
    )
    package_manifest = package_dir / "localization.yaml"
    package = {
        "package_id": "R3AUX001",
        "generation_id": "aux-generation",
        "localization_status": "LOCALIZED",
        "resource_identity": {
            "resource_name": "Reference table",
            "source_url": "https://example.org/reference.tsv",
        },
        "expected_content": "A reference table",
        "acquisition_bindings": {
            "inventories": [
                {
                    "path": relative(inventory_path, data_root),
                    "sha256": digest(inventory_path),
                    "inventory_resource_id": "R3AUX001",
                }
            ],
            "successful_runs": [
                {
                    "run_id": "synthetic_run",
                    "events_path": relative(events_path, data_root),
                    "sha256": digest(events_path),
                }
            ],
        },
        "artifacts": [
            {
                **artifact_record,
                "format": "tsv",
                "role": "required_resource_artifact",
            }
        ],
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
    write_yaml(package_manifest, {"auxiliary_localization_manifest": package})
    binding = {
        "package_manifest": {
            "package_id": "R3AUX001",
            "path": relative(package_manifest, data_root),
            "sha256": digest(package_manifest),
            "generation_id": "aux-generation",
        },
        "artifacts": [artifact_record],
        "expected_content_coverage": {
            "status": "complete",
            "items": [
                {
                    "requirement": "A reference table",
                    "artifact_ids": ["A01_ART01"],
                    "evidence": "The tabular artifact contains the required reference.",
                }
            ],
            "uncovered_requirements": [],
        },
    }
    auxiliary = {
        "resource_id": "A01",
        "resource_name": "Reference table",
        "expected_content": "A reference table",
        "source_url": "https://example.org/reference.tsv",
        "access_classification": "anonymous_direct",
        "local_availability": "localized" if localized else "absent",
        "access_notes": "Synthetic fixture",
    }
    if localized:
        auxiliary["localization_binding"] = binding

    case = {
        "stds_id": "STDS0000001",
        "source_manifest_path": "source_manifest.yaml",
        "case_data_manifest_path": "data/case_data_manifest.yaml",
        "case_candidates": [
            {
                "candidate_id": candidate_id,
                "result_ids": ["R01"],
                "result_order": ["R01"],
                "spatial_data_ids": ["D01"],
                "auxiliary_resource_ids": ["A01"],
                "result_connections": [],
            }
        ],
    }
    source = {
        "stds_id": "STDS0000001",
        "article_path": relative(article_path, data_root),
        "article_sha256": digest(article_path),
        "results": [
            {
                "result_id": "R01",
                "result_section": "Results",
                "source_anchors": [{"type": "figure", "locator": "Figure 1"}],
                "scientific_question": "How is the signal distributed?",
                "conclusion": "The signal differs across the measured regions.",
                "analysis_steps": [
                    {
                        "input": "Spatial expression matrix and reference table",
                        "method": "Reference-guided spatial comparison",
                        "output": "Regional comparison table",
                    }
                ],
            }
        ],
    }
    data = {
        "stds_id": "STDS0000001",
        "dataset_binding": {
            "samples": {
                "path": relative(samples_path, data_root),
                "sha256": digest(samples_path),
            }
        },
        "data_objects": [
            {
                "data_id": "D01",
                "path": relative(data_root_object, data_root),
                "role": "primary spatial object",
                "data_context": {
                    "organism": "Mus musculus",
                    "tissue_or_context": "synthetic tissue",
                    "spatial_assay": "spatial transcriptomics",
                    "sample_summary": "one synthetic section",
                    "available_metadata": ["region label"],
                },
                "localization_bindings": [
                    {
                        "path": relative(data_localization, data_root),
                        "sha256": digest(data_localization),
                        "generation_id": "data-generation",
                    }
                ],
                "expression_matrix": {
                    "files": [
                        {
                            "path": relative(data_file, data_root),
                            "format": "h5ad",
                            "sha256": digest(data_file),
                        }
                    ],
                    "summary": "Synthetic matrix",
                },
            }
        ],
        "auxiliary_resources": [auxiliary],
        "result_data_links": [
            {
                "result_id": "R01",
                "data_inputs": [
                    {
                        "data_id": "D01",
                        "input_role": "primary_spatial",
                        "sample_ids": ["SAMPLE01"],
                        "required_components": [
                            {
                                "component": "expression_matrix",
                                "paths": [relative(data_file, data_root)],
                            }
                        ],
                    }
                ],
                "auxiliary_resource_ids": ["A01"],
            }
        ],
    }
    write_yaml(case_dir / "case_manifest.yaml", {"case_manifest": case})
    write_yaml(case_dir / "source_manifest.yaml", {"source_manifest": source})
    write_yaml(case_dir / "data/case_data_manifest.yaml", {"case_data_manifest": data})
    return {
        "data_root": data_root,
        "case_dir": case_dir,
        "case_id": case_id,
        "candidate_id": candidate_id,
        "binding": binding,
        "auxiliary": auxiliary,
        "localized": localized,
        "data_file": data_file,
    }


def chain_objects(values: dict[str, object]) -> tuple[dict, list[dict], list[dict]]:
    data_root = values["data_root"]
    case_dir = values["case_dir"]
    case_id = values["case_id"]
    candidate_id = values["candidate_id"]
    identifier = MODULE.chain_id(case_id, candidate_id)
    manifest = {
        "case_id": case_id,
        "chain_id": identifier,
        "case_route": "public_database_stomicsdb",
        "chain_origin": "case_derived",
        "input_binding": {
            "stds_id": "STDS0000001",
            "candidate_id": candidate_id,
            "case_manifest": {
                "path": relative(case_dir / "case_manifest.yaml", data_root),
                "sha256": digest(case_dir / "case_manifest.yaml"),
            },
            "source_manifest": {
                "path": relative(case_dir / "source_manifest.yaml", data_root),
                "sha256": digest(case_dir / "source_manifest.yaml"),
            },
            "case_data_manifest": {
                "path": relative(case_dir / "data/case_data_manifest.yaml", data_root),
                "sha256": digest(case_dir / "data/case_data_manifest.yaml"),
            },
        },
        "chain_status": "draft",
        "chain_scope": {
            "scientific_objective": "Evaluate a regional spatial expression pattern.",
            "data_context": "A synthetic spatial sample and reference table.",
            "dependency_summary": "The reference table informs the spatial comparison.",
        },
        "independent_check": {
            "status": "not_started",
            "reviewer_independence": "independent_curator",
            "checked_sources": [],
            "checked_data_objects": [],
            "findings_summary": {"blocking": [], "needs_revision": [], "notes": []},
            "notes_location": f"dual_chain/{identifier}/independent_check.md",
        },
        "source": {
            "route": "public_database_stomicsdb",
            "source_type": "paper_case_section",
            "paper_or_doc": "Synthetic article",
            "section_or_example": "Results; Figure 1",
            "link": None,
            "repository": None,
        },
        "source_manifest": relative(case_dir / "source_manifest.yaml", data_root),
        "case_data_manifest": relative(
            case_dir / "data/case_data_manifest.yaml", data_root
        ),
        "used_localized_sources": [
            {
                "source_id": "article",
                "local_path": "raw_data/public_database/stomicsdb/datasets/STDS0000001/article.pdf",
                "source_role": "primary article",
                "locator": "Results; Figure 1",
            }
        ],
        "used_data_objects": [
            {
                "id": "D01",
                "role": "primary_spatial",
                "artifact_refs": [
                    {
                        "name": "matrix",
                        "role": "expression_matrix",
                        "path_or_locator": relative(values["data_file"], data_root),
                    }
                ],
                "required_by_scientific_units": ["S01"],
                "required_by_execution_subchains": ["E01"],
            }
        ],
        "used_auxiliary_resources": [],
        "round3_result_bindings": [
            {
                "result_id": "R01",
                "scientific_unit_ids": ["S01"],
                "execution_subchain_ids": ["E01"],
            }
        ],
        "data_readiness": {},
        "schema_check": {
            "scientific_chain_schema": "contracts/output_template/scientific_chain.jsonl",
            "execution_subchain_schema": "contracts/output_template/execution_subchains.jsonl",
            "jsonl_extension_policy": "no_extra_fields",
        },
        "visibility": {
            "agent_visible": "no",
            "evaluator_facing": "yes",
            "hidden_reference_candidate": "yes",
        },
        "extraction_policy": {
            "construction_mode": "hvu_execution_alternating",
            "execution_route": "ordered_multi_step_method_call_route",
            "result_material": "concrete_biological_analysis_content",
            "scientific_unit_requirement": "One HVU maps to one primary execution subchain.",
            "execution_granularity": "source_analysis_granularity",
            "minimum_execution_detail": ["input", "call", "output"],
        },
        "provenance": {
            "source_sections": ["Results"],
            "source_notebooks_or_scripts": [],
            "source_figures_or_tables": ["Figure 1"],
        },
        "limitations": ["Synthetic fixture; no scientific inference is intended."],
        "scientific_cautions": ["Do not treat this fixture as ground truth."],
    }
    if values["localized"]:
        manifest["used_auxiliary_resources"] = [
            {
                "id": "A01",
                "role": "reference",
                "canonical_resource_id": "R3AUX001",
                "package_id": "R3AUX001",
                "localization_binding": {
                    "package_manifest": deepcopy(values["binding"]["package_manifest"])
                },
                "artifact_refs": [
                    {
                        field: values["binding"]["artifacts"][0][field]
                        for field in ("artifact_id", "path", "sha256")
                    }
                ],
                "required_by_scientific_units": ["S01"],
                "required_by_execution_subchains": ["E01"],
            }
        ]
        manifest["data_readiness"] = {
            "status": "DATA_READY",
            "required_data_objects_resolved": "yes",
            "unresolved_data_objects": [],
            "notes": ["All selected inputs are localized and hash-valid."],
        }
    else:
        auxiliary = values["auxiliary"]
        manifest["used_auxiliary_resources"] = [
            {
                "id": "A01",
                "role": "reference",
                **{
                    field: auxiliary[field]
                    for field in MODULE.EXTERNAL_AUXILIARY_IDENTITY_FIELDS
                },
                "local_availability": "absent",
                "required_by_scientific_units": ["S01"],
                "required_by_execution_subchains": ["E01"],
            }
        ]
        manifest["data_readiness"] = {
            "status": "BLOCKED_EXTERNAL",
            "required_data_objects_resolved": "no",
            "unresolved_data_objects": ["A01"],
            "notes": ["A01 remains externally unresolved."],
        }
    observation = {
        "observation": "The measured signal differs across the named spatial regions.",
        "support": "Figure 1 and the regional comparison table",
        "interpretation": "This supports a bounded regional association in this sample.",
    }
    scientific = [
        {
            "scientific_unit_id": "S00",
            "parent_units": [],
            "data_summary": {
                "organism": "Mus musculus",
                "tissue": "synthetic tissue",
                "data_types": ["spatial transcriptomics"],
                "sample_count": 1,
                "spatial_unit_count": None,
                "sample_structure": ["one spatial section"],
                "grouping_variables": ["region"],
                "metadata_available": ["region label"],
                "notes": ["Synthetic validation fixture."],
            },
        },
        {
            "scientific_unit_id": "S01",
            "parent_units": [],
            "hypothesis": "Evaluate regional variation in the measured spatial signal.",
            "experiment": {
                "summary": "Compare the spatial signal across the named regions.",
                "execution_subchain_ids": ["E01"],
            },
            "result": {"observations": [observation]},
            "conclusion": {
                "summary": "The observations support a bounded regional association."
            },
            "next_hypothesis": None,
        },
    ]
    execution = [
        {
            "execution_subchain_id": "E01",
            "linked_scientific_unit_id": "S01",
            "steps": [
                {
                    "step_id": "E01.1",
                    "inputs": [
                        {
                            "id": "D01",
                            "object_content": "Spatial expression matrix",
                            "format": "h5ad",
                        },
                        {
                            "id": "A01",
                            "object_content": "Reference table",
                            "format": "tsv",
                        },
                    ],
                    "call": "Reference-guided spatial comparison",
                    "parameters": {"reference": "A01"},
                    "outputs": [
                        {
                            "id": "regional_comparison",
                            "object_content": "Regional comparison table",
                            "format": "table",
                        }
                    ],
                    "source_ref": {"type": "figure", "locator": "Figure 1"},
                }
            ],
            "result_extraction": {"observations": [observation]},
        }
    ]
    return manifest, scientific, execution


def write_extraction(directory: Path, values: dict[str, object]) -> dict:
    manifest, scientific, execution = chain_objects(values)
    write_yaml(directory / "chain_manifest.yaml", manifest)
    write_jsonl(directory / "scientific_chain.jsonl", scientific)
    write_jsonl(directory / "execution_subchains.jsonl", execution)
    return manifest


def attempt_directory(values: dict[str, object], kind: str, attempt: str) -> Path:
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    return (
        values["data_root"]
        / "raw_data/public_database/stomicsdb/staging/dual_chain"
        / kind
        / attempt
        / identifier
    )


def review_manifest(original: dict, status: str) -> dict:
    output = deepcopy(original)
    ready_status = (
        "specification_ready"
        if original["data_readiness"]["status"] == "BLOCKED_EXTERNAL"
        else "comparison_ready"
    )
    output["chain_status"] = {
        "confirmed": ready_status,
        "needs_revision": "needs_revision",
        "blocked": "blocked",
    }[status]
    output["independent_check"] = {
        "status": status,
        "reviewer_independence": "independent_curator",
        "checked_sources": [
            {
                "source_id": "article",
                "local_path": "raw_data/public_database/stomicsdb/datasets/STDS0000001/article.pdf",
                "source_role": "primary article",
                "locator": "Results; Figure 1",
            }
        ],
        "checked_data_objects": [
            {
                "id": record["id"],
                "role": record["role"],
                "local_or_prepared_path": (
                    record["artifact_refs"][0].get("path_or_locator")
                    or record["artifact_refs"][0].get("path")
                ),
                "artifact_refs": [
                    {
                        "name": (
                            ref.get("name") or ref.get("artifact_id")
                        ),
                        "role": "reviewed input",
                        "path_or_locator": (
                            ref.get("path_or_locator") or ref.get("path")
                        ),
                    }
                    for ref in record["artifact_refs"]
                ],
                "read_summary_used": "The bound local input was readable during review.",
            }
            for record in original["used_data_objects"]
            + [
                value
                for value in original["used_auxiliary_resources"]
                if value.get("local_availability") != "absent"
            ]
        ],
        "checked_unresolved_auxiliary_resource_ids": [
            value["id"]
            for value in original["used_auxiliary_resources"]
            if value.get("local_availability") == "absent"
        ],
        "findings_summary": {"blocking": [], "needs_revision": [], "notes": []},
        "notes_location": original["independent_check"]["notes_location"],
    }
    if status == "needs_revision":
        output["independent_check"]["revision_scope"] = "extraction"
    return output


def review_markdown(status: str, ready_status: str = "comparison_ready") -> str:
    chain_status = {
        "confirmed": ready_status,
        "needs_revision": "needs_revision",
        "blocked": "blocked",
    }[status]
    return (
        "# Independent Check: public_database_stomicsdb / "
        "stomicsdb_STDS0000001 / chain\n\n"
        "## Summary\n\n"
        f"- Overall result: {status}\n"
        f"- Chain status recommendation: {chain_status}\n"
        "- Main revision items: none\n"
        "- Main notes: synthetic fixture\n\n"
        "## Findings Summary\n\n"
        "- Blocking: none\n"
        "- Needs revision: none\n"
        "- Notes: synthetic fixture\n"
    )


def extraction_hashes(directory: Path) -> dict[str, str]:
    return {name: digest(directory / name) for name in MODULE.EXTRACTION_FILENAMES}


def test_chain_id_and_readiness_localized_or_absent(tmp_path: Path) -> None:
    absent = fixture(tmp_path / "absent", localized=False)
    assignments = MODULE.audit_cases(absent["data_root"])
    assert assignments[0]["data_readiness"] == "BLOCKED_EXTERNAL"
    assert "not localized" in assignments[0]["readiness_errors"][0]
    assert assignments[0]["used_data_object_ids"] == ["D01"]
    assert assignments[0]["used_auxiliary_resource_ids"] == ["A01"]
    assert assignments[0]["unresolved_auxiliary_resource_ids"] == ["A01"]
    assert assignments[0]["next_action"] == "extract_initial"

    damaged = fixture(tmp_path / "damaged", localized=True)
    damaged["data_file"].write_bytes(b"changed matrix")
    damaged_assignment = MODULE.audit_cases(damaged["data_root"])[0]
    assert damaged_assignment["data_readiness"] == "BLOCKED_EXTERNAL"
    assert "SHA-256 mismatch" in damaged_assignment["readiness_errors"][0]
    assert "used_data_object_ids" not in damaged_assignment
    assert "used_auxiliary_resource_ids" not in damaged_assignment
    assert damaged_assignment["next_action"] == "close_blocked"

    localized = fixture(tmp_path / "localized", localized=True)
    assignments = MODULE.audit_cases(localized["data_root"])
    expected = "chain_sha256_" + hashlib.sha256(
        b"stomicsdb_STDS0000001\nC01"
    ).hexdigest()[:16]
    assert assignments == [
        {
            "case_route": "public_database_stomicsdb",
            "attempt_id": "audit",
            "job_attempt_id": f"audit__{expected}",
            "max_revision_rounds": 2,
            "stds_id": "STDS0000001",
            "case_id": "stomicsdb_STDS0000001",
            "candidate_id": "C01",
            "chain_id": expected,
            "case_manifest_path": str(
                (localized["case_dir"] / "case_manifest.yaml").resolve()
            ),
            "source_manifest_path": str(
                (localized["case_dir"] / "source_manifest.yaml").resolve()
            ),
            "case_data_manifest_path": str(
                (localized["case_dir"] / "data/case_data_manifest.yaml").resolve()
            ),
            "extraction_staging_directory": str(
                (
                    localized["data_root"]
                    / f"raw_data/public_database/stomicsdb/staging/dual_chain/extraction/audit/{expected}"
                ).resolve()
            ),
            "review_staging_directory": str(
                (
                    localized["data_root"]
                    / f"raw_data/public_database/stomicsdb/staging/dual_chain/review/audit/{expected}"
                ).resolve()
            ),
            "final_chain_directory": str(
                (localized["case_dir"] / "dual_chain" / expected).resolve()
            ),
            "input_binding": {
                "stds_id": "STDS0000001",
                "candidate_id": "C01",
                "case_manifest": {
                    "path": "raw_data/public_database/stomicsdb/cases/stomicsdb_STDS0000001/case_manifest.yaml",
                    "sha256": digest(localized["case_dir"] / "case_manifest.yaml"),
                },
                "source_manifest": {
                    "path": "raw_data/public_database/stomicsdb/cases/stomicsdb_STDS0000001/source_manifest.yaml",
                    "sha256": digest(localized["case_dir"] / "source_manifest.yaml"),
                },
                "case_data_manifest": {
                    "path": "raw_data/public_database/stomicsdb/cases/stomicsdb_STDS0000001/data/case_data_manifest.yaml",
                    "sha256": digest(localized["case_dir"] / "data/case_data_manifest.yaml"),
                },
            },
            "data_readiness": "DATA_READY",
            "readiness_errors": [],
            "used_data_object_ids": ["D01"],
            "used_auxiliary_resource_ids": ["A01"],
            "current_chain_state": "absent",
            "next_action": "extract_initial",
            "committed_revision_rounds": 0,
            "remaining_revision_rounds": 2,
        }
    ]


def test_absent_auxiliary_can_publish_reviewed_specification(tmp_path: Path) -> None:
    values = fixture(tmp_path, localized=False)
    assignment = MODULE.audit_cases(values["data_root"], "external_spec")[0]
    assert MODULE.validate_job_assignment(
        assignment, values["data_root"], ROOT
    )["next_action"] == "extract_initial"
    blocked_response = {
        "stomicsdb_dual_chain_job_response": {
            "attempt_id": assignment["attempt_id"],
            "job_attempt_id": assignment["job_attempt_id"],
            "stds_id": assignment["stds_id"],
            "candidate_id": assignment["candidate_id"],
            "chain_id": assignment["chain_id"],
            "status": "blocked",
            "revision_rounds": 0,
            "review_rounds": 0,
            "output_paths": {
                "chain_directory": None,
                "chain_manifest": None,
                "scientific_chain": None,
                "execution_subchains": None,
                "independent_check": None,
            },
            "error": "A01 remains absent.",
        }
    }
    with pytest.raises(MODULE.CoordinatorError, match="absent-Axx-only"):
        MODULE.validate_job_response(
            blocked_response, assignment, values["data_root"], ROOT
        )

    stage = Path(assignment["extraction_staging_directory"])
    original = write_extraction(stage, values)
    external = original["used_auxiliary_resources"][0]
    assert external == {
        "id": "A01",
        "role": "reference",
        "resource_name": "Reference table",
        "expected_content": "A reference table",
        "source_url": "https://example.org/reference.tsv",
        "access_classification": "anonymous_direct",
        "access_notes": "Synthetic fixture",
        "local_availability": "absent",
        "required_by_scientific_units": ["S01"],
        "required_by_execution_subchains": ["E01"],
    }
    MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)

    mutated = deepcopy(original)
    mutated["used_auxiliary_resources"][0]["source_url"] = "https://wrong.example/A01"
    write_yaml(stage / "chain_manifest.yaml", mutated)
    with pytest.raises(
        MODULE.CoordinatorError,
        match="unresolved auxiliary wrapper differs from Round 3",
    ):
        MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)
    write_extraction(stage, values)

    final = Path(assignment["final_chain_directory"])
    MODULE.publish_initial(
        stage,
        final,
        "external_spec.initial",
        values["data_root"],
        ROOT,
        assignment,
    )
    review = Path(assignment["review_staging_directory"])
    proposal = review_manifest(original, "confirmed")
    write_yaml(review / "chain_manifest.yaml", proposal)
    (review / "independent_check.md").write_text(
        review_markdown("confirmed", "specification_ready"), encoding="utf-8"
    )
    MODULE.publish_review(
        review,
        final,
        "external_spec.review.r0",
        extraction_hashes(final),
        data_root=values["data_root"],
        repository_root=ROOT,
        assignment=assignment,
        review_round=0,
    )

    paths = {
        "chain_directory": str(final.resolve()),
        "chain_manifest": str((final / "chain_manifest.yaml").resolve()),
        "scientific_chain": str((final / "scientific_chain.jsonl").resolve()),
        "execution_subchains": str((final / "execution_subchains.jsonl").resolve()),
        "independent_check": str((final / "independent_check.md").resolve()),
    }
    response = {
        "stomicsdb_dual_chain_job_response": {
            "attempt_id": assignment["attempt_id"],
            "job_attempt_id": assignment["job_attempt_id"],
            "stds_id": assignment["stds_id"],
            "candidate_id": assignment["candidate_id"],
            "chain_id": assignment["chain_id"],
            "status": "specification_ready",
            "revision_rounds": 0,
            "review_rounds": 1,
            "output_paths": paths,
            "error": None,
        }
    }
    assert MODULE.validate_job_response(
        response, assignment, values["data_root"], ROOT
    )["status"] == "specification_ready"
    assert MODULE.verify_all(values["data_root"], ROOT) == [
        {
            "stds_id": "STDS0000001",
            "candidate_id": "C01",
            "chain_id": assignment["chain_id"],
            "status": "specification_ready",
        }
    ]
    resumed = MODULE.audit_cases(values["data_root"], "external_spec_resume")[0]
    assert resumed["current_chain_state"] == "specification_ready"
    assert resumed["next_action"] == "verify_and_close"


def test_assignment_semantics_reject_identity_path_and_readiness_mutations(
    tmp_path: Path,
) -> None:
    values = fixture(tmp_path)
    assignment = MODULE.audit_cases(values["data_root"], "semantic")[0]
    assert MODULE.validate_job_assignment(
        assignment, values["data_root"], ROOT
    )["next_action"] == "extract_initial"

    mutations = []
    wrong_chain = deepcopy(assignment)
    wrong_chain["chain_id"] = "chain_sha256_0000000000000000"
    mutations.append(wrong_chain)
    wrong_binding = deepcopy(assignment)
    wrong_binding["input_binding"]["candidate_id"] = "C02"
    mutations.append(wrong_binding)
    wrong_path = deepcopy(assignment)
    wrong_path["review_staging_directory"] = str(tmp_path / "other")
    mutations.append(wrong_path)
    wrong_readiness = deepcopy(assignment)
    wrong_readiness["readiness_errors"] = ["contradiction"]
    mutations.append(wrong_readiness)
    for mutated in mutations:
        with pytest.raises(MODULE.CoordinatorError):
            MODULE.validate_job_assignment(mutated, values["data_root"], ROOT)


def test_readiness_allows_narrower_case_requirement_than_package_scope(
    tmp_path: Path,
) -> None:
    values = fixture(tmp_path, localized=True)
    data_path = values["case_dir"] / "data/case_data_manifest.yaml"
    document = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    auxiliary = document["case_data_manifest"]["auxiliary_resources"][0]
    auxiliary["expected_content"] = "The retained A/B subset of the reference table"
    coverage = auxiliary["localization_binding"]["expected_content_coverage"]
    coverage["items"][0]["requirement"] = auxiliary["expected_content"]
    write_yaml(data_path, document)

    assignments = MODULE.audit_cases(values["data_root"])
    assert assignments[0]["data_readiness"] == "DATA_READY"

    document = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    document["case_data_manifest"]["auxiliary_resources"][0][
        "localization_binding"
    ]["expected_content_coverage"]["items"][0]["requirement"] = "Wrong subset"
    write_yaml(data_path, document)
    with pytest.raises(MODULE.CoordinatorError, match="coverage requirement mismatch"):
        MODULE.audit_cases(values["data_root"])


def test_jsonl_global_invariants(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    stage = attempt_directory(values, "extraction", "invariants")
    write_extraction(stage, values)
    MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)

    rows = [json.loads(line) for line in (stage / "execution_subchains.jsonl").read_text().splitlines()]
    rows[0]["steps"][0]["step_id"] = "E01.2"
    write_jsonl(stage / "execution_subchains.jsonl", rows)
    with pytest.raises(MODULE.CoordinatorError, match="nonsequential step ID"):
        MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)

    assert MODULE._locator_matches("article.pdf; Results; Figure 1A", "Figure 1A")
    assert not MODULE._locator_matches("Figure 10", "Figure 1")


def test_cross_subchain_object_resolution_is_ordered(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    manifest, scientific, execution = chain_objects(values)
    observation = deepcopy(scientific[1]["result"]["observations"][0])
    scientific.append(
        {
            "scientific_unit_id": "S02",
            "parent_units": ["S01"],
            "hypothesis": "Evaluate a downstream summary of the regional comparison.",
            "experiment": {
                "summary": "Summarize the upstream regional comparison.",
                "execution_subchain_ids": ["E02"],
            },
            "result": {"observations": [observation]},
            "conclusion": {"summary": "The upstream comparison supports the summary."},
            "next_hypothesis": None,
        }
    )
    upstream_output = deepcopy(execution[0]["steps"][0]["outputs"][0])
    execution.append(
        {
            "execution_subchain_id": "E02",
            "linked_scientific_unit_id": "S02",
            "steps": [
                {
                    "step_id": "E02.1",
                    "inputs": [upstream_output],
                    "call": "Summarize the regional comparison",
                    "parameters": {},
                    "outputs": [
                        {
                            "id": "regional_summary",
                            "object_content": "Regional comparison summary",
                            "format": "table",
                        }
                    ],
                    "source_ref": {"type": "figure", "locator": "Figure 1"},
                }
            ],
            "result_extraction": {"observations": [observation]},
        }
    )

    MODULE._validate_jsonl_invariants(scientific, execution)
    MODULE._validate_execution_object_resolution(manifest, execution)

    mismatched = deepcopy(execution)
    mismatched[1]["steps"][0]["inputs"][0]["object_content"] = "Different object"
    with pytest.raises(MODULE.CoordinatorError, match="object continuity mismatch"):
        MODULE._validate_jsonl_invariants(scientific, mismatched)

    forward_reference = deepcopy(execution)
    forward_reference[0]["steps"][0]["inputs"].append(
        {
            "id": "regional_summary",
            "object_content": "Regional comparison summary",
            "format": "table",
        }
    )
    with pytest.raises(MODULE.CoordinatorError, match="unresolved external execution input"):
        MODULE._validate_execution_object_resolution(manifest, forward_reference)

    unresolved = deepcopy(execution)
    unresolved[1]["steps"][0]["inputs"][0]["id"] = "unknown_external_object"
    with pytest.raises(MODULE.CoordinatorError, match="unresolved external execution input"):
        MODULE._validate_execution_object_resolution(manifest, unresolved)


def test_builtin_schema_validator_and_attempt_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = fixture(tmp_path)
    stage = attempt_directory(values, "extraction", "fallback")
    write_extraction(stage, values)
    monkeypatch.setattr(MODULE, "jsonschema", None)
    MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)

    manifest, _, _ = chain_objects(values)
    manifest["visibility"]["agent_visible"] = 0
    with pytest.raises(MODULE.CoordinatorError, match="schema failure"):
        MODULE._validate_schema_value(
            manifest,
            MODULE._load_schema(ROOT, "stomicsdb_dual_chain_manifest.schema.json"),
            "fallback manifest",
        )

    wrong = values["data_root"] / "raw_data/public_database/stomicsdb/staging/not_assigned"
    write_extraction(wrong, values)
    with pytest.raises(MODULE.CoordinatorError, match="canonical assigned attempt root"):
        MODULE.validate_extraction_staging(wrong, values["data_root"], ROOT)


def test_rejects_extra_dxx_artifact_ref(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    stage = attempt_directory(values, "extraction", "extra_ref")
    manifest, scientific, execution = chain_objects(values)
    manifest["used_data_objects"][0]["artifact_refs"].append(
        {
            "name": "unrelated",
            "role": "unrelated",
            "path_or_locator": "raw_data/public_database/stomicsdb/unrelated.tsv",
        }
    )
    write_yaml(stage / "chain_manifest.yaml", manifest)
    write_jsonl(stage / "scientific_chain.jsonl", scientific)
    write_jsonl(stage / "execution_subchains.jsonl", execution)
    with pytest.raises(MODULE.CoordinatorError, match="do not exactly match"):
        MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)


def test_chain_manifest_schema_rejects_unknown_field(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    stage = attempt_directory(values, "extraction", "manifest_schema")
    manifest, scientific, execution = chain_objects(values)
    manifest["unconsumed_audit_metadata"] = {"duplicate_hash": "not allowed"}
    write_yaml(stage / "chain_manifest.yaml", manifest)
    write_jsonl(stage / "scientific_chain.jsonl", scientific)
    write_jsonl(stage / "execution_subchains.jsonl", execution)

    with pytest.raises(MODULE.CoordinatorError, match="chain_manifest schema failure"):
        MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)


def test_new_extraction_requires_complete_round3_result_binding(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    stage = attempt_directory(values, "extraction", "result_binding")
    manifest, scientific, execution = chain_objects(values)
    manifest.pop("round3_result_bindings")
    write_yaml(stage / "chain_manifest.yaml", manifest)
    write_jsonl(stage / "scientific_chain.jsonl", scientific)
    write_jsonl(stage / "execution_subchains.jsonl", execution)
    with pytest.raises(MODULE.CoordinatorError, match="round3_result_bindings"):
        MODULE.validate_extraction_staging(stage, values["data_root"], ROOT)


def test_review_rejects_self_review_empty_data_and_noncanonical_notes(
    tmp_path: Path,
) -> None:
    values = fixture(tmp_path)
    stage = attempt_directory(values, "extraction", "review_negative_source")
    final = values["case_dir"] / "dual_chain" / MODULE.chain_id(
        values["case_id"], values["candidate_id"]
    )
    original = write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "review_negative_initial", values["data_root"], ROOT)

    cases = []
    self_review = review_manifest(original, "confirmed")
    self_review["independent_check"]["reviewer_independence"] = "self_review_with_limitation"
    cases.append((self_review, "independent curator"))
    empty_data = review_manifest(original, "confirmed")
    empty_data["independent_check"]["checked_data_objects"] = []
    cases.append((empty_data, "Dxx/Axx boundary"))
    wrong_notes = review_manifest(original, "confirmed")
    wrong_notes["independent_check"]["notes_location"] = "wrong/independent_check.md"
    cases.append((wrong_notes, "notes_location"))
    for index, (proposal, message) in enumerate(cases):
        review = attempt_directory(values, "review", f"negative_{index}")
        write_yaml(review / "chain_manifest.yaml", proposal)
        (review / "independent_check.md").write_text(
            review_markdown("confirmed"), encoding="utf-8"
        )
        with pytest.raises(MODULE.CoordinatorError, match=message):
            MODULE._validate_review_staging(
                review, final, values["data_root"], ROOT
            )


def test_recovery_does_not_remove_unprovable_live_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    lock = MODULE.ChainLock(
        values["data_root"], identifier, "replacement", recover_stale=True
    )
    lock.path.mkdir(parents=True)
    write_yaml(
        lock.path / "owner.yaml",
        {
            "chain_id": identifier,
            "operation_id": "current",
            "pid": __import__("os").getpid(),
            "process_start_time": None,
            "created_at": "2026-01-01T00:00:00Z",
            "lock_path": relative(lock.path, values["data_root"]),
        },
    )
    monkeypatch.setattr(MODULE.ChainLock, "_process_start_time", staticmethod(lambda pid: None))
    with pytest.raises(MODULE.CoordinatorError, match="cannot prove"):
        lock.__enter__()
    assert lock.path.is_dir()
    (lock.path / "owner.yaml").unlink()
    lock.path.rmdir()


def test_s00_sample_count_allows_manifest_supported_auxiliary_samples() -> None:
    scientific = [
        {
            "data_summary": {
                "organism": "Mus musculus",
                "tissue": "synthetic tissue",
                "data_types": ["spatial transcriptomics"],
                "sample_count": 2,
            }
        }
    ]
    context = {
        "data_objects": {
            "D01": {
                "data_context": {
                    "organism": "Mus musculus",
                    "tissue_or_context": "synthetic tissue",
                    "spatial_assay": "spatial transcriptomics",
                }
            }
        },
        "used_data_ids": ["D01"],
        "used_auxiliary_ids": ["A01"],
        "candidate_sample_ids": ["SAMPLE01"],
    }

    MODULE._validate_s00_data_context(scientific, context)

    context["used_auxiliary_ids"] = []
    with pytest.raises(MODULE.CoordinatorError, match="differs from selected"):
        MODULE._validate_s00_data_context(scientific, context)

    context["used_auxiliary_ids"] = ["A01"]
    scientific[0]["data_summary"]["sample_count"] = 0
    with pytest.raises(MODULE.CoordinatorError, match="smaller than selected"):
        MODULE._validate_s00_data_context(scientific, context)


def test_initial_publish(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "initial")
    final = values["case_dir"] / "dual_chain" / identifier
    write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "initial_attempt", values["data_root"], ROOT)
    assert not stage.exists()
    assert sorted(path.name for path in final.iterdir()) == sorted(MODULE.EXTRACTION_FILENAMES)
    locks = values["data_root"] / "raw_data/public_database/stomicsdb/staging/dual_chain/locks"
    assert not any(locks.iterdir())


def test_initial_publish_rejects_other_case_directory(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "wrong_case")
    write_extraction(stage, values)
    wrong_final = (
        values["data_root"]
        / "raw_data/public_database/stomicsdb/cases/stomicsdb_STDS9999999/dual_chain"
        / identifier
    )
    wrong_final.parent.parent.mkdir(parents=True)
    with pytest.raises(MODULE.CoordinatorError, match="does not match bound case"):
        MODULE.publish_initial(
            stage, wrong_final, "wrong_case", values["data_root"], ROOT
        )


def test_confirmed_review_transaction_preserves_jsonl(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "review_source")
    final = values["case_dir"] / "dual_chain" / identifier
    original = write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "initial", values["data_root"], ROOT)
    original_hashes = {
        name: digest(final / name)
        for name in ("scientific_chain.jsonl", "execution_subchains.jsonl")
    }
    review = attempt_directory(values, "review", "confirmed")
    write_yaml(review / "chain_manifest.yaml", review_manifest(original, "confirmed"))
    (review / "independent_check.md").write_text(review_markdown("confirmed"), encoding="utf-8")
    transaction = MODULE.publish_review(
        review,
        final,
        "review_tx",
        extraction_hashes(final),
        data_root=values["data_root"],
        repository_root=ROOT,
    )
    assert MODULE.load_yaml(transaction / "transaction.yaml")["state"] == "COMMITTED"
    assert MODULE.load_yaml(final / "chain_manifest.yaml")["chain_status"] == "comparison_ready"
    assert {
        name: digest(final / name)
        for name in ("scientific_chain.jsonl", "execution_subchains.jsonl")
    } == original_hashes
    backup = transaction / "backup" / identifier
    assert all((backup / name).is_file() for name in MODULE.EXTRACTION_FILENAMES)
    for name in ("scientific_chain.jsonl", "execution_subchains.jsonl"):
        assert (backup / name).stat().st_ino == (final / name).stat().st_ino
    MODULE.validate_chain_directory(final, values["data_root"], ROOT, final=True)
    assert MODULE.verify_all(values["data_root"], ROOT) == [
        {
            "stds_id": "STDS0000001",
            "candidate_id": "C01",
            "chain_id": identifier,
            "status": "comparison_ready",
        }
    ]


def test_revision_replacement_resets_review(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "revision_source")
    final = values["case_dir"] / "dual_chain" / identifier
    original = write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "initial", values["data_root"], ROOT)

    review = attempt_directory(values, "review", "needs_revision")
    review_value = review_manifest(original, "needs_revision")
    review_value["independent_check"]["findings_summary"]["needs_revision"] = [
        "Clarify the bounded result wording."
    ]
    write_yaml(review / "chain_manifest.yaml", review_value)
    (review / "independent_check.md").write_text(
        review_markdown("needs_revision"), encoding="utf-8"
    )
    MODULE.publish_review(
        review,
        final,
        "review_tx",
        extraction_hashes(final),
        data_root=values["data_root"],
        repository_root=ROOT,
    )

    revision = attempt_directory(values, "extraction", "revision_attempt")
    write_extraction(revision, values)
    transaction = MODULE.publish_revision(
        revision, final, "revision_tx", values["data_root"], ROOT
    )
    assert MODULE.load_yaml(transaction / "transaction.yaml")["state"] == "COMMITTED"
    revised = MODULE.load_yaml(final / "chain_manifest.yaml")
    assert revised["chain_status"] == "draft"
    assert revised["independent_check"]["status"] == "not_started"
    assert sorted(path.name for path in final.iterdir()) == sorted(MODULE.EXTRACTION_FILENAMES)
    assert (transaction / "backup" / identifier / "independent_check.md").is_file()


def test_isolated_candidate_job_simulation_resumes_and_validates_response(
    tmp_path: Path,
) -> None:
    values = fixture(tmp_path)
    assignment = MODULE.audit_cases(values["data_root"], "simulation")[0]
    identifier = assignment["chain_id"]
    final = Path(assignment["final_chain_directory"])

    initial = Path(assignment["extraction_staging_directory"])
    original = write_extraction(initial, values)
    MODULE.publish_initial(
        initial,
        final,
        "simulation.initial",
        values["data_root"],
        ROOT,
        assignment,
    )

    review0 = Path(assignment["review_staging_directory"])
    proposal = review_manifest(original, "needs_revision")
    proposal["independent_check"]["findings_summary"]["needs_revision"] = [
        "Correct the bounded extraction wording."
    ]
    write_yaml(review0 / "chain_manifest.yaml", proposal)
    (review0 / "independent_check.md").write_text(
        review_markdown("needs_revision"), encoding="utf-8"
    )
    MODULE.publish_review(
        review0,
        final,
        "simulation.review.r0",
        extraction_hashes(final),
        data_root=values["data_root"],
        repository_root=ROOT,
        assignment=assignment,
        review_round=0,
    )

    revision1 = MODULE._assigned_stage_for_round(assignment, "extraction", 1)
    revised = write_extraction(revision1, values)
    MODULE.publish_revision(
        revision1,
        final,
        "simulation.revision.r1",
        values["data_root"],
        ROOT,
        assignment,
        1,
    )

    review1 = MODULE._assigned_stage_for_round(assignment, "review", 1)
    write_yaml(review1 / "chain_manifest.yaml", review_manifest(revised, "confirmed"))
    (review1 / "independent_check.md").write_text(
        review_markdown("confirmed"), encoding="utf-8"
    )
    MODULE.publish_review(
        review1,
        final,
        "simulation.review.r1",
        extraction_hashes(final),
        data_root=values["data_root"],
        repository_root=ROOT,
        assignment=assignment,
        review_round=1,
    )

    paths = {
        "chain_directory": str(final.resolve()),
        "chain_manifest": str((final / "chain_manifest.yaml").resolve()),
        "scientific_chain": str((final / "scientific_chain.jsonl").resolve()),
        "execution_subchains": str((final / "execution_subchains.jsonl").resolve()),
        "independent_check": str((final / "independent_check.md").resolve()),
    }
    response = {
        "stomicsdb_dual_chain_job_response": {
            "attempt_id": assignment["attempt_id"],
            "job_attempt_id": assignment["job_attempt_id"],
            "stds_id": assignment["stds_id"],
            "candidate_id": assignment["candidate_id"],
            "chain_id": identifier,
            "status": "comparison_ready",
            "revision_rounds": 1,
            "review_rounds": 2,
            "output_paths": paths,
            "error": None,
        }
    }
    assert MODULE.validate_job_response(
        response, assignment, values["data_root"], ROOT
    )["status"] == "comparison_ready"

    resumed = MODULE.audit_cases(values["data_root"], "simulation_resume")[0]
    assert resumed["current_chain_state"] == "comparison_ready"
    assert resumed["next_action"] == "verify_and_close"
    assert resumed["committed_revision_rounds"] == 1
    assert resumed["remaining_revision_rounds"] == 1


def test_revision_limit_rejects_third_committed_revision(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "revision_limit_source")
    final = values["case_dir"] / "dual_chain" / identifier
    original = write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "initial", values["data_root"], ROOT)

    review = attempt_directory(values, "review", "revision_limit_review")
    review_value = review_manifest(original, "needs_revision")
    review_value["independent_check"]["findings_summary"]["needs_revision"] = [
        "Clarify the bounded result wording."
    ]
    write_yaml(review / "chain_manifest.yaml", review_value)
    (review / "independent_check.md").write_text(
        review_markdown("needs_revision"), encoding="utf-8"
    )
    MODULE.publish_review(
        review,
        final,
        "revision_limit_review_tx",
        extraction_hashes(final),
        data_root=values["data_root"],
        repository_root=ROOT,
    )

    transactions = (
        values["data_root"]
        / "raw_data/public_database/stomicsdb/staging/dual_chain/transactions"
    )
    for revision_round in (1, 2):
        write_yaml(
            transactions / f"synthetic_revision_{revision_round}/transaction.yaml",
            {
                "operation": "extraction_revision",
                "chain_id": identifier,
                "state": "COMMITTED",
            },
        )

    revision = attempt_directory(values, "extraction", "third_revision")
    write_extraction(revision, values)
    with pytest.raises(MODULE.CoordinatorError, match="revision limit reached"):
        MODULE.publish_revision(
            revision, final, "third_revision_tx", values["data_root"], ROOT
        )


def test_review_hash_and_markdown_binding(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "review_binding")
    final = values["case_dir"] / "dual_chain" / identifier
    original = write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "initial", values["data_root"], ROOT)
    review = attempt_directory(values, "review", "binding")
    write_yaml(review / "chain_manifest.yaml", review_manifest(original, "confirmed"))
    (review / "independent_check.md").write_text(
        review_markdown("needs_revision"), encoding="utf-8"
    )
    with pytest.raises(MODULE.CoordinatorError, match="overall result disagrees"):
        MODULE.publish_review(
            review,
            final,
            "bad_markdown",
            extraction_hashes(final),
            data_root=values["data_root"],
            repository_root=ROOT,
        )
    (review / "independent_check.md").write_text(
        review_markdown("confirmed"), encoding="utf-8"
    )
    wrong_hashes = extraction_hashes(final)
    wrong_hashes["scientific_chain.jsonl"] = "0" * 64
    with pytest.raises(MODULE.CoordinatorError, match="reviewer input hashes"):
        MODULE.publish_review(
            review,
            final,
            "bad_hash",
            wrong_hashes,
            data_root=values["data_root"],
            repository_root=ROOT,
        )
    assert review.is_dir()
    assert not MODULE._transaction_root(values["data_root"], "bad_hash").exists()


def test_recover_prepared_transaction_restores_and_revalidates(tmp_path: Path) -> None:
    values = fixture(tmp_path)
    identifier = MODULE.chain_id(values["case_id"], values["candidate_id"])
    stage = attempt_directory(values, "extraction", "recovery_source")
    final = values["case_dir"] / "dual_chain" / identifier
    write_extraction(stage, values)
    MODULE.publish_initial(stage, final, "initial", values["data_root"], ROOT)
    prior_hashes = extraction_hashes(final)
    transaction = MODULE._transaction_root(values["data_root"], "recover_tx")
    backup = transaction / "backup" / identifier
    backup.parent.mkdir(parents=True)
    replacement = transaction / "replacement" / identifier
    replacement.parent.mkdir(parents=True)
    MODULE.atomic_write_yaml(
        transaction / "transaction.yaml",
        {
            "transaction_id": "recover_tx",
                "operation": "synthetic_interruption",
                "chain_id": identifier,
                "case_id": values["case_id"],
            "state": "PREPARED",
            "phase": "prior_chain_backed_up",
            "chain_directory": relative(final, values["data_root"]),
            "replacement_directory": relative(replacement, values["data_root"]),
            "backup_directory": relative(backup, values["data_root"]),
            "prior_validation_mode": "extraction",
            "replacement_validation_mode": "reviewed",
            "prior_file_hashes": prior_hashes,
        },
    )
    final.parent.mkdir(parents=True, exist_ok=True)
    final.rename(backup)
    stale_lock = MODULE.ChainLock(
        values["data_root"], identifier, "interrupted"
    ).path
    stale_lock.mkdir(parents=True)
    MODULE.atomic_write_yaml(
        stale_lock / "owner.yaml",
        {
            "chain_id": identifier,
            "operation_id": "interrupted",
            "pid": 999_999_999,
            "process_start_time": None,
            "created_at": "2026-01-01T00:00:00Z",
            "lock_path": relative(stale_lock, values["data_root"]),
        },
    )
    recovered = MODULE.recover_transaction(transaction, values["data_root"], ROOT)
    assert recovered["state"] == "ROLLED_BACK"
    assert recovered["phase"] == "rollback_verified"
    assert extraction_hashes(final) == prior_hashes
    assert not stale_lock.exists()
    MODULE.validate_chain_directory(final, values["data_root"], ROOT, final=False)
