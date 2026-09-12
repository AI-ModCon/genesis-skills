---
name: documentation
description: Which documents a repository has, what each holds, and the anatomy of a docstring, comment, README, repository CLAUDE.md, development plan, and decision-log entry. Load before writing or editing any of those, before deciding where a fact or decision should be recorded, and before setting up a repository's documents. Companion to the coding, cleanup, autodocs, and write-like-aaron skills.
metadata:
  author: Aaron Tuor (PNNL), ModCon Base Data
  version: "1.0"
---

# Documentation

Sentence-level register is in the `write-like-aaron` skill. This skill is structure: which document holds a fact, and the shape of each artifact.

## Rules

- A repository has three documents with one tense each. The design document describes present architecture. The development plan holds open work, each phase with a concrete acceptance check. The decision log in `history/decisions.md` holds past decisions, dated, with the rejected alternative and the reason.
- A docstring opens with a one-line imperative summary. The body leads with behavior, then justifies the design choice and names the rejected alternative when that is the non-obvious part.
- Types stay in the signature, never restated in the docstring. Returns and raises are described as behavior, in prose. Sections only when a function is parameter-dense, and then NumPy-style.
- A major module's docstring is a title line, three to five sentences (what it does, what it backs, the load-bearing decisions), and, when the module has a real class structure, an ASCII class map in one notation (`◇` holds, `◆` owns, `▷` inherits). Refresh the map whenever the structure changes; it is a deliverable of any major refactor.
- A comment explains the reason, the hazard, or the non-obvious constraint, at the point it matters. Never a paraphrase of the line below it. No change narration; git carries the history. No "in the future this could" notes for paths nothing exercises.
- Route docstrings and request-field descriptions served to an agent as tool descriptions follow the same register: a noun phrase for a read, an imperative sentence for a write.
- A README is one sentence stating what the software does, then install, then usage, then a rules list for anything nonobvious.
- A decision settled at a checkpoint is appended to the decision log. Do not relitigate what it records as settled.
- One glossary per project. Issues, commits, comments, and user-facing copy use its words, and each term maps to a code anchor.
- When a change makes a documented statement false, fix the document in the same commit.
- The README, the site, docstrings, and comments never refer to `DESIGN.md`, `DEVELOPMENT.md`, or `history/`. Those are working documents and are absent from the remote and the site, so a pointer to them is a dead link for the reader. Where the reason for an implementation helps a user or a future developer, state it in place, in one or two sentences.
- Code removed from the working tree that git does not already hold is parked under `history/parked/` with a log entry, never deleted.

## Where a fact goes

| Fact | Document |
|---|---|
| What the software does, install, usage, nonobvious rules | `README.md` |
| Project identity, document map, commands, glossary, invariants, exceptions to the shared rules | `CLAUDE.md` |
| Present architecture: components, boundaries, data model, contracts | `DESIGN.md` |
| Open work, in build order, each phase with an acceptance check | `DEVELOPMENT.md` |
| Build, test, regeneration, and interface rules for a contributor | `DEVELOPER.md` |
| A settled decision, its reason, the rejected alternative | `history/decisions.md` |
| Uncommitted code or documents removed from the tree | `history/parked/` |
| Cross-referenced prose pages for a documentation site | `docs/` |
| Why a function exists and how it behaves | its docstring |
| A hazard or non-obvious constraint at one line | a comment at that line |

Each fact has one home. The design document has no decision history, the plan has no ledger of built phases, and the README has no roadmap. A fact that exists in two documents drifts in one of them.

Not every repository needs every document. A library without phases has no `DEVELOPMENT.md`. A repository with one contributor and no site has no `docs/`. Add a document when there is content for it, and delete it when the content is gone.

## Repository CLAUDE.md

A repository `CLAUDE.md` never restates a rule these skills already carry. Its sections, in order:

