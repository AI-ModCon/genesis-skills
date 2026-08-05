"""End-to-end tests for the path-based skill-search CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill_search.py"


def _write_fixture(root: Path) -> Path:
    valid = root / "slurm"
    valid.mkdir()
    (valid / "SKILL.md").write_text(
        "---\nname: slurm\ndescription: Write a Slurm batch job\n---\nInstructions.\n",
        encoding="utf-8",
    )
    invalid = root / "broken-skill"
    invalid.mkdir()
    (invalid / "SKILL.md").write_text(
        "---\ndescription: Missing a required name\n---\nInstructions.\n",
        encoding="utf-8",
    )
    return invalid


class CliTests(unittest.TestCase):
    def test_query_and_load_all_keep_json_clean_while_warning_on_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            invalid = _write_fixture(root)
            commands = [
                ["--query", "write a slurm batch job"],
                ["--load-all"],
            ]

            for arguments in commands:
                with self.subTest(arguments=arguments):
                    completed = subprocess.run(
                        [sys.executable, str(SCRIPT), "--central-root", str(root), *arguments],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    payload = json.loads(completed.stdout)
                    self.assertNotIn("Warning:", completed.stdout)
                    self.assertNotIn("Error:", completed.stdout)
                    self.assertIn(str(invalid.resolve()), completed.stderr)
                    self.assertIn("Missing required field in frontmatter: name", completed.stderr)
                    self.assertEqual(payload["skipped"][0]["path"], str(invalid.resolve()))
                    if "matches" in payload:
                        self.assertEqual(payload["matches"][0]["name"], "slurm")
                    else:
                        self.assertEqual(payload["skills"][0]["name"], "slurm")


if __name__ == "__main__":
    unittest.main()
