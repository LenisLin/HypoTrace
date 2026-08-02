from pathlib import Path

from hypotrace.graders.base import GradeResult
from hypotrace.graders.exact_file import ExactFileGrader


def test_grade_result_serializes_stable_json_contract() -> None:
    result = GradeResult(task_id="unit_task", score=1.0, passed=True, grader="unit")

    assert result.to_dict() == {
        "task_id": "unit_task",
        "score": 1.0,
        "passed": True,
        "grader": "unit",
        "errors": [],
    }


def test_exact_file_grader_reports_missing_required_file(tmp_path: Path) -> None:
    grader = ExactFileGrader(task_id="unit_task", required_files=["answer.csv"])

    result = grader.grade(tmp_path)

    assert result.to_dict() == {
        "task_id": "unit_task",
        "score": 0.0,
        "passed": False,
        "grader": "exact_file",
        "errors": ["missing required file: answer.csv"],
    }
