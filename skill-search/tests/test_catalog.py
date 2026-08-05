"""Tests for discovery, merge, and search behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skill_search import ValidationError, discover_skills, inspect_catalog, load_skill_body, rank_skills, search_skills, to_prompt


def _write_skill(parent: Path, name: str, description: str, body: str = "Instructions here.\n") -> Path:
    skill_dir = parent / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n\n{body}",
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


class CatalogTests(unittest.TestCase):
    def test_discover_skills_reports_and_skips_invalid_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_skill(root, "slurm", "Write a Slurm batch job")
            invalid = _write_missing_name_skill(root, "broken-skill")
            skipped: list[tuple[Path, str]] = []

            discovered = discover_skills(
                root,
                on_skip=lambda path, exc: skipped.append((path, str(exc))),
            )

            self.assertEqual([skill.name for skill in discovered], ["slurm"])
            self.assertEqual(skipped, [(invalid.resolve(), "Missing required field in frontmatter: name")])

    def test_discover_skills_reports_and_skips_unreadable_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_skill(root, "slurm", "Write a Slurm batch job")
            unreadable = root / "unreadable-skill"
            unreadable.mkdir()
            (unreadable / "SKILL.md").write_bytes(b"\xff\xfe\x00")
            skipped: list[tuple[Path, BaseException]] = []

            discovered = discover_skills(
                root,
                on_skip=lambda path, exc: skipped.append((path, exc)),
            )

            self.assertEqual([skill.name for skill in discovered], ["slurm"])
            self.assertEqual(skipped[0][0], unreadable.resolve())
            self.assertIsInstance(skipped[0][1], UnicodeDecodeError)

    def test_discover_skills_without_callback_remains_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_skill(root, "slurm", "Write a Slurm batch job")
            _write_missing_name_skill(root, "broken-skill")

            with self.assertRaises(ValidationError):
                discover_skills(root)

    def test_search_skips_invalid_override_and_uses_valid_earlier_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central = tmp_path / "central"
            central.mkdir()
            valid = _write_skill(central, "slurm", "Write a Slurm batch job")
            user = tmp_path / "user"
            user.mkdir()
            invalid = _write_missing_name_skill(user, "slurm")
            skipped: list[Path] = []

            matches = search_skills(
                [central, user],
                query="write slurm batch job",
                on_skip=lambda path, _exc: skipped.append(path),
            )

            self.assertEqual(matches[0].skill.path, valid.resolve())
            self.assertEqual(skipped, [invalid.resolve()])

    def test_discover_skills_merges_duplicate_names_with_later_root_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central_repo = tmp_path / "central-repo"
            central_skills = central_repo / "skills"
            central_skills.mkdir(parents=True)
            user_repo = tmp_path / "user-repo"
            user_skills = user_repo / "skills"
            user_skills.mkdir(parents=True)

            _write_skill(central_skills, "doc-reader", "Central description")
            _write_skill(central_skills, "pdf-reader", "Extract text from PDF files")
            user_override = _write_skill(user_skills, "doc-reader", "User override description")

            discovered = discover_skills([central_repo, user_repo])

            self.assertEqual([skill.name for skill in discovered], ["doc-reader", "pdf-reader"])
            self.assertEqual(discovered[0].path, user_override.resolve())
            self.assertEqual(discovered[0].source_root, user_repo.resolve())

    def test_inspect_catalog_reports_override_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central_repo = tmp_path / "central-repo"
            central_skills = central_repo / "skills"
            central_skills.mkdir(parents=True)
            user_repo = tmp_path / "user-repo"
            user_skills = user_repo / "skills"
            user_skills.mkdir(parents=True)

            central_skill = _write_skill(central_skills, "doc-reader", "Central description")
            user_skill = _write_skill(user_skills, "doc-reader", "User override description")

            catalog = inspect_catalog([central_repo, user_repo])

            self.assertEqual(len(catalog.overrides), 1)
            override = catalog.overrides[0]
            self.assertEqual(override.winner.path, user_skill.resolve())
            self.assertEqual([skill.path for skill in override.replaced], [central_skill.resolve()])

    def test_search_and_prompt_use_merged_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central_repo = tmp_path / "central-repo"
            central_skills = central_repo / "skills"
            central_skills.mkdir(parents=True)
            user_repo = tmp_path / "user-repo"
            user_skills = user_repo / "skills"
            user_skills.mkdir(parents=True)

            _write_skill(central_skills, "screenshot", "Capture images from the desktop")
            user_skill = _write_skill(
                user_skills,
                "screenshot",
                "Take a screenshot of a local app window",
            )

            matches = search_skills([central_repo, user_repo], query="take a screenshot", top_k=1)
            prompt = to_prompt([central_repo, user_repo])

            self.assertEqual([match.skill.name for match in matches], ["screenshot"])
            self.assertEqual(matches[0].skill.path, user_skill.resolve())
            self.assertIn("Take a screenshot of a local app window", prompt)
            self.assertEqual(prompt.count("<skill>"), 1)


    def test_search_skills_matches_rank_skills_for_overrides(self) -> None:
        """search_skills and rank_skills(discover_skills()) must pick the same winner."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            central_repo = tmp_path / "central-repo"
            central_skills = central_repo / "skills"
            central_skills.mkdir(parents=True)
            user_repo = tmp_path / "user-repo"
            user_skills = user_repo / "skills"
            user_skills.mkdir(parents=True)

            _write_skill(central_skills, "pdf-reader", "Read text from PDF documents")
            _write_skill(user_skills, "pdf-reader", "Extract text and tables from PDF files")

            query = "extract text from pdf"
            search_results = search_skills([central_repo, user_repo], query=query)
            rank_results = rank_skills(query, discover_skills([central_repo, user_repo]))

            self.assertEqual(len(search_results), len(rank_results))
            for sr, rr in zip(search_results, rank_results):
                self.assertEqual(sr.skill.name, rr.skill.name)
                self.assertEqual(sr.skill.path, rr.skill.path)
                self.assertEqual(sr.score, rr.score)

    def test_search_skills_empty_query_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            repo = tmp_path / "repo"
            skills = repo / "skills"
            skills.mkdir(parents=True)
            _write_skill(skills, "hello-world", "Write a hello world file")

            self.assertEqual(search_skills(repo, query=""), [])
            self.assertEqual(search_skills(repo, query="   "), [])

    def test_search_skills_no_matches_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            repo = tmp_path / "repo"
            skills = repo / "skills"
            skills.mkdir(parents=True)
            _write_skill(skills, "hello-world", "Write a hello world file")

            self.assertEqual(search_skills(repo, query="zyxwvutsrqp"), [])

    def test_discover_skills_finds_nested_collection_dir(self) -> None:
        """discover_skills finds skills one level inside a collection with no root SKILL.md."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            collection = tmp_path / "anthropic-skills"
            collection.mkdir()

            _write_skill(collection, "pdf", "Extract text from PDF files")
            _write_skill(collection, "canvas-design", "Design visual layouts on canvas")

            discovered = discover_skills(collection)

            self.assertEqual(
                [skill.name for skill in discovered],
                ["canvas-design", "pdf"],
            )

    def test_discover_skills_finds_nested_collections_via_skills_subdir(self) -> None:
        """discover_skills finds nested collection skills when given a repo root."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()

            _write_skill(skills_dir, "flat-skill", "A directly placed skill")

            collection = skills_dir / "my-collection"
            collection.mkdir()
            _write_skill(collection, "nested-skill", "A skill inside a collection")

            discovered = discover_skills(tmp_path)

            self.assertEqual(
                sorted(skill.name for skill in discovered),
                ["flat-skill", "nested-skill"],
            )

    def test_discover_skills_finds_deep_nested_dotdir_collection(self) -> None:
        """discover_skills recurses into hidden directories like .curated/."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()

            openai_collection = skills_dir / "openai-skills"
            openai_collection.mkdir()
            curated = openai_collection / ".curated"
            curated.mkdir()

            _write_skill(curated, "security-threat-model", "Model threats in a codebase")
            _write_skill(curated, "playwright", "Automate browser interactions")

            discovered = discover_skills(tmp_path)

            self.assertEqual(
                sorted(skill.name for skill in discovered),
                ["playwright", "security-threat-model"],
            )

    def test_search_skills_finds_nested_collection_skills(self) -> None:
        """search_skills returns results from skills nested inside collection dirs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()

            collection = skills_dir / "openai-collection"
            collection.mkdir()
            _write_skill(collection, "playwright", "Automate browser interactions with Playwright")

            results = search_skills(tmp_path, query="automate browser")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].skill.name, "playwright")

    def test_discover_skills_does_not_recurse_into_skill_subdirs(self) -> None:
        """Subdirectories inside a skill dir are not treated as nested skills."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()

            skill_dir = _write_skill(skills_dir, "my-skill", "A skill with subdirectories")

            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "SKILL.md").write_text(
                "---\nname: scripts\ndescription: Should not be found\n---\n",
                encoding="utf-8",
            )

            discovered = discover_skills(tmp_path)

            self.assertEqual(len(discovered), 1)
            self.assertEqual(discovered[0].name, "my-skill")

    def test_load_skill_body_returns_body_without_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "my-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: A test skill\n---\n# My Skill\n\nDo the thing.\n",
                encoding="utf-8",
            )

            body = load_skill_body(skill_dir)

            self.assertIn("# My Skill", body)
            self.assertIn("Do the thing.", body)
            self.assertNotIn("---", body)

    def test_load_skill_body_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "my-skill"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                "---\nname: my-skill\ndescription: A test skill\n---\nBody content.\n",
                encoding="utf-8",
            )

            body_from_dir = load_skill_body(str(skill_dir))
            body_from_file = load_skill_body(str(skill_md))

            self.assertEqual(body_from_dir, body_from_file)
            self.assertIn("Body content.", body_from_dir)


if __name__ == "__main__":
    unittest.main()
