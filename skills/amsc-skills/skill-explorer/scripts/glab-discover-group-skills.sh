#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  glab-discover-group-skills.sh --group GROUP_PATH [options]

Description:
  Discover repositories that appear to contain Codex agent skills by looking
  for SKILL.md, AGENTS.md, and CLAUDE.md files.

Options:
  --group GROUP_PATH   Group path (required), e.g. nersc/agent-skills
  --host HOST          GitLab host (default: gitlab.nersc.gov)
  --format FORMAT      text|json (default: text)
  --no-subgroups       Exclude subgroup projects
  --include-shared     Include shared projects (default excludes shared)
  -h, --help           Show help

JSON output:
  [{
    repo_path, project_id, default_branch,
    skill_path, detector,
    skill_name, main_functionality
  }, ...]
USAGE
}

urlencode() {
  jq -nr --arg v "$1" '$v|@uri'
}

trim_quotes() {
  sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

extract_frontmatter_field() {
  local key="$1"
  awk -v k="$key" '
    NR == 1 && $0 == "---" {in_fm=1; next}
    in_fm && $0 == "---" {exit}
    in_fm {
      pattern = "^" k ":[[:space:]]*(.*)$"
      if (match($0, pattern, m)) {
        print m[1]
        exit
      }
    }
  ' | trim_quotes
}

extract_agents_summary() {
  awk '
    BEGIN {in_fm=0}
    NR==1 && $0=="---" {in_fm=1; next}
    in_fm && $0=="---" {in_fm=0; next}
    in_fm {next}
    /^#/ {next}
    /^[[:space:]]*$/ {next}
    {
      print
      exit
    }
  ' | sed 's/[[:space:]]\+/ /g' | cut -c1-240
}

group=""
host="gitlab.nersc.gov"
format="text"
include_subgroups="true"
with_shared="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group) group="${2:-}"; shift 2 ;;
    --host) host="${2:-}"; shift 2 ;;
    --format) format="${2:-}"; shift 2 ;;
    --no-subgroups) include_subgroups="false"; shift ;;
    --include-shared) with_shared="true"; shift ;;
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
projects_endpoint="/groups/${encoded_group}/projects?per_page=100&with_shared=${with_shared}&include_subgroups=${include_subgroups}&order_by=path&sort=asc&simple=true"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
results="$tmpdir/results.ndjson"
: > "$results"

while IFS= read -r project; do
  [[ -z "$project" ]] && continue
  project_id="$(jq -r '.id' <<<"$project")"
  repo_path="$(jq -r '.path_with_namespace' <<<"$project")"
  default_branch="$(jq -r '.default_branch // "main"' <<<"$project")"

  tree_endpoint="/projects/${project_id}/repository/tree?recursive=true&ref=$(urlencode "$default_branch")&per_page=100"

  mapfile -t markers < <(
    glab api --hostname "$host" "$tree_endpoint" --paginate --output ndjson \
      | jq -r '
          select(.type=="blob")
          | .path
          | select(
              (. == "SKILL.md") or
              (. == "AGENTS.md") or
              (. == "CLAUDE.md") or
              (endswith("/SKILL.md")) or
              (endswith("/AGENTS.md")) or
              (endswith("/CLAUDE.md"))
            )
        ' | sort -u
  )

  if [[ ${#markers[@]} -eq 0 ]]; then
    continue
  fi

  for marker in "${markers[@]}"; do
    encoded_path="$(urlencode "$marker")"
    file_endpoint="/projects/${project_id}/repository/files/${encoded_path}/raw?ref=$(urlencode "$default_branch")"
    raw="$(glab api --hostname "$host" "$file_endpoint" 2>/dev/null || true)"

    detector="skill_md"
    skill_name=""
    main_functionality=""

    if [[ "$marker" == *"SKILL.md" ]]; then
      skill_name="$(printf '%s\n' "$raw" | extract_frontmatter_field name || true)"
      main_functionality="$(printf '%s\n' "$raw" | extract_frontmatter_field description || true)"
      detector="skill_md"
    elif [[ "$marker" == *"CLAUDE.md" ]]; then
      detector="claude_md"
      main_functionality="$(printf '%s\n' "$raw" | extract_agents_summary || true)"
    else
      detector="agents_md"
      main_functionality="$(printf '%s\n' "$raw" | extract_agents_summary || true)"
    fi

    if [[ -z "$skill_name" ]]; then
      if [[ "$marker" == "SKILL.md" || "$marker" == "AGENTS.md" || "$marker" == "CLAUDE.md" ]]; then
        skill_name="$(basename "$repo_path")"
      else
        skill_name="$(basename "$(dirname "$marker")")"
      fi
    fi

    jq -cn \
      --arg repo_path "$repo_path" \
      --arg project_id "$project_id" \
      --arg default_branch "$default_branch" \
      --arg skill_path "$marker" \
      --arg detector "$detector" \
      --arg skill_name "$skill_name" \
      --arg main_functionality "$main_functionality" \
      '{repo_path:$repo_path,project_id:($project_id|tonumber),default_branch:$default_branch,skill_path:$skill_path,detector:$detector,skill_name:$skill_name,main_functionality:$main_functionality}' \
      >> "$results"
  done
done < <(glab api --hostname "$host" "$projects_endpoint" --paginate --output ndjson)

if [[ "$format" == "json" ]]; then
  jq -sc '.' "$results"
else
  jq -sr '
    map({
      repo_path,
      skill_name,
      detector,
      skill_path,
      main_functionality
    })
    | sort_by(.repo_path, .skill_name, .skill_path)
    | .[]
    | "repo: \(.repo_path)\nskill: \(.skill_name)\ndetected_by: \(.detector)\npath: \(.skill_path)\nmain_functionality: \(.main_functionality // "")\n"
  ' "$results"
fi
