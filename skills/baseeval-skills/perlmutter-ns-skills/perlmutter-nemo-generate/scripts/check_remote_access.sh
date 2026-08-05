#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: check_remote_access.sh --env-file <absolute-path> [--require-image]

Verify SSH access, remote scratch/workspace directories, Slurm visibility, and podman-hpc image availability.
Exit code 3 means the required image is missing.
EOF
}

env_file=""
require_image=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      env_file="$2"
      shift 2
      ;;
    --require-image)
      require_image=1
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

[[ -n "${env_file}" ]] || die "Missing required argument: --env-file"
env_file="$(cd "$(dirname "${env_file}")" && pwd)/$(basename "${env_file}")"

require_cmd ssh
load_env_file "${env_file}"
require_env_vars NERSC_USER SSH_LOGIN_IDENTITY NERSC_JOB_DIR REMOTE_WORKSPACE_ROOT
ensure_absolute_path "${SSH_LOGIN_IDENTITY}"
ensure_absolute_path "${SSH_IDENTITY}"
ensure_absolute_path "${NERSC_JOB_DIR}"
ensure_absolute_path "${REMOTE_WORKSPACE_ROOT}"
require_file "${SSH_IDENTITY}"
require_file "${SSH_LOGIN_IDENTITY}"

ssh_cmd "mkdir -p '${NERSC_JOB_DIR}' '${REMOTE_WORKSPACE_ROOT}'" >/dev/null
ssh_cmd "podman-hpc images >/dev/null"
ssh_cmd "squeue -u '${NERSC_USER}' >/dev/null"

if [[ "${require_image}" -eq 1 ]]; then
  require_env_vars PERLMUTTER_IMAGE_NAME
  if ! ssh_cmd "podman-hpc images --format '{{.Repository}}:{{.Tag}}' | awk -v tag='${PERLMUTTER_IMAGE_NAME}' '\$0 == tag || \$0 == \"localhost/\" tag { found = 1 } END { exit(found ? 0 : 1) }'"; then
    echo "Image not found on ${NERSC_HOST}: ${PERLMUTTER_IMAGE_NAME}" >&2
    exit 3
  fi
fi

note "Remote access checks passed for ${NERSC_HOST}"
