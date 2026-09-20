"""Smoke tests for the nested skill-search helper.

These tests only validate the skill-search helper and do not exercise the
broader skill catalog content.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.skill_fixtures import write_skill


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill-search" / "scripts" / "skill_search.py"


class SkillSearchSmokeTests(unittest.TestCase):
    def test_cli_load_all_returns_json_for_a_simple_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            skills_dir = root / "skills"
            skills_dir.mkdir()

            write_skill(skills_dir / "demo-skill", description="Demo skill for smoke testing")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--central-root",
                    str(root),
                    "--load-all",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["mode"], "progressive_disclosure")
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["skills"][0]["name"], "demo-skill")

    def test_cli_search_returns_matching_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            skills_dir = root / "skills"
            skills_dir.mkdir()

            write_skill(skills_dir / "slurm-submit", description="Submit a Slurm batch job")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--central-root",
                    str(root),
                    "--query",
                    "slurm batch job",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["mode"], "search")
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["matches"][0]["name"], "slurm-submit")


if __name__ == "__main__":
    unittest.main()
