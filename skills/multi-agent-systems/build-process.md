# The MAS Build Process

Seven phases, in order. Each phase lists Purpose, Steps, Outputs, and **Exit
criteria** — do not proceed to the next phase until the exit criteria pass.
The exit criteria are what make a build reproducible: they force the same
sequence of verified states no matter who (or what) is doing the building.

## Phase 0 — Environment

**Purpose:** eliminate "works on my machine" and API-version drift before any
code exists.

**Steps:**
1. Create an isolated environment (e.g. a `venv`) inside the project directory.
2. Install the agent framework and test dependencies with **pinned versions**
   (exact pins from your spec; otherwise pin at least the minor version).
3. Prove the install: import the framework and print its version.

**Outputs:** an activated environment; a recorded framework version.

**Exit criteria:** the import-and-print-version command runs cleanly. If it
does not, stop and fix the environment — nothing downstream is meaningful.

## Phase 1 — Spec Capture

**Purpose:** convert the request into a checkable plan; surface misreadings in
the first minutes, not the last.

**Steps:**
1. Restate (or write, if not given) four artifacts:
   - **Domain model** — the nouns and rules that exist independent of agents.
   - **Role inventory** — each agent role, one line: name, state it owns, why
     it must be an agent (see [design-guide.md](design-guide.md)).
   - **Interaction table** — one row per call: caller → callee → action →
     payload → response.
   - **Acceptance criteria** — the observable behaviors that define done,
     each machine-checkable.
2. Write the file plan: every file you will create and what it contains.
3. If you were given a spec, echo the file plan and the interface inventory
   back before writing any code, and reconcile any mismatch with the spec.

**Outputs:** domain model, role inventory, interaction table, acceptance
criteria, file plan.

**Exit criteria:** every acceptance criterion is machine-checkable (a command
plus an expected observation), and the file plan names every file.

## Phase 2 — Pure Domain Logic First

**Purpose:** the rules of your domain do not need messaging; test them where
debugging is trivial — in plain code.

**Steps:**
1. Implement everything from the domain model as one or more plain modules
   with **zero framework imports**.
2. Write unit tests for the domain module(s): normal cases, boundary cases,
   and every error contract the spec names (invalid input, out-of-range,
   repeated operations).
3. Run the tests; fix until green.

**Outputs:** domain module(s) + green unit tests.

**Exit criteria:** domain tests pass, and the domain module imports nothing
from the agent framework (check it — grep the imports).

## Phase 3 — Agent Interfaces

**Purpose:** pin the contract between agents before any behavior exists, so
implementation cannot drift file by file.

**Steps:**
1. For each role in the inventory, write the class with:
   - constructor parameters — including every handle to another agent it
     will receive;
   - every remotely-invokable action as a full signature (name, typed
     parameters, return type) with a one-line docstring;
   - bodies stubbed (`...` or a trivial return).
2. If roles share a contract (multiple implementations of the same kind of
   agent), define an abstract base class for the role and subclass it.
3. Cross-check every row of the interaction table against a signature: caller,
   action name, payload, response type must all match.

**Outputs:** one module per role with complete, stubbed interfaces.

**Exit criteria:** **interface freeze** — every interaction-table row maps to
a declared signature. After this point signatures change only by returning to
Phase 1 and revising the spec.

## Phase 4 — Behavior and Wiring

**Purpose:** fill in the bodies without changing the shape of the system.

**Steps:**
1. Implement action bodies for leaf agents (agents that call no one) first,
   then agents that depend on them.
2. Wiring rule: an agent reaches another agent **only** through a handle it
   was given — as a constructor argument at launch, or via an explicit
   registration action. Never through globals or shared modules.
3. Autonomous loops come **last**, after the actions they orchestrate work.
   Every loop must observe its shutdown signal each iteration and yield
   control (sleep, even briefly) so it cannot starve the runtime.
4. Keep blocking work out of agents: no terminal input, no synchronous
   sleeps, no long CPU-bound calls directly inside actions or loops (the
   `academy` skill documents the framework's escape hatch for sync work).

**Outputs:** implemented agents.

**Exit criteria:** every stub is implemented; no agent references another
except through a received handle; every loop both checks shutdown and sleeps.

## Phase 5 — Runtime Entrypoint

**Purpose:** one place owns process lifecycle; startup and shutdown ordering
bugs are the classic MAS failure.

**Steps:**
1. Write a single run script that owns runtime construction (manager/exchange/
   executor choices come from your spec; the `academy` skill has the canonical
   forms).
2. Canonical order inside the script:
   1. start the runtime;
   2. launch leaf agents;
   3. launch coordinators, passing the leaf handles in;
   4. health-check every launched agent (e.g. ping) before first use;
   5. run the interaction (interactive or batch);
   6. shut down in **reverse dependency order** — coordinators before the
      workers they call — then let the runtime clean up.
3. Interactive interfaces (REPLs, prompts) live in this script only — never
   inside an agent.
4. Provide a **bounded non-interactive mode** (a flag such as a run count or
   duration) that exercises the full system, prints a single machine-readable
   result line, and exits 0. This is mandatory: it is how the build gets
   verified.

**Outputs:** the run script with both modes.

**Exit criteria:** the bounded mode runs end-to-end, exits 0 on its own (no
hang, no interrupt needed), and prints the result line.

## Phase 6 — Verify

**Purpose:** evidence, not vibes.

Run the full ladder in [verification.md](verification.md): unit tests →
per-agent tests → bounded end-to-end run → acceptance-criteria report. Fix and
re-run until everything passes. Only then report done.

## Worked Example (shape only)

A monitoring pipeline spec — "sensors publish readings; an analyzer flags
anomalies; a coordinator collects flags and answers status queries" — becomes:

- Phase 1: domain = readings + anomaly rule; roles = Sensor (owns its stream),
  Analyzer (owns thresholds), Coordinator (owns flag history); interactions =
  Coordinator→Sensor `read()`, Coordinator→Analyzer `check(reading)`, client→
  Coordinator `status()`.
- Phase 2: the anomaly rule is a plain function with unit tests — not an agent.
- Phase 3: `Sensor.read() -> Reading`, `Analyzer.check(r: Reading) -> bool`,
  `Coordinator(sensor, analyzer)` with `status() -> Report`; freeze.
- Phase 4: bodies; the Coordinator's polling loop last.
- Phase 5: run script launches Sensor and Analyzer, then Coordinator with both
  handles; `--cycles N` batch mode prints `RESULT flags=<k>` and exits.
- Phase 6: the ladder.
