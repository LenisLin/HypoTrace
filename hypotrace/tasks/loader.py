"""Smoke-fixture task loader for the initial HypoTrace skeleton.

This loader validates the legacy JSON toy task shape used by examples/toy_task.
It is not the future Git task registry and NAS bundle resolver.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TaskValidationError(ValueError):
    """Raised when a smoke-fixture task directory violates the current loader contract."""


# Kept for examples/toy_task and tests until registry loading is designed.
REQUIRED_TASK_FILES = (
    "task_prompt.md",
    "data_manifest.json",
    "reference_scientific_chain.json",
    "reference_execution_chain.json",
    "reference_claim_surface.json",
    "curation_notes.md",
)


@dataclass(frozen=True)
class TaskSpec:
    id: str
    root: Path
    prompt_path: Path
    data_manifest: dict[str, Any]
    reference_scientific_chain: dict[str, Any]
    reference_execution_chain: dict[str, Any]
    reference_claim_surface: dict[str, Any]
    curation_notes_path: Path


def load_task(task_root: Path) -> TaskSpec:
    root = Path(task_root).resolve()
    for filename in REQUIRED_TASK_FILES:
        if not (root / filename).is_file():
            raise TaskValidationError(f"{filename} is required")

    prompt_path = root / "task_prompt.md"
    data_manifest = _read_json(root / "data_manifest.json")
    reference_scientific_chain = _read_json(root / "reference_scientific_chain.json")
    reference_execution_chain = _read_json(root / "reference_execution_chain.json")
    reference_claim_surface = _read_json(root / "reference_claim_surface.json")

    _require_fields(data_manifest, "data_manifest.json", ("task_id", "modality", "data_files"))
    if not data_manifest["data_files"]:
        raise TaskValidationError("data_manifest.json data_files must not be empty")
    _require_fields(
        reference_scientific_chain,
        "reference_scientific_chain.json",
        ("reference_units",),
    )
    _require_fields(
        reference_execution_chain,
        "reference_execution_chain.json",
        ("reference_execution_units",),
    )
    _require_fields(reference_claim_surface, "reference_claim_surface.json", ("reference_claims",))

    return TaskSpec(
        id=str(data_manifest["task_id"]),
        root=root,
        prompt_path=prompt_path,
        data_manifest=data_manifest,
        reference_scientific_chain=reference_scientific_chain,
        reference_execution_chain=reference_execution_chain,
        reference_claim_surface=reference_claim_surface,
        curation_notes_path=root / "curation_notes.md",
    )


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TaskValidationError(f"{path.name} must contain a JSON object")
    return data


def _require_fields(data: dict[str, Any], filename: str, fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise TaskValidationError(f"{filename} missing required fields: {', '.join(missing)}")
