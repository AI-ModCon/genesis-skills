"""MkDocs hook: generate an index table, a page, and a nav entry for each folder in a collection.

A folder is a member of the collection when ``<COLLECTION_DIR>/<name>/README.md`` opens
with YAML frontmatter carrying every key in ``REQUIRED_KEYS``::

    ---
    title: My Use Case
    domain: Field, short descriptor          # one cell in the index table
    summary: One or two sentences shown in the index table and on the page.
    status: published                        # omit, or 'draft' to hide it
    order: 10                                # optional sort key (default 100)
    ---

The README body is the walkthrough and is inlined into the generated page. Its
frontmatter and leading ``# Title`` line are stripped, since the generated page
supplies its own. Every relative link and image is rewritten: to a sibling
folder's generated page when it points at that folder or its README, and to a
GitHub blob or tree URL otherwise, because the built site serves only ``docs/``.

The three repository-specific values are the constants below.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml
from mkdocs.structure.files import File

log = logging.getLogger("mkdocs.hooks.collection")

# Repository-specific values.
COLLECTION_DIR = "use_cases"          # directory of folders, relative to the repository root
NAV_GROUP = "Use Cases"               # nav group in mkdocs.yml that receives one entry per folder
REQUIRED_KEYS = ("title", "domain", "summary")

TABLE_MARKER = "<!-- COLLECTION_TABLE -->"
INDEX_URI = "use-cases/index.md"      # page that receives the index table
PAGE_DIR = "use-cases"                # generated pages go to docs/<PAGE_DIR>/<name>.md

_FENCE_RE = re.compile(r"^(```|~~~)")
_H1_RE = re.compile(r"^#\s")
_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^()\s]+)(\))")

# Populated in on_config, read in on_files and on_page_markdown within the same
# build. Each build runs on_config first.
_members: list[dict] = []


def _parse_frontmatter(text: str) -> dict | None:
    """Return the frontmatter mapping, or None when the text has none. Malformed YAML raises."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    data = yaml.safe_load(parts[1]) or {}
    return data if isinstance(data, dict) else None


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else text


def _strip_leading_h1(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not _H1_RE.match(lines[i]):
        return text  # no leading title line
    i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    return "\n".join(lines[i:])


def _rewrite_link_target(target: str, uc: dict, gh: str, uc_names: set[str]) -> str:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
        return target  # absolute URL, mailto:, or a same-page anchor
    path, sep, fragment = target.partition("#")
    repo_root = uc["dir"].parent.parent
    resolved = (uc["dir"] / path).resolve()
    try:
        rel = resolved.relative_to(repo_root)
    except ValueError:
        return target  # outside the repository
    use_cases_dir = uc["dir"].parent
    if resolved.parent == use_cases_dir and resolved.name in uc_names:
        return f"{resolved.name}.md"  # links at a sibling use case's folder
    if (
        resolved.name == "README.md"
        and resolved.parent.parent == use_cases_dir
        and resolved.parent.name in uc_names
    ):
        return f"{resolved.parent.name}.md"  # links at a sibling's README
    kind = "tree" if resolved.is_dir() else "blob"
    return f"{gh}/{kind}/main/{rel.as_posix()}" + (sep + fragment if sep else "")


def _inline_readme(uc: dict, gh: str, uc_names: set[str]) -> str:
    text = (uc["dir"] / "README.md").read_text(encoding="utf-8")
    text = _strip_leading_h1(_strip_frontmatter(text))
    in_fence = False
    lines = []
    for line in text.splitlines():
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            lines.append(line)
            continue
        if in_fence:
            lines.append(line)
            continue
        line = _LINK_RE.sub(
            lambda m: m[1] + _rewrite_link_target(m[2], uc, gh, uc_names) + m[3],
            line,
        )
        lines.append(line)
    return "\n".join(lines)


def _discover(config) -> list[dict]:
    uc_dir = Path(config.docs_dir).parent / COLLECTION_DIR
    found: list[dict] = []
    if not uc_dir.is_dir():
        return found
    for folder in sorted(p for p in uc_dir.iterdir() if p.is_dir()):
        readme = folder / "README.md"
        if not readme.is_file():
            continue
        fm = _parse_frontmatter(readme.read_text(encoding="utf-8"))
        if not fm:
            continue
        if str(fm.get("status", "published")).lower() == "draft":
            continue
        missing = [k for k in REQUIRED_KEYS if not fm.get(k)]
        if missing:
            log.warning(
                "%s/%s/README.md is missing frontmatter %s and is skipped",
                COLLECTION_DIR,
                folder.name,
                missing,
            )
            continue
        found.append(
            {
                "name": folder.name,
                "title": str(fm["title"]).strip(),
                "domain": str(fm["domain"]).strip(),
                "summary": " ".join(str(fm["summary"]).split()),
                "order": fm.get("order", 100),
                "dir": folder.resolve(),
            }
        )
    found.sort(key=lambda u: (u["order"], u["title"].lower()))
    return found


def on_config(config):
    global _members
    _members = _discover(config)
    log.info("%s: %d published folder(s)", COLLECTION_DIR, len(_members))

    # Append a nav entry per use case under the existing "Use Cases" group.
    for item in config.nav or []:
        if isinstance(item, dict) and isinstance(item.get(NAV_GROUP), list):
            children = item[NAV_GROUP]
            present = {next(iter(c.values())) for c in children if isinstance(c, dict)}
            for uc in _members:
                uri = f"{PAGE_DIR}/{uc['name']}.md"
                if uri not in present:
                    children.append({uc["title"]: uri})
    return config


def _render_page(uc: dict, repo_url: str, uc_names: set[str]) -> str:
    gh = (repo_url or "").rstrip("/")
    out = [f"# {uc['title']}", "", f"**Domain:** {uc['domain']}", ""]
    if gh:
        out += [
            f"**Source:** [`{COLLECTION_DIR}/{uc['name']}/`]"
            f"({gh}/tree/main/{COLLECTION_DIR}/{uc['name']}/)",
            "",
        ]
    out += [uc["summary"], "", _inline_readme(uc, gh, uc_names), ""]
    return "\n".join(out)


def on_files(files, config):
    uc_names = {uc["name"] for uc in _members}
    for uc in _members:
        files.append(
            File.generated(
                config,
                f"{PAGE_DIR}/{uc['name']}.md",
                content=_render_page(uc, config.repo_url, uc_names),
            )
        )
    return files


def _render_table(use_cases: list[dict]) -> str:
    if not use_cases:
        return "_Nothing published._"
    rows = ["| Name | Domain | Summary |", "|------|--------|---------|"]
    for uc in use_cases:
        domain = uc["domain"].replace("|", "\\|")
        summary = uc["summary"].replace("|", "\\|")
        rows.append(f"| [{uc['title']}]({uc['name']}.md) | {domain} | {summary} |")
    return "\n".join(rows)


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != INDEX_URI:
        return markdown
    table = _render_table(_members)
    if TABLE_MARKER in markdown:
        return markdown.replace(TABLE_MARKER, table)
    return f"{markdown}\n\n{table}"
