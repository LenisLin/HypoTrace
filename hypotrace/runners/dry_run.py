"""Dry-run output contract writer.

The writer creates the required submission files, placeholder workspace
directories, scores, logs, and summary file for contract smoke testing. It has
filesystem side effects under the requested run directory only and assumes that
no scientific analysis is executed.
"""

from __future__ import annotations

import json
from pathlib import Path


WORKSPACE_SUBDIRS = ("scripts", "notebooks", "figures", "tables", "logs")


def create_dry_run(data_root: Path, *, run_id: str, task_id: str) -> Path:
    run_dir = Path(data_root).resolve() / "runs" / run_id
    submission_dir = run_dir / "submission"
    workspace_dir = submission_dir / "workspace"
    artifacts_dir = run_dir / "artifacts"
    logs_dir = run_dir / "logs"
    for subdir in WORKSPACE_SUBDIRS:
        (workspace_dir / subdir).mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    for obsolete_name in ("manifest.json", "trajectory.jsonl"):
        obsolete_path = run_dir / obsolete_name
        if obsolete_path.exists():
            obsolete_path.unlink()

    manifest = {
        "run_id": run_id,
        "task_id": task_id,
        "mode": "dry_run",
        "submission_files": [
            "trace_manifest.json",
            "scientific_chain.jsonl",
            "execution_subchains.jsonl",
            "artifacts.jsonl",
            "final_claims.json",
            "final_report.md",
        ],
        "workspace_dir": "workspace",
        "workspace_subdirs": list(WORKSPACE_SUBDIRS),
    }
    scores = {
        "task_id": task_id,
        "score": None,
        "passed": None,
        "grader": "dry_run",
        "errors": [],
    }
    study_framing = {
        "scientific_unit_id": "S00",
        "parent_units": [],
        "data_summary": {
            "organism": None,
            "tissue": None,
            "data_types": [],
            "sample_count": None,
            "spatial_unit_count": None,
            "sample_structure": [],
            "grouping_variables": [],
            "metadata_available": [],
            "notes": ["Dry-run smoke test; no input dataset is analyzed."],
        },
    }
    # Smoke-test records exercise the output contract without scientific analysis.
    scientific_unit = {
        "scientific_unit_id": "S01",
        "parent_units": [],
        "hypothesis": "Dry-run submission can create required files without scientific analysis.",
        "experiment": {
            "summary": "Dry-run writer creates required contract files and placeholder log.",
            "execution_subchain_ids": ["E01"],
        },
        "result": {
            "observations": [
                {
                    "observation": "The dry-run writer created a placeholder log artifact.",
                    "support": "workspace/logs/dry_run_smoke_test.txt",
                    "interpretation": "The artifact supports contract smoke testing only.",
                }
            ]
        },
        "conclusion": {
            "summary": "Smoke submission exercises output contract only."
        },
        "next_hypothesis": None,
    }
    execution_subchain = {
        "execution_subchain_id": "E01",
        "linked_scientific_unit_id": "S01",
        "steps": [
            {
                "step_id": "E01.1",
                "inputs": [],
                "call": "create_dry_run_submission_files",
                "parameters": {"mode": "dry_run"},
                "outputs": [
                    {
                        "id": "dry_run_log_object",
                        "object_content": (
                            "placeholder log file stating that no scientific "
                            "analysis was executed"
                        ),
                        "format": "text",
                    }
                ],
                "source_ref": {
                    "type": "workspace_log",
                    "locator": "workspace/logs/dry_run_smoke_test.txt",
                },
            }
        ],
        "result_extraction": {
            "observations": [
                {
                    "observation": "The dry-run writer created a placeholder log artifact.",
                    "support": "workspace/logs/dry_run_smoke_test.txt",
                    "interpretation": "The route supports the linked smoke-test observation only.",
                }
            ]
        },
    }
    artifact = {
        "artifact_id": "A00",
        "artifact_type": "log",
        "path": "workspace/logs/dry_run_smoke_test.txt",
        "created_by": "E01.1",
        "derived_from": ["dry_run_log_object"],
        "checksum": None,
        "summary": "Dry-run placeholder artifact.",
        "validation_status": "exists_and_readable",
    }

    _write_json(submission_dir / "trace_manifest.json", manifest)
    _write_json(run_dir / "scores.json", scores)
    (submission_dir / "scientific_chain.jsonl").write_text(
        json.dumps(study_framing, sort_keys=True) + "\n"
        + json.dumps(scientific_unit, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (submission_dir / "execution_subchains.jsonl").write_text(
        json.dumps(execution_subchain, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (submission_dir / "artifacts.jsonl").write_text(
        json.dumps(artifact, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_json(submission_dir / "final_claims.json", {"claims": []})
    (submission_dir / "final_report.md").write_text(
        "# Dry-run placeholder\n\nNo scientific analysis was executed.\n",
        encoding="utf-8",
    )
    (workspace_dir / "logs" / "dry_run_smoke_test.txt").write_text(
        "Dry-run placeholder artifact. No scientific analysis was executed.\n",
        encoding="utf-8",
    )
    (run_dir / "summary.csv").write_text(
        f"run_id,task_id,score,passed\n{run_id},{task_id},,\n",
        encoding="utf-8",
    )
    (logs_dir / "stdout.txt").write_text("", encoding="utf-8")
    (logs_dir / "stderr.txt").write_text("", encoding="utf-8")
    return run_dir


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
