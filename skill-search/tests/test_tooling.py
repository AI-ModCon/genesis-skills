"""Tests for high-level tooling helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skill_search.errors import SkillSearchError
from skill_search.tooling import build_search_callable, load_all_payload, progressive_disclosure_payload, resolve_catalog_roots, resolve_central_root, search_payload


def _write_skill(parent: Path, name: str, description: str) -> Path:
    skill_dir = parent / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n\nInstructions here.\n",
        encoding="utf-8",
    )
    return skill_dir


def _write_missing_name_skill(parent: Path, directory_name: str) -> Path:
    skill_dir = parent / directory_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: Missing a required name\n---\nInstructions here.\n",
        encoding="utf-8",
    )
    return skill_dir


class ToolingTests(unittest.TestCase):
    def test_payloads_report_skipped_entries_without_losing_valid_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_skill(root, "slurm", "Write a Slurm batch job")
            invalid = _write_missing_name_skill(root, "broken-skill")

            payloads = [
                progressive_disclosure_payload(central_root=root),
                load_all_payload(central_root=root),
                search_payload("slurm batch", central_root=root),
            ]

            for payload in payloads:
                self.assertEqual(
                    payload["skipped"],
                    [{
                        "path": str(invalid.resolve()),
                        "reason": "Missing required field in frontmatter: name",
                    }],
                )
            self.assertEqual(payloads[0]["count"], 1)
            self.assertEqual(payloads[1]["count"], 1)
            self.assertEqual(payloads[2]["matches"][0]["name"], "slurm")

    def test_resolve_central_root_uses_sibling_skills_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tool_root = tmp_path / "skill-search"
            tool_root.mkdir()
            sibling_skills = tmp_path / "skills"
            sibling_skills.mkdir()

            self.assertEqual(resolve_central_root(tool_root=tool_root), sibling_skills.resolve())

    def test_load_all_and_search_payloads_include_catalog_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central_root = tmp_path / "central-skills"
            central_root.mkdir()
            _write_skill(central_root, "hello-world-writer", "Write a hello world file")

            user_root = tmp_path / "user-skills"
            user_root.mkdir()
            _write_skill(user_root, "screenshot", "Take a screenshot of a local app")

            roots = resolve_catalog_roots(central_root=central_root, my_skills_path=user_root)
            full_payload = load_all_payload(
                central_root=central_root,
                my_skills_path=user_root,
                include_prompt=True,
            )
            search_results = search_payload(
                "hello world file",
                central_root=central_root,
                my_skills_path=user_root,
            )

            self.assertEqual([str(root) for root in roots], full_payload["catalog_roots"])
            self.assertEqual(full_payload["count"], 2)
            self.assertIn("available_skills_prompt", full_payload)
            self.assertEqual(search_results["matches"][0]["name"], "hello-world-writer")


    def test_build_search_callable_returns_search_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central_root = tmp_path / "central-skills"
            central_root.mkdir()
            _write_skill(central_root, "hello-world-writer", "Write a hello world file")

            search = build_search_callable(central_root=central_root)
            result = search("hello world")

            self.assertEqual(result["mode"], "search")
            self.assertGreaterEqual(result["count"], 1)
            self.assertEqual(result["matches"][0]["name"], "hello-world-writer")

    def test_resolve_central_root_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tool_root = Path(tmp_dir) / "skill-search"
            tool_root.mkdir()
            # No sibling skills directory and no env var

            with self.assertRaises(SkillSearchError):
                resolve_central_root(tool_root=tool_root)

    def test_resolve_central_root_uses_env_var(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_skills = tmp_path / "env-skills"
            env_skills.mkdir()

            old = os.environ.get("SKILL_SEARCH_CENTRAL_ROOT")
            try:
                os.environ["SKILL_SEARCH_CENTRAL_ROOT"] = str(env_skills)
                result = resolve_central_root(tool_root=tmp_path / "nonexistent-tool")
                self.assertEqual(result, env_skills.resolve())
            finally:
                if old is None:
                    os.environ.pop("SKILL_SEARCH_CENTRAL_ROOT", None)
                else:
                    os.environ["SKILL_SEARCH_CENTRAL_ROOT"] = old


if __name__ == "__main__":
    unittest.main()
