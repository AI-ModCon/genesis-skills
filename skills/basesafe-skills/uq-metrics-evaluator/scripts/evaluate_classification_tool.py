"""Classification metrics evaluation tool.

Evaluates standard classification metrics (accuracy, F1, ROC-AUC, etc.) and,
when predicted probabilities are available, probabilistic calibration metrics
(ECE, MCE, Brier score) with a reliability diagram.

Usage
-----
uv run --with pandas --with pydantic --with numpy --with scikit-learn --with matplotlib --with seaborn \\
    ./scripts/evaluate_classification_tool.py <predictions.csv> <ground_truth.csv> \\
    --pred-col <predicted_class_column> \\
    --truth-col <true_label_column> \\
    [--prob-col <predicted_probability_column>]   # for binary; omit for hard-label-only
    [--prob-cols <class0_prob> <class1_prob> ...]  # for multiclass probabilities
    [--classification-output-path <path.csv>]
"""

from __future__ import annotations

import argparse
import json
import sys
from math import floor, log10
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import LabelEncoder

from models import (
    ArtifactInfo,
    ClassificationCalibrationMetrics,
    ClassificationMetrics,
    ClassificationMetricsResult,
    MAX_ROWS,
    sanitize_error,
    validate_input_path,
    validate_output_path,
)
from plotting import save_confusion_matrix_plot, save_reliability_diagram_plot


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def load_prediction_truth_frames(
    predictions_path: str,
    ground_truth_path: str,
    allowed_root: str = ".",
) -> tuple[Path, Path, pd.DataFrame, pd.DataFrame]:
    """Load predictions and ground-truth CSVs with same-file deduplication."""
    pred_resolved = validate_input_path(predictions_path, allowed_root=allowed_root)
    truth_resolved = validate_input_path(ground_truth_path, allowed_root=allowed_root)

    pred_df = pd.read_csv(pred_resolved, nrows=MAX_ROWS)
    truth_df = pred_df if pred_resolved == truth_resolved else pd.read_csv(truth_resolved, nrows=MAX_ROWS)
    return pred_resolved, truth_resolved, pred_df, truth_df


# ---------------------------------------------------------------------------
# Calibration helpers
# ---------------------------------------------------------------------------

