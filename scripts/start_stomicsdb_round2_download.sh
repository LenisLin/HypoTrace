#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_root="${HYPOTRACE_DATA_ROOT:-/mnt/NAS_21T/ProjectData/HypoTrace_Data}"
plan="${STOMICSDB_ACQUISITION_PLAN:-${data_root}/raw_data/public_database/stomicsdb/registry/acquisition_plan.tsv}"
workers="${STOMICSDB_DOWNLOAD_WORKERS:-4}"
python_bin="${PYTHON_BIN:-python}"
log_dir="${STOMICSDB_DOWNLOAD_LOG_DIR:-${data_root}/logs}"
downloader="${repo_root}/scripts/stomicsdb_round2_download.py"

"${python_bin}" "${downloader}" \
  --plan "${plan}" \
  --data-root "${data_root}" \
  --workers "${workers}" \
  "$@" \
  --validate-only

mkdir -p "${log_dir}"
plan_canonical="$(readlink -f -- "${plan}")"
plan_key="$(printf '%s' "${plan_canonical}" | sha256sum | awk '{print $1}')"
lock_path="${log_dir}/stomicsdb_round2a_${plan_key}.lock"
exec {lock_fd}>"${lock_path}"
if ! flock -n "${lock_fd}"; then
  printf 'download already running for plan=%s lock=%s\n' "${plan_canonical}" "${lock_path}" >&2
  exit 1
fi

stamp="$(date -u +%Y%m%dT%H%M%S%NZ)"
log_path="${log_dir}/stomicsdb_round2a_${stamp}.jsonl"
pid_path="${log_dir}/stomicsdb_round2a_${stamp}.pid"

setsid "${python_bin}" "${downloader}" \
  --plan "${plan}" \
  --data-root "${data_root}" \
  --workers "${workers}" \
  "$@" \
  </dev/null >"${log_path}" 2>&1 &
pid=$!
printf '%s\n' "${pid}" >"${pid_path}"
printf 'started pid=%s log=%s pid_file=%s\n' "${pid}" "${log_path}" "${pid_path}"
