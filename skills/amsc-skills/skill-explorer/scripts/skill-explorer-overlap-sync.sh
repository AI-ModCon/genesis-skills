#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  skill-explorer-overlap-sync.sh [options]

Description:
  Compare remotely discovered skills with locally installed skills in:
  - Codex:    Global ${CODEX_HOME:-~/.codex}/skills, Project .codex/skills
  - Claude:   Global ~/.claude/skills, Project .claude/skills
  - OpenCode: Global ${XDG_CONFIG_HOME:-~/.config}/opencode/skills, Project .opencode/skills

Sources:
  --gitlab-group GROUP      GitLab group path (repeatable)
  --github-org ORG          GitHub organization (repeatable)

Options:
  --gitlab-host HOST        GitLab host (default: gitlab.nersc.gov)
  --github-host HOST        GitHub host (default: github.com)
  --group GROUP             Backward-compatible alias for --gitlab-group
  --host HOST               Backward-compatible alias for --gitlab-host
  --cli CLI                codex|claude|opencode|all (repeatable, default: all)
  --global-root PATH        Add an extra global skills root to scan
  --project-root PATH       Add an extra project skills root to scan
  --include-compat-roots    Include optional OpenCode compatibility-mode roots:
                            ~/.opencode/agent, .claude/agents, .agents/
  --check-remote            Compare overlap content against remote repo snapshots
  --update                  Update differing overlaps from remote snapshots
  --yes                     Do not prompt during --update
  --format FORMAT           text|json (default: text)
  -h, --help                Show help

Notes:
  - --update implies --check-remote.
  - At least one source scope is required.
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
  local cli="$3"
  local kind="$4"

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
      --arg local_cli "$cli" \
      --arg local_kind "$kind" \
      --arg local_root "$root" \
      --arg local_path "$d" \
      --arg local_dir_name "$(basename "$d")" \
      --arg skill_name "$skill_name" \
      '{scope:$scope,local_cli:$local_cli,local_kind:$local_kind,local_root:$local_root,local_path:$local_path,local_dir_name:$local_dir_name,skill_name:$skill_name}'
  done
}

sync_dir_from_remote() {
  local src="$1"
  local dest="$2"
  find "$dest" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
  cp -a "$src"/. "$dest"/
}

gitlab_groups=()
github_orgs=()
selected_clis=()
gitlab_host="gitlab.nersc.gov"
github_host="github.com"
global_root=""
project_root=""
check_remote="false"
do_update="false"
auto_yes="false"
include_compat_roots="false"
format="text"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gitlab-group|--group) gitlab_groups+=("${2:-}"); shift 2 ;;
    --github-org) github_orgs+=("${2:-}"); shift 2 ;;
    --cli) selected_clis+=("${2:-}"); shift 2 ;;
    --gitlab-host|--host) gitlab_host="${2:-}"; shift 2 ;;
    --github-host) github_host="${2:-}"; shift 2 ;;
    --global-root) global_root="${2:-}"; shift 2 ;;
    --project-root) project_root="${2:-}"; shift 2 ;;
    --include-compat-roots) include_compat_roots="true"; shift ;;
    --check-remote) check_remote="true"; shift ;;
    --update) do_update="true"; check_remote="true"; shift ;;
    --yes) auto_yes="true"; shift ;;
    --format) format="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ${#gitlab_groups[@]} -eq 0 && ${#github_orgs[@]} -eq 0 ]]; then
  echo "Provide at least one --gitlab-group/--group or --github-org" >&2
  usage
  exit 1
