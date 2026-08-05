#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: submit_run.sh --manifest <absolute-path>

Execute the rendered run.sh locally, capture submission output, and update the manifest.
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

submission_log="$(json_get "${manifest}" submission_log)"
expname="$(json_get "${manifest}" expname)"
mkdir -p "$(dirname "${submission_log}")"

# Use prepare_script_path if present (split-phase eval layout); fall back to run_script_path.
run_script="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('prepare_script_path') or d['run_script_path'])" "${manifest}")"

bash "${run_script}" 2>&1 | tee "${submission_log}"

# Collapse job IDs to a single space-separated string (no newlines in JSON field).
slurm_job_id="$(grep -o 'slurm_tunnel://nemo_run/[0-9]*' "${submission_log}" | grep -o '[0-9]*$' | tr '\n' ' ' | sed 's/ $//' || true)"

update_manifest "${manifest}" submitted_at "\"$(now_utc)\"" status "\"submitted\"" submission_log "\"${submission_log}\"" expname "\"${expname}\""
if [[ -n "${slurm_job_id}" ]]; then
  update_manifest "${manifest}" job_id "\"${slurm_job_id}\""
  note "Submitted run ${expname} (job ${slurm_job_id})"
else
  note "Submitted run ${expname}"
fi
