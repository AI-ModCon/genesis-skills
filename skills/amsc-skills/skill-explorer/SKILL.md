---
name: skill-explorer
description: Discover and manage agent skills stored in repositories across multiple GitLab groups and GitHub organizations for Codex CLI, Claude Code, and OpenCode CLI. Use when you need to list repositories under GitLab/GitHub scopes, detect repositories containing skills (SKILL.md/AGENTS.md), summarize available skills and their main functionality, compare with locally installed global/project skills across those CLIs, check overlap status against remote content, and optionally update local installs to match remote repositories.
compatibility: Overlap-sync and GitLab-discover scripts require bash >= 4 and gawk (standard on Linux; on macOS install via `brew install bash gawk`)
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# Skill Explorer

Use this skill to audit and sync skills across GitLab groups and GitHub organizations for multiple CLI ecosystems.

## Preconditions

1. Verify required tools:
```bash
jq --version
git --version
glab --version   # needed for GitLab scopes
gh --version     # needed for GitHub scopes
```

2. Verify auth and hosts as needed:
```bash
# GitLab
glab auth status || glab auth login
glab config set -g host gitlab.nersc.gov

# GitHub
gh auth status || gh auth login
```

## Scripts

### 1) List repositories in one GitLab group

```bash
scripts/glab-list-group-repos.sh --group nersc/agent-skills
```

### 2) List repositories in one GitHub organization

```bash
scripts/gh-list-org-repos.sh --org my-org
```

### 3) Discover skills across multiple scopes

```bash
scripts/skill-explorer-discover.sh \
  --gitlab-group nersc/agent-skills \
  --gitlab-group nersc/other-skill-group \
  --github-org my-org \
  --github-org my-other-org
```

Useful options:
- `--gitlab-host <host>`
- `--github-host <host>`
- `--no-subgroups` (GitLab)
- `--include-shared` (GitLab)
- `--format json`

Detection markers:
- `SKILL.md` (primary signal)
- `AGENTS.md` (secondary signal)
- `CLAUDE.md` (secondary signal)

### 4) Compare discovered skills with local installs

```bash
scripts/skill-explorer-overlap-sync.sh \
  --gitlab-group nersc/agent-skills \
  --github-org my-org
```

Default local roots checked:
- Codex global: `${CODEX_HOME:-$HOME/.codex}/skills`
- Codex project: `$PWD/.codex/skills`
- Claude global: `$HOME/.claude/skills`
- Claude project: `$PWD/.claude/skills`
- OpenCode global: `${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills`
- OpenCode project: `$PWD/.opencode/skills`

Restrict checks to selected CLIs:
```bash
scripts/skill-explorer-overlap-sync.sh \
  --gitlab-group nersc/agent-skills \
  --cli codex --cli claude
```

Include OpenCode compatibility-mode roots (optional):
```bash
scripts/skill-explorer-overlap-sync.sh \
  --gitlab-group nersc/agent-skills \
  --cli opencode \
  --include-compat-roots
```
Compatibility roots scanned when enabled:
- `$HOME/.opencode/agent`
- `$PWD/.claude/agents`
- `$PWD/.agents`

### 5) Check whether overlapping local installs are up to date

```bash
scripts/skill-explorer-overlap-sync.sh \
  --gitlab-group nersc/agent-skills \
  --github-org my-org \
  --check-remote
```

Status values:
- `up_to_date`: local content matches remote snapshot
- `different`: local content differs from remote snapshot
- `remote_check_failed`: remote repository could not be checked
- `remote_skill_path_missing`: detected skill path not found in cloned snapshot

### 6) Update overlapping local installs from remote

```bash
# Prompt before each update
scripts/skill-explorer-overlap-sync.sh \
  --gitlab-group nersc/agent-skills \
  --github-org my-org \
  --update

# Non-interactive update
scripts/skill-explorer-overlap-sync.sh \
  --gitlab-group nersc/agent-skills \
  --github-org my-org \
  --update --yes
```

## Compatibility Notes

- Legacy GitLab-only scripts remain available:
  - `scripts/glab-discover-group-skills.sh`
  - `scripts/glab-skill-overlap-sync.sh`
- `scripts/skill-explorer-overlap-sync.sh` also accepts `--group` and `--host` as aliases for GitLab-only usage.

## Operational Notes

- Prefer `--check-remote` before `--update`.
- Use `--format json` for machine-readable output and downstream automation.
- When a repository contains multiple `SKILL.md` files, each one is treated as a separate discovered skill entry.
- Remote checks clone repositories with `--depth 1` for speed.
