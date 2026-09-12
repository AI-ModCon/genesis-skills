---
name: coding
description: Rules and procedures for writing, changing, and removing code in a repository that keeps a design document, a development plan, and a decision log. Load before writing a new module or function, fixing a bug, recommending a refactor or migration, removing code, adding a safeguard, or committing. Also load when reviewing code for house style. Covers simplicity, encapsulation, failure handling, structure, readability, verification, and the commit procedure.
metadata:
  author: Aaron Tuor (PNNL), ModCon Base Data
  version: "1.0"
---

# Coding

The rules first, then the procedure for each kind of change. The reference files in `references/` show the house style; read the one nearest the work before writing:

- `references/store.py`: a Python module with a class structure. Module docstring with a class map, an abstract base with one implementation, a classmethod factory, a lazy import with its reason, an `ImportError` naming the extra, validation in the constructor.
- `references/ranking_service.py`: a Python service module. Module docstring with a module map, one write function named for its side effect, pure factor functions, explicit named arguments, out-of-contract input raising.
- `references/menu.jsx`: a JavaScript component file. A hook owning state and a component owning the box, a comment per export stating what it does, one CSS class per component.

Prose in docstrings, comments, and commit messages follows the `write-like-aaron` skill. Where a fact is recorded is in the `documentation` skill.

## Rules

### Simplicity

- Write the simplest code that satisfies the stated requirement.
- Add an abstraction only when it removes real, repeated, stable duplication. An abstraction that makes the code harder to hold in your head is a net loss, even if it deduplicates.
- Do not build extension points, flags, base classes, or generic utilities for requirements that do not exist yet. Model real variation structurally, as a distinct type, not with a runtime toggle nothing flips. Do not extract a base class until a second implementation forces the seam.
- A small amount of duplication is preferable to an abstraction that obscures intent.
- Prefer concrete domain-specific functions to generic helpers. No deep inheritance, no manager-of-managers.
- Pre-1.0 code gets clean removal, not compatibility shims. Drop a defunct field by not reading it. Do not add back-compatibility sections or migration caveats unless asked. Aim for net-minus lines.
- In a refactor or migration, ask of each choice whether it exists only because the current code already works that way. Adopt the replacement over pin-and-patch. Conform the consumer to a shared contract rather than extending the contract to fit the consumer.
- Size a safeguard to who will operate it. If the manual step will be performed by nobody, propose the automatic policy with a stated tiebreak and keep the manual path as audit only.

### Encapsulation and state

- Simplicity prohibits speculative abstraction. It does not prohibit structure.
- Where the domain has a real invariant, a state machine, or interchangeable implementations, formalize it with standard OOP: a common interface called unconditionally rather than probed with `hasattr`, a type whose constructor validates so every construction path is checked, and transitions defined in one place rather than distributed across their call sites.
- Validate at the system boundary so code inside can assume its inputs are valid.
- The condition is that the thing exists today. If you cannot name the invariant, the states, or the second implementation, do not build the structure.
- Variants go in a registry, not in conditionals. Adding a variant is adding an entry.
- Each domain write has one home: a service function called by every transport (route, tool, CLI). Nothing else performs that write.
- Derived state is recomputed by a pure function from inputs and stored preferences. Never overwrite a stored preference from a transient condition, so removing the condition restores the preference.

### Failure

- Fail with a clear error rather than guessing. A chain of fallbacks means the design is not understood.
- No defensive swallowing. A guard that silently absorbs empty or invalid input (`if not items: return []`) converts a caller's bug into a silent success. Out-of-contract input raises with a message naming what was wrong. Translating a real, reachable exception into an actionable message is welcome; swallowing is not.
- A fallback path exists only with a stated reason, and there are at most one or two.
- Catch an exception only where it can be handled. Handle it, or attach context and re-raise with `raise ... from err`. Never `except Exception: pass`.
- Do not wrap whole functions in try/except. Wrap the specific operation that can fail.
- Let exceptions propagate to a defined boundary: the top-level handler or the API edge. Distinguish a clean user-facing error (`ValueError`, or an `{"error": msg}` response) from an unexpected exception, which is a logged bug.
- A missing optional dependency raises `ImportError` naming the extra that provides it.

### Structure