fi
if [[ ${#selected_clis[@]} -eq 0 ]]; then
  selected_clis=("all")
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
discover_script="$script_dir/skill-explorer-discover.sh"
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

discover_args=(--format json --gitlab-host "$gitlab_host" --github-host "$github_host")
for g in "${gitlab_groups[@]}"; do discover_args+=(--gitlab-group "$g"); done
for o in "${github_orgs[@]}"; do discover_args+=(--github-org "$o"); done
"$discover_script" "${discover_args[@]}" > "$remote_json"

if [[ " ${selected_clis[*]} " == *" all "* ]]; then
  effective_clis=("codex" "claude" "opencode")
else
  effective_clis=()
  for cli in "${selected_clis[@]}"; do
    case "$cli" in
      codex|claude|opencode) effective_clis+=("$cli") ;;
      *)
        echo "Invalid --cli value: $cli (use codex|claude|opencode|all)" >&2
        exit 1
        ;;
    esac
  done
fi

declare -A seen_clis=()
deduped_clis=()
for cli in "${effective_clis[@]}"; do
  if [[ -z "${seen_clis[$cli]+x}" ]]; then
    seen_clis[$cli]=1
    deduped_clis+=("$cli")
  fi
done
effective_clis=("${deduped_clis[@]}")

default_codex_global="${CODEX_HOME:-$HOME/.codex}/skills"
default_codex_project="$PWD/.codex/skills"
default_claude_global="$HOME/.claude/skills"
default_claude_project="$PWD/.claude/skills"
default_opencode_global="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills"
default_opencode_project="$PWD/.opencode/skills"
default_opencode_compat_global="$HOME/.opencode/agent"
default_opencode_compat_project_a="$PWD/.claude/agents"
default_opencode_compat_project_b="$PWD/.agents"

{
  for cli in "${effective_clis[@]}"; do
    case "$cli" in
      codex)
        scan_local_root "$default_codex_global" "global" "codex" "default"
        scan_local_root "$default_codex_project" "project" "codex" "default"
        ;;
      claude)
        scan_local_root "$default_claude_global" "global" "claude" "default"
        scan_local_root "$default_claude_project" "project" "claude" "default"
        ;;
      opencode)
        scan_local_root "$default_opencode_global" "global" "opencode" "default"
        scan_local_root "$default_opencode_project" "project" "opencode" "default"
        if [[ "$include_compat_roots" == "true" ]]; then
          scan_local_root "$default_opencode_compat_global" "global" "opencode" "compat"
          scan_local_root "$default_opencode_compat_project_a" "project" "opencode" "compat"
          scan_local_root "$default_opencode_compat_project_b" "project" "opencode" "compat"
        fi
        ;;
    esac
  done

  if [[ -n "$global_root" ]]; then
    scan_local_root "$global_root" "global" "custom" "override"
  fi
  if [[ -n "$project_root" ]]; then
    scan_local_root "$project_root" "project" "custom" "override"
  fi
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
          provider: $r.provider,
          scope: $r.scope,
          host: $r.host,
          skill_name: $r.skill_name,
          repo_path: $r.repo_path,
          clone_url: $r.clone_url,
          default_branch: $r.default_branch,
          skill_path: $r.skill_path,
          detector: $r.detector,
          main_functionality: $r.main_functionality,
          local_scope: $l.scope,
          local_cli: $l.local_cli,
          local_kind: $l.local_kind,
          local_path: $l.local_path,
          local_skill_name: $l.skill_name,
          remote_status: "not_checked",
          action: "none"
        }
    ]
  | unique_by(.provider, .repo_path, .skill_path, .local_path)
' "$remote_json" "$local_json" > "$overlaps_json"

if [[ "$check_remote" == "true" ]]; then
  : > "$results_json"
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue

    clone_url="$(jq -r '.clone_url // empty' <<<"$row")"
    repo_path="$(jq -r '.repo_path' <<<"$row")"
    default_branch="$(jq -r '.default_branch // "main"' <<<"$row")"
    skill_path="$(jq -r '.skill_path' <<<"$row")"
    local_path="$(jq -r '.local_path' <<<"$row")"

    if [[ -z "$clone_url" ]]; then
      clone_url="https://$(jq -r '.host' <<<"$row")/${repo_path}.git"
    fi

    clone_dir="$tmpdir/clone-$(echo "$(jq -r '.provider' <<<"$row")-${repo_path}" | tr '/.:' '___')"

    git clone --depth 1 --branch "$default_branch" "$clone_url" "$clone_dir" >/dev/null 2>&1 || {
      jq -cn --argjson base "$row" '{
        provider: $base.provider,
        scope: $base.scope,
        host: $base.host,
        skill_name: $base.skill_name,
        repo_path: $base.repo_path,
        clone_url: $base.clone_url,
        default_branch: $base.default_branch,
        skill_path: $base.skill_path,
        detector: $base.detector,
        main_functionality: $base.main_functionality,
        local_scope: $base.local_scope,
        local_cli: $base.local_cli,
        local_kind: $base.local_kind,
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
        provider: $base.provider,
        scope: $base.scope,
        host: $base.host,
        skill_name: $base.skill_name,
        repo_path: $base.repo_path,
        clone_url: $base.clone_url,
        default_branch: $base.default_branch,
        skill_path: $base.skill_path,
        detector: $base.detector,
        main_functionality: $base.main_functionality,
        local_scope: $base.local_scope,
        local_cli: $base.local_cli,
        local_kind: $base.local_kind,
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
      provider: $base.provider,
      scope: $base.scope,
      host: $base.host,
      skill_name: $base.skill_name,
      repo_path: $base.repo_path,
      clone_url: $base.clone_url,
      default_branch: $base.default_branch,
      skill_path: $base.skill_path,
      detector: $base.detector,
      main_functionality: $base.main_functionality,
      local_scope: $base.local_scope,
      local_cli: $base.local_cli,
      local_kind: $base.local_kind,
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
  sort_by(.provider, .scope, .skill_name, .local_scope, .local_path)
  | .[]
  | [
      "provider=" + .provider,
      "scope=" + .scope,
      "skill=" + .skill_name,
      "repo=" + .repo_path,
      "cli_local=" + .local_cli,
      "kind_local=" + .local_kind,
      "scope_local=" + .local_scope,
      "local=" + .local_path,
      "status=" + .remote_status,
      "action=" + .action
    ]
  | join(" | ")
' "$results_json"
