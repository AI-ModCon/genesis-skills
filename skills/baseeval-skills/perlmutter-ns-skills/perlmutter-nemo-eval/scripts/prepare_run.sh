#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: prepare_run.sh --env-file <absolute-path> --benchmark <name> --model <model>
                      [--job-type eval|robust_eval] [--run-id <slug>]
                      [--prompt-set-config <absolute-yaml>] [--num-samples <int>]
                      [--max-concurrent-requests <int>]

Validate inputs and env vars, then render a run-specific perlmutter.yaml, run.sh, and manifest.json.
--prompt-set-config is required when --job-type=robust_eval.
EOF
}

env_file=""
benchmark=""
model_name=""
job_type="eval"
run_id=""
prompt_set_config=""
num_seeds=""
max_samples=""
max_concurrent_requests=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)            env_file="$2";              shift 2 ;;
    --benchmark)           benchmark="$2";             shift 2 ;;
    --model)               model_name="$2";            shift 2 ;;
    --job-type)            job_type="$2";              shift 2 ;;
    --run-id)              run_id="$2";                shift 2 ;;
    --prompt-set-config)   prompt_set_config="$2";     shift 2 ;;
    --num-seeds)           num_seeds="$2";             shift 2 ;;
    --max-samples)         max_samples="$2";           shift 2 ;;
    --max-concurrent-requests) max_concurrent_requests="$2"; shift 2 ;;
    -h|--help)             usage; exit 0 ;;
    *)                     die "Unknown argument: $1" ;;
  esac
done

[[ -n "${env_file}" ]]    || die "Missing required argument: --env-file"
[[ -n "${benchmark}" ]]   || die "Missing required argument: --benchmark"
[[ -n "${model_name}" ]]  || die "Missing required argument: --model"

[[ "${job_type}" == "eval" || "${job_type}" == "robust_eval" ]] \
  || die "Invalid --job-type '${job_type}': must be 'eval' or 'robust_eval'"

if [[ "${job_type}" == "robust_eval" && -z "${prompt_set_config}" ]]; then
  die "--prompt-set-config is required when --job-type=robust_eval"
fi

env_file="$(cd "$(dirname "${env_file}")" && pwd)/$(basename "${env_file}")"
ensure_absolute_path "${env_file}"
require_file "${env_file}"

if [[ -n "${prompt_set_config}" ]]; then
  prompt_set_config="$(cd "$(dirname "${prompt_set_config}")" && pwd)/$(basename "${prompt_set_config}")"
  ensure_absolute_path "${prompt_set_config}"
  require_file "${prompt_set_config}"
fi

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

# Mirror NeMo-Skills openai.py _is_reasoning_model() logic: gpt-5* or o<digit>*
if [[ "${model_name}" == *gpt-5* ]] || [[ "${model_name}" =~ ^o[0-9] ]]; then
  export IS_REASONING_MODEL="true"
else
  export IS_REASONING_MODEL="false"
fi

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

# Apply defaults for optional numeric params — CLI flag > env file var > hardcoded default
: "${num_seeds:=${NUM_SEEDS:-0}}"
: "${max_samples:=${MAX_SAMPLES:--1}}"
: "${max_concurrent_requests:=${MAX_CONCURRENT_REQUESTS:-32}}"
nemo_skills_data_dir="${NEMO_SKILLS_DATA_DIR:-/workspace/ns-data}"

: "${PERLMUTTER_AGENT_RUNS_DIR:=${PWD}/.perlmutter-nemo-eval-runs}"
artifact_root="$(run_artifact_root)"
run_dir="${artifact_root}/${run_id}"
if [[ -e "${run_dir}" ]]; then
  die "Run directory already exists: ${run_dir}"
fi
mkdir -p "${run_dir}/logs" "${run_dir}/results"

if [[ "${job_type}" == "robust_eval" ]]; then
  expname_prefix="perlmutter-robust"
else
  expname_prefix="perlmutter-eval"
fi

export ENV_FILE="${env_file}"
export MODEL="${model_name}"
export REPO_DIR="${repo_dir}"
export NS_BIN="${ns_bin}"
export BENCHMARK="${benchmark}"
export JOB_TYPE="${job_type}"
export NUM_SEEDS="${num_seeds}"
export MAX_SAMPLES="${max_samples}"
export MAX_CONCURRENT_REQUESTS="${max_concurrent_requests}"
export NEMO_SKILLS_DATA_DIR="${nemo_skills_data_dir}"
export REMOTE_RUN_DIR="${REMOTE_WORKSPACE_ROOT}/runs/${run_id}"
export MOUNT_OUTPUT_DIR="/workspace/eval/${run_id}"
export EXPNAME="${expname_prefix}-${run_id}"
export PROMPT_SET_CONFIG_LOCAL_PATH="${prompt_set_config}"

cluster_config_path="${run_dir}/perlmutter.yaml"
prepare_script_path="${run_dir}/prepare.sh"
eval_script_path="${run_dir}/eval.sh"
run_script_path="${prepare_script_path}"  # used by submit_run.sh
manifest_path="${run_dir}/manifest.json"
remote_output_dir="${REMOTE_RUN_DIR}/eval/${run_id}"
remote_done_file="${remote_output_dir}/eval-results/${benchmark}/metrics.json"

render_template "$(bundle_root)/templates/perlmutter.yaml.tmpl" "${cluster_config_path}"
render_template "$(bundle_root)/templates/prepare_data.sh.tmpl" "${prepare_script_path}"
render_template "$(bundle_root)/templates/run.sh.tmpl" "${eval_script_path}"
chmod +x "${prepare_script_path}" "${eval_script_path}"

prompt_set_config_field="None"
if [[ -n "${prompt_set_config}" ]]; then
  prompt_set_config_field="\"${prompt_set_config}\""
fi

python3 - "${manifest_path}" <<PY
import json
from pathlib import Path

manifest = {
    "artifact_root": "${artifact_root}",
    "benchmark": "${benchmark}",
    "bundle_root": "$(bundle_root)",
    "cluster_config_path": "${cluster_config_path}",
    "cluster_name": "perlmutter",
    "created_at": "$(now_utc)",
    "env_file": "${env_file}",
    "expname": "${EXPNAME}",
    "image_name": "${PERLMUTTER_IMAGE_NAME}",
    "job_type": "${job_type}",
    "max_concurrent_requests": ${max_concurrent_requests},
    "max_samples": ${max_samples},
    "model": "${model_name}",
    "nemo_skills_data_dir": "${nemo_skills_data_dir}",
    "nersc_host": "${NERSC_HOST}",
    "nersc_job_dir": "${NERSC_JOB_DIR}",
    "nersc_user": "${NERSC_USER}",
    "ns_bin": "${ns_bin}",
    "num_seeds": ${num_seeds},
    "prompt_set_config_local_path": ${prompt_set_config_field},
    "remote_done_file": "${remote_done_file}",
    "remote_output_dir": "${remote_output_dir}",
    "remote_run_dir": "${REMOTE_RUN_DIR}",
    "repo_dir": "${repo_dir}",
    "results_dir": "${run_dir}/results",
    "eval_script_path": "${eval_script_path}",
    "eval_submitted": False,
    "prepare_script_path": "${prepare_script_path}",
    "run_dir": "${run_dir}",
    "run_id": "${run_id}",
    "run_script_path": "${run_script_path}",
    "status": "prepared",
    "submission_log": "${run_dir}/logs/submission.log",
}
Path("${manifest_path}").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf '%s\n' "${manifest_path}"
