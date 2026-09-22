---
name: integrate-apeiron
description: >-
  Add apeiron's drift detection and continual-learning adaptation to an existing
  training framework. Use when the user already has a training loop — PyTorch,
  Lightning, Hugging Face Trainer, Accelerate — and wants to bolt apeiron on
  rather than adopt its runner. Inspects the repo, recommends the lightest
  integration path, writes the adapter glue, and smoke-tests it. If `import
  apeiron` fails, use install-apeiron first.
compatibility: >-
  Requires apeiron importable in the target project's environment. Reads
  apeiron's source for current API signatures, from a local checkout of
  https://github.com/AI-ModCon/BaseSIM_APEIRON or the installed package.
metadata:
  short-description: Integrate apeiron into an existing training loop
  upstream: https://github.com/AI-ModCon/BaseSIM_APEIRON
allowed-tools: Bash Read Write Edit Glob Grep
---

# Integrate apeiron into an existing training loop

Integrate apeiron into the user's existing training framework with the least
coupling that meets their goal.

## Inputs

- **Target project directory** — the user's own project. Use the path they give,
  otherwise the current working directory.

## Locate apeiron's source

This skill reads apeiron's source so the glue it writes matches the current API
rather than a remembered one. Resolve a source root once and reuse it as
`APEIRON_SRC`:

```bash
# 1. A local checkout (preferred — it also carries main.py and the examples)
grep -qm1 'name = "apeiron"' pyproject.toml 2>/dev/null && echo "APEIRON_ROOT=$PWD"

# 2. Otherwise the installed package
python -c "import apeiron, pathlib; print('APEIRON_SRC=' + str(pathlib.Path(apeiron.__file__).parent))"
```

With a checkout, `APEIRON_ROOT` is that directory and `APEIRON_SRC` is
`$APEIRON_ROOT/src/apeiron`; `$APEIRON_ROOT/src/main.py` and the bundled
examples are then available as wiring references. With only the installed
package, `APEIRON_SRC` is the package directory, `main.py` and the examples are
not present, and `APEIRON_ROOT` is unset — rely on the module sources under
`APEIRON_SRC` and point the user at
https://github.com/AI-ModCon/BaseSIM_APEIRON for the runner reference.

Read these before writing any glue:

```bash
# APEIRON_SRC is the apeiron package directory, so these paths hold for both
# a checkout and an installed package.
cat "$APEIRON_SRC/drift_detection/detectors/base.py"       # DriftSignal / LearningRegime fields
cat "$APEIRON_SRC/drift_detection/load_drift_detector.py"  # building a detector from config
cat "$APEIRON_SRC/model/torch_model_harness.py"            # the harness ABC
grep -nA12 "class ContinuousMonitor" "$APEIRON_SRC/driver/continuous_monitor.py"

# With a checkout, also read the full wiring reference:
cat "$APEIRON_ROOT/src/main.py"
```

## Background: what apeiron exposes

Verify each of these against the source above; do not assume them.

- **Drift detectors are standalone** —
  `detector.update(metric_value: float) -> DriftSignal`, where the signal
  carries `drift_detected`, `regime` (a `LearningRegime`) and `drift_score`.
  This is the lowest-coupling entry point. Build one with
  `from apeiron.drift_detection import ADWINDetector` (or the others).
- **`ContinuousMonitor` drives the full loop** but requires a
  `BaseModelHarness` wrapping the model and data stream, plus a `Config` and a
  detector.
- **CL updaters (EWC / JVP / KFAC) are harness-coupled** — they take a
  `modelHarness`, so using them implies the harness and monitor route.

## Procedure

### 1. Confirm apeiron is importable

From the target project's environment:

```bash
python -c "import apeiron; print('apeiron', apeiron.__file__)" 2>&1
```

If this fails, stop and direct the user to the `install-apeiron` skill, then
resume.

### 2. Discover the user's framework

In the target project, find the training loop and the evaluation signal:

- Detect the stack:
  `grep -rlE "pytorch_lightning|lightning|transformers|Trainer|accelerate" <target>`,
  and look for a manual loop (`loss.backward()`, `optimizer.step()`).
- Locate where a scalar quality metric is available per step or epoch
  (validation accuracy, loss) — this is what a detector consumes.
- Locate the model object and the data iterator; these are needed only if the
  full path is chosen.

Summarize what you found before proposing anything.

### 3. Recommend the lightest path, and confirm

Based on what the user wants out of apeiron:

- **Just detect drift, or trigger their own retrain** → *detectors-only*, with
  no harness. Lowest coupling; recommend this unless they need apeiron's CL
  math.
- **Want apeiron's CL regularizers (EWC/JVP/KFAC) or the full monitor → adapt
  loop** → *harness + `ContinuousMonitor`*.

Present the recommendation with its tradeoffs and get the user's pick before
writing code.

### 4a. Detectors-only adapter (lightest)

Write a small module into the user's repo — for example
`<their_pkg>/apeiron_drift.py` — that:

- constructs a detector once (ADWIN, KSWIN or PageHinkley)
- exposes a hook called from their existing eval step:
  `signal = detector.update(metric)`, then invokes a callback when
  `signal.drift_detected`
- leaves the decision of what to do on drift (log, retrain, reload) to that
  user-provided callback

Wire the hook into their loop with a minimal, clearly-marked edit.

### 4b. Harness + monitor adapter (full)

When CL adaptation is wanted:

- Write a `BaseModelHarness` subclass in their repo wrapping their existing
  model and data loaders, implementing the abstract methods the current ABC
  declares. Read `torch_model_harness.py` for the current set — and, when a
  checkout is available, the bundled harness at
  `$APEIRON_ROOT/examples/mnist/model.py`. Preserve the declared spelling of
  each method, including `get_optmizer` if the source still spells it that way.
- Build a `Config` — via `build_config` from a small TOML, or constructed
  directly — selecting the detector and `continual_learning.update_mode`.
- Construct and run `ContinuousMonitor`, using `$APEIRON_ROOT/src/main.py` as
  the wiring reference.

### 5. Smoke-test the integration

Prove the wiring with a tiny run before handing back:

- **Detectors-only:** a short script feeding a handful of synthetic metric
  values through the hook, asserting a `DriftSignal` comes back and that the
  drift callback fires on an obvious shift.
- **Full path:** run their loop or the monitor for a couple of iterations with
  minimal settings — small `max_iter`, few stream updates, `device=cpu`,
  `logging.backend=none`.

Read failures, fix the glue, and re-run until it completes cleanly.

### 6. Report

Summarize: the detected stack, the chosen path, the files added or edited with
their exact insertion points, how to run the smoke test, and what happens on
drift. Note any assumptions the user should revisit — especially which metric
drives detection, and the detector's sensitivity parameters.

## Notes

- Keep edits to the user's training loop minimal and clearly commented so they
  remain easy to revert.
- Do not hardcode detector, monitor or harness signatures. They are read from
  source in this skill precisely so the glue does not rot.
- To choose and tune the detector, use `apeiron-choose-detector`.
- This skill is vendored from the apeiron project; see the bundle's
  `ATTRIBUTION.md` for where it is developed.
