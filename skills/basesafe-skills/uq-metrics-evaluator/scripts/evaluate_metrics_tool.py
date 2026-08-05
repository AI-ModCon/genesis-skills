from pathlib import Path
import argparse
import sys
from math import log10, floor

import numpy as np
import json

import pandas as pd
import uncertainty_toolbox as uct
from models import (
    AccuracyMetrics,
    AccuracyMetricsResult,
    ArtifactInfo,
    CalibrationMetrics,
    CalibrationMetricsResult,
    EvaluateMetricsArtifacts,
    EvaluateMetricsResult,
    MAX_ROWS,
    sanitize_error,
    validate_input_path,
    validate_output_path,
)

from plotting import save_residual_distribution_plot, save_average_calibration_plot

def load_prediction_truth_frames(
    predictions_path: str,
    ground_truth_path: str,
    allowed_root: str = ".",
) -> tuple[Path, Path, pd.DataFrame, pd.DataFrame]:
    """Load predictions and ground-truth CSVs with same-file deduplication."""
    # TODO: Add optional key-based alignment for split prediction/truth files; current behavior assumes row-wise alignment.
    pred_resolved = validate_input_path(predictions_path, allowed_root=allowed_root)
    truth_resolved = validate_input_path(ground_truth_path, allowed_root=allowed_root)

    pred_df = pd.read_csv(pred_resolved, nrows=MAX_ROWS)
    truth_df = pred_df if pred_resolved == truth_resolved else pd.read_csv(truth_resolved, nrows=MAX_ROWS)

    return pred_resolved, truth_resolved, pred_df, truth_df


def _compute_accuracy_metrics(
    pred_df: pd.DataFrame,
    truth_df: pd.DataFrame,
    pred_col: str,
    truth_col: str,
    artifact_path: Path,
    source_name: str,
) -> AccuracyMetricsResult:
    missing_pred = [c for c in [pred_col] if c not in pred_df.columns]
    if missing_pred:
        raise ValueError(
            f"Column(s) not found in predictions CSV: {missing_pred}. Available columns: {pred_df.columns.tolist()}"
        )

    missing_truth = [c for c in [truth_col] if c not in truth_df.columns]
    if missing_truth:
        raise ValueError(
            f"Column(s) not found in ground truth CSV: {missing_truth}. Available columns: {truth_df.columns.tolist()}"
        )

    df = pd.DataFrame({truth_col: truth_df[truth_col], pred_col: pred_df[pred_col]}).dropna()

    if df.empty:
        raise ValueError("No valid rows remain after dropping rows with missing values.")

    if len(pred_df[pred_col]) != len(truth_df[truth_col]):
        raise ValueError(
            f"Prediction ({len(pred_df[pred_col])}) and truth ({len(truth_df[truth_col])}) have different lengths."
        )

    for col in (truth_col, pred_col):
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column '{col}' is not numeric (dtype: {df[col].dtype}).")

    y_true = df[truth_col].to_numpy(dtype=float)
    y_pred = df[pred_col].to_numpy(dtype=float)

    residuals = y_true - y_pred
    accuracy_metrics = uct.metrics.get_all_accuracy_metrics(y_pred, y_true, verbose=False)

    metrics = {
        "mae": float(accuracy_metrics["mae"]),
        "rmse": float(accuracy_metrics["rmse"]),
        "mdae": float(accuracy_metrics["mdae"]),
        "marpd": float(accuracy_metrics["marpd"]),
        "r2": float(accuracy_metrics["r2"]),
        "corr": float(accuracy_metrics["corr"]),
        "row_count": len(df),
    }

    artifact_df = df.copy().reset_index(drop=True)
    artifact_df["residual"] = residuals
    artifact_df["abs_residual"] = np.abs(residuals)
    artifact_df["pct_diff"] = (residuals / np.where(y_true == 0, np.nan, y_true)) * 100

    artifact_columns = [truth_col, pred_col, "residual", "abs_residual", "pct_diff"]

    plot_path = artifact_path.with_name(f"{artifact_path.stem}_distribution.png")

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_df[artifact_columns].to_csv(artifact_path, index=False)
    save_residual_distribution_plot(residuals=residuals, plot_path=plot_path)

    description = (
        f"Each row corresponds to one prediction from '{source_name}'. "
        f"'{truth_col}' is the ground truth, '{pred_col}' is the model prediction. "
        f"'residual' is y_true - y_pred. "
        f"'abs_residual' is the absolute residual, useful for sorting by largest errors. "
        f"'pct_diff' is the signed percentage difference relative to y_true (NaN where y_true is 0). "
        f"Use this file to plot a predicted-vs-actual scatter plot (x={pred_col}, y={truth_col}), "
        f"a residual histogram (x=residual), and an abs_residual CDF for error analysis."
    )

    return AccuracyMetricsResult(
        metrics=AccuracyMetrics(**metrics),
        artifact=ArtifactInfo(
            path=str(artifact_path),
            format="csv",
            columns=artifact_columns,
            description=description,
        ),
        plot_artifact=ArtifactInfo(
            path=str(plot_path),
            format="png",
            columns=[],
            description=(
                f"Residual distribution plot for '{source_name}'. "
                f"Histogram and KDE summarize residual spread, and the dashed line marks zero error. "
                f"Use this plot to quickly assess bias (center shift) and error dispersion."
            ),
        ),
    )

