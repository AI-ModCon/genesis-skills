"""High-level helpers for full catalog loading and iterative search."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from .catalog import discover_skills, search_skills
from .errors import SkillSearchError
from .prompt import to_prompt

_CENTRAL_ROOT_ENV_VAR = "SKILL_SEARCH_CENTRAL_ROOT"


def _collect_skips():
    """Return a deterministic list plus a callback for skipped catalog entries."""

    skipped: list[dict[str, str]] = []

    def record_skip(path: Path, exc: BaseException) -> None:
        reason = " ".join(str(exc).splitlines())
        skipped.append({"path": str(path), "reason": reason})

    return skipped, record_skip


def _sorted_skips(skipped: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(skipped, key=lambda item: item["path"])


def get_tool_root() -> Path:
    """Return the filesystem root of the deployable skill-search directory."""

    return Path(__file__).resolve().parents[1]


def _normalize_optional_paths(
    value: Sequence[str | Path] | str | Path | None,
) -> list[Path]:
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        return [Path(value).expanduser().resolve()]
    return [Path(item).expanduser().resolve() for item in value]


def resolve_central_root(
    central_root: str | Path | None = None,
    *,
    tool_root: str | Path | None = None,
) -> Path:
    """Resolve the central skills root for local or DOE deployments.

    Resolution order:
    1. Explicit ``central_root`` parameter
    2. ``SKILL_SEARCH_CENTRAL_ROOT`` environment variable
    3. Sibling ``../skills`` directory next to ``tool_root``
    """

    if central_root is not None:
        return Path(central_root).expanduser().resolve()

    env_root = os.environ.get(_CENTRAL_ROOT_ENV_VAR)
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if candidate.exists():
            return candidate

    base_root = Path(tool_root).resolve() if tool_root is not None else get_tool_root()
    sibling_skills = base_root.parent / "skills"
    if sibling_skills.exists():
        return sibling_skills.resolve()

    raise SkillSearchError(
        "Central skills root not found. Provide an explicit central root, set the "
        f"{_CENTRAL_ROOT_ENV_VAR} environment variable, or deploy skill-search next "
        "to a sibling `skills` directory."
    )


def resolve_catalog_roots(
    *,
    central_root: str | Path | None = None,
    my_skills_path: Sequence[str | Path] | str | Path | None = None,
    tool_root: str | Path | None = None,
) -> list[Path]:
    """Resolve central and optional user skill roots into an ordered list."""

    roots = [resolve_central_root(central_root, tool_root=tool_root)]
    roots.extend(_normalize_optional_paths(my_skills_path))
    return roots


def progressive_disclosure_payload(
    *,
    central_root: str | Path | None = None,
    my_skills_path: Sequence[str | Path] | str | Path | None = None,
    tool_root: str | Path | None = None,
) -> dict[str, object]:
    """Build a serializable payload for standard progressive disclosure.

    Returns a compact index of every skill — name, description, and path —
    without loading any SKILL.md bodies.  The caller receives the full menu
    upfront and calls ``load_skill_body()`` for whichever skill it selects.

    Contrast with ``search_payload()``, which accepts a query and returns
    only the top-k keyword matches instead of the full catalog.
    """

    roots = resolve_catalog_roots(
        central_root=central_root,
        my_skills_path=my_skills_path,
        tool_root=tool_root,
    )
    skipped, on_skip = _collect_skips()
    skills = discover_skills(roots, on_skip=on_skip)

    return {
        "mode": "progressive_disclosure",
        "central_root": str(roots[0]),
        "catalog_roots": [str(root) for root in roots],
        "count": len(skills),
        "skills": [skill.to_dict() for skill in skills],
        "skipped": _sorted_skips(skipped),
    }


def load_all_payload(
    *,
    central_root: str | Path | None = None,
    my_skills_path: Sequence[str | Path] | str | Path | None = None,
    tool_root: str | Path | None = None,
    include_prompt: bool = False,
) -> dict[str, object]:
    """Build a serializable full-catalog payload.

    Prefer ``progressive_disclosure_payload()`` for the standard two-phase
    agent pattern (compact index upfront, bodies on demand).  Use this
    function when you also need the ``available_skills_prompt`` XML block
    via ``include_prompt=True``.
    """

    roots = resolve_catalog_roots(
        central_root=central_root,
        my_skills_path=my_skills_path,
        tool_root=tool_root,
    )
    skipped, on_skip = _collect_skips()
    skills = discover_skills(roots, on_skip=on_skip)

    payload: dict[str, object] = {
        "mode": "full",
        "central_root": str(roots[0]),
        "catalog_roots": [str(root) for root in roots],
        "count": len(skills),
        "skills": [skill.to_dict() for skill in skills],
        "skipped": _sorted_skips(skipped),
    }
    if include_prompt:
        payload["available_skills_prompt"] = to_prompt(skills)
    return payload


def search_payload(
    query: str,
    *,
    top_k: int = 5,
    min_score: int = 1,
    central_root: str | Path | None = None,
    my_skills_path: Sequence[str | Path] | str | Path | None = None,
    tool_root: str | Path | None = None,
) -> dict[str, object]:
    """Build a serializable search payload."""

    roots = resolve_catalog_roots(
        central_root=central_root,
        my_skills_path=my_skills_path,
        tool_root=tool_root,
    )
    skipped, on_skip = _collect_skips()
    matches = search_skills(
        roots,
        query=query,
        top_k=top_k,
        min_score=min_score,
        on_skip=on_skip,
    )
    return {
        "mode": "search",
        "query": query,
        "top_k": top_k,
        "min_score": min_score,
        "central_root": str(roots[0]),
        "catalog_roots": [str(root) for root in roots],
        "count": len(matches),
        "matches": [match.to_dict() for match in matches],
        "skipped": _sorted_skips(skipped),
    }


def build_search_callable(
    *,
    central_root: str | Path | None = None,
    my_skills_path: Sequence[str | Path] | str | Path | None = None,
    tool_root: str | Path | None = None,
):
    """Create a reusable plain-Python search callable."""

    def _search(query: str, top_k: int = 5, min_score: int = 1) -> dict[str, object]:
        return search_payload(
            query,
            top_k=top_k,
            min_score=min_score,
            central_root=central_root,
            my_skills_path=my_skills_path,
            tool_root=tool_root,
        )

    return _search