1. **What this is.** One paragraph: what the software does, who uses it, and the one or two architectural facts every change has to respect.
2. **Documents.** The map above, listing only the documents that exist, one line each.
3. **Commands.** Setup, run, test, lint, build, regenerate. One line each, exact.
4. **Glossary.** The project's defined terms, each with its code anchor. Comments, commits, issues, and user-facing copy use these words and coin no others.
5. **Invariants.** Rules specific to this codebase that a test does not yet enforce. State each as a present-tense fact with its reason. Examples: "Named keys are the wire. Torch objects never cross the boundary." "Every popup dropdown is `useMenu` and `MenuPanel` from `agent-ui`."
6. **Exceptions.** Any shared rule this repository tightens or suspends, with the reason.

Under fifty lines is the target. A settled decision goes to `history/decisions.md`, not here. Phase history goes nowhere; the code and the log carry it.

## Docstring

```python
def decorate_factors(rows, weights):
    """Attach the boost factors to each ranked row.

    Every route that returns ranked rows calls this so the boost math has one
    definition. Weights below the floor are clamped rather than rejected because
    a stale weights file is a routine condition after a model refresh, and the
    caller has no better value to substitute.
    """
```

- First line: one imperative sentence.
- Body: behavior first, then the reason for the design choice, naming the rejected alternative when that is the non-obvious part.
- Types stay in the signature. Returns and raises are described as behavior, in prose.
- Behavior is stated positively. The rejected alternative appears only as the reason for a design choice ("clamped rather than rejected because a stale weights file is routine after a refresh"), never as "does not" or "is not", and never with a failure as the alternative: "rather than raising" documents a swallow.
- Sections only for a parameter-dense function, NumPy-style (`Parameters`, `Returns`, `Raises` with underlines), never Google-style `Args:`.
- The reason is stated in place. Never `see DESIGN.md §4.7`, never a pointer to `DEVELOPMENT.md` or `history/`: those are working documents absent from the remote, so the reader of a docstring cannot follow the pointer. When the design document gives the reason at length, the docstring carries the deciding constraint in one or two sentences.

## Module docstring

For a module with a real structure:

```python
"""Knowledge base: documents, chunks, embeddings, and retrieval.

One KnowledgeBase owns the on-disk store and every reader goes through it,
so a corpus is never open for write from two places. Embedders are
interchangeable behind one interface because the local and API paths differ
only in where the vectors are computed. Retrieval is a pure function over the
store so it can be tested without a model.

    KnowledgeBase ◆── Store
                  ◆── Embedder «abstract»
                        ▷ LocalEmbedder
                        ▷ APIEmbedder
                  ◇── Retriever ──▷ 1..* Chunk
"""
```

- Title line naming the module's subject.
- Three to five sentences: what it does, what it backs, the load-bearing decisions and their reasons.
- A class map when there are classes, in one notation: `◇` holds, `◆` owns, `▷` inherits, `«abstract»`, `1..*` and `*` for multiplicity. A function-heavy module gets a call or phase map instead.
- Refresh the map whenever the structure changes. It is a deliverable of any major refactor.
- A class from another module is written with its module, `records.RunRecorder`.

A JavaScript component file opens with a short banner comment: what it renders or computes, and the one or two design decisions that explain its shape.

## Comment

- Explains the reason, the hazard, or the non-obvious constraint. Never a paraphrase of the line below it.
- Sits at the point it matters: a lazy import is justified at the import, a magic constant where it is used.
- Describes the present. No "previously", "no longer", "instead of the old", "moved from". No "in the future this could".
- States what the code does. "Does not", "is not a", "no X here" describe a rejected alternative or a removed feature as an absence, which is the history rule evaded. Would the sentence exist if the alternative had never come up? If not, delete it. A negative survives only as a guarantee a caller relies on.
- Names an alternative only with its reason. "Rather than X" and "instead of X" are the same evasion when X is the old mechanism or a roadmap item. When X is a failure ("rather than crash", "rather than raising", "returns 0 rather than failing the report") the comment is documenting a swallowed error. The fix is in the code; the comment then goes.
- Does not document a guard that swallows a caller's bug. Remove the guard.

## Agent-facing descriptions

A route docstring and its request model's field descriptions are served verbatim as tool descriptions and schemas. A read is a noun phrase: "The papers in the current view, one page." A write is an imperative sentence: "Move the node above its parent's next sibling." No coined labels; the glossary's words.

## README

1. One sentence stating what the software does.
2. Install.
3. Usage.
4. Rules, as a list, for anything nonobvious.

