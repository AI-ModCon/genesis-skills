#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: prepare_run.sh --env-file <absolute-path> --input <absolute-jsonl> --prompt <absolute-yaml> --model <model> [--run-id <slug>]

Validate inputs and env vars, then render a run-specific perlmutter.yaml, run.sh, and manifest.json.
The env file must define NEMO_SKILLS_REPO_DIR for the Perlmutter-enabled NeMo-Skills checkout.
EOF
}

env_file=""
input_file=""
prompt_file=""
model_name=""
run_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      env_file="$2"
      shift 2
      ;;
    --input)
      input_file="$2"
      shift 2
      ;;
    --prompt)
      prompt_file="$2"
      shift 2
      ;;
    --model)
      model_name="$2"
      shift 2
      ;;
    --run-id)
      run_id="$2"
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

[[ -n "${env_file}" ]] || die "Missing required argument: --env-file"
[[ -n "${input_file}" ]] || die "Missing required argument: --input"
[[ -n "${prompt_file}" ]] || die "Missing required argument: --prompt"
[[ -n "${model_name}" ]] || die "Missing required argument: --model"

env_file="$(cd "$(dirname "${env_file}")" && pwd)/$(basename "${env_file}")"
input_file="$(cd "$(dirname "${input_file}")" && pwd)/$(basename "${input_file}")"
prompt_file="$(cd "$(dirname "${prompt_file}")" && pwd)/$(basename "${prompt_file}")"

ensure_absolute_path "${env_file}"
ensure_absolute_path "${input_file}"
ensure_absolute_path "${prompt_file}"
require_file "${env_file}"
require_file "${input_file}"
require_file "${prompt_file}"

load_env_file "${env_file}"
require_env_vars OPENAI_BASE_URL NERSC_USER SSH_LOGIN_IDENTITY NERSC_ACCOUNT NERSC_QOS NERSC_CONSTRAINT NERSC_JOB_DIR REMOTE_WORKSPACE_ROOT PERLMUTTER_IMAGE_NAME NEMO_SKILLS_REPO_DIR
ensure_absolute_path "${SSH_LOGIN_IDENTITY}"
ensure_absolute_path "${SSH_IDENTITY}"
ensure_absolute_path "${NERSC_JOB_DIR}"
ensure_absolute_path "${REMOTE_WORKSPACE_ROOT}"
ensure_absolute_path "${NEMO_SKILLS_REPO_DIR}"
require_parent_dir "${SSH_IDENTITY}"
require_file "${SSH_IDENTITY}"
require_file "${SSH_LOGIN_IDENTITY}"

if [[ -z "${OPENAI_API_KEY:-}" && -z "${NVIDIA_API_KEY:-}" ]]; then
  die "At least one of OPENAI_API_KEY or NVIDIA_API_KEY must be defined in ${env_file}"
fi

require_supported_model "${model_name}"

repo_dir="${NEMO_SKILLS_REPO_DIR}"
require_perlmutter_repo "${repo_dir}"
ns_bin="$(ensure_managed_ns_cli "${repo_dir}")"
ensure_absolute_path "${ns_bin}"
require_file "${ns_bin}"

if [[ -z "${run_id}" ]]; then
  run_id="$(slug_timestamp)"
fi
run_id="${run_id//[^A-Za-z0-9._-]/-}"
[[ -n "${run_id}" ]] || die "Run id resolved to an empty value"

artifact_root="$(run_artifact_root)"
run_dir="${artifact_root}/${run_id}"
if [[ -e "${run_dir}" ]]; then
  die "Run directory already exists: ${run_dir}"
fi
mkdir -p "${run_dir}/logs" "${run_dir}/results"

export ENV_FILE="${env_file}"
export MODEL="${model_name}"
export REPO_DIR="${repo_dir}"
export NS_BIN="${ns_bin}"
export REMOTE_RUN_DIR="${REMOTE_WORKSPACE_ROOT}/runs/${run_id}"
export MOUNT_OUTPUT_DIR="/workspace/generation/${run_id}"
export EXPNAME="perlmutter-generate-${run_id}"

cluster_config_path="${run_dir}/perlmutter.yaml"
run_script_path="${run_dir}/run.sh"
manifest_path="${run_dir}/manifest.json"
remote_output_dir="${REMOTE_RUN_DIR}/generation/${run_id}"
remote_result_file="${remote_output_dir}/output.jsonl"
remote_done_file="${remote_result_file}.done"

render_template "$(bundle_root)/templates/perlmutter.yaml.tmpl" "${cluster_config_path}"
render_template "$(bundle_root)/templates/run.sh.tmpl" "${run_script_path}"
chmod +x "${run_script_path}"

python3 - "${manifest_path}" <<PY
import json
from pathlib import Path

manifest = {
    "artifact_root": "${artifact_root}",
    "bundle_root": "$(bundle_root)",
    "cluster_config_path": "${cluster_config_path}",
    "cluster_name": "perlmutter",
    "created_at": "$(now_utc)",
    "env_file": "${env_file}",
    "expname": "${EXPNAME}",
    "image_name": "${PERLMUTTER_IMAGE_NAME}",
    "input_local_path": "${input_file}",
    "model": "${model_name}",
    "nersc_host": "${NERSC_HOST}",
    "nersc_job_dir": "${NERSC_JOB_DIR}",
    "nersc_user": "${NERSC_USER}",
    "ns_bin": "${ns_bin}",
    "prompt_local_path": "${prompt_file}",
    "remote_done_file": "${remote_done_file}",
    "remote_output_dir": "${remote_output_dir}",
    "remote_result_file": "${remote_result_file}",
    "remote_run_dir": "${REMOTE_RUN_DIR}",
    "repo_dir": "${repo_dir}",
    "results_dir": "${run_dir}/results",
    "run_dir": "${run_dir}",
    "run_id": "${run_id}",
    "run_script_path": "${run_script_path}",
    "status": "prepared",
    "submission_log": "${run_dir}/logs/submission.log",
}
Path("${manifest_path}").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf '%s\n' "${manifest_path}"
