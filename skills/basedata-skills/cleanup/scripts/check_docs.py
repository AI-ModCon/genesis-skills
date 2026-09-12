"""Report documentation that disagrees with the tree.

Checks over a repository, each a class of drift that can be found
mechanically: a path or filename named in prose that is absent from the tree, a
relative Markdown link whose target is missing, change-narration words in
documentation and source comments, negated statements in docstrings and
comments (a rejected design stated as an absence), a comparison whose object is
a failure (a swallowed error documented as a virtue), and any other "rather
than" or "instead of" (an alternative named, listed for judgment). Memory files outside
the repository are checked for missing paths the same way when a memory
directory is given.

Usage: python check_docs.py <repo> [--memory <dir>] [--skip <dir> ...]
``--skip`` adds directories to leave out: vendored trees, exempt scripts.
Exit status is 1 when anything is reported, so the script can gate a cleanup.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build", ".pytest_cache",
    "__pycache__", "history", ".mypy_cache", ".ruff_cache", "site",
}
DOC_SUFFIXES = {".md"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
PATH_SUFFIXES = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".css", ".toml",
    ".yml", ".yaml", ".sh", ".txt", ".sql", ".html",
)
NARRATION = re.compile(
    r"\b(previously|no longer|formerly|will be added|planned|deferred|"
    r"instead of the old|used to|once was|in the future)\b",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"\b(does not|doesn't|is not a|are not|no longer|there is no|there are no|"
    r"not a wrapper|not (?:used|needed|required|supported))\b",
    re.IGNORECASE,
)
# A comparison whose object is a failure is a swallowed error documented as a
# virtue: "returns [] rather than raising". A comparison with any other
# object names an alternative and is listed for the ledger to judge.
SWALLOW = re.compile(
    r"\b(?:rather than|instead of)\s+(?:\w+\s+){0,3}?"
    r"(?:crash\w*|fail\w*|rais\w*|abort\w*|error\w*|drop\w*|404|traceback|throw\w*)",
    re.IGNORECASE,
)
COMPARISON = re.compile(r"\b(rather than|instead of)\b", re.IGNORECASE)
# Working documents absent from the remote. A reader of the README, the site, or a
# docstring cannot follow a pointer to them.
WORKING_DOC = re.compile(r"(?<![\w/])(DESIGN\.md|DEVELOPMENT\.md|history/)")
BACKTICK = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
COMMENT = re.compile(r"(?:#|//)\s*(.*)$")
DOCSTRING = re.compile(r'"""(.*?)"""', re.DOTALL)


def walk(root: Path, suffixes: set[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix in suffixes:
                yield path


def looks_like_path(token: str) -> bool:
    # Home-relative paths and placeholders name nothing in this tree.
    if " " in token or "<" in token or token.startswith(("http", "$", "-", "~")):
        return False
    if "/" in token and not token.startswith("/"):
        return True
    return token.endswith(PATH_SUFFIXES)


def filenames_in_tree(repo: Path) -> set[str]:
    """Every file and directory name under the repository, skipping the
    directories in SKIP_DIRS, so a bare filename in prose is one set lookup."""
    names: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        names.update(dirnames)
        names.update(filenames)
    return names


def exists_in_tree(repo: Path, names: set[str], token: str, relative_to: Path) -> bool:
    token = token.strip("./").split("::")[0].split("#")[0]
    if (repo / token).exists() or (relative_to / token).exists():
        return True
    # A bare filename is accepted if any file in the tree has that name.
    return "/" not in token and token in names


def check_paths(repo: Path, names: set[str], files, report):
    for path in files:
        text = path.read_text(errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for token in BACKTICK.findall(line):
                if looks_like_path(token) and not exists_in_tree(repo, names, token, path.parent):
                    report.append((path, lineno, f"missing path `{token}`"))


def check_links(repo: Path, files, report):
    for path in files:
        text = path.read_text(errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for target in LINK.findall(line):
                if target.startswith(("http", "mailto:")):
                    continue
                if not (path.parent / target).exists() and not (repo / target).exists():
                    report.append((path, lineno, f"broken link {target}"))


def check_narration(files, report):
    for path in files:
        text = path.read_text(errors="replace")
        if path.suffix in DOC_SUFFIXES:
            # Only the README and the site reach a reader; the working documents may name each other.
            delivered = path.name == "README.md" or "docs" in path.parts
            for lineno, line in enumerate(text.splitlines(), 1):
                if NARRATION.search(line):
                    report.append((path, lineno, f"narration: {line.strip()[:80]}"))
                if delivered and WORKING_DOC.search(line):
                    report.append((path, lineno, f"working-doc: {line.strip()[:80]}"))
            continue
        # A test states what must not happen, so tests get the narration check only.
        patterns = [("narration", NARRATION), ("working-doc", WORKING_DOC)]
        if not any(part in ("tests", "test") for part in path.parts):
            patterns += [("swallow", SWALLOW), ("comparison", COMPARISON)]
            patterns.append(("negation", NEGATION))
        lines = text.splitlines()
        for lineno, line in enumerate(lines, 1):
            match = COMMENT.search(line)
            if not match:
                continue
            found = [label for label, pattern in patterns if pattern.search(match.group(1))]
            if "swallow" in found:
                found.remove("comparison")
            for label in found:
                report.append((path, lineno, f"{label}: {match.group(1).strip()[:80]}"))
        for match in DOCSTRING.finditer(text):
            body = match.group(1)
            swallowed = {hit.start() for hit in SWALLOW.finditer(body)}
            for label, pattern in patterns:
                for hit in pattern.finditer(body):
                    if label == "comparison" and any(hit.start() >= s0 and hit.start() < s0 + 12 for s0 in swallowed):
                        continue
                    lineno = text[: match.start() + hit.start()].count("\n") + 1
                    excerpt = body[max(0, hit.start() - 30): hit.end() + 30].strip()
                    report.append((path, lineno, f"{label}: {excerpt!r}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", type=Path)
    parser.add_argument("--memory", type=Path, help="memory directory to check for missing paths")
    parser.add_argument("--skip", action="append", default=[], metavar="DIR",
                        help="directory name to leave out, in addition to the built-in list")
    args = parser.parse_args()
    SKIP_DIRS.update(args.skip)
    repo = args.repo.resolve()
    if not repo.is_dir():
        parser.error(f"{repo} is not a directory")

    report: list[tuple[Path, int, str]] = []
    names = filenames_in_tree(repo)
    docs = list(walk(repo, DOC_SUFFIXES))
    sources = list(walk(repo, SOURCE_SUFFIXES))
    check_paths(repo, names, docs, report)
    check_links(repo, docs, report)
    check_narration(docs + sources, report)
    if args.memory:
        if not args.memory.is_dir():
            parser.error(f"{args.memory} is not a directory")
        check_paths(repo, names, list(args.memory.glob("*.md")), report)

    for path, lineno, message in sorted(report):
        try:
            shown = path.relative_to(repo)
        except ValueError:
            shown = path
        print(f"{shown}:{lineno}: {message}")
    print(f"{len(report)} findings", file=sys.stderr)
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())
