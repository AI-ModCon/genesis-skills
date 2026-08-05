"""Catalog discovery and search helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path

from .errors import SkillSearchError
from .frontmatter import find_skill_md, parse_frontmatter, read_properties
from .models import DiscoveredSkill, SkillCatalog, SkillOverride, SkillSearchResult

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
_SKILLS_DIR_NAME = "skills"
SkipHandler = Callable[[Path, BaseException], None]
_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "please",
    "the",
    "this",
    "to",
    "use",
    "using",
    "with",
}


def _normalize_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def _normalize_paths(paths: Sequence[str | Path] | str | Path) -> list[Path]:
    if isinstance(paths, (str, Path)):
        return [_normalize_path(paths)]
    return [_normalize_path(path) for path in paths]


def _tokenize(text: str) -> set[str]:
    normalized = text.casefold().replace("-", " ")
    return {
        token
        for token in _TOKEN_RE.findall(normalized)
        if len(token) > 1 and token not in _STOPWORDS
    }


def _find_skill_dirs_in(root: Path) -> list[Path]:
    """Recursively collect all skill directories under *root*.

    Recurse into subdirectories that lack a SKILL.md (collection dirs).
    Stop recursing into a directory once a SKILL.md is found — skill-internal
    subdirs (scripts/, references/, assets/) are never traversed as skills.
    """
    results: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if find_skill_md(child) is not None:
            results.append(child.resolve())
        else:
            results.extend(_find_skill_dirs_in(child))
    return results


def _resolve_candidate_skill_dirs(path: Path) -> list[Path]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SkillSearchError(f"Path does not exist: {resolved}")

    if resolved.is_file():
        if resolved.name.lower() != "skill.md":
            raise SkillSearchError(f"Expected a skill directory or SKILL.md file: {resolved}")
        return [resolved.parent.resolve()]

    if find_skill_md(resolved) is not None:
        return [resolved]

    scan_root = resolved / _SKILLS_DIR_NAME if (resolved / _SKILLS_DIR_NAME).is_dir() else resolved
    return _find_skill_dirs_in(scan_root)


def _iter_resolved_skill_dirs(
    paths: Sequence[str | Path] | str | Path,
) -> Iterator[tuple[Path, Path]]:
    seen: set[Path] = set()
    for input_path in _normalize_paths(paths):
        source_root = input_path.expanduser().resolve()
        for skill_dir in _resolve_candidate_skill_dirs(source_root):
            if skill_dir in seen:
                continue
            seen.add(skill_dir)
            yield source_root, skill_dir


def _discover_skill(skill_dir: Path, *, source_root: Path | None = None) -> DiscoveredSkill:
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        raise SkillSearchError(f"SKILL.md not found in {skill_dir}")

    properties = read_properties(skill_dir)
    return DiscoveredSkill.from_properties(
        properties=properties,
        path=skill_dir.resolve(),
        skill_md_path=skill_md.resolve(),
        source_root=source_root.resolve() if source_root is not None else None,
    )


def _discover_or_skip(
    skill_dir: Path,
    *,
    source_root: Path | None = None,
    on_skip: SkipHandler | None = None,
) -> DiscoveredSkill | None:
    """Discover one skill, optionally reporting recoverable per-entry failures."""

    try:
        return _discover_skill(skill_dir, source_root=source_root)
    except (SkillSearchError, OSError, UnicodeError) as exc:
        if on_skip is None:
            raise
        on_skip(skill_dir.resolve(), exc)
        return None


def discover_skill_dirs(paths: Sequence[str | Path] | str | Path) -> list[Path]:
    """Resolve one or more inputs into concrete skill directories."""

    return [skill_dir for _, skill_dir in _iter_resolved_skill_dirs(paths)]


def merge_skills(skills: Iterable[DiscoveredSkill]) -> SkillCatalog:
    """Merge discovered skills by name, keeping later roots as winners."""

    merged_skills: list[DiscoveredSkill] = []
    index_by_name: dict[str, int] = {}
    replaced_by_name: dict[str, list[DiscoveredSkill]] = {}

    for skill in skills:
        existing_index = index_by_name.get(skill.name)
        if existing_index is None:
            index_by_name[skill.name] = len(merged_skills)
            merged_skills.append(skill)
            continue

        replaced_by_name.setdefault(skill.name, []).append(merged_skills[existing_index])
        merged_skills[existing_index] = skill

    overrides = tuple(
        SkillOverride(
            name=name,
            winner=merged_skills[index_by_name[name]],
            replaced=tuple(replaced),
        )
        for name, replaced in replaced_by_name.items()
    )
    return SkillCatalog(skills=tuple(merged_skills), overrides=overrides)


def inspect_catalog(
    paths: Sequence[str | Path] | str | Path,
    *,
    on_skip: SkipHandler | None = None,
) -> SkillCatalog:
    """Inspect a merged catalog from one or more configured roots."""

    discovered: list[DiscoveredSkill] = []
    for source_root, skill_dir in _iter_resolved_skill_dirs(paths):
        skill = _discover_or_skip(
            skill_dir,
            source_root=source_root,
            on_skip=on_skip,
        )
        if skill is not None:
            discovered.append(skill)
    return merge_skills(discovered)


def discover_skills(
    paths: Sequence[str | Path] | str | Path,
    *,
    on_skip: SkipHandler | None = None,
) -> list[DiscoveredSkill]:
    """Discover skills from one or more configured roots."""

    return list(inspect_catalog(paths, on_skip=on_skip).skills)


def _validate_rank_inputs(top_k: int | None, min_score: int) -> None:
    if top_k is not None and top_k < 1:
        raise ValueError("top_k must be at least 1 when provided")
    if min_score < 0:
        raise ValueError("min_score must be at least 0")


def _prepare_query(query: str) -> tuple[set[str], str]:
    return _tokenize(query), query.casefold().strip()


def _score_skill(
    *,
    query_tokens: set[str],
    normalized_query: str,
    skill: DiscoveredSkill,
    min_score: int,
) -> SkillSearchResult | None:
    name_tokens = _tokenize(skill.name)
    description_tokens = _tokenize(skill.description)
    matched_name = query_tokens.intersection(name_tokens)
    matched_description = query_tokens.intersection(description_tokens)
    matched_terms = tuple(sorted(matched_name.union(matched_description)))

    score = (2 * len(matched_name)) + len(matched_description)
    if normalized_query:
        if normalized_query == skill.name.casefold():
            score += 6
        elif normalized_query in skill.name.casefold():
            score += 4
        elif normalized_query in skill.description.casefold():
            score += 2

    if score < min_score:
        return None

    return SkillSearchResult(skill=skill, score=score, matched_terms=matched_terms)


def rank_skills(
    query: str,
    skills: Sequence[DiscoveredSkill],
    top_k: int | None = None,
    min_score: int = 1,
) -> list[SkillSearchResult]:
    """Rank skills using deterministic keyword overlap."""

    _validate_rank_inputs(top_k, min_score)
    query_tokens, normalized_query = _prepare_query(query)
    if not query_tokens and not normalized_query:
        return []

    ranked = [
        result
        for skill in skills
        if (
            result := _score_skill(
                query_tokens=query_tokens,
                normalized_query=normalized_query,
                skill=skill,
                min_score=min_score,
            )
        )
        is not None
    ]
    ranked.sort(key=lambda result: (-result.score, result.skill.name))
    return ranked[:top_k] if top_k is not None else ranked


def search_skills(
    paths: Sequence[str | Path] | str | Path,
    query: str,
    top_k: int | None = 5,
    min_score: int = 1,
    *,
    on_skip: SkipHandler | None = None,
) -> list[SkillSearchResult]:
    """Search a merged catalog without materializing the full prompt block."""

    _validate_rank_inputs(top_k, min_score)
    query_tokens, normalized_query = _prepare_query(query)
    if not query_tokens and not normalized_query:
        return []

    ranked: list[SkillSearchResult] = []
    seen_names: set[str] = set()

    # Iterate in reverse so that later roots (user overrides) are encountered
    # first.  When a name repeats, the earlier (central) duplicate is skipped
    # via ``seen_names``, producing the same winner as ``merge_skills`` which
    # processes forward and lets the last occurrence replace earlier ones.
    for source_root, skill_dir in reversed(list(_iter_resolved_skill_dirs(paths))):
        skill = _discover_or_skip(
            skill_dir,
            source_root=source_root,
            on_skip=on_skip,
        )
        if skill is None:
            continue
        if skill.name in seen_names:
            continue
        seen_names.add(skill.name)

        result = _score_skill(
            query_tokens=query_tokens,
            normalized_query=normalized_query,
            skill=skill,
            min_score=min_score,
        )
        if result is not None:
            ranked.append(result)

    ranked.sort(key=lambda result: (-result.score, result.skill.name))
    return ranked[:top_k] if top_k is not None else ranked


def load_skill_body(skill: DiscoveredSkill | str | Path) -> str:
    """Load the markdown body for a discovered skill."""

    if isinstance(skill, DiscoveredSkill):
        skill_md_path = skill.skill_md_path
    else:
        path = _normalize_path(skill).expanduser().resolve()
        if path.is_file():
            if path.name.lower() != "skill.md":
                raise SkillSearchError(f"Expected SKILL.md file, got: {path}")
            skill_md_path = path
        else:
            skill_md_path = find_skill_md(path)
            if skill_md_path is None:
                raise SkillSearchError(f"SKILL.md not found in {path}")

    content = skill_md_path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)
    return body
