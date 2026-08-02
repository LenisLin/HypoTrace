from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPTS / "stomicsdb_round3_auxiliary_scope_revision.py"
SPEC = importlib.util.spec_from_file_location("stomicsdb_round3_auxiliary_scope_revision", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
revision = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = revision
SPEC.loader.exec_module(revision)


def case_objects() -> dict:
    return {
        "source": {
            "stds_id": "STDS0000001",
            "results": [{"result_id": value} for value in ("R01", "R02", "R03", "R04")],
        },
        "data": {
            "stds_id": "STDS0000001",
            "dataset_binding": {},
            "data_objects": [{"data_id": "D01"}],
            "auxiliary_resources": [
                {"resource_id": "A01"},
                {"resource_id": "A02"},
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
                    "auxiliary_resource_ids": [],
                },
                {
                    "result_id": "R03",
                    "data_inputs": [{"data_id": "D01", "input_role": "primary_spatial"}],
                    "auxiliary_resource_ids": ["A02"],
                },
                {
                    "result_id": "R04",
                    "data_inputs": [{"data_id": "D01", "input_role": "primary_spatial"}],
                    "auxiliary_resource_ids": [],
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


def test_prune_case_removes_direct_and_transitive_downstream_results() -> None:
    revised, details = revision.prune_case(case_objects(), {"R01"})

    assert revised is not None
    assert details["direct_removed_result_ids"] == ["R01"]
    assert details["downstream_removed_result_ids"] == ["R02"]
    assert details["retained_result_ids"] == ["R03", "R04"]
    assert [value["result_id"] for value in revised["source"]["results"]] == [
        "R03",
        "R04",
    ]
    assert [
        value["resource_id"]
        for value in revised["data"]["auxiliary_resources"]
    ] == ["A02"]
    assert [
        value["candidate_id"] for value in revised["case"]["case_candidates"]
    ] == ["C02"]
    revision.validate_case(revised, "STDS0000001")


def test_prune_case_returns_no_candidate_when_every_chain_is_removed() -> None:
    revised, details = revision.prune_case(case_objects(), {"R01", "R03"})

    assert revised is None
    assert details["removed_result_ids"] == ["R01", "R02", "R03", "R04"]
    assert details["retained_candidate_ids"] == []


def test_terminal_record_path_accepts_historical_absolute_or_relative_paths(
    tmp_path: Path,
) -> None:
    terminal = tmp_path / "round3_runs/b03/jobs/STDS0000001/terminal.yaml"
    terminal.parent.mkdir(parents=True)
    terminal.write_text("terminal\n")

    relative = terminal.relative_to(tmp_path).as_posix()
    assert revision.terminal_record_path_matches(str(terminal), terminal, tmp_path)
    assert revision.terminal_record_path_matches(relative, terminal, tmp_path)
    assert not revision.terminal_record_path_matches("round3_runs/other.yaml", terminal, tmp_path)


def test_excluded_auxiliary_references_reports_only_matching_resource_identity() -> None:
    objects = {
        "data": {
            "auxiliary_resources": [
                {
                    "resource_id": "A01",
                    "resource_name": "excluded",
                    "source_url": "https://example.org/excluded",
                },
                {
                    "resource_id": "A02",
                    "resource_name": "retained",
                    "source_url": "https://example.org/retained",
                },
            ]
        }
    }

    assert revision.excluded_auxiliary_references(
        objects, {("excluded", "https://example.org/excluded")}
    ) == ["A01"]