- A function has clear inputs and outputs. Keep helpers free of I/O and global state.
- A function that has a side effect says so in its name: `save_user`, `send_email`, `log_event`.
- Explicit named arguments. No `**kwargs` splat threaded through layers; unpack a config dict at the boundary. A coherent group of settings that crosses two boundaries is a dataclass.
- Put behavior where it belongs. A factory is a classmethod on the class it builds. A trivial getter is an attribute. A pure stateless algorithm shared by several classes is a module-level function.
- A module does one thing. No god objects, no utility module that knows about everything. A file is due for a split when a second concern moves in, not when it reaches a line count.
- Group related code. Do not scatter one behavior across files, and do not add dependencies that tie unrelated parts of the codebase together.
- Import hygiene. A module on a frequently invoked path does not import a heavy dependency for an annotation-only hint; use `from __future__ import annotations` and a `TYPE_CHECKING` guard. Lazy-import a heavy leaf at its single use site, with the reason stated at the import.
- A gap exposed in a shared package is fixed in the package with its own tests and commit, never worked around in the consumer.

### Readability

- Code is read more often than it is written. Choose the obvious version.
- Optimize only what profiling shows to be slow.
- Use full words in names. Concise domain names. If the clever version needs a comment to explain it, write the obvious version instead.
- Prefer an explicit loop to a dense one-liner.
- Comment where intent is not recoverable from the code.
- Follow the existing conventions of the repository.

### Verification

- Test critical and non-obvious logic. Test behavior, not implementation.
- A feature is done end-to-end or it is not done. Write it, delete what it replaces (no dead branches, orphaned imports or CSS, stale tests, unused dependencies), update the docs and tests it touches, run the suites green, and verify the change in the running application. Sweep the repository for references to anything removed before committing. Do not end a turn with steps left for later.
- When fixing a bug, add a regression test verified to fail without the fix.
- A convention that matters is enforced by a test that fails the build, not by review: a checked-in declaration with a drift test, a snapshot of a served surface, a scan that refuses a hand-rolled copy of a shared primitive.
- Validate inputs at boundaries and fail with a message that says what was wrong.
- Log at boundaries, with messages that would help someone debugging. Anything else is noise.

### Commits and git

- Commit message: imperative or a declarative statement of what now holds, literal, with the reason in the body. Record real behavior changes; a pure rename or comment edit is noise in the log.
- One commit per concern. Stage by explicit pathspec. Run `git diff --cached --stat` before every commit and commit only what this effort touched; another session or the owner may share the index.
- Never stash, reset, or force-push to repair a push. Treat a non-fast-forward as another session's work: fetch and continue, or surface it.
- Work on a branch; `main` holds reviewed work. A pull request carries one concern. Small, focused pull requests receive full review; a monolithic refactor receives a cursory one. Code an agent wrote gets a human review before it merges.

## Before any change

1. Read the repository `CLAUDE.md`: its document map, commands, glossary, invariants, and exceptions.
2. Do not read `history/` for present state. It holds past decisions and parked files.
3. Check `git status --short`. Files another session or the owner has modified are off-limits. Do not stash.
4. Find the existing home for the behavior before adding one: the service module for a domain write, the registry for a variant, the shared package for a UI primitive.

## New module

1. Name it with a concise domain word. The import path says what it needs: a subpackage named after an optional extra imports that extra's dependency, and nothing outside the subpackage does.
2. Write the module docstring first, per the `documentation` skill: title line, three to five sentences, class map if there is a class structure.
3. Module scope imports nothing heavy. A heavy leaf is imported at its single use site with the reason in a comment at the import. Annotation-only imports go under `TYPE_CHECKING` with `from __future__ import annotations`.
4. A missing optional dependency raises `ImportError` naming the extra: `raise ImportError("the MLflow sink needs mypkg[traces]") from err`.
5. Place behavior: factory as a classmethod on the class it builds, trivial getter as an attribute, shared pure algorithm as a module function.
6. Signatures take explicit named arguments. A config dict is unpacked at the boundary. A group of settings that crosses construction and serialization is a dataclass.

## New function

1. Inputs and outputs are explicit. No I/O or global state in a helper.
2. A side effect is in the name: `save_workspace`, `record_run`, `send_email`.
3. Out-of-contract input raises with a message naming what was wrong. No guard that returns an empty result for empty or invalid input.
4. Wrap only the operation that can fail. Re-raise with `raise ... from err` and context. A user-facing refusal is a `ValueError` or an `{"error": msg}` response per the repository's route convention; anything else propagates to the boundary and is logged there.
5. An assert that can fail carries a message naming the observed value.

