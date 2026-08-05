# MAS Design Guide

Heuristics for the design decisions in Phases 1 and 3 of
[build-process.md](build-process.md): what becomes an agent, how agents relate,
who owns state, and how the system starts and stops.

## Agent vs Plain Function

The most common MAS design error is promoting everything to an agent. An agent
is expensive: it adds messaging, lifecycle, and failure modes. Promote a
component to an agent **only** if at least one of these is true:

| Criterion | Test | Example |
|---|---|---|
| Private state across interactions | Does it remember things between calls that no one else should own? | A player remembers its own past moves |
| Autonomous behavior | Must it act without being called? | A monitor that samples on a timer |
| Independent addressability | Do multiple parties need to call *it*, by identity? | A shared scoreboard service |
| Distribution boundary | Must it run elsewhere (another process, machine, site)? | A simulation on an HPC node |

Everything else is a plain module. The sharpest form of the rule: **the rules
of a game are a library; a player of the game is an agent.** Domain logic —
validation, scoring, physics, parsing — never needs to be an agent, and making
it one just makes it untestable.

## Coordinator Patterns

Most small systems are one of these shapes. (For framework-level pattern code,
see the `academy` skill's orchestration patterns reference.)

- **Hub-and-spoke** — one coordinator holds handles to N workers, sequences
  the work, and owns the session state. Right choice when there is a genuine
  protocol to referee (turns, rounds, phases). Wrong when workers could just
  be called directly — then the hub is ceremony.
- **Pipeline** — each stage holds a handle to the next; data flows one way.
  Right for transform chains. Watch for: the last stage needs a way to deliver
  results (return values up the chain, or a handle back to a sink).
- **Pool** — one dispatcher, N interchangeable workers, work distributed by
  availability. Right for throughput. Requires that workers are truly
  stateless-per-task.
- **Peer-to-peer** — agents hold handles to each other symmetrically. Almost
  always the wrong first design: cyclic dependencies complicate startup,
  shutdown, and reasoning. Prefer a coordinator until proven otherwise.

Default for a first MAS: hub-and-spoke with a single coordinator.

## State Ownership

Every fact in the system has exactly **one** owner; everyone else asks.

- The **coordinator** owns shared session state: whose turn it is, the score,
  the round number, aggregate statistics.
- A **worker** owns its private state: its strategy, its history, its secrets.
  In adversarial or independent-role designs, private state is the point —
  workers must not read each other's state, and the coordinator must not
  reach into theirs.
- **Never mirror state** across agents. A copy that two agents both update is
  a race and a lie; pass the fact in messages instead, or ask the owner.

Write the ownership table in Phase 1: fact → owning agent. If a fact has two
plausible owners, your roles are drawn wrong.

## Request/Response vs Autonomous Loops

Default to plain request/response actions — they are synchronous to reason
about, trivial to test, and compose. Reach for an autonomous loop only when
the behavior is genuinely open-ended: "keep playing rounds", "keep sampling",
"watch for X". Rules for every loop:

- It observes its shutdown signal every iteration (see
  [verification.md](verification.md) pitfalls 3 and 4).
- It yields control every iteration (a sleep, even tiny).
- It does the minimum: a loop that *sequences* work by calling actions is
  good; a loop that *contains* all the logic inline is an untestable monolith.
  Factor the body into a callable method the loop invokes — then tests can
  drive one round deterministically without the loop.

## Startup and Shutdown Ordering

Draw the dependency arrow: A → B means "A calls actions on B".

- **Launch against the arrows**: leaves (called, call no one) first; then the
  agents that call them; coordinators last. A coordinator constructed before
  its workers exist has nothing to hold handles to.
- **Health-check before first use**: ping every agent after launch; a dead
  agent found at wiring time is a one-line fix, found mid-protocol it is a
  mystery.
- **Shut down with the arrows**: roots (callers) first, leaves last. Rationale:
  a coordinator mid-call into an already-dead worker throws during teardown —
  the classic "it worked but printed errors at exit" bug. The runtime's own
  cleanup usually handles stragglers, but explicit reverse-order shutdown of
  what you launched is what makes exits clean.

## Design for Testability

- **Abstract the roles.** If a role has any polymorphism (different strategies,
  different backends), define an abstract base class for it in Phase 3. Tests
  then substitute a scripted, deterministic implementation of the same
  interface — the single most valuable testing move in a MAS.
- **In-process doubles.** Test an agent's behavior by wrapping it in the
  framework's in-process test double and awaiting its actions directly — no
  live runtime needed (Academy's is `ProxyHandle`; see the `academy` skill).
  Keep the calling code identical to the live path.
- **Shrink the world.** Agent tests use the smallest problem instance that
  exercises the protocol: the tiny board, two rounds, one worker. Bounded,
  deterministic, fast.
- **Determinism knobs.** Anywhere behavior is random, accept an injectable
  source of randomness or a scripted sequence, so a test can pin it.
