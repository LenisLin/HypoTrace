"""Stable grader result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GradeResult:
    task_id: str
    score: float | None
    passed: bool | None
    grader: str
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "score": self.score,
            "passed": self.passed,
            "grader": self.grader,
            "errors": list(self.errors),
        }