## Front-end component

When the project consumes a shared UI package for its shell, primitives, and tokens:

1. A primitive (menu, modal, tab dock, tree, chip, bar) comes from the package. A ratchet test fails the build on a copy. A gap is fixed in the package with its own tests and commit.
2. A container component owns mechanism only: its props are content nodes or a registry, and it holds no domain state and makes no API calls. A domain component owns data and composes containers. Split at that seam before adding to a component that has both.
3. A new view, tab, or tool is an entry in the registry, not a conditional.
4. Layout is a pure function of inputs and stored preferences. A transient condition such as window width never writes a preference.
5. Per-frame work during a gesture writes a CSS variable on the DOM and commits React state once at the end.
6. Styling is plain CSS, one class-name block per component. Inline styles only for computed values.

## Bug fix

1. Reproduce it with a test that fails. Keep the test.
2. Before reading the failure as a code regression, rule out the environment: a full disk, an unseeded random generator in a fixture, a server running old code, a stale cached binary, the wrong `pytest` on the path.
3. Fix at the cause, not at the symptom. A guard at the call site that hides the bad input is the wrong fix.
4. Run the test; it passes. Run the suite for the touched area.
5. Sweep for the same defect elsewhere with `grep`.

## Refactor or migration recommendation

1. For each choice, ask whether it exists only because the current code already works that way. Say so when it does.
2. Prefer adopting the replacement over pinning and patching. Prefer conforming the consumer to a shared contract over extending the contract to fit the consumer. Separate real domain expressiveness from encoding and convention, and converge the latter.
3. Risky work goes last and is labeled committed-but-last, never deferred.
4. No back-compatibility section, no migration caveat, in pre-1.0 code unless asked.
5. End with the shipped-versus-proposed ledger.

## Adding a safeguard

1. Name who performs the manual step and how often.
2. If the answer is nobody, propose the automatic policy with a stated tiebreak, and keep the manual path as audit only.
3. A safeguard that can be a test is a test: a checked-in declaration with a drift test, a snapshot of a served surface, a validator that refuses to start on inconsistency.

## Removing code

1. Committed code is deleted. The commit message says what was removed and why.
2. Uncommitted code that will be lost is copied first to `history/parked/<date>-<reason>/<original path>` with a line in `history/decisions.md`. Never `rm` it.
3. Sweep for references: imports, CSS classes, test names, documentation, dependencies in `pyproject.toml` or `package.json`. Delete the orphans in the same change.
4. No shim, no detect-and-warn, no tolerant parser for a field nothing writes any more. Drop it by not reading it.
5. Never register an agent-facing tool whose handler reaches an unimplemented path. An internal stub or `NotImplementedError` is fine; the boundary is the registered tool.

## Feature done

A feature is done when every item holds. Do not end a turn with items left for later.

- The code is written and what it replaces is deleted: no dead branch, orphaned import, unused CSS, stale test, or unused dependency.
- The docs and tests it touches are updated in the same change, including any checked-in declaration or snapshot.
- The suites are green per the repository `CLAUDE.md`.
- The change is verified in the running application, not only in tests. Restart a server that does not auto-reload before checking.
- The repository has been swept for references to anything removed.
- A settled design question has an entry in `history/decisions.md`.

## Commit

1. `git status --short`, then stage by explicit pathspec. Never `git add -A` or `git add .` in a checkout another session may share.
2. `git diff --cached --stat`. Anything staged that this effort did not touch is unstaged or committed separately with `git commit -- <paths>`.
3. One commit per concern. Message: imperative or a declarative statement of what now holds, literal, the reason in the body. A pure rename or comment edit does not get its own log line.
4. Do not stash. Do not reset or force-push to repair a push. A non-fast-forward is another session's work: fetch, continue, or surface it.
5. Work on a branch. When the repository's loop is commit, push, reload, do those without asking. Ask only about merging to `main`.

## Reporting

End a turn that implemented anything with a ledger:

- Shipped: commit hash and one line each.
- Proposed: marked as not in the repository.
- Left undone: named, with the reason.
