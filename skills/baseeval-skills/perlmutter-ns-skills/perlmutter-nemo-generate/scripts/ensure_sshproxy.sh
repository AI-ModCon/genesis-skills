#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: ensure_sshproxy.sh --env-file <absolute-path>

Acquire or refresh the NERSC sshproxy certificate, then verify direct SSH access to Perlmutter.
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

require_cmd sshproxy
require_cmd ssh

load_env_file "${env_file}"
require_env_vars NERSC_USER SSH_LOGIN_IDENTITY
ensure_absolute_path "${SSH_LOGIN_IDENTITY}"
ensure_absolute_path "${SSH_IDENTITY}"
require_parent_dir "${SSH_IDENTITY}"
require_parent_dir "${SSH_LOGIN_IDENTITY}"

if [[ -f "${SSH_LOGIN_IDENTITY}" ]] && ssh $(ssh_options) "${NERSC_USER}@${NERSC_HOST}" "echo connected" >/dev/null 2>&1; then
  note "Existing SSH access to ${NERSC_HOST} is already valid"
  exit 0
fi

note "Refreshing sshproxy credentials for ${NERSC_USER}"
sshproxy -u "${NERSC_USER}" -a

require_file "${SSH_IDENTITY}"
require_file "${SSH_LOGIN_IDENTITY}"
ssh $(ssh_options) "${NERSC_USER}@${NERSC_HOST}" "echo connected" >/dev/null
note "SSH access to ${NERSC_HOST} is ready"
