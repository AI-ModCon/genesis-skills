#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: stage_inputs.sh --manifest <absolute-path>

Create the remote run directory and upload input.jsonl and prompt.yaml into the mounted Perlmutter workspace.
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
remote_run_dir="$(json_get "${manifest}" remote_run_dir)"
input_file="$(json_get "${manifest}" input_local_path)"
prompt_file="$(json_get "${manifest}" prompt_local_path)"

load_env_file "${env_file}"
require_env_vars NERSC_USER SSH_LOGIN_IDENTITY
ssh_cmd "mkdir -p '${remote_run_dir}/generation' '${remote_run_dir}/hf-cache'" >/dev/null
scp_to "${input_file}" "${remote_run_dir}/input.jsonl"
scp_to "${prompt_file}" "${remote_run_dir}/prompt.yaml"

update_manifest "${manifest}" staged_at "\"$(now_utc)\"" status "\"staged\""
note "Staged input files to ${remote_run_dir}"
