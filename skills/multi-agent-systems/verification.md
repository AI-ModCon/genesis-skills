# Verifying Multi-Agent Systems

How to prove a MAS works: the test pyramid, the non-interactive-mode rule, a
pitfalls checklist, the definition of done, and a debugging ladder.

## The MAS Test Pyramid

Three layers, cheapest first. Each layer catches what the layer above would
turn into an expensive, confusing failure.

1. **Pure domain unit tests.** The domain modules (Phase 2) tested as plain
   code, no framework imports. Fast, deterministic, debuggable.
2. **Per-agent behavior tests.** Each agent exercised through an in-process
   test double so its actions run without a live runtime (Academy ships one —
   `ProxyHandle`; see the `academy` skill). Use small, deterministic fixtures:
   scripted counterpart agents, shrunken problem sizes, fixed inputs.
3. **Bounded whole-system smoke run.** The run script's non-interactive mode,
   under a timeout, asserting: exit code 0, the result line appears, and no
   tracebacks in the output.

## The Non-Interactive-Mode Rule

Every interactive MAS application must also have a flagged batch mode that:

- exercises the full system (all agents, real messaging),
- is **bounded** (a count or duration — it cannot run forever),
- prints one **ASCII, greppable result line** in a pinned format,
- exits 0 on its own.

Reason: coding agents and CI systems cannot reliably drive a TTY. Without a
batch mode, "verification" silently degenerates into reading the code and
declaring it plausible. The result line is deliberately ASCII-only so that a
regex can check it on any terminal.

## Pitfalls Checklist

Symptom → check → where the canonical form lives. Run down this list whenever
a build misbehaves — and once, proactively, before declaring done.

1. **TypeError or hang constructing the runtime** → did you configure an
   executor for the manager? An in-process (local) exchange needs an
   in-process executor (thread pool). → canonical form: `academy` skill.
2. **Agents can't hear each other across processes** → a process-pool executor
   paired with an in-process local exchange cannot work; cross-process agents
   need an external exchange. Local demo = local exchange + thread pool.
3. **App never exits / hangs at shutdown** → an autonomous loop that ignores
   its shutdown signal (`while True:` with no check). Every loop's condition
   must observe the shutdown event. → `academy` skill for the exact signature.
4. **Loop pegs a CPU core** → a loop that never sleeps. Every iteration must
   yield control, even for a fraction of a second.
5. **Got a coroutine/future instead of a value, or double-await errors** → a
   handle action call is awaited **exactly once** and returns the result
   directly (current Academy semantics; older examples online double-await).
6. **Action never callable / framework rejects the class** → remotely-invokable
   actions must be `async def` methods with the framework's action decorator.
7. **Crash or deadlock during startup** → inter-agent communication in
   `__init__`. Constructors only store what they are given; first contact with
   other agents happens in the startup hook (`agent_on_startup` in Academy).
8. **Coordinator launched before its workers** → it has no handles to receive.
   Launch order follows the dependency DAG: leaves first.
9. **Errors spray at exit** → shutdown in launch order instead of reverse. The
   coordinator must stop calling before the workers it calls go away: shut
   down roots first, leaves last.
10. **REPL or prompt freezes the system** → blocking calls (`input()`,
    synchronous sleeps) inside an agent's actions or loops. Interactive I/O
    belongs in the run script; agents must never block their event loop.
11. **Tests pass with the double but the live system fails** → the test double
    was treated differently from a real handle (e.g. not awaited). Write agent
    tests so the calling code is identical either way.
12. **Worked yesterday, fails today** → unpinned framework install. Pin the
    version (Phase 0) and record it.

## Definition of Done

In order — a later item is meaningless while an earlier one fails:

1. Environment pinned; framework imported and version printed.
2. Domain unit tests green; domain modules contain no framework imports.
3. Per-agent tests green.
4. Bounded end-to-end run: exits 0 by itself, within a stated timeout.
5. The result line appears and matches its pinned format.
6. No `Traceback` anywhere in any output (tests, batch run, logs).
7. The process actually terminated — no orphaned hang you interrupted.
8. Every acceptance criterion from Phase 1 checked against **actual observed
   output** and reported pass/fail, with the evidence (the command run and the
   line of output that satisfies it).

Do not report success before item 8. "The code looks right" is not a state in
this list.

## Debugging Ladder

| Symptom | Most likely cause | Check |
|---|---|---|
| TypeError constructing the manager/runtime | Missing or wrong executor argument | Runtime construction against the `academy` skill's canonical form |
| Hang at exit | A loop not polling its shutdown event | Every loop's `while` condition |
| Hang at startup | Comms in `__init__`, or two agents calling each other during startup | Move first contact to the startup hook |
| AttributeError on a handle | Action name typo, or method not declared as an action, or not `async` | The interface freeze list vs the call site |
| Coroutine object where a value was expected | Missing `await` on a handle call | Exactly one `await` per action call |
| Works via test double, fails live | Calling-convention mismatch between double and handle | Identical call syntax in both paths |
| Result line never printed | Batch mode waits on a condition that can't be reached (e.g. polls state no one updates) | Does the autonomous producer actually run? Is the bound reachable? |
| Random failures across runs | Hidden shared state or unpinned versions | State-ownership table; `pip freeze` |