No feature bullets written as marketing. No roadmap. No history. An interrogative heading becomes a noun phrase: Install, Usage, Rules, not "How do I get started?".

## Development plan

```
## Phase 8: the study tree

Replaces branch, checkpoint, and library with one tree of nodes.

- Node moves validate against the producing node's fields.
- Export from a named node.

Check: a fresh project shows 4,013,046 rows with no action taken; moving an
annotate-dependent filter above its annotate is refused naming the field;
export from a named node round-trips.
```

- Phases are sequential; items within a phase are independent unless stated.
- Every phase ends with a `Check:` line that a person can run or observe. A phase without a check is not planned.
- A finished phase is deleted. The code and the decision log carry it. The plan lists only open work, so its length is the remaining work.
- Vocabulary is the glossary's. A plan that introduces a term adds it to the glossary in the same change.

## history/

```
history/
  README.md        one line: nothing here describes present state
  decisions.md     the decision log, append-only, chronological
  parked/
    2026-07-10-goose-removal/
      agents/goose.py
```

`history/README.md` reads: "Past decisions and parked files. Nothing here describes present state; read the code and the documents above for that."

Tools skip `history/`: the ratchet, the documentation site source, the doc-check script, any scanner over the tree.

### Decision entry

```
## 2026-08-26 Study tree replaces branches and checkpoints

Context: three concepts (branch, checkpoint, library) carried one mechanism, a
versioned set of filters over the corpus.
Decision: one project holds a tree of nodes; a node is a version.
Rejected: keep branches and add a library layer. A second layout system for one
mechanism.
Consequence: PANELS_PLAN.md deleted; medici/study.py is the one write path.
Commits: 574e6ed, 9c76f74
Supersedes: 2026-07-14 Branch and checkpoint model
```

- Heading: date and a noun phrase naming the decision.
- `Context`: what was true that made the question arise. One or two sentences.
- `Decision`: what was chosen, as a present-tense fact.
- `Rejected`: each alternative and the reason it lost.
- `Consequence`: what changed, as files or behavior.
- `Commits`: the hashes.
- `Supersedes`: only when this entry reverses an earlier one, naming it by date and heading.
- No status field. Status is what the code shows.

An entry is appended when a design question is settled at a checkpoint, and by the `cleanup` skill when it migrates a decision out of a design document or a memory. Entries are never edited after the fact; a change of mind is a new entry with `Supersedes`.

### Parked files

- Only what git does not already hold: uncommitted code, and documents that were never checked in. A committed file being deleted is not parked; the log cites the removing commit.
- The original path is preserved under a dated subfolder named for the reason.
- Each parking gets a decision entry whose `Consequence` names the subfolder.
- Nothing is pruned from `parked/` except by the owner's explicit approval of a listed item.

## Documentation site

A repository with users beyond its contributors gets a `docs/` site. The `autodocs` skill sets it up and adds to it. The standing rules:

- A module page is handwritten usage and cross-references on top, and the API reference generated from the module's docstrings below. The two never overlap: the docstring says what a thing does and why, the page says how it is used.
- A class map in a module docstring is indented four spaces so it renders as a code block.
- Prose names a symbol as `[Name][dotted.path]`, so the strict build fails when the symbol moves.
- The README is the source for install, quickstart, and CLI text. The site includes those blocks; it does not restate them.
- A directory of self-describing folders gets a generated index from the folders' README frontmatter, not hand-written pages.
- The site builds with `mkdocs build --strict` on every push and pull request. It deploys to GitHub Pages only when the repository is public. The `gh-pages` branch is a build product.
- The site never holds, links, or names `history/`, `DESIGN.md`, or `DEVELOPMENT.md`. A page that needs the reason for an implementation states it in place.
- A new public module gets its page in the same commit.

## Consistency

- A change that makes a documented statement false fixes the document in the same commit.
- A declaration that both code and documentation depend on (a view grammar, a capability surface, a tab list) is checked in as data with a test that fails when the served version differs.
- Counts, versions, filenames, and commands in prose are the class of statement that drifts. Prefer a link to the file over restating its name in prose, and prefer "the suite" over a test count.
