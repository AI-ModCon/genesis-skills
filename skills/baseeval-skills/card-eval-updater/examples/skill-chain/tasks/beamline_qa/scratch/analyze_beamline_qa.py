#!/usr/bin/env python3
"""
Analysis: structure, targets, and choice properties of beamline_qa.
Purpose: confirm the multiple_choice plan and settle two open assumptions from
         plan.md - whether acc_norm is needed, and whether answer position or
         option length leaks the correct answer.

Usage:
    python3 analyze_beamline_qa.py [path/to/beamline_qa.jsonl]
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

DEFAULT_DATA = (
    Path(__file__).resolve().parents[4] / "custom-benchmark" / "data" / "beamline_qa.jsonl"
)

EXPECTED_FIELDS = {"id": str, "question": str, "choices": list, "answer_index": int}


def load_data(path: Path) -> list[dict]:
    """Load the dataset for analysis (plain json: no datasets dependency)."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def analyze_field_types(rows: list[dict]) -> None:
    """Check field presence and types across all samples."""
    missing, wrong_type, empty = [], [], []
    for row in rows:
        for field, kind in EXPECTED_FIELDS.items():
            if field not in row:
                missing.append((row.get("id", "?"), field))
            elif not isinstance(row[field], kind):
                wrong_type.append((row.get("id"), field, type(row[field]).__name__))
            elif isinstance(row[field], (str, list)) and not row[field]:
                empty.append((row.get("id"), field))
    print(f"   records                : {len(rows)}")
    print(f"   unique ids             : {len({r['id'] for r in rows})}")
    print(f"   missing fields         : {missing or 'none'}")
    print(f"   wrong-typed fields     : {wrong_type or 'none'}")
    print(f"   empty values           : {empty or 'none'}")

    non_ascii = [r["id"] for r in rows if not r["question"].isascii()]
    newlines = [r["id"] for r in rows if "\n" in r["question"]]
    print(f"   non-ascii questions    : {non_ascii or 'none'}")
    print(f"   questions w/ newlines  : {newlines or 'none'}")


def analyze_questions(rows: list[dict]) -> None:
    """Length distribution and format variation of the question stems."""
    lengths = [len(r["question"]) for r in rows]
    print(
        f"   question chars min/med/max: {min(lengths)}/"
        f"{int(statistics.median(lengths))}/{max(lengths)}"
    )
    print(f"   all end with '?'       : {all(r['question'].rstrip().endswith('?') for r in rows)}")


def analyze_choices(rows: list[dict]) -> None:
    """Multiple-choice specific checks: arity, encoding, duplicates."""
    arity = Counter(len(r["choices"]) for r in rows)
    print(f"   options per question   : {dict(arity)}")

    dupes = [r["id"] for r in rows if len(set(r["choices"])) != len(r["choices"])]
    print(f"   duplicate options      : {dupes or 'none'}")

    bad_index = [r["id"] for r in rows if not 0 <= r["answer_index"] < len(r["choices"])]
    print(f"   out-of-range answers   : {bad_index or 'none'}")

    positions = Counter(r["answer_index"] for r in rows)
    print(f"   answer position counts : {dict(sorted(positions.items()))}")
    majority = max(positions.values()) / len(rows)
    print(f"   always-pick-best-position baseline: {majority:.4f}")
    mean_options = statistics.mean(len(r["choices"]) for r in rows)
    print(f"   random baseline                   : {1 / mean_options:.4f}")


def analyze_length_leakage(rows: list[dict]) -> None:
    """Does option length predict correctness? Settles the acc_norm question."""
    correct_longest = 0
    correct_shortest = 0
    correct_lens, distractor_lens = [], []
    for row in rows:
        lens = [len(c) for c in row["choices"]]
        gold = row["answer_index"]
        if lens[gold] == max(lens):
            correct_longest += 1
        if lens[gold] == min(lens):
            correct_shortest += 1
        correct_lens.append(lens[gold])
        distractor_lens.extend(length for i, length in enumerate(lens) if i != gold)

    n = len(rows)
    print(
        f"   gold is longest option : {correct_longest}/{n} ({correct_longest / n:.3f}) "
        f"[chance {1 / 4:.3f}]"
    )
    print(f"   gold is shortest option: {correct_shortest}/{n} ({correct_shortest / n:.3f})")
    print(f"   mean gold length       : {statistics.mean(correct_lens):.1f} chars")
    print(f"   mean distractor length : {statistics.mean(distractor_lens):.1f} chars")


def check_edge_cases(rows: list[dict]) -> None:
    """Context dependencies, special notation, very short options."""
    short = [(r["id"], c) for r in rows for c in r["choices"] if len(c) < 4]
    print(f"   very short options     : {short or 'none'}")
    needs_context = [
        r["id"]
        for r in rows
        if any(w in r["question"].lower() for w in ("figure", "image", "above", "shown below"))
    ]
    print(f"   questions needing external context: {needs_context or 'none'}")
    special = [r["id"] for r in rows if any(ch in r["question"] for ch in "$\\{}")]
    print(f"   LaTeX/code notation    : {special or 'none'}")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
    print("=" * 60)
    print("Data Analysis for beamline_qa")
    print(f"source: {path}")
    print("=" * 60)

    rows = load_data(path)

    print("\n1. Field Types and Consistency")
    analyze_field_types(rows)
    print("\n2. Question Format")
    analyze_questions(rows)
    print("\n3. Choice Structure")
    analyze_choices(rows)
    print("\n4. Length Leakage (acc_norm decision)")
    analyze_length_leakage(rows)
    print("\n5. Edge Cases")
    check_edge_cases(rows)

    print("\n" + "=" * 60)
    print("Analysis Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
