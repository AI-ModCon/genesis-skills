#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: check_status.sh --manifest <absolute-path> [--wait]

Poll Slurm for the run expname, fall back to sacct, and only report success when metrics.json exists.
Fallback: if metrics.json is absent but found anywhere under remote_output_dir (maxdepth 4), treat as complete.
With --wait, exits with failure if the job does not complete within 2x DEFAULT_TIMEOUT.
EOF
}

manifest=""
wait_mode=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) manifest="$2"; shift 2 ;;
    --wait)     wait_mode=1;   shift   ;;
    -h|--help)  usage; exit 0 ;;
    *)          die "Unknown argument: $1" ;;
  esac
done

[[ -n "${manifest}" ]] || die "Missing required argument: --manifest"
manifest="$(cd "$(dirname "${manifest}")" && pwd)/$(basename "${manifest}")"
require_file "${manifest}"

env_file="$(json_get "${manifest}" env_file)"
expname="$(json_get "${manifest}" expname)"
job_type="$(json_get "${manifest}" job_type)"
remote_done_file="$(json_get "${manifest}" remote_done_file)"
remote_output_dir="$(json_get "${manifest}" remote_output_dir)"
submission_log="$(json_get "${manifest}" submission_log)"
load_env_file "${env_file}"

timeout_to_seconds() {
  local t="$1"
  local h m s
  IFS=: read -r h m s <<<"${t}"
  echo $(( 10#${h} * 3600 + 10#${m} * 60 + 10#${s} ))
}

# Split-phase: run eval.sh (data-wait + ns eval/robust_eval) before polling for metrics.
# Mark eval_submitted=true BEFORE running to prevent double-submission on restart.
eval_script="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('eval_script_path',''))" "${manifest}")"
eval_submitted="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(str(d.get('eval_submitted',True)).lower())" "${manifest}")"

if [[ "${wait_mode}" -eq 1 && -n "${eval_script}" && -f "${eval_script}" && "${eval_submitted}" == "false" ]]; then
  # Wait for the prepare_data Slurm job to complete (or fail fast) before running eval.sh.
  prepare_job_id="$(json_get "${manifest}" job_id)"
  if [[ -n "${prepare_job_id}" && "${prepare_job_id}" != "null" ]]; then
    note "Waiting for prepare_data job ${prepare_job_id} ..."
    while :; do
      _sacct="$(ssh_cmd "sacct -X -n -j '${prepare_job_id}' -o State --delimiter='|' 2>/dev/null | head -1" || true)"
      _pstate="${_sacct%%|*}"
      _pstate="${_pstate// /}"
      _pstate="${_pstate%%+}"
      case "${_pstate}" in
        COMPLETED) note "prepare_data job ${prepare_job_id} COMPLETED"; break ;;
        FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|BOOT_FAIL|DEADLINE)
          die "prepare_data job ${prepare_job_id} failed with state: ${_pstate}" ;;
        *) note "prepare_data: ${_pstate:-PENDING} (job ${prepare_job_id})"; sleep "${STATUS_POLL_INTERVAL}" ;;
      esac
    done
  fi

  update_manifest "${manifest}" eval_submitted "true"
  note "Running eval.sh (ns eval/robust_eval submission) ..."
  eval_tmp="$(mktemp)"
  bash "${eval_script}" 2>&1 | tee -a "${submission_log}" | tee "${eval_tmp}"
  new_ids="$(grep -o 'slurm_tunnel://nemo_run/[0-9]*' "${eval_tmp}" | grep -o '[0-9]*$' | sort -u | tr '\n' ' ' | sed 's/ $//' || true)"
  rm -f "${eval_tmp}"
  [[ -n "${new_ids}" ]] && update_manifest "${manifest}" job_id "\"${new_ids}\""
  note "Eval jobs submitted: ${new_ids:-none}"
fi

# Reset timeout clock after eval submission — queue wait + job runtime is what we budget here.
max_wait_seconds=$(( $(timeout_to_seconds "${DEFAULT_TIMEOUT}") * 4 ))
start_ts=$(date +%s)
_poll_count=0

terminal_failure() {
  case "$1" in
    FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|BOOT_FAIL|DEADLINE)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

while :; do
  # Use prefix match: ns robust_eval names jobs like expname_prompt_variant-benchmark.
  squeue_line="$(ssh_cmd "squeue -h -u '${NERSC_USER}' -o '%A|%j|%T' | awk -F'|' -v pfx='${expname}' 'index(\$2,pfx)==1{print;exit}'" || true)"
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
  if [[ "${job_type}" == "robust_eval" ]]; then
    if ssh_cmd "find '${remote_output_dir}' -name 'metrics.json' -maxdepth 6 -type f | head -1 | grep -q ." >/dev/null 2>&1; then
      result_ready=true
      job_state="COMPLETED"
    fi
  else
    if ssh_cmd "test -f '${remote_done_file}'" >/dev/null 2>&1; then
      result_ready=true
      job_state="COMPLETED"
    elif ssh_cmd "find '${remote_output_dir}' -name 'metrics.json' -maxdepth 6 -type f | head -1 | grep -q ." >/dev/null 2>&1; then
      result_ready=true
      job_state="COMPLETED"
      note "WARNING: eval.done absent but metrics.json found — treating as complete"
    fi
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

  (( _poll_count += 1 )) || true
  if   [[ "${_poll_count}" -le 3 ]]; then sleep 5
  elif [[ "${_poll_count}" -le 7 ]]; then sleep 15
  else sleep "${STATUS_POLL_INTERVAL}"
  fi
done
