#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  glab-list-group-repos.sh --group GROUP_PATH [options]

Description:
  List repositories under a GitLab group/subgroup.

Options:
  --group GROUP_PATH   Group path (required), e.g. nersc/agent-skills
  --host HOST          GitLab host (default: gitlab.nersc.gov)
  --no-subgroups       Exclude subgroup projects
  --include-shared     Include shared projects (default excludes shared)
  --format FORMAT      text|json (default: text)
  -h, --help           Show help
USAGE
}

group=""
host="gitlab.nersc.gov"
include_subgroups="true"
with_shared="false"
format="text"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group) group="${2:-}"; shift 2 ;;
    --host) host="${2:-}"; shift 2 ;;
    --no-subgroups) include_subgroups="false"; shift ;;
    --include-shared) with_shared="true"; shift ;;
    --format) format="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$group" ]]; then
  echo "--group is required" >&2
  usage
  exit 1
fi
if ! command -v glab >/dev/null 2>&1; then
  echo "glab is required but not found" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not found" >&2
  exit 1
fi
if [[ "$format" != "text" && "$format" != "json" ]]; then
  echo "--format must be text or json" >&2
  exit 1
fi

encoded_group="${group//\//%2F}"
endpoint="/groups/${encoded_group}/projects?per_page=100&with_shared=${with_shared}&include_subgroups=${include_subgroups}&order_by=path&sort=asc&simple=true"

if [[ "$format" == "json" ]]; then
  glab api --hostname "$host" "$endpoint" --paginate --output ndjson \
    | jq -sc 'map({id, path_with_namespace, default_branch, web_url})'
else
  glab api --hostname "$host" "$endpoint" --paginate --output ndjson \
    | jq -r '.path_with_namespace'
fi
