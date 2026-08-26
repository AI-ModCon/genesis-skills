---
name: configuration-planner
description: Reads the information about the benchmark provided by the user, asks any additional questions to clarify missing details, and makes a plan for the design of the configuration. Use when beginning an evaluation configuration creation task. Do not use this skill until you have first loaded the configuration-creator skill.
---

# Steps

Follow these steps to make a plan for configuration creation:
1. Read the information provided by the user to understand the benchmark data
2. Read only the reference files needed for this benchmark from [configuration files](references/config_files.md), [new task creation](references/new_task_guide.md), [more details on task creation](references/task_guide.md), [common pitfalls](references/footguns.md), and [troubleshooting guide](references/troubleshooting.md).
3. Resolve the benchmark task, dataset, and metrics and how they should map to lm-eval-harness parameters. Ask the user targeted questions only for missing information that would materially change the configuration; otherwise make a reasonable assumption and record it in the plan.
4. Create `tasks/{benchmark_name}/` if needed.
5. Write a summary of the plan using the [assets/plan_template.md](assets/plan_template.md) format and save it to `tasks/{benchmark_name}/plan.md`.
6. Provide a concise checkpoint summary. Ask the user for concurrence before proceeding to data analysis.

# Key questions to answer (ask user if not clear):
- Is the data provided locally or from huggingface?
- Is the task output multiple choice (fixed set of options) or free form?
- What prompt template should be used?
- Should few shot examples be provided?
- What metrics should be used to evaluate the outputs? Are these built in metrics or will they require custom implementation?

# Important instructions:
- During the planning stage, focus on the high-level approach plus the key implementation contracts needed for later stages. Fine-grained data processing details can be refined later.
- CRITICAL: Do not create the YAML file or `utils.py` at this stage. Only create `plan.md`.
