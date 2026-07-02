"""Filesystem contracts for HypoTrace data roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DATA_SUBDIRECTORIES = (
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
)


@dataclass(frozen=True)
class DataPaths:
    """Resolve and create NAS-backed data subdirectories."""

    root: Path
    repo_root: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).expanduser().resolve())
        if self.repo_root is not None:
            object.__setattr__(self, "repo_root", Path(self.repo_root).expanduser().resolve())

    def ensure(self) -> list[Path]:
        self._validate_data_root()
        self.root.mkdir(parents=True, exist_ok=True)
        created: list[Path] = []
        for name in DATA_SUBDIRECTORIES:
            path = self.root / name
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
        return created

    def subdir(self, name: str) -> Path:
        if name not in DATA_SUBDIRECTORIES:
            raise KeyError(f"unknown data subdirectory: {name}")
        return self.root / name

    def _validate_data_root(self) -> None:
        if self.repo_root is None:
            return
        try:
            self.root.relative_to(self.repo_root)
        except ValueError:
            return
        raise ValueError("data root must be outside the repository")
