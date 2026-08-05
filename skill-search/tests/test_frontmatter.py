"""Tests for the minimal frontmatter parser."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skill_search.errors import ParseError, ValidationError
from skill_search.frontmatter import parse_frontmatter, read_properties


class FrontmatterTests(unittest.TestCase):
    def test_parse_frontmatter_supports_quotes_and_metadata(self) -> None:
        content = """---
name: "demo-skill"
description: "Use this when a demo is needed."
license: LICENSE.txt
metadata:
  author: DOE
  version: "1.0"
---
# Demo

Run the demo.
"""
        metadata, body = parse_frontmatter(content)

        self.assertEqual(metadata["name"], "demo-skill")
        self.assertEqual(metadata["description"], "Use this when a demo is needed.")
        self.assertEqual(metadata["license"], "LICENSE.txt")
        self.assertEqual(metadata["metadata"], {"author": "DOE", "version": "1.0"})
        self.assertIn("# Demo", body)

    def test_read_properties_reads_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "demo-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                """---
name: demo-skill
description: Use for demonstrations.
compatibility: Requires a local model endpoint.
---
Body
""",
                encoding="utf-8",
            )

            props = read_properties(skill_dir)

            self.assertEqual(props.name, "demo-skill")
            self.assertEqual(props.description, "Use for demonstrations.")
            self.assertEqual(props.compatibility, "Requires a local model endpoint.")


    def test_parse_frontmatter_folded_block_scalar(self) -> None:
        content = """---
name: aurora
description: >
  ALCF Aurora supercomputer at Argonne. Use when submitting PBS jobs,
  choosing queues, or loading Intel modules.
compatibility: Must be on an Aurora login node.
---
Body
"""
        metadata, _ = parse_frontmatter(content)

        self.assertEqual(
            metadata["description"],
            "ALCF Aurora supercomputer at Argonne. Use when submitting PBS jobs, "
            "choosing queues, or loading Intel modules.",
        )
        # The key after the block scalar must still be parsed.
        self.assertEqual(metadata["compatibility"], "Must be on an Aurora login node.")

    def test_parse_frontmatter_literal_block_scalar_preserves_newlines(self) -> None:
        content = """---
name: demo
description: |
  line one
  line two
---
Body
"""
        metadata, _ = parse_frontmatter(content)

        self.assertEqual(metadata["description"], "line one\nline two")

    def test_parse_frontmatter_folded_scalar_with_metadata_block(self) -> None:
        content = """---
name: demo
description: >
  folded value spanning
  two lines
metadata:
  version: "1.0"
---
Body
"""
        metadata, _ = parse_frontmatter(content)

        self.assertEqual(metadata["description"], "folded value spanning two lines")
        self.assertEqual(metadata["metadata"], {"version": "1.0"})

    def test_parse_frontmatter_missing_opening_fence_raises(self) -> None:
        with self.assertRaises(ParseError):
            parse_frontmatter("name: demo\ndescription: test\n---\nBody\n")

    def test_parse_frontmatter_missing_closing_fence_raises(self) -> None:
        with self.assertRaises(ParseError):
            parse_frontmatter("---\nname: demo\ndescription: test\nBody\n")

    def test_read_properties_missing_name_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "bad-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\ndescription: Missing the name field\n---\nBody\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValidationError):
                read_properties(skill_dir)


if __name__ == "__main__":
    unittest.main()
