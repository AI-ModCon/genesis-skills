"""Skill search exceptions."""


class SkillSearchError(Exception):
    """Base exception for skill search operations."""


class ParseError(SkillSearchError):
    """Raised when SKILL.md parsing fails."""


class ValidationError(SkillSearchError):
    """Raised when skill frontmatter is missing required fields."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors if errors is not None else [message]
