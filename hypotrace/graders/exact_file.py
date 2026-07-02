"""Minimal file-presence grader used by the skeleton contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hypotrace.graders.base import GradeResult


@dataclass(frozen=True)
class ExactFileGrader:
    task_id: str
    required_files: list[str]

    def grade(self, artifacts_dir: Path) -> GradeResult:
        root = Path(artifacts_dir)
        errors = [
            f"missing required file: {relative_path}"
            for relative_path in self.required_files
            if not (root / relative_path).is_file()
        ]
        if errors:
            return GradeResult(
                task_id=self.task_id,
                score=0.0,
                passed=False,
                grader="exact_file",
                errors=errors,
            )
        return GradeResult(
            task_id=self.task_id,
            score=1.0,
            passed=True,
            grader="exact_file",
        )
