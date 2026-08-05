#!/usr/bin/env python3
"""
Lightweight repository scanner for model fingerprinting.

This helper gathers likely evidence for a repository fingerprint. It does not
assign a final taxonomy; that remains the analyst or LLM's job.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


MAX_FILE_BYTES = 1_000_000
TEXT_EXTENSIONS = {
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
    ".env",
    ".sh",
    ".ipynb",
}
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}
FILE_HINTS = {
    "readme": ["README", "readme"],
    "dependencies": [
        "requirements.txt",
        "pyproject.toml",
        "environment.yml",
        "environment.yaml",
        "poetry.lock",
        "Pipfile",
        "package.json",
    ],
    "training": ["train.py", "trainer.py", "fit.py"],
    "evaluation": ["eval.py", "evaluate.py", "metrics.py", "benchmark.py"],
    "inference": ["infer.py", "inference.py", "predict.py", "serve.py"],
    "configs": [".yaml", ".yml", ".json", ".toml"],
    "notebooks": [".ipynb"],
    "tests": ["test_", "_test.py", "tests"],
}
CONTENT_PATTERNS = {
    "frameworks": [
        r"\bimport torch\b",
        r"\bfrom torch\b",
        r"\btensorflow\b",
        r"\bsklearn\b",
        r"\bxgboost\b",
        r"\blightgbm\b",
        r"\bhuggingface\b",
        r"\btransformers\b",
        r"\blangchain\b",
        r"\bllama_index\b",
        r"\bfaiss\b",
    ],
    "modalities": [
        r"\bimage\b",
        r"\bvideo\b",
        r"\btext\b",
        r"\baudio\b",
        r"\btabular\b",
        r"\btimeseries\b",
        r"\bsensor\b",
        r"\bmultimodal\b",
    ],
    "tasks": [
        r"\bclassification\b",
        r"\bsegmentation\b",
        r"\bobject detection\b",
        r"\bretrieval\b",
        r"\branking\b",
        r"\brecommendation\b",
        r"\bsummarization\b",
        r"\bgeneration\b",
        r"\bforecasting\b",
        r"\banomaly detection\b",
        r"\bpolicy\b",
        r"\breward\b",
    ],
    "signals": [
        r"\brag\b",
        r"\bvector store\b",
        r"\bprompt\b",
        r"\btool\b",
        r"\bendpoint\b",
        r"\bfastapi\b",
        r"\bgradio\b",
        r"\bstreamlit\b",
        r"\bdocker\b",
        r"\bkubernetes\b",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a repository for fingerprint evidence.")
    parser.add_argument("root", help="Path to the repository root.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Maximum number of sample files to retain per category.",
    )
    return parser.parse_args()


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def read_text(path: Path) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def detect_file_hints(path: Path) -> list[str]:
    matches: list[str] = []
    name = path.name
    for category, hints in FILE_HINTS.items():
        for hint in hints:
            if hint.startswith("."):
                if path.suffix.lower() == hint:
                    matches.append(category)
                    break
            elif hint in name or hint in str(path):
                matches.append(category)
                break
    return matches


def detect_content(path: Path, content: str) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = defaultdict(list)
    if not content:
        return findings

    for category, patterns in CONTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if match:
                findings[category].append(match.group(0))
    return findings


def summarize(root: Path, limit: int) -> dict:
    files_by_hint: dict[str, list[str]] = defaultdict(list)
    content_hits: dict[str, list[dict[str, list[str]]]] = defaultdict(list)
    counts = defaultdict(int)

    for path in iter_files(root):
        rel = str(path.relative_to(root))

        for hint in detect_file_hints(path):
            counts[f"file_hint:{hint}"] += 1
            if len(files_by_hint[hint]) < limit:
                files_by_hint[hint].append(rel)

        content = read_text(path)
        findings = detect_content(path, content)
        for category, matched_terms in findings.items():
            counts[f"content:{category}"] += 1
            if len(content_hits[category]) < limit:
                content_hits[category].append(
                    {"path": rel, "matched_terms": sorted(set(matched_terms))}
                )

    return {
        "root": str(root),
        "sample_files": dict(files_by_hint),
        "content_hits": dict(content_hits),
        "counts": dict(sorted(counts.items())),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Fingerprint Repository Scan",
        "",
        f"**Root:** `{report['root']}`",
        "",
        "## Sample Files",
        "",
    ]
    if not report["sample_files"]:
        lines.append("- No matching files found")
    else:
        for category, paths in sorted(report["sample_files"].items()):
            lines.append(f"### {category.title()}")
            for path in paths:
                lines.append(f"- `{path}`")
            lines.append("")

    lines.extend(["## Content Hits", ""])
    if not report["content_hits"]:
        lines.append("- No keyword hits found")
    else:
        for category, items in sorted(report["content_hits"].items()):
            lines.append(f"### {category.title()}")
            for item in items:
                terms = ", ".join(f"`{term}`" for term in item["matched_terms"])
                lines.append(f"- `{item['path']}`: {terms}")
            lines.append("")

    lines.extend(["## Counts", ""])
    for key, value in report["counts"].items():
        lines.append(f"- **{key}**: {value}")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    report = summarize(root, args.limit)
    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
