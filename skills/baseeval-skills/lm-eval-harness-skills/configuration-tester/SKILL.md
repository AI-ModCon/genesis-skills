---
name: configuration-tester
description: Runs testing of the generated configuration for the benchmark and identifies any issues that need correction. Use this skill after the completion of the configuration-implementor skill.
---

# Steps

1. First test each of the individual functions within `tasks/{benchmark_name}/utils.py`, if it exists, to make sure they function as expected, focusing on potential edge cases. Save all custom testing scripts in `tasks/{benchmark_name}/scratch/`.

2. Update the code to fix any issues that are identified.

3. Test the functionality of each full task using `scripts/test_config.sh` in the configuration-tester skill directory. This script may take several minutes. It accepts overrides for model, model args, sample limit, and whether to enable `--run_llm_judge`, but use the default parameters unless there is a strong justification for changing them. Especially make sure that the model used is large enough to achieve better than zero accuracy on the task.
   
   **Sandbox Mode**:
   - **Issue**: lm-eval-harness requires access to `/dev/shm` (shared memory) for PyTorch/HuggingFace operations, which may be restricted in some sandbox modes
   - **Symptoms**: Errors mentioning `/dev/shm` or OpenMP shared-memory errors
   - **Solution**: Request user approval for running the test script outside the sandbox

4. Examine the outputs under `results/<task_name>/`. This will contain a `results_*.json` file with summary metrics and a `samples_*.jsonl` file with the full formatted prompts and responses for each instance.

5. Use `scripts/display_sample_results.py --no-pager` to extract the LLM inputs, LLM outputs, and resulting metrics from those files in an easily readable format when running non-interactively.

6. Check each sample in detail using the **Validation Checklist** below to verify correctness. Track checklist progress in `plan.md`.

7. If any issues are discovered, consult [references/troubleshooting.md](references/troubleshooting.md) for common failure modes and solutions. Iterate until the task behavior and metrics look correct, but stop after 3 unsuccessful iterations and ask the user for guidance.

8. Document testing results by appending a **Testing Decision Log** section to `plan.md`:
   ```markdown
   ## Testing Decision Log
   
   **Date**: <date>
   
   **Test Configuration**:
   - Model: <model used>
   - Samples tested: <number>
   - Test results: <summary of metrics>
   
   **Issues Found and Fixed**:
   - Issue 1: <description> - **Root cause**: <why it happened> - **Fix**: <what was changed>
   
   **Validation Results**:
   - All prompts formatted correctly: ✓/✗
   - Model outputs parsed successfully: ✓/✗
   - Metrics in expected range: ✓/✗
   - Spot-check accuracy: <description of manual verification>
   
   **Remaining Concerns**:
   - Concern 1: <if any> - **Severity**: <low/medium/high>
   ```

9. Finalize with a concise testing summary. Ask the user for concurrence before completion.

# Validation Checklist

Use this checklist to systematically verify test results. Copy this checklist into `plan.md` and track progress there.

## Prompt Formatting
- [ ] **Template variables replaced**: No literal `{{...}}` in prompts
- [ ] **Instructions present**: Task instructions are included if required
- [ ] **Format is correct**: Question/context/choices formatted as expected
- [ ] **Few-shot examples**: If enabled, few-shot examples appear correctly formatted
- [ ] **No truncation**: Prompts aren't unexpectedly cut off
- [ ] **Special characters**: Quotes, newlines, etc. rendered correctly

## Model Outputs
- [ ] **Non-empty**: Model generated responses (not empty strings)
- [ ] **Appropriate length**: Outputs aren't truncated too early
- [ ] **Expected format**: Outputs match expected format (e.g., A/B/C/D for multiple choice)
- [ ] **Stopped correctly**: Generation stopped at appropriate `until` tokens
- [ ] **Diverse**: Outputs vary across samples (not all identical)

## Output Parsing
- [ ] **Filter works**: Filter correctly extracts answers from outputs
- [ ] **Edge cases handled**: Handles malformed outputs gracefully
- [ ] **No errors**: No parsing errors in logs
- [ ] **Consistent results**: Same output consistently parsed the same way

## Metrics
- [ ] **In expected range**: Metrics are in valid range (e.g., 0-1 for accuracy)
- [ ] **Not all None/NaN**: Metrics computed successfully
- [ ] **Reasonable values**: Results seem plausible for the task
- [ ] **Metric breakdown**: Per-sample metrics look sensible

## Correctness Spot-Check
Manually verify at least 3 samples:
- [ ] **Sample 1**: Prompt → Output → Metric is correct
- [ ] **Sample 2**: Prompt → Output → Metric is correct
- [ ] **Sample 3**: Prompt → Output → Metric is correct

## Error Cases
- [ ] **No exceptions**: No Python exceptions in logs
- [ ] **All samples processed**: Sample count matches expected
- [ ] **No warnings**: Or warnings are understood and acceptable


# Scripts

## test_config.sh

```
./test_config.sh <benchmark_name> <path_to_task_directory> [model] [model_args] [limit] [run_llm_judge]
```

Defaults may also be supplied via `LM_EVAL_MODEL`, `LM_EVAL_MODEL_ARGS`, `LM_EVAL_LIMIT`, and `LM_EVAL_RUN_JUDGE`.

## display_sample_results.py

```
python display_sample_results.py <jsonl_sample_file> [--no-pager]
```
