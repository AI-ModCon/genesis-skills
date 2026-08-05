#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: build_remote_image.sh --env-file <absolute-path>

Render the minimal Perlmutter Containerfile, upload build inputs to Perlmutter,
build and smoke-test the podman-hpc image, and migrate it for job use.
EOF
}

env_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      env_file="$2"
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

env_file="$(cd "$(dirname "${env_file}")" && pwd)/$(basename "${env_file}")"

require_cmd ssh
require_cmd scp
require_cmd python3
load_env_file "${env_file}"
require_env_vars NERSC_USER SSH_LOGIN_IDENTITY PERLMUTTER_IMAGE_NAME NEMO_SKILLS_REPO_DIR
ensure_absolute_path "${SSH_LOGIN_IDENTITY}"
require_file "${SSH_LOGIN_IDENTITY}"
repo_dir="${NEMO_SKILLS_REPO_DIR}"
require_perlmutter_repo "${repo_dir}"
require_file "${repo_dir}/core/requirements.txt"
require_file "${repo_dir}/requirements/pipeline.txt"

artifact_root="$(run_artifact_root)"
artifact_dir="${artifact_root}/image-build-$(slug_timestamp)"
mkdir -p "${artifact_dir}"
local_log="${artifact_dir}/build.log"
temp_dir="$(mktemp -d "${artifact_dir}/tmp.XXXXXX")"
remote_build_dir="$(resolve_remote_path "${REMOTE_IMAGE_BUILD_DIR}")"

export PERLMUTTER_BASE_IMAGE
render_template "$(bundle_root)/templates/Containerfile.minimal.tmpl" "${temp_dir}/Containerfile"
cp "${repo_dir}/core/requirements.txt" "${temp_dir}/core.requirements.txt"
cp "${repo_dir}/requirements/pipeline.txt" "${temp_dir}/pipeline.requirements.txt"

ssh_cmd "mkdir -p \"${remote_build_dir}\"" >/dev/null
scp_to "${temp_dir}/Containerfile" "${remote_build_dir}/Containerfile"
scp_to "${temp_dir}/core.requirements.txt" "${remote_build_dir}/core.requirements.txt"
scp_to "${temp_dir}/pipeline.requirements.txt" "${remote_build_dir}/pipeline.requirements.txt"

remote_cmd="set -euo pipefail
cd \"${remote_build_dir}\"
podman-hpc build -t '${PERLMUTTER_IMAGE_NAME}' .
podman-hpc run --rm --entrypoint= '${PERLMUTTER_IMAGE_NAME}' bash -lc 'python -c \"import nemo_run, typer, openai, litellm, hydra; print(\\\"image ok\\\")\"'
podman-hpc migrate '${PERLMUTTER_IMAGE_NAME}'"

ssh_cmd "${remote_cmd}" 2>&1 | tee "${local_log}"

note "Image build completed: ${PERLMUTTER_IMAGE_NAME}"
note "Local build log: ${local_log}"
