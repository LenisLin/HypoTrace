#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_root="${HYPOTRACE_DATA_ROOT:-/mnt/NAS_21T/ProjectData/HypoTrace_Data}"
workers="${STOMICSDB_AUX_DOWNLOAD_WORKERS:-4}"
python_bin="${PYTHON_BIN:-python}"
output_root="${STOMICSDB_AUX_OUTPUT_ROOT:-${data_root}/raw_data/public_database/stomicsdb/staging/round3_auxiliary_downloads}"
worker="${repo_root}/scripts/stomicsdb_round3_auxiliary_download.py"

"${python_bin}" "${worker}" \
  --data-root "${data_root}" \
  --output-root "${output_root}" \
  --workers "${workers}" \
  "$@" \
  --dry-run

mkdir -p "${output_root}/locks" "${output_root}/runs"
lock_path="${output_root}/locks/downloader.lock"
exec {lock_fd}>"${lock_path}"
if ! flock -n "${lock_fd}"; then
  printf 'Round 3 auxiliary download is already running; lock=%s\n' "${lock_path}" >&2
  exit 1
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_id="round3_auxiliary_${stamp}_pid$$"
run_dir="${output_root}/runs/${run_id}"
mkdir -p "${run_dir}"
log_path="${run_dir}/run.jsonl"
pid_path="${run_dir}/run.pid"

setsid "${python_bin}" "${worker}" \
  --data-root "${data_root}" \
  --output-root "${output_root}" \
  --run-id "${run_id}" \
  --workers "${workers}" \
  "$@" \
  </dev/null >"${log_path}" 2>&1 &
pid=$!
printf '%s\n' "${pid}" >"${pid_path}"
printf 'started pid=%s log=%s inventory=%s\n' \
  "${pid}" "${log_path}" "${run_dir}/inventory.json"
