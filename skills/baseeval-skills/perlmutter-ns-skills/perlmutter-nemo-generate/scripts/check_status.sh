#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: check_status.sh --manifest <absolute-path> [--wait]

Poll Slurm for the run expname, fall back to sacct, and only report success when output.jsonl.done exists.
With --wait, exits with failure if the job does not complete within 2x DEFAULT_TIMEOUT.
EOF
}

manifest=""
wait_mode=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      manifest="$2"
      shift 2
      ;;
    --wait)
      wait_mode=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

[[ -n "${manifest}" ]] || die "Missing required argument: --manifest"
manifest="$(cd "$(dirname "${manifest}")" && pwd)/$(basename "${manifest}")"
require_file "${manifest}"

env_file="$(json_get "${manifest}" env_file)"
expname="$(json_get "${manifest}" expname)"
remote_done_file="$(json_get "${manifest}" remote_done_file)"
load_env_file "${env_file}"

# Convert HH:MM:SS to seconds
timeout_to_seconds() {
  local t="$1"
  local h m s
  IFS=: read -r h m s <<<"${t}"
  echo $(( 10#${h} * 3600 + 10#${m} * 60 + 10#${s} ))
}

max_wait_seconds=$(( $(timeout_to_seconds "${DEFAULT_TIMEOUT}") * 2 ))
start_ts=$(date +%s)

terminal_failure() {
  case "$1" in
    FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|BOOT_FAIL|DEADLINE)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

while :; do
  squeue_line="$(ssh_cmd "squeue -h -u '${NERSC_USER}' -o '%A|%j|%T' | awk -F'|' -v target='${expname}' '\$2 == target {print; exit}'" || true)"
  job_id=""
  job_state=""

  if [[ -n "${squeue_line}" ]]; then
    IFS='|' read -r job_id _ job_state <<<"${squeue_line}"
  else
    sacct_line="$(ssh_cmd "sacct -X -n -u '${NERSC_USER}' -o JobIDRaw,JobName,State --delimiter='|' | awk -F'|' -v target='${expname}' '\$2 == target {line=\$0} END {print line}'" || true)"
    if [[ -n "${sacct_line}" ]]; then
      IFS='|' read -r job_id _ job_state <<<"${sacct_line}"
      job_state="${job_state%% *}"
      job_state="${job_state%%+}"
    fi
  fi

  result_ready=false
  if ssh_cmd "test -f '${remote_done_file}'" >/dev/null 2>&1; then
    result_ready=true
    job_state="COMPLETED"
  fi

  if [[ -n "${job_id}" ]]; then
    update_manifest "${manifest}" job_id "\"${job_id}\""
  fi
  update_manifest "${manifest}" last_checked_at "\"$(now_utc)\"" last_status "\"${job_state:-UNKNOWN}\"" result_ready "${result_ready}"

  if [[ "${result_ready}" == true ]]; then
    note "COMPLETED ${expname} ${job_id}"
    exit 0
  fi

  if [[ -n "${job_state}" ]] && terminal_failure "${job_state}"; then
    note "${job_state} ${expname} ${job_id}"
    exit 1
  fi

  if [[ "${wait_mode}" -eq 0 ]]; then
    note "${job_state:-NOT_FOUND} ${expname} ${job_id}"
    exit 0
  fi

  elapsed=$(( $(date +%s) - start_ts ))
  note "Waiting: ${job_state:-UNKNOWN} ${expname} ${job_id:-} (elapsed: ${elapsed}s / max: ${max_wait_seconds}s)"

  if [[ "${elapsed}" -ge "${max_wait_seconds}" ]]; then
    die "Timed out after ${elapsed}s waiting for ${expname} to complete (max_wait=${max_wait_seconds}s)"
  fi

  sleep "${STATUS_POLL_INTERVAL}"
done
