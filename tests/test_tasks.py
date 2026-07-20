import json
from pathlib import Path

import pytest

from hypotrace.tasks.loader import TaskValidationError, load_task


def write_task(root: Path, *, missing_file: str | None = None) -> None:
    root.mkdir()
    files = {
        "task_prompt.md": "Use the provided synthetic data to produce a HypoTrace submission.",
        "data_manifest.json": """
{
  "task_id": "toy_task",
  "modality": ["table"],
  "organism": "synthetic",
  "data_files": [
    {
      "path": "data/input.csv",
      "type": "CSV",
      "raw_or_processed": "prepared",
      "checksum": "sha256:placeholder"
    }
  ],
  "metadata_columns": ["sample_id", "group"]
}
""".lstrip(),
        "reference_scientific_chain.json": """
{
  "reference_units": [
    {
      "unit_id": "RS01",
      "hypothesis": "The synthetic group difference can be described from the table.",
      "required_evidence": ["group summary table"],
      "acceptable_method_families": ["descriptive statistics"]
    }
  ]
}
""".lstrip(),
        "reference_execution_chain.json": json.dumps(
            {
                "reference_execution_units": [
                    {
                        "unit_id": "RE01",
                        "method" + "_family": "descriptive_statistics",
                        "original_method": "group summary",
                        "acceptable_alternatives": ["summary table"],
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        "reference_claim_surface.json": """
{
  "reference_claims": [
    {
      "claim_id": "RC01",
      "claim_text": "The synthetic table can support a descriptive group comparison.",
      "required_evidence_types": ["summary table"],
      "acceptable_alternative_claims": ["The data support a descriptive comparison."],
      "forbidden_overclaims": ["causal claim"]
    }
  ]
}
""".lstrip(),
        "curation_notes.md": "# Curation Notes\n\nSchema smoke test only.\n",
    }
    for filename, content in files.items():
        if filename != missing_file:
            (root / filename).write_text(content, encoding="utf-8")


def write_legacy_task(root: Path) -> None:
    root.mkdir()
    (root / "task.yaml").write_text(
        """
id: toy_task
domain: synthetic
modality: table
input_refs:
  - raw/toy/input.csv
expected_outputs:
  - filename: answer.csv
    media_type: text/csv
scorer: exact_file
resource_limits:
  walltime_minutes: 5
  cpus: 1
  memory_gb: 1
leakage_controls:
  agent_visible:
    - prompt.md
  agent_hidden:
    - grader.yaml
    - reference/
""".lstrip(),
        encoding="utf-8",
    )
    (root / "prompt.md").write_text("Return the expected CSV.", encoding="utf-8")
    (root / "grader.yaml").write_text("method: exact_file\n", encoding="utf-8")


def test_load_task_accepts_valid_task_contract(tmp_path: Path) -> None:
    task_root = tmp_path / "toy_task"
    write_task(task_root)

    task = load_task(task_root)

    assert task.id == "toy_task"
    assert task.prompt_path.name == "task_prompt.md"
    assert task.data_manifest["modality"] == ["table"]
    assert task.reference_scientific_chain["reference_units"][0]["unit_id"] == "RS01"
    assert task.reference_claim_surface["reference_claims"][0]["claim_id"] == "RC01"


@pytest.mark.parametrize(
    "missing_file",
    [
        "task_prompt.md",
        "data_manifest.json",
        "reference_scientific_chain.json",
        "reference_execution_chain.json",
        "reference_claim_surface.json",
        "curation_notes.md",
    ],
)
def test_load_task_rejects_missing_contract_files(tmp_path: Path, missing_file: str) -> None:
    task_root = tmp_path / "toy_task"
    write_task(task_root, missing_file=missing_file)

    with pytest.raises(TaskValidationError, match=missing_file):
        load_task(task_root)


def test_load_task_does_not_require_evaluator_config_inside_task_package(tmp_path: Path) -> None:
    task_root = tmp_path / "toy_task"
    write_task(task_root)

    task = load_task(task_root)

    assert not (task_root / "grader.yaml").exists()
    assert task.id == "toy_task"


def test_load_task_rejects_legacy_grader_mixed_task_package(tmp_path: Path) -> None:
    task_root = tmp_path / "legacy_task"
    write_legacy_task(task_root)

    with pytest.raises(TaskValidationError, match="task_prompt.md"):
        load_task(task_root)
