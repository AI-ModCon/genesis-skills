#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: fetch_results.sh --manifest <absolute-path>

Fetch output.jsonl, the .done marker, generation logs, and any Slurm sbatch/srun logs found for the job.
EOF
}

manifest=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      manifest="$2"
      shift 2
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
results_dir="$(json_get "${manifest}" results_dir)"
remote_output_dir="$(json_get "${manifest}" remote_output_dir)"
remote_result_file="$(json_get "${manifest}" remote_result_file)"
remote_done_file="$(json_get "${manifest}" remote_done_file)"
job_id="$(json_get "${manifest}" job_id)"
nersc_job_dir="$(json_get "${manifest}" nersc_job_dir)"

mkdir -p "${results_dir}" "${results_dir}/job-logs"
load_env_file "${env_file}"

scp_from "${remote_result_file}" "${results_dir}/output.jsonl"
if ssh_cmd "test -f '${remote_done_file}'" >/dev/null 2>&1; then
  scp_from "${remote_done_file}" "${results_dir}/output.jsonl.done"
fi

if ssh_cmd "test -d '${remote_output_dir}/generation-logs'" >/dev/null 2>&1; then
  scp -pr $(ssh_options) "${NERSC_USER}@${NERSC_HOST}:${remote_output_dir}/generation-logs" "${results_dir}/"
fi

if [[ -n "${job_id}" ]]; then
  remote_logs="$(ssh_cmd "find '${nersc_job_dir}' -type f \\( -name '*${job_id}_sbatch.log' -o -name '*${job_id}_srun.log' \\) -print" || true)"
  while IFS= read -r remote_log; do
    [[ -n "${remote_log}" ]] || continue
    scp_from "${remote_log}" "${results_dir}/job-logs/$(basename "${remote_log}")"
  done <<< "${remote_logs}"
fi

input_local_path="$(json_get "${manifest}" input_local_path)"
if [[ -f "${input_local_path}" && -f "${results_dir}/output.jsonl" ]]; then
  input_count="$(wc -l < "${input_local_path}")"
  output_count="$(wc -l < "${results_dir}/output.jsonl")"
  if [[ "${output_count}" -lt "${input_count}" ]]; then
    note "WARNING: output.jsonl has ${output_count} record(s) but input.jsonl has ${input_count}; generation may be incomplete"
  fi
fi

update_manifest \
  "${manifest}" \
  fetched_at "\"$(now_utc)\"" \
  local_output_path "\"${results_dir}/output.jsonl\"" \
  local_done_path "\"${results_dir}/output.jsonl.done\"" \
  local_logs_dir "\"${results_dir}\"" \
  status "\"fetched\""

note "Fetched results into ${results_dir}"
