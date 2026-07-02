from pathlib import Path

import pytest

from hypotrace.datasets.paths import DataPaths


def test_data_paths_create_expected_nas_subdirectories(tmp_path: Path) -> None:
    paths = DataPaths(tmp_path)

    created = paths.ensure()

    assert {path.name for path in created} == {
        "raw",
        "prepared",
        "tasks",
        "references",
        "runs",
        "trajectories",
        "results",
        "logs",
        "cache",
        "manifests",
    }
    assert all(path.is_dir() for path in created)


def test_data_paths_reject_repository_root_as_data_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with pytest.raises(ValueError, match="outside the repository"):
        DataPaths(repo_root, repo_root=repo_root).ensure()
