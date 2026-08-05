---
name: multi-agent-systems
description: A disciplined build process for multi-agent systems - turn a written spec into agent roles, action interfaces, handle wiring, a runtime entrypoint, and verified behavior. Use when building or structuring a multi-agent application (MAS) with an agent framework such as Academy, when deciding what should be an agent versus a plain function, when wiring coordinator agents to worker agents, or when a multi-agent build must reliably pass acceptance tests.
---

# Building Multi-Agent Systems

A process scaffold for building multi-agent systems (MAS) that work on the first
run: phased build order, design heuristics, and a verification discipline.

## What This Skill Is (and Is Not)

This skill teaches **how to build** a multi-agent system: the order of work, the
design decisions, and how to prove the result works. It is framework-agnostic.

It does **not** teach framework APIs. For Academy specifics (decorators,
managers, exchanges, handles), use the `academy` skill if installed, otherwise
the official docs at https://docs.academy-agents.org/stable/. When a spec or
prompt you were given conflicts with either skill, the spec wins.

## The Build Sequence

Work through these phases **in order**. Each phase has exit criteria in
[build-process.md](build-process.md) — do not start a phase until the previous
one's criteria pass.

0. **Environment** — create an isolated environment, install *pinned* framework
   versions, and prove the install by importing the framework and printing its
   version. No application code before this works.
1. **Spec capture** — restate the target as a domain model, an agent role
   inventory, an interaction table (who calls what on whom), and acceptance
   criteria. Echo your file plan before writing code.
2. **Pure domain logic** — everything that needs no messaging is a plain
   module. Write it and its unit tests first; get them green with zero
   framework imports.
3. **Agent interfaces** — for each role: the class, its constructor arguments
   (including which handles to other agents it receives), and every action
   signature with a docstring. Bodies stay stubbed. Then freeze the interfaces.
4. **Behavior and wiring** — implement action bodies; autonomous loops last.
   Dependencies are passed in at launch time, never reached through globals.
5. **Runtime entrypoint** — one run script owns runtime construction: start the
   runtime, launch leaf agents, launch coordinators with the leaves' handles,
   health-check every agent, interact, shut down in reverse dependency order.
   Include a bounded non-interactive mode.
6. **Verify** — run the ladder in [verification.md](verification.md): unit
   tests, per-agent tests, then a bounded end-to-end run checked against the
   acceptance criteria.

## Golden Rules

- **Pure logic before agents.** If it doesn't need messages or state-over-time,
  it's a library module, not an agent.
- **Interfaces before bodies.** Freeze names and signatures before implementing;
  interface drift is how multi-file builds go wrong.
- **Handles flow downward at launch.** An agent receives the handles it needs as
  constructor arguments when it is launched.
- **Launch leaves first; shut down roots first.** Workers exist before the
  coordinator that calls them; the coordinator dies before the workers it calls.
- **Every loop has a shutdown story.** An autonomous loop must observe its
  shutdown signal and yield control every iteration.
- **Interactive apps get a non-interactive mode.** A bounded, scriptable run
  mode with a greppable result line is what makes verification possible.
- **Never declare done without a bounded end-to-end run.** Reading the code is
  not verification; a clean exit with expected output is.

## Definition of Done (short form)

Full checklist in [verification.md](verification.md):

1. Environment pinned; framework import + version verified.
2. Domain unit tests green (no framework imports).
3. Per-agent tests green (in-process test doubles).
4. Bounded end-to-end run exits cleanly within a timeout, output matches the
   acceptance criteria, and no tracebacks appear anywhere.
5. Every acceptance criterion reported pass/fail with evidence.

## Additional Resources

- For the detailed phase-by-phase build sequence, see
  [build-process.md](build-process.md)
- For design heuristics (agent vs function, coordinator patterns, state
  ownership, shutdown ordering), see [design-guide.md](design-guide.md)
- For the test pyramid, pitfalls checklist, and debugging ladder, see
  [verification.md](verification.md)
