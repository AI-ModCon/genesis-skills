#!/usr/bin/env python3
"""Path-based entrypoint for skill catalog loading and search."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKAGE_PARENT = Path(__file__).resolve().parents[1]
if str(PACKAGE_PARENT) in sys.path:
    sys.path.remove(str(PACKAGE_PARENT))
sys.path.insert(0, str(PACKAGE_PARENT))

from skill_search.errors import SkillSearchError
from skill_search.tooling import load_all_payload, progressive_disclosure_payload, search_payload


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Skill catalog tool with two discovery strategies: "
            "skill search (--query) and standard progressive disclosure (--load-all)."
        )
    )
    parser.add_argument(
        "--central-root",
        type=Path,
        help="Explicit central skills root. Defaults to sibling ../skills next to skill-search.",
    )
    parser.add_argument(
        "--my-skills-path",
        action="append",
        default=[],
        type=Path,
        help="Optional user-managed skills root. Repeat to add multiple roots.",
    )
    parser.add_argument(
        "--load-all",
        action="store_true",
        help=(
            "Standard progressive disclosure: return a compact index of every skill "
            "(name, description, path) without loading any SKILL.md bodies. "
            "Mutually exclusive with --query."
        ),
    )
    parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="Include the <available_skills> XML block in --load-all mode.",
    )
    parser.add_argument(
        "--query",
        help=(
            "Skill search: return the top-k keyword matches for this query. "
            "Mutually exclusive with --load-all."
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of search matches to return.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=1,
        help="Minimum score required for a search result.",
    )
    return parser


def main() -> int:
    """Run the path-based skill search entrypoint."""

    parser = build_parser()
    args = parser.parse_args()

    tool_root = Path(__file__).resolve().parents[1]

    try:
        if args.load_all:
            if args.include_prompt:
                payload = load_all_payload(
                    central_root=args.central_root,
                    my_skills_path=args.my_skills_path,
                    tool_root=tool_root,
                    include_prompt=True,
                )
            else:
                payload = progressive_disclosure_payload(
                    central_root=args.central_root,
                    my_skills_path=args.my_skills_path,
                    tool_root=tool_root,
                )
        else:
            if not args.query:
                parser.error("--query is required for skill search unless --load-all is used")
            payload = search_payload(
                args.query,
                top_k=args.top_k,
                min_score=args.min_score,
                central_root=args.central_root,
                my_skills_path=args.my_skills_path,
                tool_root=tool_root,
            )
    except (SkillSearchError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for skipped in payload.get("skipped", []):
        print(
            f"Warning: skipped skill {skipped['path']}: {skipped['reason']}",
            file=sys.stderr,
        )

    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
