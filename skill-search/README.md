# `skill-search`

`skill-search` is a self-contained, path-based helper for working with a central skills catalog plus optional user-provided skill roots.

It is designed for the DOE-style deployment shape where a helper directory sits next to a centrally maintained `skills/` directory:

```text
deploy-root/
├── skills/
└── skill-search/
```

## What It Provides

- Full catalog loading:
  returns all merged skill `name`, `description`, and path metadata.
- Iterative search:
  returns only the top matching skills for a query, which keeps the full catalog out of prompt context.
- User override support:
  later roots win when the same skill `name` appears in both the central catalog and a user-managed root.

The core runtime uses only the Python standard library.

## Root Resolution

The helper resolves the central catalog in this order:

1. `--central-root` if provided
2. `SKILL_SEARCH_CENTRAL_ROOT` environment variable
3. sibling `../skills` next to `skill-search`

Optional user-managed roots can be added with repeated `--my-skills-path` flags.

## Script Usage

The stable path-based entrypoint is:

```bash
python scripts/skill_search.py
```

### Full Catalog Load

```bash
python scripts/skill_search.py --load-all --include-prompt
```

With explicit roots:

```bash
python scripts/skill_search.py \
  --central-root /opt/doe/skills \
  --my-skills-path ~/my-team-skills \
  --load-all \
  --include-prompt
```

### Iterative Search

```bash
python scripts/skill_search.py --query "draft a Slurm batch script for a four-GPU job"
```

With explicit roots:

```bash
python scripts/skill_search.py \
  --central-root /opt/doe/skills \
  --my-skills-path ~/my-team-skills \
  --query "validate Croissant metadata for an ML dataset" \
  --top-k 5
```

## Output Format

The script always returns JSON.

Catalog entries that cannot be read are skipped rather than aborting the whole
request. Each skip is included as `{path, reason}` in the `skipped` array and is
also repeated as a warning on stderr; stdout remains valid JSON. `count` covers
usable skills or matches and does not include skipped entries.

Full-load mode returns:

- `mode`
- `central_root`
- `catalog_roots`
- `count`
- `skills`
- `skipped`
- `available_skills_prompt` when `--include-prompt` is used

Search mode returns:

- `mode`
- `query`
- `top_k`
- `min_score`
- `central_root`
- `catalog_roots`
- `count`
- `matches`
- `skipped`

## As A Skill

This directory includes `SKILL.md` so filesystem-based agents can treat it as a skill wrapper and follow the documented workflow there. To expose the Genesis catalog through it, symlink `skill-search/` into your agent's skills dir; to expose each skill directly to a compatible client instead, use the repo's `unpack.sh` (`./unpack.sh --help`).

The importable Python package lives under `skill-search/skill_search/` so the outer directory can keep the validator-friendly hyphenated name.

The frontmatter parser handles single-line scalars, quoted values, YAML folded/literal block scalars (`description: >` / `|`), and a nested `metadata:` block.

## Deployment Model

`skill-search` is intentionally stdlib-only so it can be deployed as a standalone directory alongside a `skills/` catalog without requiring `pip install`.

## Local Demo

See [`search_example`](search_example) for a runnable end-to-end example that:

- prints the full merged 25-skill catalog
- loads the iterative search tool into a LangGraph flow
- runs sample requests for scientific literature, Slurm, and Croissant metadata
