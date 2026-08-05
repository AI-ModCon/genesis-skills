"""Data models for skill search."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SkillProperties:
    """Properties parsed from a skill's SKILL.md frontmatter."""

    name: str
    description: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""

        result: dict[str, object] = {
            "name": self.name,
            "description": self.description,
        }
        if self.license is not None:
            result["license"] = self.license
        if self.compatibility is not None:
            result["compatibility"] = self.compatibility
        if self.allowed_tools is not None:
            result["allowed-tools"] = self.allowed_tools
        if self.metadata:
            result["metadata"] = dict(self.metadata)
        return result


@dataclass(frozen=True)
class DiscoveredSkill:
    """Skill metadata plus canonical filesystem locations."""

    name: str
    description: str
    path: Path
    skill_md_path: Path
    source_root: Optional[Path] = None
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_properties(
        cls,
        properties: SkillProperties,
        path: Path,
        skill_md_path: Path,
        *,
        source_root: Optional[Path] = None,
    ) -> "DiscoveredSkill":
        """Create a discovered skill from parsed properties."""

        return cls(
            name=properties.name,
            description=properties.description,
            path=path,
            skill_md_path=skill_md_path,
            source_root=source_root,
            license=properties.license,
            compatibility=properties.compatibility,
            allowed_tools=properties.allowed_tools,
            metadata=dict(properties.metadata),
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""

        result: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
            "skill_md_path": str(self.skill_md_path),
        }
        if self.source_root is not None:
            result["source_root"] = str(self.source_root)
        if self.license is not None:
            result["license"] = self.license
        if self.compatibility is not None:
            result["compatibility"] = self.compatibility
        if self.allowed_tools is not None:
            result["allowed-tools"] = self.allowed_tools
        if self.metadata:
            result["metadata"] = dict(self.metadata)
        return result


@dataclass(frozen=True)
class SkillOverride:
    """A duplicate skill-name collision resolved by precedence."""

    name: str
    winner: DiscoveredSkill
    replaced: tuple[DiscoveredSkill, ...]

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""

        return {
            "name": self.name,
            "winner": self.winner.to_dict(),
            "replaced": [skill.to_dict() for skill in self.replaced],
        }


@dataclass(frozen=True)
class SkillCatalog:
    """A merged skill catalog plus override details."""

    skills: tuple[DiscoveredSkill, ...]
    overrides: tuple[SkillOverride, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""

        result: dict[str, object] = {"skills": [skill.to_dict() for skill in self.skills]}
        if self.overrides:
            result["overrides"] = [override.to_dict() for override in self.overrides]
        return result


@dataclass(frozen=True)
class SkillSearchResult:
    """A ranked search result."""

    skill: DiscoveredSkill
    score: int
    matched_terms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""

        result = self.skill.to_dict()
        result["score"] = self.score
        if self.matched_terms:
            result["matched_terms"] = list(self.matched_terms)
        return result
