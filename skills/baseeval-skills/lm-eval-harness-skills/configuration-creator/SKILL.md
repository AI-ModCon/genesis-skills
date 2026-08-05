---
name: configuration-creator
description: Develop evaluation configurations for novel benchmark tasks within the EleutherAI lm-evaluation-harness framework. Use when the user requests to create a new configuration or mentions a new benchmark or evaluation task. Use this skill first before any other skills when creating a new configuration.
---

# Project Goal
We aim to develop evaluation configurations for novel benchmark tasks within the EleutherAI lm-evaluation-harness framework.

# Development Steps
Follow each step below in order:
1. The user will provide information about the location of the data and any relevant details about the data and task. Create a new directory `tasks/{benchmark_name}/` if it does not already exist.  

2. Using the configuration-planner skill, ask any questions needed to resolve ambiguities and write a high-level plan for the configuration using the provided template.
   - **Validation**: Verify `tasks/{benchmark_name}/plan.md` exists and contains all required sections before proceeding.

3. Using the data-exploration skill, explore the data provided by the user. If necessary, write Python code to analyze the data to understand its contents and what preprocessing, formatting, and filtering steps might be needed.
   - **Validation**: Check that analysis scripts ran successfully and `plan.md` was updated with concrete findings.

4. Using the configuration-implementor skill, create at least one YAML file specifying the task and, if needed, place supporting code in a Python script called `utils.py`.
   - **Validation**: Verify YAML file is valid (no syntax errors) and required functions exist in `utils.py`.

5. Using the configuration-tester skill, test the generated configuration files and iterate on the above steps if necessary to correct any issues.
   - **Validation**: All test samples should process without errors; metrics should be in expected ranges.

6. Present the final artifacts, summarize assumptions, and ask the user only if unresolved tradeoffs remain or if they requested staged concurrence.

# Guidance

## When to Proceed Automatically vs. Ask User
* **Proceed automatically** when:
  - Making low-risk design choices with reasonable defaults
  - Standard patterns apply (e.g., multiple-choice task with accuracy metric)
  - Fixing clear bugs or syntax errors
  - Iterating based on test results with obvious corrections

* **Ask the user** when:
  - Fundamental ambiguity about task semantics (e.g., what counts as a correct answer?)
  - Multiple valid approaches with significant tradeoffs
  - Data quality issues that affect evaluation validity
  - Custom metric definition is unclear

## General Guidelines
* Default to repo-root-relative paths under `tasks/{benchmark_name}/...`.
* For any temporary analysis scripts and artifacts, create a directory at `tasks/{benchmark_name}/scratch/` and place them there.
* Write reusable analysis scripts to files rather than embedding long Python snippets in shell commands.
* Keep simple filtering or prompt formatting steps in the YAML config file, while more complex operations should be implemented in the associated `utils.py` file.
* Whenever possible, use huggingface datasets for data downloading and management, unless specified by the user that a local dataset or other source is being used.
* If the user points to preexisting evaluation code, please install any packages needed to allow access to necessary functions.
* Make sure to consider any special instructions that should be provided to the LLM as far as output format when crafting the benchmark examples.
* For free form LLM outputs, carefully consider how to extract and process the relevant outputs to be compared with the ground truth answer. Any functions for this should be tested thoroughly.
* Make reasonable low-risk assumptions when needed, and record them in `plan.md`. Ask the user only when ambiguity would materially change the benchmark configuration or evaluation semantics.
