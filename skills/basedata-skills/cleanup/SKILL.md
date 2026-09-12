---
name: cleanup
description: Bring a repository's documents, memories, and CLAUDE.md back in line with its code. Load when asked to purge stale memories, align documentation with code, condense or retire design documents, migrate decisions into history/, converge a repository CLAUDE.md to the template, or park uncommitted work. Runs a mechanical drift check (missing paths, broken links, change narration, negated statements, swallowed errors documented as virtues), verifies every claim in the documents, and reports a ledger. Every removal is reversible.
compatibility: Claude Code memory directories are read when --memory is given; the repository steps work anywhere. The check script needs Python 3.
metadata:
  author: Aaron Tuor (PNNL), ModCon Base Data
  version: "1.0"
---

# Cleanup

Cleanup converges a repository on the document map in the `documentation` skill: three documents with one tense each, a short `CLAUDE.md`, a decision log, and memories that are still true. Every removal is reversible: tracked content is in git, untracked content is parked, memories are retired. The ledger is the report.

## Scope

- The repository's `CLAUDE.md`, `README.md`, `DESIGN.md`, `DEVELOPMENT.md`, `DEVELOPER.md`, `docs/`, and any design or planning file outside those names.
- The memory directory for the repository: `~/.claude/projects/<path with / replaced by ->/memory/`.
- Docstrings and comments, for change narration only. A register pass over prose is separate work and is listed in the ledger as optional.
- Never `history/parked/`. Pruning it is the one destructive step; it is listed as a candidate and never applied by the agent.

## Procedure

### 1. Preconditions

- `git status --short` is clean, or the dirty files are the owner's and are named as off-limits.
- On a branch, not `main`.
- The repository `CLAUDE.md` is read, and the `documentation` skill for the document map. `history/` is not read for present state; it is read only to avoid writing a duplicate decision entry.

### 2. Mechanical check

Run the bundled script:

```
python ${CLAUDE_SKILL_DIR}/scripts/check_docs.py <repo> [--memory <memory dir>] [--skip <dir> ...]
```

`--skip` leaves out vendored trees and exempt scripts by directory name. It reports:

- Paths and filenames named in Markdown, docstrings, memories, and the repository `CLAUDE.md` that are absent from the tree.
- Relative Markdown links whose target is missing.
- References to `DESIGN.md`, `DEVELOPMENT.md`, or `history/` in docstrings, comments, README, and `docs/`. Those documents are absent from the remote; the reference is replaced by the reason, stated in place.
- Change-narration words ("previously", "no longer", "will be", "planned", "deferred", "formerly", "instead of the old") in docstrings, comments, README, and `docs/`.
- Negated statements ("does not", "is not a", "there is no", "not supported") in docstrings and comments outside tests. Each is a rejected design or a removed feature stated as an absence, and is deleted or rewritten as the positive consequence unless it is a guarantee a caller relies on.
- A comparison whose object is a failure ("rather than raising", "instead of crashing", "rather than 404"). Each marks a swallowed error documented as a virtue. It is a code finding, listed for a coding pass; the comment goes when the code raises.
- Every other "rather than" or "instead of", listed for judgment: it stays when a domain reason follows, and is deleted when the object is the old mechanism, a roadmap item, or nothing.

Every finding goes into the ledger. The script finds the class of drift that is mechanical; it does not find a stale claim written in prose. A path in a sibling repository (an extraction source, a consumer) is reported as missing; check it against that repository and list it under unverifiable if it cannot be checked.

### 3. Verify claims

For each memory file and each document in scope, read every statement that names a command, a flag, a count, a version, a filename, a phase, or a workflow step, and check it against the tree, the lockfile, or `git log`. Classify each as true, false, or unverifiable. Unverifiable means the statement cannot be checked from the repository; it is listed, not deleted.

### 4. Classify memories

