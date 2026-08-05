#!/usr/bin/env bash

die() {
  echo "Error: $*" >&2
  exit 1
}

note() {
  echo "$*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

require_file() {
  [[ -f "$1" ]] || die "File not found: $1"
}

require_dir() {
  [[ -d "$1" ]] || die "Directory not found: $1"
}

ensure_absolute_path() {
  [[ "$1" = /* ]] || die "Expected an absolute path, got: $1"
}

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

bundle_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${script_dir}/.." && pwd
}

run_artifact_root() {
  local candidate=""

  if [[ -n "${PERLMUTTER_AGENT_RUNS_DIR:-}" ]]; then
    candidate="${PERLMUTTER_AGENT_RUNS_DIR}"
  elif [[ -w "${PWD}" ]]; then
    candidate="${PWD}/.perlmutter-nemo-generate-runs"
  elif [[ -w "$(bundle_root)" ]]; then
    candidate="$(bundle_root)/runs"
  else
    candidate="${TMPDIR:-/tmp}/perlmutter-nemo-generate-runs"
  fi

  mkdir -p "${candidate}"
  cd "${candidate}" && pwd
}

state_root() {
  local candidate=""

  if [[ -n "${PERLMUTTER_AGENT_STATE_DIR:-}" ]]; then
    candidate="${PERLMUTTER_AGENT_STATE_DIR}"
  elif [[ -n "${XDG_CACHE_HOME:-}" ]]; then
    candidate="${XDG_CACHE_HOME}/perlmutter-nemo-generate"
  else
    candidate="${HOME}/.cache/perlmutter-nemo-generate"
  fi

  mkdir -p "${candidate}"
  cd "${candidate}" && pwd
}

slug_timestamp() {
  date +"%Y%m%d-%H%M%S"
}

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

normalize_remote_build_dir() {
  local value="$1"
  if [[ "${value}" == "~/"* ]]; then
    printf '$HOME/%s\n' "${value#~/}"
  else
    printf '%s\n' "${value}"
  fi
}

derive_ssh_login_identity() {
  local identity="$1"
  if [[ "${identity}" == *-cert.pub ]]; then
    printf '%s\n' "${identity%-cert.pub}"
  elif [[ "${identity}" == *.pub ]]; then
    printf '%s\n' "${identity%.pub}"
  else
    printf '%s\n' "${identity}"
  fi
}

derive_ssh_cert_identity() {
  local identity="$1"
  if [[ "${identity}" == *-cert.pub ]]; then
    printf '%s\n' "${identity}"
  elif [[ "${identity}" == *.pub ]]; then
    printf '%s-cert.pub\n' "${identity%.pub}"
  else
    printf '%s-cert.pub\n' "${identity}"
  fi
}

require_env_vars() {
  local name
  for name in "$@"; do
    [[ -n "${!name:-}" ]] || die "Missing required env var: ${name}"
  done
}

require_parent_dir() {
  local path="$1"
  local parent_dir
  parent_dir="$(dirname "${path}")"
  [[ -d "${parent_dir}" ]] || die "Parent directory not found: ${parent_dir}"
}

load_env_file() {
  local env_file="$1"
  require_file "${env_file}"
  ensure_absolute_path "${env_file}"

  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a

  : "${NERSC_HOST:=perlmutter.nersc.gov}"
  : "${NODES:=1}"
  : "${NTASKS_PER_NODE:=1}"
  : "${DEFAULT_TIMEOUT:=00:20:00}"
  : "${HF_HOME_IN_WORKSPACE:=/workspace/hf-cache}"
  : "${REMOTE_IMAGE_BUILD_DIR:=~/ns-image-build}"
  : "${STATUS_POLL_INTERVAL:=30}"
  : "${PERLMUTTER_BASE_IMAGE:=docker.io/library/python:3.11}"

  REMOTE_IMAGE_BUILD_DIR="$(normalize_remote_build_dir "${REMOTE_IMAGE_BUILD_DIR}")"

  if [[ -n "${SSH_LOGIN_IDENTITY:-}" && -z "${SSH_IDENTITY:-}" ]]; then
    SSH_IDENTITY="$(derive_ssh_cert_identity "${SSH_LOGIN_IDENTITY}")"
  fi

  if [[ -n "${SSH_IDENTITY:-}" && -z "${SSH_LOGIN_IDENTITY:-}" ]]; then
    SSH_LOGIN_IDENTITY="$(derive_ssh_login_identity "${SSH_IDENTITY}")"
  fi

  export NERSC_HOST
  export NODES
  export NTASKS_PER_NODE
  export DEFAULT_TIMEOUT
  export HF_HOME_IN_WORKSPACE
  export REMOTE_IMAGE_BUILD_DIR
  export STATUS_POLL_INTERVAL
  export PERLMUTTER_BASE_IMAGE
  if [[ -n "${SSH_IDENTITY:-}" ]]; then
    export SSH_IDENTITY
  fi
  if [[ -n "${SSH_LOGIN_IDENTITY:-}" ]]; then
    export SSH_LOGIN_IDENTITY
  fi
}

require_perlmutter_repo() {
  local repo_dir="$1"
  ensure_absolute_path "${repo_dir}"
  require_dir "${repo_dir}"
  require_file "${repo_dir}/pyproject.toml"
  require_file "${repo_dir}/docs/basics/perlmutter.md"
  require_file "${repo_dir}/ns-tests/test_api_perlmutter.sh"
  require_file "${repo_dir}/ns-tests/cluster_configs/perlmutter.yaml"
  require_file "${repo_dir}/nemo_skills/pipeline/utils/cluster.py"

  grep -F "podman-hpc" "${repo_dir}/nemo_skills/pipeline/utils/cluster.py" >/dev/null 2>&1 || \
    die "Repo at ${repo_dir} does not look like the Perlmutter-enabled NeMo-Skills checkout (missing podman-hpc support)"
}

repo_cache_key() {
  local repo_dir="$1"
  python3 - "${repo_dir}" <<'PY'
import hashlib
import pathlib
import sys

repo_dir = pathlib.Path(sys.argv[1]).resolve()
print(hashlib.sha256(str(repo_dir).encode("utf-8")).hexdigest()[:16])
PY
}

repo_install_stamp() {
  local repo_dir="$1"
  python3 - "${repo_dir}" <<'PY'
import hashlib
import pathlib
import sys

repo_dir = pathlib.Path(sys.argv[1]).resolve()
tracked = [
    "pyproject.toml",
    "core/requirements.txt",
    "requirements/pipeline.txt",
]
h = hashlib.sha256()
for rel in tracked:
    path = repo_dir / rel
    stat = path.stat()
    h.update(rel.encode("utf-8"))
    h.update(str(stat.st_mtime_ns).encode("utf-8"))
    h.update(str(stat.st_size).encode("utf-8"))
print(h.hexdigest())
PY
}

managed_venv_dir() {
  local repo_dir="$1"
  local key
  key="$(repo_cache_key "${repo_dir}")"
  printf '%s/venvs/%s\n' "$(state_root)" "${key}"
}

venv_uses_repo() {
  local venv_dir="$1"
  local repo_dir="$2"
  [[ -x "${venv_dir}/bin/python" ]] || return 1
  "${venv_dir}/bin/python" - "${repo_dir}" <<'PY'
import importlib.util
import pathlib
import sys

repo_dir = pathlib.Path(sys.argv[1]).resolve()
spec = importlib.util.find_spec("nemo_skills")
if spec is None or not spec.origin:
    raise SystemExit(1)
origin = pathlib.Path(spec.origin).resolve()
if repo_dir == origin or repo_dir in origin.parents:
    raise SystemExit(0)
raise SystemExit(1)
PY
}

find_compatible_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3.10; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      printf '%s\n' "$(command -v "${candidate}")"
      return 0
    fi
  done
  # Fall back to python3 with a version warning
  local ver
  ver="$(python3 -c 'import sys; print(sys.version_info[:2])'  2>/dev/null || true)"
  echo "WARNING: no python3.10–3.13 found; using system python3 (${ver}) — install may fail" >&2
  printf '%s\n' "$(command -v python3)"
}

ensure_managed_ns_cli() {
  local repo_dir="$1"
  local venv_dir
  local stamp_file
  local expected_stamp
  local current_stamp=""
  local reinstall=0
  local py_bin

  require_cmd python3
  require_perlmutter_repo "${repo_dir}"

  py_bin="$(find_compatible_python)"

  venv_dir="$(managed_venv_dir "${repo_dir}")"
  mkdir -p "$(dirname "${venv_dir}")"
  stamp_file="${venv_dir}/.repo-install-stamp"
  expected_stamp="$(repo_install_stamp "${repo_dir}")"

  if [[ ! -x "${venv_dir}/bin/ns" || ! -x "${venv_dir}/bin/python" ]]; then
    reinstall=1
  fi

  if [[ "${reinstall}" -eq 0 && -f "${stamp_file}" ]]; then
    current_stamp="$(<"${stamp_file}")"
    if [[ "${current_stamp}" != "${expected_stamp}" ]]; then
      reinstall=1
    fi
  elif [[ "${reinstall}" -eq 0 ]]; then
    reinstall=1
  fi

  if [[ "${reinstall}" -eq 0 ]] && ! venv_uses_repo "${venv_dir}" "${repo_dir}"; then
    reinstall=1
  fi

  # Also reinstall if the existing venv was built with an incompatible Python
  if [[ "${reinstall}" -eq 0 && -x "${venv_dir}/bin/python" ]]; then
    local venv_py_ver
    venv_py_ver="$("${venv_dir}/bin/python" -c 'import sys; print(sys.version_info[:2])' 2>/dev/null || true)"
    local target_py_ver
    target_py_ver="$("${py_bin}" -c 'import sys; print(sys.version_info[:2])')"
    if [[ "${venv_py_ver}" != "${target_py_ver}" ]]; then
      reinstall=1
    fi
  fi

  if [[ "${reinstall}" -eq 1 ]]; then
    rm -rf "${venv_dir}"
    echo "Preparing isolated NeMo-Skills CLI at ${venv_dir} (using ${py_bin})" >&2
    "${py_bin}" -m venv "${venv_dir}"
    if ! "${venv_dir}/bin/python" - <<'PY' >/dev/null 2>&1
import setuptools  # noqa: F401
import wheel  # noqa: F401
PY
    then
      echo "Bootstrapping setuptools and wheel into ${venv_dir}" >&2
      "${venv_dir}/bin/pip" install --disable-pip-version-check setuptools wheel hatchling 1>&2 || \
        die "Failed to install setuptools and wheel into ${venv_dir}. Internet access may be required on first run."
    fi
    "${venv_dir}/bin/pip" install --disable-pip-version-check "pdm[all]" 1>&2 || \
      die "Failed to install pdm[all] into ${venv_dir}. Internet access may be required on first run."
    "${venv_dir}/bin/pip" install --disable-pip-version-check -e "${repo_dir}" 1>&2 || \
      die "Failed to install ${repo_dir} into ${venv_dir}. Internet access may be required on first run."
    "${venv_dir}/bin/ns" --help >/dev/null 2>&1 || die "Managed ns CLI did not become available in ${venv_dir}"
    venv_uses_repo "${venv_dir}" "${repo_dir}" || die "Managed ns CLI in ${venv_dir} is not using repo ${repo_dir}"
    printf '%s\n' "${expected_stamp}" > "${stamp_file}"
  fi

  printf '%s\n' "${venv_dir}/bin/ns"
}

ssh_options() {
  local _ctl="/tmp/nersc-ctl-${NERSC_USER:-nersc}@${NERSC_HOST:-perlmutter}.sock"
  if [[ -f "${SSH_LOGIN_IDENTITY}" ]]; then
    printf '%s\n' \
      "-o" "ControlMaster=auto" "-o" "ControlPath=${_ctl}" "-o" "ControlPersist=300" \
      "-o" "BatchMode=yes" "-o" "StrictHostKeyChecking=accept-new" \
      "-i" "${SSH_LOGIN_IDENTITY}"
  else
    printf '%s\n' \
      "-o" "ControlMaster=auto" "-o" "ControlPath=${_ctl}" "-o" "ControlPersist=300" \
      "-o" "BatchMode=yes" "-o" "StrictHostKeyChecking=accept-new"
  fi
}

# Require that SSH_LOGIN_IDENTITY is either a file on disk or already loaded in
# the ssh-agent (identified by a matching comment). Dies if neither is true.
require_ssh_identity() {
  [[ -f "${SSH_LOGIN_IDENTITY}" ]] && return 0
  ssh-add -l 2>/dev/null | grep -qF "$(basename "${SSH_LOGIN_IDENTITY}")" && return 0
  die "SSH identity ${SSH_LOGIN_IDENTITY} is neither a file on disk nor loaded in the ssh-agent"
}

ssh_cmd() {
  local remote_cmd="$1"
  require_env_vars NERSC_USER NERSC_HOST SSH_LOGIN_IDENTITY
  require_ssh_identity
  ssh $(ssh_options) "${NERSC_USER}@${NERSC_HOST}" "${remote_cmd}"
}

resolve_remote_path() {
  local value="$1"
  local remote_home

  if [[ "${value}" == '$HOME/'* ]]; then
    remote_home="$(ssh_cmd 'printf %s "$HOME"')"
    printf '%s/%s\n' "${remote_home}" "${value#\$HOME/}"
  elif [[ "${value}" == "~/"* ]]; then
    remote_home="$(ssh_cmd 'printf %s "$HOME"')"
    printf '%s/%s\n' "${remote_home}" "${value#~/}"
  else
    printf '%s\n' "${value}"
  fi
}

scp_to() {
  local source_path="$1"
  local dest_path="$2"
  require_env_vars NERSC_USER NERSC_HOST SSH_LOGIN_IDENTITY
  require_ssh_identity
  scp -p $(ssh_options) "${source_path}" "${NERSC_USER}@${NERSC_HOST}:${dest_path}"
}

scp_from() {
  local source_path="$1"
  local dest_path="$2"
  require_env_vars NERSC_USER NERSC_HOST SSH_LOGIN_IDENTITY
  require_ssh_identity
  scp -p $(ssh_options) "${NERSC_USER}@${NERSC_HOST}:${source_path}" "${dest_path}"
}

render_template() {
  local template_path="$1"
  local output_path="$2"
  require_file "${template_path}"
  TEMPLATE_PATH="${template_path}" OUTPUT_PATH="${output_path}" python3 - <<'PY'
import os
import pathlib
import re

template_path = pathlib.Path(os.environ["TEMPLATE_PATH"])
output_path = pathlib.Path(os.environ["OUTPUT_PATH"])
text = template_path.read_text()
for key, value in os.environ.items():
    text = text.replace("{{" + key + "}}", value)
leftovers = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
if leftovers:
    raise SystemExit(f"Unresolved template placeholders: {', '.join(leftovers)}")
output_path.write_text(text)
PY
}

json_get() {
  local manifest_path="$1"
  local key="$2"
  python3 - "${manifest_path}" "${key}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    data = json.load(handle)
value = data.get(sys.argv[2], "")
if value is None:
    value = ""
if isinstance(value, (dict, list)):
    print(json.dumps(value))
else:
    print(value)
PY
}

update_manifest() {
  local manifest_path="$1"
  shift
  python3 - "${manifest_path}" "$@" <<'PY'
import json
import sys

path = sys.argv[1]
pairs = sys.argv[2:]
if len(pairs) % 2:
    raise SystemExit("update_manifest expects key/value pairs")

with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

for idx in range(0, len(pairs), 2):
    key = pairs[idx]
    raw = pairs[idx + 1]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    data[key] = value

with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
}

require_supported_model() {
  local model_name="$1"
  local allowlist
  allowlist="$(bundle_root)/config/supported_models.txt"
  require_file "${allowlist}"
  grep -Fx -- "${model_name}" "${allowlist}" >/dev/null 2>&1 || die "Unsupported model '${model_name}'. See ${allowlist}"
}
