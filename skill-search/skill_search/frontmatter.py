"""Minimal frontmatter parsing for SKILL.md files."""

from __future__ import annotations

import ast
from pathlib import Path

from .errors import ParseError, ValidationError
from .models import SkillProperties


def find_skill_md(skill_dir: Path) -> Path | None:
    """Find the SKILL.md file in a skill directory."""

    for name in ("SKILL.md", "skill.md"):
        candidate = skill_dir / name
        if candidate.exists():
            return candidate
    return None


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
        return str(parsed)
    return value


def _parse_scalar(value: str) -> str:
    return _strip_quotes(value.strip())


_BLOCK_INDICATORS = (">", "|")


def _is_block_scalar(value: str) -> bool:
    """True if *value* is a YAML block-scalar header (>, |, optionally chomped)."""

    if not value or value[0] not in _BLOCK_INDICATORS:
        return False
    return value[1:] in ("", "-", "+")


def _collect_block_scalar(
    lines: list[str], start: int, key_indent: int, indicator: str
) -> tuple[str, int]:
    """Collect a block scalar starting at line *start*.

    Returns the assembled value and the index of the first line not consumed.
    Lines belong to the block while they are blank or indented more than the
    key. Folded (``>``) joins lines within a paragraph with spaces and turns a
    blank line into a newline; literal (``|``) preserves newlines.
    """

    block: list[str] = []
    index = start
    while index < len(lines):
        raw = lines[index]
        if raw.strip() == "":
            block.append("")
            index += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent <= key_indent:
            break
        block.append(raw)
        index += 1

    # Trim trailing blank lines, then dedent by the least-indented content line.
    while block and block[-1] == "":
        block.pop()
    content_indents = [len(b) - len(b.lstrip(" ")) for b in block if b != ""]
    dedent = min(content_indents) if content_indents else 0
    stripped = [b[dedent:] if b != "" else "" for b in block]

    if indicator == "|":
        value = "\n".join(stripped)
    else:  # folded: blank line -> newline, otherwise join paragraph lines with spaces
        parts: list[str] = []
        paragraph: list[str] = []
        for piece in stripped:
            if piece == "":
                if paragraph:
                    parts.append(" ".join(paragraph))
                    paragraph = []
                parts.append("")
            else:
                paragraph.append(piece)
        if paragraph:
            parts.append(" ".join(paragraph))
        value = "\n".join(parts)

    return value.strip(), index


def _split_frontmatter(content: str) -> tuple[list[str], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ParseError("SKILL.md must start with YAML frontmatter (---)")

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise ParseError("SKILL.md frontmatter not properly closed with ---")

    frontmatter_lines = lines[1:closing_index]
    body = "\n".join(lines[closing_index + 1 :]).strip()
    return frontmatter_lines, body


def parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    """Parse a limited YAML subset from SKILL.md frontmatter."""

    frontmatter_lines, body = _split_frontmatter(content)
    metadata: dict[str, object] = {}
    in_metadata_block = False

    index = 0
    while index < len(frontmatter_lines):
        raw_line = frontmatter_lines[index]
        index += 1

        if not raw_line.strip():
            continue
        if raw_line.strip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            key, separator, value = line.partition(":")
            if not separator:
                raise ParseError(f"Invalid frontmatter line: {raw_line}")

            key = key.strip()
            value = value.lstrip()
            in_metadata_block = False

            if key == "metadata" and value == "":
                metadata[key] = {}
                in_metadata_block = True
                continue

            if _is_block_scalar(value):
                metadata[key], index = _collect_block_scalar(
                    frontmatter_lines, index, indent, value[0]
                )
                continue

            metadata[key] = _parse_scalar(value)
            continue

        if not in_metadata_block or "metadata" not in metadata or not isinstance(metadata["metadata"], dict):
            raise ParseError(f"Unexpected indented frontmatter line: {raw_line}")

        child_key, separator, child_value = line.partition(":")
        if not separator:
            raise ParseError(f"Invalid metadata line: {raw_line}")
        metadata["metadata"][child_key.strip()] = _parse_scalar(child_value.lstrip())

    return metadata, body


def read_properties(skill_dir: Path) -> SkillProperties:
    """Read minimal skill properties from a skill directory."""

    skill_dir = Path(skill_dir)
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        raise ParseError(f"SKILL.md not found in {skill_dir}")

    content = skill_md.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(content)

    if "name" not in metadata:
        raise ValidationError("Missing required field in frontmatter: name")
    if "description" not in metadata:
        raise ValidationError("Missing required field in frontmatter: description")

    name = metadata["name"]
    description = metadata["description"]
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Field 'name' must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ValidationError("Field 'description' must be a non-empty string")

    raw_metadata = metadata.get("metadata")
    normalized_metadata: dict[str, str] = {}
    if isinstance(raw_metadata, dict):
        normalized_metadata = {
            str(key): str(value) for key, value in raw_metadata.items() if str(key).strip()
        }

    return SkillProperties(
        name=name.strip(),
        description=description.strip(),
        license=str(metadata["license"]).strip() if "license" in metadata else None,
        compatibility=(
            str(metadata["compatibility"]).strip() if "compatibility" in metadata else None
        ),
        allowed_tools=(
            str(metadata["allowed-tools"]).strip() if "allowed-tools" in metadata else None
        ),
        metadata=normalized_metadata,
    )
