# `search_example`

This directory contains a unified, runnable demo that exercises the [`skill-search`](..) helper in two phases:

1. Full catalog load:
   read all skills from the configured central catalog and print the discovered list.
2. Iterative discovery:
   load the search tool into a simple LangGraph flow and run several sample requests.

## Prerequisites

- Python 3.11+
- Install example dependencies:

```bash
pip install -r requirements.txt
```

The `skill-search` core itself is path-based and stdlib-only; these dependencies are only for the LangGraph demo layer.

## Run

From this directory:

```bash
python run_demo.py
```

The demo defaults to:

- `--model-endpoint http://localhost:1234/v1`
- `--central-root ../../skills`

That points directly at this repository's 25-skill catalog.

## What The Demo Does

### Phase 1: Full Catalog Load

- calls `../scripts/skill_search.py --load-all --include-prompt`
- prints the merged catalog roots
- prints all 25 discovered skills with each skill's name, description, and `SKILL.md` path

### Phase 2: Iterative Discovery

- wraps the same `skill_search.py` script as a search tool
- creates a small LangGraph flow around that tool
- runs three sample tasks by default:
  - `search scientific literature and organize bibliography citations`
  - `draft a Slurm script for a four-GPU job`
  - `validate Croissant metadata for an ML dataset`
- loads a preview of the selected skill's instructions without executing skill-specific actions

## Model Behavior

If the configured model endpoint is available, the demo uses it for:

- planning a discovery query
- selecting one skill from the discovered candidates

If the model endpoint is unavailable, the demo still runs end to end by falling back to heuristic search and top-result selection.

## Useful Flags

Override the model endpoint (any OpenAI-compatible endpoint):

```bash
python run_demo.py --model-endpoint "http://localhost:1234/v1"
```

Override the central skills root:

```bash
python run_demo.py --central-root /opt/doe/skills
```

Add one or more user-managed roots:

```bash
python run_demo.py \
  --my-skills-path ~/my-team-skills \
  --my-skills-path ~/personal-skills
```

Replace the built-in sample tasks:

```bash
python run_demo.py \
  --sample-task "write a Gkeyll plasma simulation input file" \
  --sample-task "design an Academy multi-agent scientific workflow" \
  --sample-task "evaluate uncertainty calibration from CSV data"
```
