import json
from pathlib import Path

import jsonschema

from hypotrace.runners.dry_run import create_dry_run


WORKSPACE_SUBDIRS = ("scripts", "notebooks", "figures", "tables", "logs")
SUBMISSION_FILES = [
    "trace_manifest.json",
    "scientific_chain.jsonl",
    "execution_subchains.jsonl",
    "artifacts.jsonl",
    "final_claims.json",
    "final_report.md",
]


def test_create_dry_run_writes_smoke_test_submission_contract(tmp_path: Path) -> None:
    run_dir = create_dry_run(tmp_path, run_id="run-001", task_id="toy_task")

    assert run_dir == tmp_path / "runs" / "run-001"
    assert (run_dir / "artifacts").is_dir()
    for subdir in WORKSPACE_SUBDIRS:
        assert (run_dir / "submission" / "workspace" / subdir).is_dir()
    assert (run_dir / "logs" / "stdout.txt").read_text(encoding="utf-8") == ""
    assert (run_dir / "logs" / "stderr.txt").read_text(encoding="utf-8") == ""

    manifest = json.loads((run_dir / "submission" / "trace_manifest.json").read_text(encoding="utf-8"))
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
    scientific_chain = (run_dir / "submission" / "scientific_chain.jsonl").read_text(
        encoding="utf-8"
    ).strip()
    execution_subchains = (run_dir / "submission" / "execution_subchains.jsonl").read_text(
        encoding="utf-8"
    ).strip()
    artifacts = (run_dir / "submission" / "artifacts.jsonl").read_text(encoding="utf-8").strip()
    final_claims = json.loads((run_dir / "submission" / "final_claims.json").read_text(encoding="utf-8"))
    final_report = (run_dir / "submission" / "final_report.md").read_text(encoding="utf-8")
    summary = (run_dir / "summary.csv").read_text(encoding="utf-8").strip()

    assert manifest["run_id"] == "run-001"
    assert manifest["task_id"] == "toy_task"
    assert manifest["mode"] == "dry_run"
    assert manifest["submission_files"] == SUBMISSION_FILES
    assert manifest["workspace_subdirs"] == list(WORKSPACE_SUBDIRS)
    assert scores == {
        "task_id": "toy_task",
        "score": None,
        "passed": None,
        "grader": "dry_run",
        "errors": [],
    }
    scientific_records = [json.loads(line) for line in scientific_chain.splitlines()]
    execution_records = [json.loads(line) for line in execution_subchains.splitlines()]
    assert "sample_structure" in scientific_records[0]["data_summary"]
    assert scientific_records[1]["experiment"]["execution_subchain_ids"] == ["E01"]
    assert scientific_records[1]["result"]["observations"][0]
    assert execution_records[0]["execution_subchain_id"] == "E01"
    assert execution_records[0]["steps"][0]["step_id"] == "E01.1"
    assert execution_records[0]["result_extraction"]["observations"][0]
    artifact = json.loads(artifacts)
    assert artifact["artifact_id"] == "A00"
    assert artifact["path"] == "workspace/logs/dry_run_smoke_test.txt"
    assert artifact["created_by"] == "E01.1"
    assert (run_dir / "submission" / artifact["path"]).is_file()
    assert final_claims == {"claims": []}
    assert "Dry-run placeholder" in final_report
    assert summary == "run_id,task_id,score,passed\nrun-001,toy_task,,"

    _validate_jsonl(scientific_records, Path("contracts/schemas/scientific_chain.schema.json"))
    _validate_jsonl(execution_records, Path("contracts/schemas/execution_subchains.schema.json"))
    _validate_jsonl([artifact], Path("contracts/schemas/artifacts.schema.json"))
    _validate_json(final_claims, Path("contracts/schemas/final_claims.schema.json"))


def test_create_dry_run_removes_obsolete_root_level_trace_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-001"
    run_dir.mkdir(parents=True)
    for filename in ["manifest.json", "trajectory.jsonl"]:
        (run_dir / filename).write_text("legacy", encoding="utf-8")

    create_dry_run(tmp_path, run_id="run-001", task_id="toy_task")

    assert not (run_dir / "manifest.json").exists()
    assert not (run_dir / "trajectory.jsonl").exists()


def _validate_json(payload: object, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


def _validate_jsonl(records: list[object], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for record in records:
        jsonschema.validate(record, schema)
