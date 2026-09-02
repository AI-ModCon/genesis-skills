"""Shared helpers for reading and editing BPSW card markdown.

`normalize_heading` and the fence-aware heading scan are adapted from
`modcon-bpsw/scripts/analyze_cards.py` (functions `normalize_heading` and
`extract_headings`, lines 81-105), so that this tool matches headings exactly
the way the BPSW analysis pipeline already does. Vendored rather than imported
because the two live in separate repositories.

Why normalization matters: real cards deviate from the template. Across the 346
cards in `cards/resources/`, `## Uncertainty Quantification.` appears with a
trailing period in 77 of them, `## Evaluation Data` is capitalized in 8, and
`## Evaluation Results` in 7. Matching on the raw string would miss all of those.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def normalize_heading(text: str) -> str:
    """Lowercase, strip emphasis and punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[`*_]", "", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


@dataclass
class Heading:
    level: int
    title: str
    normalized: str
    line: int  # index into the body line list


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_without_fences, body). Frontmatter is None if absent."""
    if not text.startswith("---"):
        return None, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), text[match.end() :]


def scan_headings(body_lines: list[str]) -> list[Heading]:
    """Headings in document order, skipping anything inside a fenced code block."""
    out: list[Heading] = []
    in_code = False
    for idx, line in enumerate(body_lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        title = match.group(2).strip()
        normalized = normalize_heading(title)
        if normalized:
            out.append(Heading(len(match.group(1)), title, normalized, idx))
    return out


def section_span(
    headings: list[Heading], body_lines: list[str], normalized_title: str
) -> tuple[int, int] | None:
    """Body-line span (content_start, content_end) for a section, excluding its heading.

    The section ends at the next heading of the same or shallower level.
    """
    for pos, heading in enumerate(headings):
        if heading.normalized != normalized_title:
            continue
        start = heading.line + 1
        end = len(body_lines)
        for later in headings[pos + 1 :]:
            if later.level <= heading.level:
                end = later.line
                break
        return start, end
    return None


def subsection_span(
    headings: list[Heading],
    body_lines: list[str],
    outer: tuple[int, int],
    normalized_title: str,
) -> tuple[int, int] | None:
    """Span of a subsection *including* its heading line, within `outer`."""
    start_line, end_line = outer
    for pos, heading in enumerate(headings):
        if not (start_line <= heading.line < end_line):
            continue
        if heading.normalized != normalized_title:
            continue
        end = end_line
        for later in headings[pos + 1 :]:
            if later.line >= end_line:
                break
            if later.level <= heading.level:
                end = later.line
                break
        return heading.line, end
    return None


def trim_blank_edges(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines
