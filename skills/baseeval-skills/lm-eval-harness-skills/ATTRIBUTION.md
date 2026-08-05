# Attribution

The skills in this directory were sourced from the **eval-agents** project.

**Original repository:** https://gitlab.osti.gov/modcon-base/base-eval/eval-agents

**Author:** Emily Saldanha, Pacific Northwest National Laboratory (PNNL)

These skills were retrieved from the `lm-eval-harness-skills/` directory of the
upstream repository and are included here as retrieved, unmodified. Please refer
to the original repository for the most current licensing information and terms
of use.

Skills included:
- `configuration-creator` — Orchestrates the end-to-end workflow for developing
  evaluation configurations for novel benchmark tasks within the EleutherAI
  lm-evaluation-harness framework.
- `configuration-planner` — Reads the benchmark information provided by the user,
  clarifies missing details, and drafts a high-level plan for the configuration.
- `data-exploration` — Writes Python scripts to ingest user-provided data and
  perform the analysis needed to determine key configuration components.
- `configuration-implementor` — Creates the YAML file and associated `utils.py`
  code that define the benchmark configuration.
- `configuration-tester` — Runs testing of the generated configuration and
  identifies any issues that need correction.
