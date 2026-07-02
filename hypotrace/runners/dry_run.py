"""Dry-run output contract writer."""

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
    scientific_unit = {
        "scientific_unit_id": "S00",
        "unit_type": "dry_run_placeholder",
        "parent_units": [],
        "question_or_hypothesis": "Dry-run placeholder; no scientific claim is evaluated.",
        "evidence_need": [],
        "method_intent": [],
        "execution_subchain_ids": ["E00"],
        "result": {
            "computational_observation": "No computation was run.",
            "key_artifacts": ["A00"],
        },
        "conclusion": {
            "biological_inference": "No biological inference is made.",
            "scope": "schema smoke test",
            "not_claimed": ["scientific validity", "task completion"],
        },
        "next_question": None,
    }
    execution_subchain = {
        "execution_subchain_id": "E00",
        "linked_scientific_unit_id": "S00",
        "stage_question": "Dry-run placeholder.",
        "execution_goal": "Create required submission files without running analysis.",
        "steps": [],
        "result_extraction": {"summary": "No result extracted.", "key_numbers": {}},
    }
    artifact = {
        "artifact_id": "A00",
        "artifact_type": "log",
        "path": "workspace/logs/dry_run_placeholder.txt",
        "created_by": "E00",
        "derived_from": [],
        "checksum": None,
        "summary": "Dry-run placeholder artifact.",
        "validation_status": "exists_and_readable",
    }

    _write_json(submission_dir / "trace_manifest.json", manifest)
    _write_json(run_dir / "scores.json", scores)
    (submission_dir / "scientific_chain.jsonl").write_text(
        json.dumps(scientific_unit, sort_keys=True) + "\n",
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
    (workspace_dir / "logs" / "dry_run_placeholder.txt").write_text(
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
