---
name: uq-metrics-evaluator
description: 'Use when the user asks for model evaluation, accuracy, calibration, or uncertainty quantification (UQ) analysis from CSV data. Handles both regression (MAE, RMSE, R², calibration) and classification (accuracy, F1, ROC-AUC, ECE, confusion matrix). Discovers the right CSV files and columns from prompt intent, then runs evaluation with artifact outputs.'
# user-invocable: true
# disable-model-invocation: false
allowed-tools: Bash(uv *) Read Glob Grep
---

# Model Accuracy and Calibration Analysis

## Arguments

The user provides a dataset or folder path and optional flags.

Expected format: `<dataset_or_folder> [--task {regression|classification}] [--pred <file>] [--truth <file>]`

What to specify:
- Dataset or folder path to analyze
- Task type (regression or classification) if not auto-detectable
- Specific prediction/truth/probability column names or files if needed

Examples:
- `./data` — auto-discover files in directory
- `predictions.csv ground_truth.csv` — explicit files
- `./results --task classification` — force classification mode

## Overview

This skill performs end-to-end model evaluation from CSV files using two tools:
- [csv_reader_tool](./scripts/csv_reader_tool.py) — schema/statistics inspection
- [evaluate_metrics_tool](./scripts/evaluate_metrics_tool.py) — regression accuracy and UQ calibration
- [evaluate_classification_tool](./scripts/evaluate_classification_tool.py) — classification metrics and probabilistic calibration

Core behavior:
1. Determine task type (regression or classification) from the user's prompt and inspected column types.
2. Discover and inspect candidate CSV files.
3. Select relevant columns and run the appropriate evaluation tool.
4. Return a concise analysis with artifact locations.

## Environment Bootstrap

Use ephemeral `uv run --with` execution to avoid creating dependency files in the repository.

Schema inspection (both task types):
```bash
uv run --with pandas --with pydantic \
    scripts/csv_reader_tool.py <file.csv>
```

Regression evaluation:
```bash
uv run --with pandas --with pydantic --with numpy --with uncertainty-toolbox --with matplotlib --with seaborn \
    scripts/evaluate_metrics_tool.py <predictions.csv> <ground_truth.csv> \
    --pred-col <prediction_column> \
    --truth-col <truth_column> \
    [--uncertainty-col <uncertainty_column>]
```

Classification evaluation:
```bash
uv run --with pandas --with pydantic --with numpy --with scikit-learn --with matplotlib --with seaborn \
    scripts/evaluate_classification_tool.py <predictions.csv> <ground_truth.csv> \
    --pred-col <predicted_class_column> \
    --truth-col <true_label_column> \
    [--prob-col <positive_class_prob_column>]        # binary only
    [--prob-cols <class0_prob> <class1_prob> ...]    # multiclass
```

Validation loop for execution:
1. Run the command.
2. If dependency or import errors appear, add missing packages via `--with` and rerun.
3. Repeat until the command succeeds.

## Task Type Routing

Determine task type before selecting columns:

| Signal | Route to |
|--------|----------|
| Prompt mentions "regression", "RMSE", "MAE", "R²", "residuals", "continuous" | Regression |
| Prompt mentions "classification", "F1", "accuracy", "confusion matrix", "AUC", "labels", "classes" | Classification |
| Prediction column is continuous numeric (float, wide range) | Regression |
| Prediction column is categorical or integer with few unique values | Classification |
| Uncertainty column present with no class labels | Regression |

When ambiguous, inspect the prediction column with csv_reader_tool and use dtype and cardinality to decide. Ask the user only if inspection is inconclusive.

## Decision Logic

### 1. Resolve candidate CSV files

1. Start from paths explicitly named by the user.
2. If user gives a directory, list CSV files and rank by filename hints:
   - predictions-like: `pred`, `prediction`, `inference`, `forecast`, `output`
   - truth-like: `truth`, `target`, `label`, `actual`, `ground`
   - uncertainty/probability-like: `uncert`, `sigma`, `std`, `prob`, `score`
3. If one file appears to contain both predictions and truth, use it for both inputs.

### 2. Inspect schemas before selecting columns

Run csv_reader_tool on each candidate file first. Prefer columns that are numeric, low missingness, and semantically matched to user language.

### 3. Map semantic roles to columns

**Regression:**
- Prediction (`--pred-col`): `y_pred`, `pred`, `prediction`, `mean`, `mu`, `forecast`
- Truth (`--truth-col`): `y`, `y_true`, `truth`, `ground_truth`, `actual`, `target`
- Uncertainty (`--uncertainty-col`): `sigma`, `std`, `stddev`, `uncertainty`, `pred_std`

**Classification:**
- Predicted class (`--pred-col`): `y_pred`, `pred`, `prediction`, `class`, `label_pred`
- True label (`--truth-col`): `y`, `y_true`, `label`, `ground_truth`, `actual`, `target`
- Binary probability (`--prob-col`): `prob`, `score`, `prob_pos`, `p_pos`, `probability`
- Multiclass probabilities (`--prob-cols`): one column per class, ordered to match class order

Branching (classification):
- If predicted class + truth found, run hard-label metrics (accuracy, F1, precision, recall, confusion matrix).
- If a probability column is also found and the user asks for calibration or UQ, include ECE/MCE/Brier + reliability diagram.
- If probability column missing, run hard-label metrics only and report calibration skipped.

## Output Contract

**Regression** — return:
1. Chosen files and columns (+ rationale).
2. Accuracy metrics: `mae`, `rmse`, `r2`, `corr`, `row_count`.
3. UQ calibration (when available): `mean_calibration_error`, `rms_calibration_error`, `miscalibration_area`, `sharpness`, `nll`.
4. Artifacts: residuals CSV + residual distribution PNG; calibration CSV + calibration plot PNG.

**Classification** — return:
1. Chosen files and columns (+ rationale).
2. Hard-label metrics: `accuracy`, `precision_macro`, `recall_macro`, `f1_macro`, `num_classes`, `row_count`.
3. Probability metrics (when available): `roc_auc`, `log_loss`.
4. Calibration (when probability column present): `expected_calibration_error`, `max_calibration_error`, `brier_score`.
5. Artifacts: confusion matrix CSV + heatmap PNG; reliability diagram PNG (if probabilities available).
6. Any skipped steps or assumptions.

## Quality Checks

Before finalizing analysis, verify:
- Selected columns exist in the inspected schema.
- Prediction/truth lengths are compatible.
- Non-null rows remain after filtering.
- For regression: prediction and truth columns are numeric.
- For regression calibration: uncertainty values are strictly positive.
- For classification: at least 2 unique classes are present in truth column.
- For classification probabilities: probability columns are numeric and in [0, 1].

If checks fail, explain what failed, propose 2–3 alternative columns, and ask for clarification only when needed.

## Procedure

1. Parse the user-provided files, directory, column hints, and task type.
2. Determine task type (regression vs. classification) from prompt and schema inspection.
3. Discover and inspect candidate CSV files with csv_reader_tool.
4. Select file pair and column mapping.
5. Execute the appropriate evaluation tool.
6. Summarize metrics and interpret model behavior.
7. Report artifact paths for follow-on visualization or debugging.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running regression tool on class label columns | Inspect cardinality; route to classification tool |
| Running classification tool on continuous outputs | Inspect dtype and range; route to regression tool |
| Using `--prob-col` for multiclass | Use `--prob-cols` with one column per class |
| Requesting calibration without probability column | Run hard-label metrics only; report calibration skipped |
| Mixing row-misaligned files | Use same-row datasets or ask for join key workflow |
| Guessing columns without inspection | Always run csv_reader_tool first |