def _compute_calibration_metrics(
    pred_df: pd.DataFrame,
    truth_df: pd.DataFrame,
    pred_col: str,
    truth_col: str,
    uncertainty_col: str,
    artifact_path: Path,
    source_name: str,
) -> CalibrationMetricsResult:
    # Suggestion: Extend uncertainty input handling to support interval-style schemas (e.g., lower/upper bounds) in addition to std/sigma columns.
    required_pred = [pred_col, uncertainty_col]
    missing_pred = [c for c in required_pred if c not in pred_df.columns]
    if missing_pred:
        raise ValueError(
            f"Column(s) not found in predictions CSV: {missing_pred}. "
            f"Available columns: {pred_df.columns.tolist()}"
        )

    if truth_col not in truth_df.columns:
        raise ValueError(
            f"Column '{truth_col}' not found in ground truth CSV. "
            f"Available columns: {truth_df.columns.tolist()}"
        )

    df = pd.DataFrame(
        {
            truth_col: truth_df[truth_col],
            pred_col: pred_df[pred_col],
            uncertainty_col: pred_df[uncertainty_col],
        }
    ).dropna()

    if len(df) < 2:
        raise ValueError("Fewer than 2 valid rows remain after dropping NaNs.")

    if len(pred_df[pred_col]) != len(truth_df[truth_col]):
        raise ValueError(
            f"Prediction ({len(pred_df[pred_col])}) and truth ({len(truth_df[truth_col])}) "
            "have different lengths."
        )

    for col in [truth_col, pred_col, uncertainty_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column '{col}' is not numeric (dtype: {df[col].dtype}).")

    if (df[uncertainty_col] <= 0).any():
        n_bad = (df[uncertainty_col] <= 0).sum()
        raise ValueError(
            f"Column '{uncertainty_col}' contains {n_bad} non-positive value(s). "
            f"Predicted standard deviations must be strictly positive."
        )

    y_true = df[truth_col].to_numpy(dtype=float)
    y_pred = df[pred_col].to_numpy(dtype=float)
    y_std = df[uncertainty_col].to_numpy(dtype=float)

    cal_metrics = uct.metrics.get_all_metrics(y_pred, y_std, y_true, verbose=False)

    metrics = {
        "mean_calibration_error": float(cal_metrics["avg_calibration"]["ma_cal"]),
        "rms_calibration_error": float(cal_metrics["avg_calibration"]["rms_cal"]),
        "miscalibration_area": float(cal_metrics["avg_calibration"]["miscal_area"]),
        "sharpness": float(cal_metrics["sharpness"]["sharp"]),
        "nll": float(cal_metrics["scoring_rule"]["nll"]),
        "crps": float(cal_metrics["scoring_rule"]["crps"]),
        "check_score": float(cal_metrics["scoring_rule"]["check"]),
        "interval_score": float(cal_metrics["scoring_rule"]["interval"]),
    }

    exp_proportions, obs_proportions = uct.metrics_calibration.get_proportion_lists(
        y_pred, y_std, y_true
    )

    calibration_df = pd.DataFrame(
        {
            "expected_proportion": exp_proportions,
            "observed_proportion": obs_proportions,
            "calibration_error": obs_proportions - exp_proportions,
        }
    )

    plot_path = artifact_path.with_suffix(".png")

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    calibration_df.to_csv(artifact_path, index=False)

    save_average_calibration_plot(
        exp_proportions=exp_proportions,
        obs_proportions=obs_proportions,
        plot_path=plot_path,
    )

    description = (
        f"Calibration artifact for '{source_name}' on '{truth_col}', '{pred_col}', and '{uncertainty_col}'. "
        f"Each row represents one confidence level from 0 to 1. "
        f"'expected_proportion' is the nominal confidence level; "
        f"'observed_proportion' is the fraction of true values that actually fell "
        f"within that confidence interval. "
        f"A perfectly calibrated model has observed == expected (the diagonal). "
        f"'calibration_error' is observed - expected: positive means overconfident, "
        f"negative means underconfident. "
        f"Use this file to plot a reliability diagram (x=expected_proportion, "
        f"y=observed_proportion) with the diagonal as reference. "
        f"Combine with the residuals artifact from calculate_accuracy_metrics() "
        f"for a full evaluation dashboard."
    )

    plot_description = (
        f"Calibration reliability plot for '{source_name}'. "
        f"The dashed orange line is ideal calibration (y=x). "
        f"The blue curve is observed coverage versus expected coverage; shaded area shows deviation from ideal. "
        f"Axes are square and bounded slightly beyond [0, 1]."
    )

    return CalibrationMetricsResult(
        metrics=CalibrationMetrics(**metrics),
        artifact=ArtifactInfo(
            path=str(artifact_path),
            format="csv",
            columns=calibration_df.columns.tolist(),
            description=description,
        ),
        plot_artifact=ArtifactInfo(
            path=str(plot_path),
            format="png",
            columns=[],
            description=plot_description,
        ),
    )


def evaluate_metrics_tool(
    predictions_path: str,
    ground_truth_path: str,
    pred_col: str = "prediction",
    truth_col: str = "ground_truth",
    uncertainty_col: str | None = None,
    accuracy_output_path: str | None = None,
    calibration_output_path: str | None = None,
    run: str = "both",
    allowed_root: str = ".",
) -> EvaluateMetricsResult:
    """Evaluate model accuracy and optional calibration in one tool call."""
    if run not in {"accuracy", "calibration", "both"}:
        raise ValueError("run must be one of: 'accuracy', 'calibration', 'both'.")

    pred_resolved, _, pred_df, truth_df = load_prediction_truth_frames(
        predictions_path=predictions_path,
        ground_truth_path=ground_truth_path,
        allowed_root=allowed_root,
    )

    accuracy_result = None
    calibration_result = None
    notes: list[str] = []

    run_accuracy = run in {"accuracy", "both"}
    run_calibration = run in {"calibration", "both"}

    if run_accuracy:
        if accuracy_output_path:
            accuracy_artifact_path = validate_output_path(accuracy_output_path, allowed_root=allowed_root)
        else:
            accuracy_artifact_path = pred_resolved.parent / f"{pred_resolved.stem}_residuals.csv"

        accuracy_result = _compute_accuracy_metrics(
            pred_df=pred_df,
            truth_df=truth_df,
            pred_col=pred_col,
            truth_col=truth_col,
            artifact_path=accuracy_artifact_path,
            source_name=pred_resolved.name,
        )
    else:
        notes.append("Accuracy metrics were skipped because run mode excludes accuracy.")

    if run_calibration:
        if uncertainty_col:
            if calibration_output_path:
                calibration_artifact_path = validate_output_path(calibration_output_path, allowed_root=allowed_root)
            else:
                calibration_artifact_path = pred_resolved.parent / f"{pred_resolved.stem}_calibration.csv"

            calibration_result = _compute_calibration_metrics(
                pred_df=pred_df,
                truth_df=truth_df,
                pred_col=pred_col,
                truth_col=truth_col,
                uncertainty_col=uncertainty_col,
                artifact_path=calibration_artifact_path,
                source_name=pred_resolved.name,
            )
        else:
            notes.append("Calibration metrics were skipped because uncertainty_col was not provided.")
    else:
        notes.append("Calibration metrics were skipped because run mode excludes calibration.")

    return EvaluateMetricsResult(
        status="ok",
        metrics={
            "accuracy": (accuracy_result.metrics.model_dump() if accuracy_result else None),
            "calibration": (calibration_result.metrics.model_dump() if calibration_result else None),
        },
        artifacts=EvaluateMetricsArtifacts(
            accuracy=(accuracy_result.artifact if accuracy_result else None),
            accuracy_plot=(accuracy_result.plot_artifact if accuracy_result else None),
            calibration=(calibration_result.artifact if calibration_result else None),
            calibration_plot=(calibration_result.plot_artifact if calibration_result else None),
        ),
        notes=notes,
    )


def _round_to_sig_figs(x: float, sig_figs: int = 4) -> float:
    """Round a number to the specified number of significant figures.
    
    Args:
        x: The number to round
        sig_figs: Number of significant figures (default: 4)
        
    Returns:
        The rounded number, or the original value if it's zero or non-numeric
    """
    if x == 0 or not isinstance(x, (int, float)):
        return x
    return round(x, -int(floor(log10(abs(x)))) + (sig_figs - 1))


def _round_result(result: EvaluateMetricsResult) -> EvaluateMetricsResult:
    """Round all numeric values in the result to 4 significant figures."""
    if result.metrics.get("accuracy"):
        for key in result.metrics["accuracy"].keys():
            if isinstance(result.metrics["accuracy"][key], (int, float)):
                result.metrics["accuracy"][key] = _round_to_sig_figs(
                    result.metrics["accuracy"][key]
                )
    if result.metrics.get("calibration"):
        for key in result.metrics["calibration"].keys():
            if isinstance(result.metrics["calibration"][key], (int, float)):
                result.metrics["calibration"][key] = _round_to_sig_figs(
                    result.metrics["calibration"][key]
                )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate model accuracy and calibration metrics."
    )
    parser.add_argument(
        "predictions_path",
        help="Path to the predictions CSV file.",
    )
    parser.add_argument(
        "ground_truth_path",
        help="Path to the ground truth CSV file.",
    )
    parser.add_argument(
        "--pred-col",
        default="prediction",
        help="Column name for predictions (default: prediction).",
    )
    parser.add_argument(
        "--truth-col",
        default="ground_truth",
        help="Column name for ground truth (default: ground_truth).",
    )
    parser.add_argument(
        "--uncertainty-col",
        default=None,
        help="Column name for uncertainty/std (required for calibration).",
    )
    parser.add_argument(
        "--accuracy-output-path",
        default=None,
        help="Path to save accuracy artifact CSV.",
    )
    parser.add_argument(
        "--calibration-output-path",
        default=None,
        help="Path to save calibration artifact CSV.",
    )
    parser.add_argument(
        "--run",
        choices=["accuracy", "calibration", "both"],
        default="both",
        help="Which metrics to compute (default: both).",
    )
    parser.add_argument(
        "--allowed-root",
        default=".",
        help="Root directory for path validation (default: current directory).",
    )

    args = parser.parse_args()

    try:
        result = evaluate_metrics_tool(
            predictions_path=args.predictions_path,
            ground_truth_path=args.ground_truth_path,
            pred_col=args.pred_col,
            truth_col=args.truth_col,
            uncertainty_col=args.uncertainty_col,
            accuracy_output_path=args.accuracy_output_path,
            calibration_output_path=args.calibration_output_path,
            run=args.run,
            allowed_root=args.allowed_root,
        )
        result = _round_result(result)
        print(result.model_dump_json(indent=2))
        return 0
    except Exception as e:
        error_result = {"status": "error", "error": sanitize_error(e)}
        print(json.dumps(error_result, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
