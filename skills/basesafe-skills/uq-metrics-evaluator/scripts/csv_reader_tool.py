import argparse
import sys
from pathlib import Path
from math import log10, floor

from typing import Optional

import pandas as pd
from pydantic import BaseModel
from models import ColumnInfo, CsvInspectResult, validate_input_path, sanitize_error

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



def inspect_csv_columns(file_path: str, allowed_root: str = ".") -> CsvInspectResult:
    """Inspect CSV schema, row counts, missing values, and summary statistics."""
    stat_row_limit = 50_000

    try:
        resolved = validate_input_path(file_path, allowed_root=allowed_root)
    except ValueError as e:
        return CsvInspectResult(
            file_name=Path(file_path).name,
            total_rows=0,
            sampled=False,
            columns=[],
            summary_statistics=[],
            error=sanitize_error(e),
        )

    try:
        df = pd.read_csv(resolved, nrows=stat_row_limit)

        with resolved.open(newline="", encoding="utf-8") as file_handle:
            total_rows = max(sum(1 for _ in file_handle) - 1, 0)

        sampled = total_rows > stat_row_limit

        missing = df.isnull().sum()
        columns = [
            ColumnInfo(name=col, dtype=str(df[col].dtype), missing_count=int(missing[col]))
            for col in df.columns
        ]

        stats_df = df.describe(percentiles=[0.05, 0.25, 0.75, 0.95])
        summary_statistics = [
            {
                "name": col,
                **{
                    str(stat): (
                        _round_to_sig_figs(float(val)) if pd.notna(val) else None
                    )
                    for stat, val in stats_df[col].items()
                },
            }
            for col in stats_df.columns
        ]

        return CsvInspectResult(
            file_name=resolved.name,
            total_rows=total_rows,
            sampled=sampled,
            columns=columns,
            summary_statistics=summary_statistics,
        )

    except Exception as e:
        return CsvInspectResult(
            file_name=resolved.name,
            total_rows=0,
            sampled=False,
            columns=[],
            summary_statistics=[],
            error=f"Error reading CSV: {sanitize_error(e)}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a CSV file and return schema and summary statistics as JSON."
    )
    parser.add_argument(
        "file_path",
        help="Path to the CSV file to inspect.",
    )
    parser.add_argument(
        "--allowed-root",
        default=".",
        help="Root directory for path validation (default: current directory).",
    )

    args = parser.parse_args()
    result = inspect_csv_columns(args.file_path, allowed_root=args.allowed_root)
    print(result.model_dump_json(indent=2))
    return 1 if result.error else 0


if __name__ == "__main__":
    sys.exit(main())