| Memory | Action |
|---|---|
| `feedback` type, codified in the repository `CLAUDE.md` or these skills | Retire. The `CLAUDE.md` is authoritative. |
| `feedback` type, not codified | Add the `CLAUDE.md` line, then retire the memory. |
| `project` type recording a decision with a reason | Write a decision entry, then retire. |
| `project` type recording state that is now in the code, a document, or `git log` | Retire. |
| `project` type recording an operational fact still true and not derivable from the repository | Keep. Refresh the date. |
| Any type, verified false | Retire. |
| `reference` type whose target resolves | Keep. |

Retire means move the file to `<memory dir>/retired/` and drop its line from `MEMORY.md`. Only `MEMORY.md` is loaded, so a retired memory is inert, and one `mv` restores it.

### 5. Classify design and planning content

For each section of each design or planning document:

| Content | Action |
|---|---|
| A decision with a reason or a rejected alternative | Decision entry in `history/decisions.md`, dated from the document or `git log`. Delete the section. |
| Description of built mechanism that the code, `DESIGN.md`, or `DEVELOPER.md` already covers | Delete. |
| Description of built mechanism nothing else covers | Move to `DESIGN.md` as present state, rewritten in present tense. |
| A phase whose acceptance check passes | Delete. |
| A phase whose check fails or has never run | Keep in `DEVELOPMENT.md`, with its check. Add a check if it has none. |
| An open question with no decision | Keep in `DEVELOPMENT.md` under open items. |
| A "built versus gap", "current state", or "supersedes" ledger | Delete; the code and the log carry it. |
| A document that was never committed and is now empty of live content | Park under `history/parked/<date>-<reason>/` with a decision entry. A committed one is deleted with the removing commit cited. |

When this is done, one design document describes the present, one plan lists open work, and the log holds the past.

### 6. Converge CLAUDE.md

Rewrite the repository `CLAUDE.md` to the six sections in the `documentation` skill. Every rule that restates a rule these skills carry is deleted. Every dated or narrative passage is a decision entry or is deleted. Every allowed-term list becomes the glossary, with a code anchor per term. Conflicts between the repository's documents on the same fact (two test commands, two counts, two branch policies) are resolved to what the tree shows, and the losing statements are listed in the ledger.

### 7. Apply

In this order:

1. Park files. Verify each copy exists at its target path before touching the original.
2. Write decision entries. Append only; never reorder or edit existing entries.
3. Move passages to their present-state homes.
4. Delete sections and documents; retire memories.
5. Fix false statements.
6. Rewrite `CLAUDE.md`.
7. Run the mechanical check again; it reports nothing.
8. Run the suites. Cleanup changes no code, so a failure means a test depended on a document; fix the test or restore the document, and list which.

### 8. Commit

- Documentation changes in their own commits, separate from any code change. One commit per document or concern: the log, the design document, the plan, `CLAUDE.md`.
- Memories are outside the repository and are not committed.
- Message form per the `coding` skill. The subject states what now holds: "DESIGN.md describes the study tree as built; decisions move to history".
- A coherent unit done is a checkpoint: commit, report it in one line, continue.

### 9. Ledger

Write the ledger to the scratchpad and present it at the end. Sections, in order:

1. **Shipped**: commits, one line each.
2. **Fixed**: each false statement, its file and line, the correction.
3. **Retired**: each memory, by name, with the reason from the table above.
4. **Migrated**: each decision entry written.
5. **Moved**: each passage moved to `DESIGN.md` or `DEVELOPMENT.md`.
6. **Parked**: each file and its target path.
7. **Unverifiable**: statements that could not be checked, for the owner to settle.
8. **Code findings**: each swallow the scan found, with its file and line. Cleanup changes no code; these go to a coding pass under the `coding` skill, and their comments are deleted there.
9. **Optional**: register violations found in prose, offered as a separate pass.
10. **Prune candidates**: items in `history/parked/` older than the current work that nothing references. Listed only; the owner deletes.
11. Anything left undone, with the reason.
