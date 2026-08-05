#!/usr/bin/env python3
"""
Repository evidence scanner for uncertainty quantification.

This script is intentionally lightweight and dependency-free. It searches a
repository for common UQ signals in filenames and file contents, then emits a
compact report to help an agent or analyst start a UQ review.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


MAX_FILE_BYTES = 1_000_000
MAX_DEPTH = 20
DEFAULT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".ipynb",
    ".sh",
}

KEYWORDS = {
    "methods": [
        r"\bensemble(s)?\b",
        r"\bmc[_ -]?dropout\b",
        r"\bdropout\b",
        r"\bbayesian\b",
        r"\bgaussian process(es)?\b",
        r"\bconformal\b",
        r"\blaplace\b",
        r"\bvariance\b",
        r"\bprediction interval(s)?\b",
        r"\bquantile regression\b",
    ],
    "calibration": [
        r"\bcalibration\b",
        r"\btemperature scaling\b",
        r"\bisotonic\b",
        r"\bplatt\b",
        r"\breliability diagram(s)?\b",
        r"\bece\b",
        r"\bmce\b",
        r"\bbrier\b",
        r"\bnegative log[- ]likelihood\b",
        r"\bnll\b",
    ],
    "ood": [
        r"\bood\b",
        r"\bout[- ]of[- ]distribution\b",
        r"\bdistribution shift\b",
        r"\bdrift\b",
        r"\bcorruption(s)?\b",
        r"\bnovelty detection\b",
    ],
    "policy": [
        r"\babstain\b",
        r"\breject option\b",
        r"\bdefer\b",
        r"\bescalat(e|ion)\b",
        r"\bfallback\b",
        r"\bhuman review\b",
        r"\bthreshold\b",
        r"\bconfidence score\b",
    ],
    "agentic": [
        r"\bretrieval confidence\b",
        r"\bself-consistency\b",
        r"\bgrounding\b",
        r"\bcitation support\b",
        r"\btool selection\b",
        r"\bverifier\b",
        r"\bjudge disagreement\b",
    ],
}

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a repository for UQ evidence.")
    parser.add_argument("root", help="Path to the repository root to scan.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum matches to retain per category.",
    )
    return parser.parse_args()


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.is_symlink():
            continue  # Skip symlinks to prevent escape/cycles
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(root)):
                continue  # Skip paths that escape root
        except OSError:
            continue
        if len(path.relative_to(root).parts) > MAX_DEPTH:
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def classify_file(path: Path, content: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = defaultdict(list)
    haystack = f"{path.name}\n{content}"
    for category, patterns in KEYWORDS.items():
        for pattern in patterns:
            match = re.search(pattern, haystack, flags=re.IGNORECASE)
            if match:
                hits[category].append(match.group(0))
    return hits


def scan_repository(root: Path, limit: int) -> dict:
    findings = {category: [] for category in KEYWORDS}
    evidence_counts = {category: 0 for category in KEYWORDS}

    for path in iter_files(root):
        content = read_text(path)
        hits = classify_file(path, content)
        if not hits:
            continue

        relpath = str(path.relative_to(root))
        for category, matched_terms in hits.items():
            evidence_counts[category] += 1
            if len(findings[category]) >= limit:
                continue
            findings[category].append(
                {
                    "path": relpath,
                    "matched_terms": sorted(set(matched_terms)),
                }
            )

    summary = {
        "root": str(root),
        "categories_with_evidence": [
            category for category, count in evidence_counts.items() if count > 0
        ],
        "evidence_counts": evidence_counts,
        "findings": findings,
    }

    summary["high_level_assessment"] = assess(summary["evidence_counts"])
    return summary


def assess(counts: dict[str, int]) -> str:
    present = {name for name, count in counts.items() if count > 0}
    if {"methods", "calibration", "policy"} <= present:
        return "Repository shows multiple UQ layers: estimation, calibration, and operational policy."
    if {"methods", "calibration"} <= present:
        return "Repository appears to implement uncertainty estimation and some calibration evidence, but operational policy may be thin."
    if "methods" in present:
        return "Repository references uncertainty methods, but calibration and deployment policy evidence look limited."
    return "Little explicit UQ evidence found. Either UQ is absent, implemented elsewhere, or described using non-standard terminology."


def escape_md(text: str) -> str:
    """Escape characters that have meaning in markdown."""
    for ch in r"\`*_{}[]()#+-.!|":
        text = text.replace(ch, f"\\{ch}")
    return text


def render_markdown(report: dict) -> str:
    lines = [
        "# UQ Repository Scan",
        "",
        f"**Root:** `{report['root']}`",
        "",
        "## High-Level Assessment",
        "",
        report["high_level_assessment"],
        "",
        "## Evidence Counts",
        "",
    ]

    for category, count in report["evidence_counts"].items():
        lines.append(f"- **{category}**: {count}")

    lines.extend(["", "## Sample Findings", ""])

    for category, items in report["findings"].items():
        lines.append(f"### {category.title()}")
        if not items:
            lines.append("- No evidence found")
            lines.append("")
            continue
        for item in items:
            terms = ", ".join(f"`{escape_md(term)}`" for term in item["matched_terms"])
            lines.append(f"- `{escape_md(item['path'])}`: {terms}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    report = scan_repository(root, args.limit)

    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
