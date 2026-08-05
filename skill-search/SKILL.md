---
name: skill-search
description: Load or search a centrally managed skills catalog plus optional user-provided skills. Use when an agent needs either the full list of available skills up front or an iterative search tool for multi-turn discovery without loading the whole catalog into context.
compatibility: Designed to live next to a sibling skills directory on a filesystem-based agent runtime. Also supports an explicit central root or the SKILL_SEARCH_CENTRAL_ROOT environment variable for alternate deployments.
allowed-tools: Bash
---
# Skill Search

Use this helper when an agent needs one of two discovery strategies:

1. **Skill search** — accept a query and return only the top-k keyword matches. Keeps the full catalog out of context; scales to large catalogs.
2. **Standard progressive disclosure** — return a compact index of every skill (name, description, path) upfront, then load the full SKILL.md body for whichever skill the agent selects.

## Configuration

- `my_skills_path`: optional user-managed skills root. Repeat if more than one user root is needed.

The helper resolves the central catalog in this order: the `--central-root` flag, then the `SKILL_SEARCH_CENTRAL_ROOT` environment variable, then a sibling `../skills` directory. To make this skill expose the Genesis catalog, symlink `skill-search/` into your agent's skills dir and (if it isn't beside `skills/`) point one of those at the catalog. The alternative — flattening every skill into a client skills directory for direct discovery — is handled by the repo's `unpack.sh` (`./unpack.sh --help`).

## Skill search

Use when the agent should search on demand rather than hold the full catalog in context:

```bash
python scripts/skill_search.py --query "draft a Slurm batch script for a four-GPU job"
```

With a user-provided skills path and a custom result limit:

```bash
python scripts/skill_search.py \
  --query "validate Croissant metadata for an ML dataset" \
  --top-k 3 \
  --my-skills-path /path/to/my/skills
```

Scoring weights name token matches (×2) over description token matches (×1), with substring bonuses for closer matches. Results with a score below `--min-score` (default 1) are excluded.

## Standard progressive disclosure

Use when the agent should receive the full menu upfront and pick without needing a query. The compact index (names + descriptions + paths, no bodies) is loaded first; the full SKILL.md body is loaded on demand for the selected skill.

```bash
python scripts/skill_search.py --load-all
```

With a user-provided skills path:

```bash
python scripts/skill_search.py --load-all --my-skills-path /path/to/my/skills
```

After loading the index, load a selected skill's body via the Python API:

```python
from skill_search import load_skill_body
body = load_skill_body(selected_skill)
```

Pass `--include-prompt` to also receive a pre-formatted `<available_skills>` XML block suitable for injection into an agent system prompt.

## Output

The script returns machine-readable JSON so it can be called directly by agents or host tools. Unreadable catalog entries appear in the `skipped` array and as warnings on stderr; stdout remains valid JSON.

## Python API

If the agent runtime can import Python packages directly, the `skill_search` package provides:

- `search_payload(query, top_k, min_score, ...)` — skill search: returns top-k scored matches
- `progressive_disclosure_payload(...)` — standard progressive disclosure: returns compact index of all skills
- `load_skill_body(skill)` — load the full SKILL.md body for a selected skill
- `discover_skills(paths)` — discover all skills from one or more roots
- `to_prompt(skills)` — generate an `<available_skills>` XML block
- `build_search_callable()` — create a reusable search function with pre-configured roots

See `README.md` for details.

## Related Files

- `scripts/skill_search.py`
- `README.md`
