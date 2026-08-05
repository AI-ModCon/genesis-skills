import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Path validation and file safety utilities
# ---------------------------------------------------------------------------

MAX_ROWS = 500_000  # Default row-count limit for evaluation tools


def validate_input_path(file_path: str, allowed_root: str = ".") -> Path:
    """Ensure the resolved path is within the allowed root directory.

    Also rejects symlinks to prevent path-escape attacks.
    """
    original = Path(file_path)
    if original.is_symlink():
        raise ValueError("Symlinks are not allowed for input files.")
    resolved = original.resolve()
    allowed = Path(allowed_root).resolve()
    if not str(resolved).startswith(str(allowed) + os.sep) and resolved != allowed:
        raise ValueError(
            f"File path resolves outside allowed directory."
        )
    if not resolved.exists():
        raise ValueError(f"File not found: '{original.name}'.")
    if resolved.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got '{resolved.suffix}'.")
    if not looks_like_csv(resolved):
        raise ValueError("File does not appear to contain CSV-formatted text.")
    return resolved


def validate_output_path(output_path: str, allowed_root: str = ".") -> Path:
    """Ensure output path is within allowed directory."""
    resolved = Path(output_path).resolve()
    allowed = Path(allowed_root).resolve()
    if not str(resolved).startswith(str(allowed) + os.sep) and resolved != allowed:
        raise ValueError(
            f"Output path resolves outside allowed directory."
        )
    return resolved


def looks_like_csv(path: Path, peek_bytes: int = 4096) -> bool:
    """Quick heuristic check that a file looks like text/CSV."""
    try:
        sample = path.read_bytes()[:peek_bytes]
        sample.decode("utf-8")
        return b"," in sample or b"\t" in sample
    except (UnicodeDecodeError, OSError):
        return False


def sanitize_error(error: Exception) -> str:
    """Return error message with absolute paths replaced by relative ones."""
    msg = str(error)
    cwd = str(Path.cwd())
    if cwd in msg:
        msg = msg.replace(cwd, ".")
    return msg


# --- CSV reader ---

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    missing_count: int

class CsvInspectResult(BaseModel):
    file_name: str
    total_rows: int
    sampled: bool
    columns: list[ColumnInfo]
    summary_statistics: list[dict] = []
    error: Optional[str] = None

# --- Shared artifact ---

class ArtifactInfo(BaseModel):
    path: str
    format: str
    columns: list[str]
    description: str

# --- Accuracy metrics ---

class AccuracyMetrics(BaseModel):
    mae: float
    rmse: float
    mdae: float
    marpd: float
    r2: float
    corr: float
    row_count: int


class AccuracyMetricsResult(BaseModel):
    metrics: AccuracyMetrics
    artifact: ArtifactInfo
    plot_artifact: ArtifactInfo


# --- Calibration metrics ---

class CalibrationMetrics(BaseModel):
    mean_calibration_error: float
    rms_calibration_error: float
    miscalibration_area: float
    sharpness: float
    nll: float
    crps: float
    check_score: float
    interval_score: float

class CalibrationMetricsResult(BaseModel):
    metrics: CalibrationMetrics
    artifact: ArtifactInfo
    plot_artifact: ArtifactInfo


# --- Classification metrics ---

class ClassificationMetrics(BaseModel):
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    roc_auc: Optional[float] = None       # None when probs unavailable or multiclass OvR fails
    log_loss: Optional[float] = None      # None when probs unavailable
    row_count: int
    num_classes: int


class ClassificationCalibrationMetrics(BaseModel):
    expected_calibration_error: float     # ECE (equal-width bins)
    max_calibration_error: float          # MCE
    brier_score: float                    # mean squared prob error (binary or macro-averaged)


class ClassificationMetricsResult(BaseModel):
    metrics: ClassificationMetrics
    calibration: Optional[ClassificationCalibrationMetrics] = None
    artifact: ArtifactInfo
    plot_artifact: ArtifactInfo
    calibration_plot_artifact: Optional[ArtifactInfo] = None


# --- Evaluate (combined) ---

class EvaluateMetricsArtifacts(BaseModel):
    accuracy: Optional[ArtifactInfo] = None
    accuracy_plot: Optional[ArtifactInfo] = None
    calibration: Optional[ArtifactInfo] = None
    calibration_plot: Optional[ArtifactInfo] = None


class EvaluateMetricsResult(BaseModel):
    status: str
    metrics: dict
    artifacts: EvaluateMetricsArtifacts
    notes: list[str]
