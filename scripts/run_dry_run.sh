#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${HYPOTRACE_DATA_ROOT:-/mnt/NAS_21T/ProjectData/HypoTrace_Data}"
RUN_ID="${1:?run id required}"
TASK_ID="${2:?task id required}"

python -m hypotrace.cli dry-run --data-root "$DATA_ROOT" --run-id "$RUN_ID" --task-id "$TASK_ID"
