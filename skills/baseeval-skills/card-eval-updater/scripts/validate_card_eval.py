#!/usr/bin/env python3
"""Verify a card's generated evaluation blocks against the bundle they came from.

The check is a re-render and compare, not a number hunt: the generated block is
rebuilt from the bundle and diffed against what is in the card. Anything a human
(or a model) altered inside the block shows up as a mismatch, which is exactly
the failure this tool exists to prevent — a benchmark number in a card that no
artifact supports.

Findings use structured codes so a caller can act on them:

    MISSING_SECTION     an evaluation section has no generated block
    UNTRACED            a generated block does not match a re-render of the bundle
    METRICS_MISMATCH    frontmatter `metrics:` is missing a bundle entry
    PARTIAL_UNLABELLED  a partial run is not disclosed as partial
    PLACEHOLDER         template placeholder markup survived into the card

Usage:
    validate_card_eval.py <card.md> <bundle.json> [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from card_text import (  # noqa: E402
    normalize_heading,
    scan_headings,
    section_span,
    split_frontmatter,
    subsection_span,
    trim_blank_edges,
)
from render_card_sections import (  # noqa: E402
    ANCHOR,
    SECTION_ORDER,
    render_metrics_frontmatter,
    render_sections,
)

ANCHOR_NORMALIZED = normalize_heading(ANCHOR.lstrip("#").strip())
PLACEHOLDER_RE = re.compile(r"\[!TODO\]|<REPLACE:|<INSTRUCTIONS:|\$\{[A-Z_]+\}|__VALUE__")


def _normalize_block(text: str) -> list[str]:
    """Compare on content, ignoring trailing whitespace and blank-line runs."""
    lines = [line.rstrip() for line in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if not line and out and not out[-1]:
            continue
        out.append(line)
    return trim_blank_edges(out)


def validate(card_text: str, bundle: dict) -> list[dict]:
    findings: list[dict] = []
    frontmatter, body = split_frontmatter(card_text)
    body_lines = body.split("\n")
    expected = render_sections(bundle)

    for name in SECTION_ORDER:
        headings = scan_headings(body_lines)
        outer = section_span(headings, body_lines, name)
        if outer is None:
            findings.append(
                {
                    "code": "MISSING_SECTION",
                    "severity": "error",
                    "section": name,
                    "message": f"card has no '## {name.title()}' section",
                }
            )
            continue
        inner = subsection_span(headings, body_lines, outer, ANCHOR_NORMALIZED)
        if inner is None:
            findings.append(
                {
                    "code": "MISSING_SECTION",
                    "severity": "error",
                    "section": name,
                    "message": f"'{name}' contains no '{ANCHOR}' block",
                }
            )
            continue
        actual = _normalize_block("\n".join(body_lines[inner[0] : inner[1]]))
        wanted = _normalize_block(expected[name])
        if actual != wanted:
            diff = next(
                (
                    f"card: {a!r} != bundle: {b!r}"
                    for a, b in zip(
                        actual + [""] * len(wanted),
                        wanted + [""] * len(actual),
                        strict=False,
                    )
                    if a != b
                ),
                "block lengths differ",
            )
            findings.append(
                {
                    "code": "UNTRACED",
                    "severity": "error",
                    "section": name,
                    "message": (
                        f"'{name}' block does not match a re-render of the bundle; "
                        f"its content is not supported by the run artifacts ({diff})"
                    ),
                }
            )

    if frontmatter is not None:
        present = set(re.findall(r"^\s*-\s*(\S+)", frontmatter, re.M))
        for entry in render_metrics_frontmatter(bundle):
            if entry not in present:
                findings.append(
                    {
                        "code": "METRICS_MISMATCH",
                        "severity": "warn",
                        "section": "frontmatter",
                        "message": f"`metrics:` does not list '{entry}'",
                    }
                )

    if any(r.get("is_partial") for r in bundle["results"]):
        if "partial" not in card_text.lower():
            findings.append(
                {
                    "code": "PARTIAL_UNLABELLED",
                    "severity": "error",
                    "section": "body",
                    "message": (
                        "the bundle contains sample-limited results but the card does not "
                        "disclose them as partial"
                    ),
                }
            )

    for match in PLACEHOLDER_RE.finditer(card_text):
        findings.append(
            {
                "code": "PLACEHOLDER",
                "severity": "warn",
                "section": "body",
                "message": f"template placeholder left in card: {match.group(0)}",
            }
        )

    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("card", type=Path)
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    findings = validate(args.card.read_text(encoding="utf-8"), bundle)
    errors = [f for f in findings if f["severity"] == "error"]

    if args.json:
        print(json.dumps({"ok": not errors, "findings": findings}, indent=2))
    elif not findings:
        print(f"ok: every generated block in {args.card} traces to {args.bundle}")
    else:
        for finding in findings:
            print(f"{finding['severity'].upper():5} {finding['code']}: {finding['message']}")
        print(f"\n{len(errors)} error(s), {len(findings) - len(errors)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
