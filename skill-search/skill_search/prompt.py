"""Prompt generation helpers."""

from __future__ import annotations

import html
from pathlib import Path

from .catalog import discover_skills, merge_skills
from .models import DiscoveredSkill


def to_prompt(skill_inputs: list[Path | str | DiscoveredSkill]) -> str:
    """Generate the <available_skills> XML block for inclusion in agent prompts.

    This XML format is what Anthropic uses and recommends for Claude models.
    Skill Clients may format skill information differently to suit their
    models or preferences.

    Args:
        skill_inputs: List of discovered skills, skill directories, or repo roots

    Returns:
        XML string with <available_skills> block containing each skill's
        name, description, and location.

    Example output:
        <available_skills>
        <skill>
        <name>pdf-reader</name>
        <description>Read and extract text from PDF files</description>
        <location>/path/to/pdf-reader/SKILL.md</location>
        </skill>
        </available_skills>
    """

    if not skill_inputs:
        return "<available_skills>\n</available_skills>"

    inline_skills: list[DiscoveredSkill] = []
    path_inputs: list[Path | str] = []

    for item in skill_inputs:
        if isinstance(item, DiscoveredSkill):
            inline_skills.append(item)
        else:
            path_inputs.append(item)

    resolved_skills = inline_skills + (discover_skills(path_inputs) if path_inputs else [])
    merged_skills = merge_skills(resolved_skills).skills

    lines = ["<available_skills>"]
    for skill in merged_skills:
        lines.append("<skill>")
        lines.append("<name>")
        lines.append(html.escape(skill.name))
        lines.append("</name>")
        lines.append("<description>")
        lines.append(html.escape(skill.description))
        lines.append("</description>")
        lines.append("<location>")
        lines.append(html.escape(str(Path(skill.skill_md_path).resolve())))
        lines.append("</location>")
        lines.append("</skill>")
    lines.append("</available_skills>")
    return "\n".join(lines)
