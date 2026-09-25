#!/usr/bin/env python3
"""Helpers for validating the repository structure and provenance docs."""

from __future__ import annotations

import re
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _skill_names(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    names = {path.parent.name for path in root.rglob("SKILL.md") if path.is_file()}
    return sorted(names, key=str.casefold)


def _top_level_skill_dirs(skills_root: Path) -> list[Path]:
    if not skills_root.is_dir():
        return []

    candidates = [
        path
        for path in skills_root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and any(child.is_file() for child in path.rglob("SKILL.md"))
    ]
    return sorted(candidates, key=lambda path: path.name.casefold())


def _skill_tree_line(skill_root: Path) -> str:
    direct_skill = skill_root / "SKILL.md"
    skill_files = [path for path in skill_root.rglob("SKILL.md") if path.is_file()]
    if len(skill_files) == 1 and skill_files[0] == direct_skill:
        return f"{skill_root.name}/SKILL.md"

    names = _skill_names(skill_root)
    return f"{skill_root.name}/  # {', '.join(names)} ({len(names)})"


def _people_sort_key(name: str) -> tuple[str, str]:
    parts = name.split()
    last = parts[-1] if parts else name
    return (last.casefold(), name.casefold())


ROOT_README_EXTRA_CONTRIBUTORS = (
    "Matt Baughman",
    "Ian Foster",
    "Nathan Hodas",
    "Stefan Wild",
)

ROOT_README_EXTRA_TEAMS = ("ModCon Base CAF Team",)


def _extract_name(fragment: str) -> str:
    fragment = fragment.strip()
    fragment = re.sub(r"\s*\[.*?\]$", "", fragment)
    fragment = re.split(r"\s*[\(<]", fragment, maxsplit=1)[0].strip()
    return fragment


def _names_from_csv_line(text: str) -> list[str]:
    names: list[str] = []
    for chunk in text.split(","):
        name = _extract_name(chunk)
        if name:
            names.append(name)
    return names


def _notice_contact(root: Path) -> str | None:
    notice = root / "NOTICE"
    if not notice.is_file():
        return None
    match = re.search(r"^Contact:\s*(.+?)\s*<", _read(notice), re.MULTILINE)
    if not match:
        return None
    return _extract_name(match.group(1))


def _basedata_contributors(root: Path) -> tuple[str | None, list[str]]:
    path = root / "skills" / "basedata-skills" / "ATTRIBUTION.md"
    if not path.is_file():
        return None, []
    team = None
    names: list[str] = []
    for line in _read(path).splitlines():
        if line.startswith("**Team:**"):
            team = "ModCon Base Data Team"
            tail = line.split(":", 1)[1]
            if ":" in tail:
                tail = tail.split(":", 1)[1]
            names.extend(_names_from_csv_line(tail))
    return team, names


def _amsc_team(root: Path) -> str | None:
    path = root / "skills" / "amsc-skills" / "ATTRIBUTION.md"
    if not path.is_file():
        return None
    return "American Science Cloud Intelligent Interfaces Team"


def _lm_eval_contributors(root: Path) -> list[str]:
    path = root / "skills" / "baseeval-skills" / "lm-eval-harness-skills" / "ATTRIBUTION.md"
    if not path.is_file():
        return []
    for line in _read(path).splitlines():
        if line.startswith("**Author:**"):
            match = re.match(r"\*\*Author:\*\*\s*(.+?)(?:,|$)", line)
            if match:
                return [_extract_name(match.group(1))]
    return []


def _perlmutter_ns_contributors(root: Path) -> list[str]:
    path = root / "skills" / "baseeval-skills" / "perlmutter-ns-skills" / "ATTRIBUTION.md"
    if not path.is_file():
        return []
    names: list[str] = []
    in_authors = False
    for line in _read(path).splitlines():
        if line.startswith("**Authors:**"):
            in_authors = True
            continue
        if in_authors:
            if line.startswith("- "):
                names.append(_extract_name(line[2:].split(",", 1)[0]))
            elif line.strip():
                break
    return names


def _baseeval_team(root: Path) -> str | None:
    path = root / "skills" / "baseeval-skills" / "README.md"
    if not path.is_file():
        return None
    return "ModCon Base Eval Team"


def _basesafe_contributors(root: Path) -> tuple[str | None, list[str]]:
    path = root / "skills" / "basesafe-skills" / "readme.md"
    if not path.is_file():
        return None, []
    names: list[str] = []
    in_table = False
    for line in _read(path).splitlines():
        if line.startswith("| Name"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 1 and cells[0] and set(cells[0]) != {"-"}:
                names.append(_extract_name(cells[0]))
    return "ModCon Base Safe Team", names


def build_readme_tree_lines(root: Path) -> list[str]:
    """Return the canonical README repository-structure tree as lines."""

    skills = root / "skills"
    lines = [
        "genesis-skills/",
        "├── unpack.sh                  # flatten skills into an agent's skills dir (Method 1)",
        "├── skill-search/              # the upper-level discovery skill (Method 2)",
        "│   ├── SKILL.md",
        "│   └── scripts/skill_search.py",
        "├── skills/",
    ]

    skill_roots = _top_level_skill_dirs(skills)
    for index, skill_root in enumerate(skill_roots):
        branch = "└──" if index == len(skill_roots) - 1 else "├──"
        lines.append(f"│   {branch} {_skill_tree_line(skill_root)}")

    lines.extend(
        [
            "├── CONTRIBUTING.md",
            "├── LICENSE",
            "├── NOTICE                     # third-party licensing and attribution inventory",
            "├── README.md",
            "└── skill_spec.md              # Agent Skills format specification",
        ]
    )
    return lines


def build_readme_contributor_names(root: Path) -> list[str]:
    """Return the canonical contributor list for the README."""

    individuals: set[str] = set()
    teams: set[str] = set()

    contact = _notice_contact(root)
    if contact:
        individuals.add(contact)

    amsc_team = _amsc_team(root)
    if amsc_team:
        teams.add(amsc_team)

    team, names = _basedata_contributors(root)
    if team:
        teams.add(team)
    individuals.update(names)

    individuals.update(_lm_eval_contributors(root))
    individuals.update(_perlmutter_ns_contributors(root))
    individuals.update(ROOT_README_EXTRA_CONTRIBUTORS)
    teams.update(ROOT_README_EXTRA_TEAMS)

    baseeval_team = _baseeval_team(root)
    if baseeval_team:
        teams.add(baseeval_team)

    team, names = _basesafe_contributors(root)
    if team:
        teams.add(team)
    individuals.update(names)

    ordered_individuals = sorted(individuals, key=_people_sort_key)
    ordered_teams = sorted(teams, key=str.casefold)
    return ordered_individuals + ordered_teams
