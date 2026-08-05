#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: fetch_results.sh --manifest <absolute-path>

Fetch the full eval output directory, the eval.done marker, and any Slurm sbatch/srun logs.
For ns eval: downloads eval-results/{benchmark}/metrics.json and output*.jsonl.
For ns robust_eval: downloads the entire nested output tree including summarize_robustness/.
EOF
}

manifest=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) manifest="$2"; shift 2 ;;
    -h|--help)  usage; exit 0 ;;
    *)          die "Unknown argument: $1" ;;
  esac
done

[[ -n "${manifest}" ]] || die "Missing required argument: --manifest"
manifest="$(cd "$(dirname "${manifest}")" && pwd)/$(basename "${manifest}")"
require_file "${manifest}"

env_file="$(json_get "${manifest}" env_file)"
results_dir="$(json_get "${manifest}" results_dir)"
remote_output_dir="$(json_get "${manifest}" remote_output_dir)"
remote_done_file="$(json_get "${manifest}" remote_done_file)"
job_id="$(json_get "${manifest}" job_id)"
nersc_job_dir="$(json_get "${manifest}" nersc_job_dir)"
benchmark="$(json_get "${manifest}" benchmark)"
job_type="$(json_get "${manifest}" job_type)"

mkdir -p "${results_dir}" "${results_dir}/job-logs"
load_env_file "${env_file}"

local_eval_output="${results_dir}/eval-output"
mkdir -p "${local_eval_output}"

# Download the full eval output directory recursively
if ssh_cmd "test -d '${remote_output_dir}'" >/dev/null 2>&1; then
  scp -pr $(ssh_options) "${NERSC_USER}@${NERSC_HOST}:${remote_output_dir}/." "${local_eval_output}/"
else
  note "WARNING: remote output directory not found: ${remote_output_dir}"
fi

local_done_path="${results_dir}/eval.done"
if ssh_cmd "test -f '${remote_done_file}'" >/dev/null 2>&1; then
  scp_from "${remote_done_file}" "${local_done_path}"
fi

# Download Slurm job logs
if [[ -n "${job_id}" && "${job_id}" != "null" ]]; then
  remote_logs="$(ssh_cmd "find '${nersc_job_dir}' -type f \\( -name '*${job_id}_sbatch.log' -o -name '*${job_id}_srun.log' \\) -print" || true)"
  while IFS= read -r remote_log; do
    [[ -n "${remote_log}" ]] || continue
    scp_from "${remote_log}" "${results_dir}/job-logs/$(basename "${remote_log}")"
  done <<< "${remote_logs}"
fi

# Find the primary metrics.json to surface in the manifest
local_metrics_path=""
if [[ "${job_type}" == "robust_eval" ]]; then
  # Robust eval: look for aggregated summary first, then any metrics.json
  if [[ -d "${local_eval_output}/summarize_robustness" ]]; then
    local_metrics_path="${local_eval_output}/summarize_robustness"
  else
    local_metrics_path="$(find "${local_eval_output}" -name 'metrics.json' | head -1 || true)"
  fi
else
  local_metrics_path="$(find "${local_eval_output}" -path "*/${benchmark}/metrics.json" | head -1 || true)"
  if [[ -z "${local_metrics_path}" ]]; then
    local_metrics_path="$(find "${local_eval_output}" -name 'metrics.json' | head -1 || true)"
  fi
fi

update_manifest \
  "${manifest}" \
  fetched_at "\"$(now_utc)\"" \
  local_results_dir "\"${local_eval_output}\"" \
  local_done_path "\"${local_done_path}\"" \
  local_metrics_path "\"${local_metrics_path}\"" \
  local_logs_dir "\"${results_dir}\"" \
  status "\"fetched\""

note "Fetched results into ${results_dir}"
if [[ -n "${local_metrics_path}" ]]; then
  note "Primary metrics: ${local_metrics_path}"
fi
