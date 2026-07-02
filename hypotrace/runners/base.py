"""Base runner adapter contract."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class BaseAgentAdapter(Protocol):
    """Adapter interface for model-harness execution.

    Implementations prepare sandboxes, launch harnesses, collect passive logs,
    and collect submissions. They must not provide active HypoTrace repair
    feedback or auto-fill scientific chains.
    """

    name: str

    def prepare(self, run_dir: Path, task_package: Path, condition_config: dict[str, object]) -> None:
        """Create workspace, copy agent-visible inputs, and inject condition files."""

    def run(self, run_dir: Path, model_config: dict[str, object], budget_config: dict[str, object]) -> int:
        """Launch the harness without active feedback to the agent."""

    def collect(self, run_dir: Path) -> None:
        """Collect final submission and passive logs after the harness exits."""

    def summarize(self, run_dir: Path) -> dict[str, object]:
        """Return a structured run record for downstream evaluation."""
