"""Minimal command line entrypoint for the initial skeleton."""

from __future__ import annotations

import argparse
from pathlib import Path

from hypotrace.datasets.paths import DataPaths
from hypotrace.runners.dry_run import create_dry_run
from hypotrace.tasks.loader import load_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hypotrace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_data = subparsers.add_parser("init-data", help="Create data root subdirectories.")
    init_data.add_argument("--data-root", default="/mnt/NAS_21T/ProjectData/HypoTrace_Data")

    validate_task = subparsers.add_parser(
        "validate-task",
        help="Validate the current smoke-fixture task contract.",
    )
    validate_task.add_argument("task_root")

    dry_run = subparsers.add_parser("dry-run", help="Create a dry-run output contract.")
    dry_run.add_argument("--data-root", default="/mnt/NAS_21T/ProjectData/HypoTrace_Data")
    dry_run.add_argument("--run-id", required=True)
    dry_run.add_argument("--task-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init-data":
        DataPaths(Path(args.data_root)).ensure()
        return 0
    if args.command == "validate-task":
        load_task(Path(args.task_root))
        return 0
    if args.command == "dry-run":
        create_dry_run(Path(args.data_root), run_id=args.run_id, task_id=args.task_id)
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
