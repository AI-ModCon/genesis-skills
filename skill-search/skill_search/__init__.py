"""Self-contained skill search helpers."""

from .catalog import (
    discover_skill_dirs,
    discover_skills,
    inspect_catalog,
    load_skill_body,
    merge_skills,
    rank_skills,
    search_skills,
)
from .errors import ParseError, SkillSearchError, ValidationError
from .frontmatter import find_skill_md, parse_frontmatter, read_properties
from .models import (
    DiscoveredSkill,
    SkillCatalog,
    SkillOverride,
    SkillProperties,
    SkillSearchResult,
)
from .prompt import to_prompt
from .tooling import (
    build_search_callable,
    load_all_payload,
    progressive_disclosure_payload,
    resolve_catalog_roots,
    search_payload,
)

__all__ = [
    "SkillSearchError",
    "ParseError",
    "ValidationError",
    "SkillProperties",
    "DiscoveredSkill",
    "SkillCatalog",
    "SkillOverride",
    "SkillSearchResult",
    "find_skill_md",
    "parse_frontmatter",
    "read_properties",
    "to_prompt",
    "discover_skill_dirs",
    "discover_skills",
    "inspect_catalog",
    "merge_skills",
    "rank_skills",
    "search_skills",
    "load_skill_body",
    "resolve_catalog_roots",
    "load_all_payload",
    "progressive_disclosure_payload",
    "search_payload",
    "build_search_callable",
]
