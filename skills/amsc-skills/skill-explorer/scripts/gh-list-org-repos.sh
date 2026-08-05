#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  gh-list-org-repos.sh --org ORG [options]

Description:
  List repositories under a GitHub organization.

Options:
  --org ORG            Organization name (required)
  --host HOST          GitHub host (default: github.com)
  --format FORMAT      text|json (default: text)
  -h, --help           Show help
USAGE
}

org=""
host="github.com"
format="text"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --org) org="${2:-}"; shift 2 ;;
    --host) host="${2:-}"; shift 2 ;;
    --format) format="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$org" ]]; then
  echo "--org is required" >&2
  usage
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "gh is required but not found" >&2
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

endpoint="/orgs/${org}/repos?per_page=100&type=all&sort=full_name&direction=asc"

if [[ "$format" == "json" ]]; then
  gh api --hostname "$host" "$endpoint" --paginate \
    | jq -sc 'map({id, full_name, default_branch, html_url})'
else
  gh api --hostname "$host" "$endpoint" --paginate \
    | jq -r '.[] | .full_name'
fi
