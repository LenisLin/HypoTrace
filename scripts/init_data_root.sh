#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${1:-/mnt/NAS_21T/ProjectData/HypoTrace_Data}"
python -m hypotrace.cli init-data --data-root "$DATA_ROOT"
