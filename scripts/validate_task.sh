#!/usr/bin/env bash
set -euo pipefail

# Validates the current examples/toy_task-style smoke fixture, not the future
# Git task registry + NAS bundle contract.
python -m hypotrace.cli validate-task "${1:?task root required}"
