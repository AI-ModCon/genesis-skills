#!/usr/bin/env bash
set -eo pipefail

usage() {
  cat <<'USAGE'
Usage:
  skill-explorer-discover.sh [options]

Description:
  Discover repositories containing Codex skills from one or more GitLab groups
  and/or GitHub organizations.

Options:
  --gitlab-group GROUP      GitLab group path (repeatable)
  --github-org ORG          GitHub organization (repeatable)
  --gitlab-host HOST        GitLab host (default: gitlab.nersc.gov)
  --github-host HOST        GitHub host (default: github.com)
  --no-subgroups            Exclude GitLab subgroup projects
  --include-shared          Include GitLab shared projects
  --format FORMAT           text|json (default: text)
  -h, --help                Show help

Notes:
  - At least one of --gitlab-group or --github-org is required.
  - Detection markers: SKILL.md, AGENTS.md, and CLAUDE.md.
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
      if ($0 ~ ("^" k ":")) {
        line = $0
        sub("^" k ":[[:space:]]*", "", line)
        print line
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

emit_marker_result() {
  local provider="$1"
  local scope="$2"
  local host="$3"
  local repo_path="$4"
  local repo_id="$5"
  local default_branch="$6"
  local web_url="$7"
  local clone_url="$8"
  local marker="$9"
  local raw="${10}"

  local detector="skill_md"
  local skill_name=""
  local main_functionality=""

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
    --arg provider "$provider" \
    --arg scope "$scope" \
    --arg host "$host" \
    --arg repo_path "$repo_path" \
    --arg repo_id "$repo_id" \
    --arg default_branch "$default_branch" \
    --arg web_url "$web_url" \
    --arg clone_url "$clone_url" \
    --arg skill_path "$marker" \
    --arg detector "$detector" \
    --arg skill_name "$skill_name" \
    --arg main_functionality "$main_functionality" \
    '{provider:$provider,scope:$scope,host:$host,repo_path:$repo_path,repo_id:(if $repo_id=="" then null else ($repo_id|tonumber) end),default_branch:$default_branch,web_url:$web_url,clone_url:$clone_url,skill_path:$skill_path,detector:$detector,skill_name:$skill_name,main_functionality:$main_functionality}'
}

gitlab_groups=()
github_orgs=()
gitlab_host="gitlab.nersc.gov"
github_host="github.com"
include_subgroups="true"
with_shared="false"
format="text"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gitlab-group) gitlab_groups+=("${2:-}"); shift 2 ;;
    --github-org) github_orgs+=("${2:-}"); shift 2 ;;
    --gitlab-host) gitlab_host="${2:-}"; shift 2 ;;
    --github-host) github_host="${2:-}"; shift 2 ;;
    --no-subgroups) include_subgroups="false"; shift ;;
    --include-shared) with_shared="true"; shift ;;
    --format) format="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ${#gitlab_groups[@]} -eq 0 && ${#github_orgs[@]} -eq 0 ]]; then
  echo "Provide at least one --gitlab-group or --github-org" >&2
  usage
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not found" >&2
  exit 1
fi
if [[ ${#gitlab_groups[@]} -gt 0 ]] && ! command -v glab >/dev/null 2>&1; then
  echo "glab is required for --gitlab-group" >&2
  exit 1
fi
if [[ ${#github_orgs[@]} -gt 0 ]] && ! command -v gh >/dev/null 2>&1; then
  echo "gh is required for --github-org" >&2
  exit 1
fi
if [[ "$format" != "text" && "$format" != "json" ]]; then
  echo "--format must be text or json" >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
results="$tmpdir/results.ndjson"
: > "$results"

for group in "${gitlab_groups[@]}"; do
  encoded_group="${group//\//%2F}"
  projects_endpoint="/groups/${encoded_group}/projects?per_page=100&with_shared=${with_shared}&include_subgroups=${include_subgroups}&order_by=path&sort=asc&simple=true"

  while IFS= read -r project; do
    [[ -z "$project" ]] && continue
    project_id="$(jq -r '.id' <<<"$project")"
    repo_path="$(jq -r '.path_with_namespace' <<<"$project")"
    default_branch="$(jq -r '.default_branch // "main"' <<<"$project")"
    web_url="$(jq -r '.web_url // ""' <<<"$project")"
    clone_url="https://${gitlab_host}/${repo_path}.git"

    tree_endpoint="/projects/${project_id}/repository/tree?recursive=true&ref=$(urlencode "$default_branch")&per_page=100"

    markers=()
    while IFS= read -r _m; do
      [[ -n "$_m" ]] && markers+=("$_m")
    done < <(
      glab api --hostname "$gitlab_host" "$tree_endpoint" --paginate --output ndjson \
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

    [[ ${#markers[@]} -eq 0 ]] && continue

    for marker in "${markers[@]}"; do
      encoded_path="$(urlencode "$marker")"
      file_endpoint="/projects/${project_id}/repository/files/${encoded_path}/raw?ref=$(urlencode "$default_branch")"
      raw="$(glab api --hostname "$gitlab_host" "$file_endpoint" 2>/dev/null || true)"
      emit_marker_result "gitlab" "$group" "$gitlab_host" "$repo_path" "$project_id" "$default_branch" "$web_url" "$clone_url" "$marker" "$raw" >> "$results"
    done
  done < <(glab api --hostname "$gitlab_host" "$projects_endpoint" --paginate --output ndjson)
done

for org in "${github_orgs[@]}"; do
  repos_endpoint="/orgs/${org}/repos?per_page=100&type=all&sort=full_name&direction=asc"

  gh api --hostname "$github_host" "$repos_endpoint" --paginate \
    | jq -c '.[]' \
    | while IFS= read -r repo; do
        [[ -z "$repo" ]] && continue
        repo_id="$(jq -r '.id' <<<"$repo")"
        repo_path="$(jq -r '.full_name' <<<"$repo")"
        default_branch="$(jq -r '.default_branch // "main"' <<<"$repo")"
        web_url="$(jq -r '.html_url // ""' <<<"$repo")"
        clone_url="$(jq -r '.clone_url // ""' <<<"$repo")"

        tree_endpoint="/repos/${repo_path}/git/trees/$(urlencode "$default_branch")?recursive=1"

        markers=()
        while IFS= read -r _m; do
          [[ -n "$_m" ]] && markers+=("$_m")
        done < <(
          gh api --hostname "$github_host" "$tree_endpoint" 2>/dev/null \
            | jq -r '
                .tree[]?
                | select(.type=="blob")
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

        [[ ${#markers[@]} -eq 0 ]] && continue

        for marker in "${markers[@]}"; do
          encoded_marker="$(urlencode "$marker")"
          raw_endpoint="/repos/${repo_path}/contents/${encoded_marker}?ref=$(urlencode "$default_branch")"
          raw="$(gh api --hostname "$github_host" -H 'Accept: application/vnd.github.raw' "$raw_endpoint" 2>/dev/null || true)"
          emit_marker_result "github" "$org" "$github_host" "$repo_path" "$repo_id" "$default_branch" "$web_url" "$clone_url" "$marker" "$raw" >> "$results"
        done
      done
done

if [[ "$format" == "json" ]]; then
  jq -sc '.' "$results"
else
  jq -sr '
    sort_by(.provider, .scope, .repo_path, .skill_name, .skill_path)
    | .[]
    | "provider: \(.provider)\nscope: \(.scope)\nrepo: \(.repo_path)\nskill: \(.skill_name)\ndetected_by: \(.detector)\npath: \(.skill_path)\nmain_functionality: \(.main_functionality // "")\n"
  ' "$results"
fi