def _compute_ece_mce(
    y_true_bin: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[float, float]:
    """Equal-width binning ECE and MCE for a binary probability vector."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n = len(y_true_bin)
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        if not mask.any():
            continue
        frac = mask.sum() / n
        acc = y_true_bin[mask].mean()
        conf = y_prob[mask].mean()
        ece += frac * abs(acc - conf)
        mce = max(mce, abs(acc - conf))
    return float(ece), float(mce)


def _reliability_curve(
    y_true_bin: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[list[float], list[float]]:
    """Return (mean_predicted_prob, fraction_of_positives) per bin."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    mean_probs: list[float] = []
    frac_pos: list[float] = []
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        if not mask.any():
            continue
        mean_probs.append(float(y_prob[mask].mean()))
        frac_pos.append(float(y_true_bin[mask].mean()))
    return mean_probs, frac_pos


# ---------------------------------------------------------------------------
# Core compute function
# ---------------------------------------------------------------------------

def _compute_classification_metrics(
    pred_df: pd.DataFrame,
    truth_df: pd.DataFrame,
    pred_col: str,
    truth_col: str,
    prob_col: Optional[str],
    prob_cols: Optional[list[str]],
    artifact_path: Path,
    source_name: str,
) -> ClassificationMetricsResult:
    # --- Column presence checks ---
    if pred_col not in pred_df.columns:
        raise ValueError(
            f"Prediction column '{pred_col}' not found. "
            f"Available: {pred_df.columns.tolist()}"
        )
    if truth_col not in truth_df.columns:
        raise ValueError(
            f"Truth column '{truth_col}' not found. "
            f"Available: {truth_df.columns.tolist()}"
        )
    if prob_col and prob_col not in pred_df.columns:
        raise ValueError(
            f"Probability column '{prob_col}' not found. "
            f"Available: {pred_df.columns.tolist()}"
        )
    if prob_cols:
        missing = [c for c in prob_cols if c not in pred_df.columns]
        if missing:
            raise ValueError(
                f"Probability column(s) {missing} not found. "
                f"Available: {pred_df.columns.tolist()}"
            )

    # --- Alignment check ---
    if len(pred_df) != len(truth_df):
        raise ValueError(
            f"Prediction ({len(pred_df)}) and truth ({len(truth_df)}) row counts differ."
        )

    # --- Build working frame ---
    cols: dict[str, pd.Series] = {
        truth_col: truth_df[truth_col],
        pred_col: pred_df[pred_col],
    }
    if prob_col:
        cols[prob_col] = pred_df[prob_col]
    if prob_cols:
        for c in prob_cols:
            cols[c] = pred_df[c]

    df = pd.DataFrame(cols).dropna()
    if df.empty:
        raise ValueError("No valid rows remain after dropping rows with missing values.")

    y_true = df[truth_col].astype(str).to_numpy()
    y_pred = df[pred_col].astype(str).to_numpy()

    classes = np.unique(np.concatenate([y_true, y_pred]))
    num_classes = len(classes)
    is_binary = num_classes == 2

    # Encode labels to integers for sklearn metrics that require it
    le = LabelEncoder().fit(classes)
    y_true_enc = le.transform(y_true)
    y_pred_enc = le.transform(y_pred)

    # --- Hard-label metrics ---
    acc = float(accuracy_score(y_true_enc, y_pred_enc))
    prec = float(precision_score(y_true_enc, y_pred_enc, average="macro", zero_division=0))
    rec = float(recall_score(y_true_enc, y_pred_enc, average="macro", zero_division=0))
    f1 = float(f1_score(y_true_enc, y_pred_enc, average="macro", zero_division=0))

    # --- Probability-based metrics ---
    roc_auc: Optional[float] = None
    log_loss_val: Optional[float] = None
    calibration_metrics: Optional[ClassificationCalibrationMetrics] = None
    calibration_plot_artifact: Optional[ArtifactInfo] = None

    y_prob_binary: Optional[np.ndarray] = None   # shape (n,)  — binary positive-class prob
    y_prob_matrix: Optional[np.ndarray] = None   # shape (n, k) — multiclass probs

    if prob_col:
        if not pd.api.types.is_numeric_dtype(df[prob_col]):
            raise ValueError(f"Probability column '{prob_col}' is not numeric.")
        y_prob_binary = df[prob_col].to_numpy(dtype=float)
        if not is_binary:
            raise ValueError(
                f"--prob-col is only valid for binary classification ({num_classes} classes found). "
                "Use --prob-cols for multiclass."
            )

    if prob_cols:
        if len(prob_cols) != num_classes:
            raise ValueError(
                f"--prob-cols expects one column per class ({num_classes} classes), "
                f"got {len(prob_cols)} columns."
            )
        for c in prob_cols:
            if not pd.api.types.is_numeric_dtype(df[c]):
                raise ValueError(f"Probability column '{c}' is not numeric.")
        y_prob_matrix = df[prob_cols].to_numpy(dtype=float)

    if y_prob_binary is not None or y_prob_matrix is not None:
        # ROC-AUC
        try:
            if is_binary and y_prob_binary is not None:
                roc_auc = float(roc_auc_score(y_true_enc, y_prob_binary))
            elif y_prob_matrix is not None:
                roc_auc = float(
                    roc_auc_score(y_true_enc, y_prob_matrix, multi_class="ovr", average="macro")
                )
        except ValueError:
            roc_auc = None  # can fail with very few samples or missing classes

        # Log loss
        try:
            probs_for_logloss = y_prob_matrix if y_prob_matrix is not None else y_prob_binary
            log_loss_val = float(log_loss(y_true_enc, probs_for_logloss))
        except Exception:
            log_loss_val = None

        # ECE / MCE / Brier — binary path
        if is_binary and y_prob_binary is not None:
            from sklearn.metrics import brier_score_loss

            ece, mce = _compute_ece_mce(y_true_enc.astype(float), y_prob_binary)
            brier = float(brier_score_loss(y_true_enc, y_prob_binary))
            calibration_metrics = ClassificationCalibrationMetrics(
                expected_calibration_error=ece,
                max_calibration_error=mce,
                brier_score=brier,
            )
            mean_probs, frac_pos = _reliability_curve(y_true_enc.astype(float), y_prob_binary)
            cal_plot_path = artifact_path.with_name(f"{artifact_path.stem}_reliability.png")
            save_reliability_diagram_plot(
                mean_predicted_probs=mean_probs,
                fraction_of_positives=frac_pos,
                plot_path=cal_plot_path,
            )
            calibration_plot_artifact = ArtifactInfo(
                path=str(cal_plot_path),
                format="png",
                columns=[],
                description=(
                    f"Reliability diagram for '{source_name}'. "
                    "Each point is a probability bin; the dashed orange line is perfect calibration. "
                    "Points above the diagonal indicate underconfidence; below indicates overconfidence."
                ),
            )

        # ECE / MCE / Brier — multiclass (macro-averaged one-vs-rest)
        elif y_prob_matrix is not None:
            from sklearn.metrics import brier_score_loss

            ece_vals, mce_vals, brier_vals = [], [], []
            reliability_data: list[tuple[list[float], list[float]]] = []
            for k in range(num_classes):
                y_bin = (y_true_enc == k).astype(float)
                p_k = y_prob_matrix[:, k]
                e, m = _compute_ece_mce(y_bin, p_k)
                ece_vals.append(e)
                mce_vals.append(m)
                brier_vals.append(float(brier_score_loss(y_bin, p_k)))
                mp, fp = _reliability_curve(y_bin, p_k)
                reliability_data.append((mp, fp))

            calibration_metrics = ClassificationCalibrationMetrics(
                expected_calibration_error=float(np.mean(ece_vals)),
                max_calibration_error=float(np.mean(mce_vals)),
                brier_score=float(np.mean(brier_vals)),
            )
            cal_plot_path = artifact_path.with_name(f"{artifact_path.stem}_reliability.png")
            save_reliability_diagram_plot(
                mean_predicted_probs=reliability_data[0][0],
                fraction_of_positives=reliability_data[0][1],
                plot_path=cal_plot_path,
                class_label=str(le.classes_[0]),
                extra_curves=[
                    (reliability_data[k][0], reliability_data[k][1], str(le.classes_[k]))
                    for k in range(1, num_classes)
                ],
            )
            calibration_plot_artifact = ArtifactInfo(
                path=str(cal_plot_path),
                format="png",
                columns=[],
                description=(
                    f"Reliability diagram (one-vs-rest per class) for '{source_name}'. "
                    "Each curve is one class; the dashed orange line is perfect calibration. "
                    "ECE/MCE/Brier reported as macro-averages across classes."
                ),
            )

    # --- Confusion matrix artifact ---
    cm = confusion_matrix(y_true_enc, y_pred_enc, labels=le.transform(classes))
    cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
    cm_df.index.name = "true_label"

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    cm_df.to_csv(artifact_path)

    cm_plot_path = artifact_path.with_name(f"{artifact_path.stem}_confusion_matrix.png")
    save_confusion_matrix_plot(
        confusion_matrix=cm,
        class_labels=list(le.classes_.astype(str)),
        plot_path=cm_plot_path,
    )

    artifact_description = (
        f"Confusion matrix for '{source_name}'. "
        f"Rows are true labels; columns are predicted labels. "
        f"Diagonal cells are correct predictions; off-diagonal cells are misclassifications. "
        f"Class order: {list(le.classes_.astype(str))}."
    )

    plot_description = (
        f"Confusion matrix heatmap for '{source_name}'. "
        "Cell color and annotation show count per (true, predicted) pair. "
        "Use to identify which classes are most often confused."
    )

    return ClassificationMetricsResult(
        metrics=ClassificationMetrics(
            accuracy=acc,
            precision_macro=prec,
            recall_macro=rec,
            f1_macro=f1,
            roc_auc=roc_auc,
            log_loss=log_loss_val,
            row_count=len(df),
            num_classes=num_classes,
        ),
        calibration=calibration_metrics,
        artifact=ArtifactInfo(
            path=str(artifact_path),
            format="csv",
            columns=cm_df.columns.tolist(),
            description=artifact_description,
        ),
        plot_artifact=ArtifactInfo(
            path=str(cm_plot_path),
            format="png",
            columns=[],
            description=plot_description,
        ),
        calibration_plot_artifact=calibration_plot_artifact,
    )


# ---------------------------------------------------------------------------
# Rounding helper
# ---------------------------------------------------------------------------

def _round_to_sig_figs(x: float, sig_figs: int = 4) -> float:
    if x == 0 or not isinstance(x, (int, float)):
        return x
    return round(x, -int(floor(log10(abs(x)))) + (sig_figs - 1))


def _round_result(result: ClassificationMetricsResult) -> ClassificationMetricsResult:
    m = result.metrics.model_dump()
    for k, v in m.items():
        if isinstance(v, float):
            m[k] = _round_to_sig_figs(v)
    result.metrics = ClassificationMetrics(**m)

    if result.calibration:
        c = result.calibration.model_dump()
        for k, v in c.items():
            if isinstance(v, float):
                c[k] = _round_to_sig_figs(v)
        result.calibration = ClassificationCalibrationMetrics(**c)

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate classification metrics from CSV predictions."
    )
    parser.add_argument("predictions_path", help="Path to the predictions CSV file.")
    parser.add_argument("ground_truth_path", help="Path to the ground truth CSV file.")
    parser.add_argument(
        "--pred-col",
        default="prediction",
        help="Column name for predicted class labels (default: prediction).",
    )
    parser.add_argument(
        "--truth-col",
        default="label",
        help="Column name for true class labels (default: label).",
    )
    parser.add_argument(
        "--prob-col",
        default=None,
        help="Column of predicted positive-class probabilities (binary only).",
    )
    parser.add_argument(
        "--prob-cols",
        nargs="+",
        default=None,
        help="Ordered list of probability columns, one per class (multiclass).",
    )
    parser.add_argument(
        "--classification-output-path",
        default=None,
        help="Path to save confusion matrix CSV artifact.",
    )
    parser.add_argument(
        "--allowed-root",
        default=".",
        help="Root directory for path validation (default: current directory).",
    )

    args = parser.parse_args()

    try:
        pred_resolved, truth_resolved, pred_df, truth_df = load_prediction_truth_frames(
            predictions_path=args.predictions_path,
            ground_truth_path=args.ground_truth_path,
            allowed_root=args.allowed_root,
        )

        if args.classification_output_path:
            artifact_path = validate_output_path(args.classification_output_path, allowed_root=args.allowed_root)
        else:
            artifact_path = pred_resolved.parent / f"{pred_resolved.stem}_confusion_matrix.csv"

        result = _compute_classification_metrics(
            pred_df=pred_df,
            truth_df=truth_df,
            pred_col=args.pred_col,
            truth_col=args.truth_col,
            prob_col=args.prob_col,
            prob_cols=args.prob_cols,
            artifact_path=artifact_path,
            source_name=pred_resolved.name,
        )
        result = _round_result(result)
        print(result.model_dump_json(indent=2))
        return 0

    except Exception as e:
        print(json.dumps({"status": "error", "error": sanitize_error(e)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
