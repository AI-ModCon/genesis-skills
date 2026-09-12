---
name: autodocs
description: Set up or extend a repository's MkDocs documentation site. The configuration, the README shared blocks, a page per public module with the API reference generated from docstrings, the strict CI build, deployment to GitHub Pages, and a generated index for a directory of self-describing folders. Invoke when asked to set up docs, add a docs site, add a module page, or wire a collection into the site. Templates for mkdocs.yml, the docs workflow, and the collection hook are bundled.
compatibility: Python projects using uv; MkDocs Material, mkdocstrings, and the include-markdown plugin; GitHub Actions for the build and Pages deploy.
metadata:
  author: Aaron Tuor (PNNL), ModCon Base Data
  version: "1.0"
---

# autodocs

Sets up the documentation site the `documentation` skill describes. Run once to create the site, and again to add a module page or a collection. This skill's `templates/` (under `${CLAUDE_SKILL_DIR}/templates/`) hold the configuration, the workflow, and the collection hook, with the repository-specific parts marked `CHANGE`.

## Shape of the site

- `docs/index.md` pulls the README's shared blocks. It writes nothing of its own beyond a nav.
- One page per capability or public module. The top is handwritten: what the module backs, how it is used, the reason for a non-obvious implementation choice in a sentence or two, cross-references to other modules. The bottom is the API reference generated from the module's docstrings by `mkdocstrings`. The handwritten part never restates the docstring; the docstring says what a thing does and why, the page says how it is used.
- `docs/developer.md` for build, test, and regeneration commands.
- A generated index and page set for any directory of self-describing folders.
- Nothing from `history/`, `DESIGN.md`, or `DEVELOPMENT.md`, and no link or reference to them. They are absent from the remote.

## Setup

### 1. Dependencies

Add a `docs` dependency group to `pyproject.toml`:

```toml
[dependency-groups]
docs = [
    "mkdocs-material>=9.5",
    "mkdocs-include-markdown-plugin>=6.0",
    "mkdocstrings[python]>=0.26",
]
```

### 2. Configuration

Copy `${CLAUDE_SKILL_DIR}/templates/mkdocs.yml` to the repository root and fill in every value marked `CHANGE`: the site and repository names, the palette, and `nav`. Delete the `hooks:` block when the repository has no collection. The `mkdocstrings` plugin is already configured:

```yaml
plugins:
  - search
  - include-markdown
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: numpy
            members_order: source
            show_root_heading: true
            show_source: false
            filters: ["!^_"]
```

`paths` is `[src]` for a src layout and `[.]` otherwise. `filters` hides private members. The handler reads the source statically, so the docs build does not import the package and the `docs` group needs none of the package's dependencies.

### 3. README shared blocks

Fence each README section the site needs with marker comments and include it from the page:

```
<!-- md-shared:install:start -->
...
<!-- md-shared:install:end -->
```

```
<!-- Shared with README.md. Edit there, not here. -->
{%
   include-markdown "../README.md"
   start="<!-- md-shared:install:start -->"
   end="<!-- md-shared:install:end -->"
%}
```

The README is the one home. Typical blocks: install, quickstart, CLI, project tree.

### 4. Module pages

One page per public module, named for the module:

```markdown
# Knowledge base

The knowledge base backs the `kb_search` and `kb_add` tools. A project has
one, at `<project>/kb/`, and every reader goes through
[KnowledgeBase][mypkg.knowledge.KnowledgeBase]. Documents are split into
1024-character chunks with a 128-character overlap, so a query matches one
chunk and a sentence cut at a boundary still appears whole in its neighbor.
Embeddings come from the gateway's `text-embedding-3-small` alias unless
the project sets `EMBEDDING_MODEL`.

## Usage

    from mypkg.knowledge import KnowledgeBase
    kb = KnowledgeBase.open(project_dir)
    kb.add(path)
    hits = kb.search("thermal model", k=5)

## Reference

::: mypkg.knowledge
```

- The `:::` directive renders the module docstring, then each public member with its signature from the source and its docstring.
- Cross-reference a symbol in prose as `[Name][dotted.path]`. The strict build fails when the path does not resolve, which is the drift test for prose that names code.
- A class map in a module docstring is indented four spaces so it renders as a code block. A map at column zero renders as collapsed paragraphs.
- Types stay in the signature. The handler renders them; a docstring that restates them renders them twice.
- Add the page to `nav`. A new public module gets its page in the same commit.

When the module count outgrows hand-listed pages, switch the reference to a generated tree with `mkdocs-gen-files` and `mkdocs-literate-nav`, and keep the handwritten prose on capability pages. Do not do this for a dozen modules.

### 5. Workflow

Copy `${CLAUDE_SKILL_DIR}/templates/docs.yml` to `.github/workflows/docs.yml`. It runs `mkdocs build --strict` on every push to `main` and every pull request. For a public repository it also runs `mkdocs gh-deploy --force` on push to `main` and publishes a pull-request preview with `rossjrw/pr-preview-action`. For a private repository delete the deploy step and the preview job; the strict build stays.

The `gh-pages` branch is a build product. Never commit to it by hand.

### 6. Collections

A directory of self-describing folders (use cases, examples, walkthroughs) gets a hook. Copy `${CLAUDE_SKILL_DIR}/templates/gen_collection.py` to `hooks/gen_collection.py`, keep it registered under `hooks:` in `mkdocs.yml`, and set the constants at its top: the directory name, the required frontmatter keys, the nav group the pages are appended to, and the index page. Each folder's `README.md` opens with frontmatter:

```yaml
---
title: Two-tank system identification
domain: Process control
summary: One or two sentences for the index table and the page.
status: draft          # omit to publish
order: 10              # optional sort key
---
```

The hook generates the index table, one page per folder, and the nav entries, and rewrites relative links to a site page or a GitHub blob. Nothing under `docs/` restates a folder's README.

### 7. Figures

`docs/assets/` holds each rendered figure beside its editable source, `architecture.png` with `architecture.pptx`.

### 8. Verify

```
uv run mkdocs build --strict
uv run mkdocs serve
```

The build passes with no warnings. Open the served site and check one module page renders its docstring, its class map as a code block, and its members. Commit `mkdocs.yml`, `docs/`, `hooks/`, the workflow, and the `pyproject.toml` change as one commit.

## Adding to an existing site

- New public module: write the page per step 4 and add it to `nav`.
- New shared README block: fence it and include it per step 3.
- New collection: step 6.
- A page that has drifted from the code: the strict build reports a broken cross-reference; fix the reference or the code path, never by removing the link.
