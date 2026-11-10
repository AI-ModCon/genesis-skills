#!/usr/bin/env python3
"""Summarise and plot AthenaK history (.hst) files, including restarted runs.

The parser and summary use only the standard library; ``--plot`` also needs
matplotlib.

AthenaK appends to ``<basename>.<physics>.hst`` (hydro, mhd, user; Z4c:
``z4c.user``) and writes a new ``# Athena++ history data`` header each time
the code starts, so a restarted run has one header per segment. Rows written
after the last restart dump but before a crash or wall-time stop reappear
(with the same or later times) in the next segment. This tool joins all
segments and drops superseded rows: when a row's time is not later than the
previous row's, earlier rows at or after that time are discarded. That matches
the rule AthenaK's ``athena_read.hst`` applies within one segment. Note that
``athena_read.hst`` itself reads only the data after the *last* header, so on
a restarted run it returns only the final segment. ``--raw`` keeps every row
in file order.

Usage::

    hst_summary.py FILE.hst                    # columns, segments, first/last/min/max
    hst_summary.py FILE.hst --columns          # column names only
    hst_summary.py FILE.hst --plot tot-E,mass -o hist.png [--logy]
    hst_summary.py FILE.hst --csv > hist.csv   # merged table
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

HEADER = "# Athena++ history data"
COLUMN_RE = re.compile(r"\[(\d+)\]=(\S+)")


class HstError(Exception):
    """Raised for unreadable or inconsistent history files."""


class History:
    """Merged history data: ``columns`` (names) and ``rows`` (lists of floats)."""

    def __init__(self, columns: list[str], rows: list[list[float]], segments: int, dropped: int) -> None:
        self.columns = columns
        self.rows = rows
        self.segments = segments
        self.dropped = dropped

    def column(self, name: str) -> list[float]:
        try:
            index = self.columns.index(name)
        except ValueError:
            raise HstError(f"no column {name!r}; available: {', '.join(self.columns)}") from None
        return [row[index] for row in self.rows]


def _parse_columns(line: str) -> list[str]:
    found = COLUMN_RE.findall(line)
    if not found:
        raise HstError(f"could not parse column header: {line.strip()!r}")
    return [name for _, name in sorted(found, key=lambda item: int(item[0]))]


def parse_text(text: str, raw: bool = False) -> History:
    columns: list[str] | None = None
    rows: list[list[float]] = []
    segments = 0
    dropped = 0
    expect_columns = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == HEADER:
            segments += 1
            expect_columns = True
            continue
        if expect_columns:
            names = _parse_columns(stripped)
            if columns is not None and names != columns:
                raise HstError(
                    f"line {lineno}: segment {segments} has different columns than earlier segments; "
                    "split the file at the header lines and read each part separately"
                )
            columns = names
            expect_columns = False
            continue
        if stripped.startswith("#"):
            continue
        if columns is None:
            raise HstError(f"line {lineno}: data before the '{HEADER}' header")
        try:
            values = [float(v) for v in stripped.split()]
        except ValueError:
            raise HstError(f"line {lineno}: non-numeric data: {stripped[:60]!r}") from None
        if len(values) != len(columns):
            raise HstError(f"line {lineno}: {len(values)} values for {len(columns)} columns")
        if not raw and columns[0] == "time":
            while rows and rows[-1][0] >= values[0]:
                rows.pop()
                dropped += 1
        rows.append(values)
    if columns is None:
        raise HstError(f"no '{HEADER}' header found")
    return History(columns, rows, segments, dropped)


def load(path: str | Path, raw: bool = False) -> History:
    return parse_text(Path(path).read_text(encoding="utf-8", errors="replace"), raw=raw)


def _fmt(value: float) -> str:
    return f"{value:.6e}"


def summary(hist: History) -> str:
    lines = [
        f"columns: {len(hist.columns)}   rows: {len(hist.rows)}   segments (starts/restarts): {hist.segments}"
        + (f"   superseded rows dropped: {hist.dropped}" if hist.dropped else "")
    ]
    if not hist.rows:
        lines.append("no data rows")
        return "\n".join(lines)
    width = max(len("column"), *(len(name) for name in hist.columns))
    lines.append(f"{'column':<{width}}  {'first':>13}  {'last':>13}  {'min':>13}  {'max':>13}  notes")
    for index, name in enumerate(hist.columns):
        values = [row[index] for row in hist.rows]
        finite = [v for v in values if math.isfinite(v)]
        notes = ""
        bad = len(values) - len(finite)
        if bad:
            first_bad = next(i for i, v in enumerate(values) if not math.isfinite(v))
            notes = f"{bad} non-finite, first at time={_fmt(hist.rows[first_bad][0])}"
        lo = _fmt(min(finite)) if finite else "nan"
        hi = _fmt(max(finite)) if finite else "nan"
        lines.append(
            f"{name:<{width}}  {_fmt(values[0]):>13}  {_fmt(values[-1]):>13}  {lo:>13}  {hi:>13}  {notes}".rstrip()
        )
    return "\n".join(lines)


def to_csv(hist: History) -> str:
    out = [",".join(hist.columns)]
    out.extend(",".join(repr(v) for v in row) for row in hist.rows)
    return "\n".join(out)


def plot(hist: History, names: list[str], output: str, xname: str, logy: bool) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise HstError("--plot needs matplotlib (pip install matplotlib)") from exc
    x = hist.column(xname)
    fig, ax = plt.subplots()
    for name in names:
        ax.plot(x, hist.column(name), label=name)
    ax.set_xlabel(xname)
    if logy:
        ax.set_yscale("log")
    if len(names) > 1:
        ax.legend()
    else:
        ax.set_ylabel(names[0])
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("file", help="AthenaK .hst file")
    parser.add_argument("--columns", action="store_true", help="list column names and exit")
    parser.add_argument("--csv", action="store_true", help="print the merged table as CSV")
    parser.add_argument("--plot", metavar="COL[,COL...]", help="plot comma-separated columns vs --x")
    parser.add_argument("-x", "--x", default="time", help="x-axis column for --plot (default: time)")
    parser.add_argument("-o", "--output", default="hst.png", help="image file for --plot (default: hst.png)")
    parser.add_argument("--logy", action="store_true", help="log y axis for --plot")
    parser.add_argument("--raw", action="store_true", help="keep every row; do not drop superseded rows")
    args = parser.parse_args(argv)

    try:
        hist = load(args.file, raw=args.raw)
        if args.columns:
            print("\n".join(hist.columns))
        elif args.csv:
            print(to_csv(hist))
        elif args.plot:
            names = [n.strip() for n in args.plot.split(",") if n.strip()]
            plot(hist, names, args.output, args.x, args.logy)
            print(f"wrote {args.output}")
        else:
            print(summary(hist))
    except (HstError, OSError) as exc:
        print(f"hst_summary: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
