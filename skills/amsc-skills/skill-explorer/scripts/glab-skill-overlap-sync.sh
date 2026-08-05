#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  glab-skill-overlap-sync.sh --group GROUP_PATH [options]

Description:
  Compare skills discovered under a GitLab group with local installations in:
  - Global: $CODEX_HOME/skills (or ~/.codex/skills)
  - Project: <current-working-directory>/.codex/skills

Options:
  --group GROUP_PATH     Group path (required), e.g. nersc/agent-skills
  --host HOST            GitLab host (default: gitlab.nersc.gov)
  --global-root PATH     Override global skills root
  --project-root PATH    Override project skills root
  --check-remote         Compare overlapping local skills against remote content
  --update               Update differing overlaps from remote snapshot
  --yes                  Do not prompt during --update
  --format FORMAT        text|json (default: text)
  -h, --help             Show help

Notes:
  - --update implies --check-remote.
  - Remote checks clone each overlapping repository with --depth 1.
USAGE
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

scan_local_root() {
  local root="$1"
  local scope="$2"

  [[ -d "$root" ]] || return 0

  local d skill_md skill_name
  for d in "$root"/*; do
    [[ -d "$d" ]] || continue
    skill_md="$d/SKILL.md"
    [[ -f "$skill_md" ]] || continue

    skill_name="$(extract_frontmatter_field name < "$skill_md" || true)"
    if [[ -z "$skill_name" ]]; then
      skill_name="$(basename "$d")"
    fi

    jq -cn \
      --arg scope "$scope" \
      --arg local_root "$root" \
      --arg local_path "$d" \
      --arg local_dir_name "$(basename "$d")" \
      --arg skill_name "$skill_name" \
      '{scope:$scope,local_root:$local_root,local_path:$local_path,local_dir_name:$local_dir_name,skill_name:$skill_name}'
  done
}

sync_dir_from_remote() {
  local src="$1"
  local dest="$2"

  # Replace destination contents while preserving destination directory.
  find "$dest" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
  cp -a "$src"/. "$dest"/
}

group=""
host="gitlab.nersc.gov"
global_root="${CODEX_HOME:-$HOME/.codex}/skills"
project_root="$PWD/.codex/skills"
check_remote="false"
do_update="false"
auto_yes="false"
format="text"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group) group="${2:-}"; shift 2 ;;
    --host) host="${2:-}"; shift 2 ;;
    --global-root) global_root="${2:-}"; shift 2 ;;
    --project-root) project_root="${2:-}"; shift 2 ;;
    --check-remote) check_remote="true"; shift ;;
    --update) do_update="true"; check_remote="true"; shift ;;
    --yes) auto_yes="true"; shift ;;
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
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not found" >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "git is required but not found" >&2
  exit 1
fi
if [[ "$format" != "text" && "$format" != "json" ]]; then
  echo "--format must be text or json" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
discover_script="$script_dir/glab-discover-group-skills.sh"
if [[ ! -x "$discover_script" ]]; then
  echo "Missing executable: $discover_script" >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
remote_json="$tmpdir/remote.json"
local_json="$tmpdir/local.json"
overlaps_json="$tmpdir/overlaps.json"
results_json="$tmpdir/results.json"

"$discover_script" --group "$group" --host "$host" --format json > "$remote_json"

{
  scan_local_root "$global_root" "global"
  scan_local_root "$project_root" "project"
} | jq -sc '.' > "$local_json"

jq -s '
  def repo_base($r): ($r.repo_path | split("/") | last);
  .[0] as $remote
  | .[1] as $local
  | [
      $remote[] as $r
      | $local[] as $l
      | select(
          ($l.skill_name == $r.skill_name) or
          ($l.local_dir_name == $r.skill_name) or
          ($l.local_dir_name == repo_base($r))
        )
      | {
          skill_name: $r.skill_name,
          repo_path: $r.repo_path,
          default_branch: $r.default_branch,
          skill_path: $r.skill_path,
          detector: $r.detector,
          main_functionality: $r.main_functionality,
          local_scope: $l.scope,
          local_path: $l.local_path,
          local_skill_name: $l.skill_name,
          remote_status: "not_checked",
          action: "none"
        }
    ]
  | unique_by(.repo_path, .skill_path, .local_path)
' "$remote_json" "$local_json" > "$overlaps_json"

if [[ "$check_remote" == "true" ]]; then
  : > "$results_json"
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue

    repo_path="$(jq -r '.repo_path' <<<"$row")"
    default_branch="$(jq -r '.default_branch // "main"' <<<"$row")"
    skill_path="$(jq -r '.skill_path' <<<"$row")"
    local_path="$(jq -r '.local_path' <<<"$row")"

    repo_url="https://${host}/${repo_path}.git"
    clone_dir="$tmpdir/clone-$(echo "$repo_path" | tr '/.' '__')"

    git clone --depth 1 --branch "$default_branch" "$repo_url" "$clone_dir" >/dev/null 2>&1 || {
      jq -cn --argjson base "$row" '{
        skill_name: $base.skill_name,
        repo_path: $base.repo_path,
        default_branch: $base.default_branch,
        skill_path: $base.skill_path,
        detector: $base.detector,
        main_functionality: $base.main_functionality,
        local_scope: $base.local_scope,
        local_path: $base.local_path,
        local_skill_name: $base.local_skill_name,
        remote_status: "remote_check_failed",
        action: "none"
      }' >> "$results_json"
      continue
    }

    skill_dir="$(dirname "$skill_path")"
    if [[ "$skill_dir" == "." ]]; then
      remote_skill_dir="$clone_dir"
    else
      remote_skill_dir="$clone_dir/$skill_dir"
    fi

    if [[ ! -d "$remote_skill_dir" ]]; then
      jq -cn --argjson base "$row" '{
        skill_name: $base.skill_name,
        repo_path: $base.repo_path,
        default_branch: $base.default_branch,
        skill_path: $base.skill_path,
        detector: $base.detector,
        main_functionality: $base.main_functionality,
        local_scope: $base.local_scope,
        local_path: $base.local_path,
        local_skill_name: $base.local_skill_name,
        remote_status: "remote_skill_path_missing",
        action: "none"
      }' >> "$results_json"
      continue
    fi

    if diff -qr --exclude .git "$local_path" "$remote_skill_dir" >/dev/null 2>&1; then
      status="up_to_date"
      action="none"
    else
      status="different"
      action="none"

      if [[ "$do_update" == "true" ]]; then
        run_update="yes"
        if [[ "$auto_yes" != "true" ]]; then
          printf "Update %s (%s) from %s? [y/N]: " "$local_path" "$(jq -r '.local_scope' <<<"$row")" "$repo_path" >&2
          read -r answer
          if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            run_update="no"
          fi
        fi

        if [[ "$run_update" == "yes" ]]; then
          sync_dir_from_remote "$remote_skill_dir" "$local_path"
          action="updated"
          if diff -qr --exclude .git "$local_path" "$remote_skill_dir" >/dev/null 2>&1; then
            status="up_to_date"
          else
            status="update_attempted_but_still_different"
          fi
        else
          action="skipped_update"
        fi
      fi
    fi

    jq -cn --argjson base "$row" --arg status "$status" --arg action "$action" '{
      skill_name: $base.skill_name,
      repo_path: $base.repo_path,
      default_branch: $base.default_branch,
      skill_path: $base.skill_path,
      detector: $base.detector,
      main_functionality: $base.main_functionality,
      local_scope: $base.local_scope,
      local_path: $base.local_path,
      local_skill_name: $base.local_skill_name,
      remote_status: $status,
      action: $action
    }' >> "$results_json"
  done < <(jq -c '.[]' "$overlaps_json")

  jq -sc '.' "$results_json" > "$results_json.tmp" && mv "$results_json.tmp" "$results_json"
else
  cp "$overlaps_json" "$results_json"
fi

if [[ "$format" == "json" ]]; then
  cat "$results_json"
  exit 0
fi

remote_count="$(jq 'length' "$remote_json")"
local_count="$(jq 'length' "$local_json")"
overlap_count="$(jq 'length' "$results_json")"

echo "Discovered remote skill candidates: $remote_count"
echo "Discovered local installed skills: $local_count"
echo "Overlaps: $overlap_count"

if [[ "$overlap_count" -eq 0 ]]; then
  exit 0
fi

echo
jq -r '
  sort_by(.skill_name, .local_scope, .local_path)
  | .[]
  | [
      "skill=" + .skill_name,
      "repo=" + .repo_path,
      "scope=" + .local_scope,
      "local=" + .local_path,
      "status=" + .remote_status,
      "action=" + .action
    ]
  | join(" | ")
' "$results_json"
