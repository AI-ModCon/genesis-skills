---
name: apeiron-choose-detector
description: >-
  Pick and tune a drift detector for an apeiron continual-learning run. Use when
  choosing between ADWIN, KSWIN and Page-Hinkley, setting detector thresholds,
  combining detectors into a voting ensemble, or producing a ready-to-use
  [drift_detection] TOML block. Asks about the monitored metric and drift shape,
  recommends a detector, writes the config block, and validates that it loads.
  Does not run an experiment; for that use apeiron-explore-examples.
compatibility: >-
  Requires a local clone of the apeiron repository
  (https://github.com/AI-ModCon/BaseSIM_APEIRON), Python 3.13, and Poetry.
metadata:
  short-description: Recommend and configure an apeiron drift detector
  upstream: https://github.com/AI-ModCon/BaseSIM_APEIRON
allowed-tools: Bash Read Edit Write Grep Glob AskUserQuestion
---

# Choose an apeiron drift detector

Help the user choose a drift detector and produce a validated
`[drift_detection]` config block. The authoritative reference for detector
behavior and every option is `$APEIRON_ROOT/docs/drift_detectors.md`, published
at https://basesim-apeiron.readthedocs.io/. Read it first and stay consistent
with it rather than restating numbers that may change.

## Inputs

- Optional config path: if the user provides one, patch that file's
  `[drift_detection]` section in place. If omitted, emit a standalone block the
  user can paste into their own config.

## Locate the apeiron checkout

This skill reads apeiron's source and docs, so it needs a checkout. Resolve it
once and reuse it as `APEIRON_ROOT`:

```bash
grep -qm1 'name = "apeiron"' pyproject.toml 2>/dev/null && echo "APEIRON_ROOT=$PWD"
```

If that does not match, ask the user where their checkout is. If they do not
have one, offer to clone it:

```bash
git clone https://github.com/AI-ModCon/BaseSIM_APEIRON.git
```

Run the commands below from `APEIRON_ROOT` — `poetry run` and
`python -m src.main` both resolve relative to it:

```bash
cd "$APEIRON_ROOT"
```

## Ground truth to respect (do not recommend around it)

`ContinuousMonitor._check_drift()` calls `detector.update(agg_metric)` with a
single aggregated scalar and no kwargs. Anything that needs more than that
scalar is not drop-in.

Drop-in:

- `ADWINDetector`, `KSWINDetector`, `PageHinkleyDetector` take the scalar
  directly.
- `EnsembleDetector` forwards the scalar to each sub-detector via
  `update(value, **kwargs)`, so it is drop-in **provided every name in
  `ensemble_detectors` is one of the three scalar detectors above**. Naming a
  non-drop-in detector as a sub-detector just moves the failure into the
  ensemble.

**Not** drop-in, and must not be offered as defaults:

- `ModelPerformanceDetector` needs reference data and batch DataFrames that the
  monitor does not pass; `update()` raises `ValueError` unless `set_reference()`
  ran first.
- `EvalDetector` (`ModelEvalDetector`) needs extra `update(...)` kwargs the
  monitor does not send (`modelHarness`, `reference_validation_metrics`,
  `higher_is_better`).

Confirm this is still true before relying on it:

```bash
sed -n '1,100p' "$APEIRON_ROOT/src/apeiron/drift_detection/load_drift_detector.py"
```

If the user specifically wants one of the non-wired detectors, be honest that it
requires extra wiring and point them at the integration notes in the doc.

## Procedure

### 1. Understand the monitored signal

Ask the user (batch these into a single set of questions):

- **Which metric** feeds the detector, and its rough scale? Bounded like
  accuracy or error rate in `[0, 1]`, or unbounded like a loss? This drives
  `metric_index` and threshold scaling.
- **What drift shape** do they expect — abrupt jumps in the mean, gradual or
  slow drift, or a distribution/variance change with little mean movement?
- **Sensitivity vs. false alarms**: react early and tolerate some false alarms,
  or fire only on clear, sustained drift? A strong preference at either extreme,
  or "I expect more than one kind of drift", is the cue to consider an ensemble.
- **Cadence**: roughly how many `update()` calls (that is,
  `detection_interval`-sized checks) happen before they would want a first
  detection, and how many batches per check. This sets warm-up expectations.

Note that the scalar detectors fire on **change in either direction** — they do
not know "good" from "bad". If the user only cares about degradation, say so
plainly; that is what the non-wired `EvalDetector` is for.

### 2. Recommend a detector

Map the answers to a detector:

- distribution / variance / shape change without mean movement → **KSWIN**
- abrupt mean shift, want fast and cheap detection → **PageHinkley**
- gradual, mixed, or "not sure / general default" → **ADWIN**
- more than one drift shape expected, or an explicit sensitivity preference a
  single detector cannot express → **Ensemble** over two or three of the above
  (see the voting rules in step 3)

Prefer a single detector when one clearly fits. The ensemble costs an update on
every sub-detector per check and makes tuning harder to reason about, since each
sub-detector is still driven by its own hyperparameters in the same config
block. Reach for it when the shapes genuinely differ (for example PageHinkley
for abrupt jumps plus KSWIN for variance changes) or when the user wants a
deliberate sensitivity bias they can state as a voting rule.

State the recommendation and the one-line reason. If it is a close call, name
the runner-up and the tradeoff.

### 3. Recommend settings (scale to the metric)

Pull defaults and semantics from `$APEIRON_ROOT/docs/drift_detectors.md`, then
adjust for the metric scale and the sensitivity preference:

- **ADWIN** — `adwin_delta` is the main knob: lower (`~0.001`) means fewer false
  alarms and later detection, higher (`~0.01`) means more sensitive. Keep
  `adwin_minor_threshold` / `adwin_moderate_threshold` at `0.3` / `0.6` unless
  the user wants to steer the CL → fine-tune → retrain regime split.
- **KSWIN** — `kswin_alpha` for sensitivity; size `kswin_window_size` /
  `kswin_stat_size` to how many samples they can retain
  (`stat_size < window_size`).
- **PageHinkley** — the `ph_threshold` scale **depends on the metric**. For a
  bounded metric in `[0,1]` (accuracy or error) the default `50` is very large
  and will rarely fire, so start much smaller (order `1–10`) and tune; for
  larger-magnitude losses, larger thresholds are appropriate. `ph_delta` is the
  slack (minimum change treated as real); `ph_min_instances` is warm-up.
- **Ensemble** — `ensemble_detectors` is the list of sub-detector names. Each is
  built from this same `[drift_detection]` block, so a detector type can appear
  at most once and still needs its own hyperparameters set here. An empty list,
  a nested `"EnsembleDetector"`, or an unknown voting name raises `ValueError` at
  load. `ensemble_voting` sets the bias:
  - `any` (alias `or`) — fires when any sub-detector fires. Most sensitive; use
    when a missed drift costs more than a needless CL dispatch.
  - `majority` (default) — strictly more than half. Balanced, but needs 3+
    detectors to mean anything; with 2 it behaves like `unanimous`.
  - `unanimous` (aliases `all`, `and`) — every detector must fire. Most
    conservative; suppresses small or noisy changes at the cost of latency.

  Note that `drift_score` is the mean of the sub-detector scores and the regime
  is a plurality vote, both independent of the voting rule — so the
  `adwin_minor_threshold` / `adwin_moderate_threshold` regime split gets diluted
  by sub-detectors that report a score of 0.

Set `detection_interval`, `aggregation` (`mean`/`median`/`last`), `metric_index`
and `max_stream_updates` from the cadence answers. Explain any value that
deviates from the documented default.

### 4. Produce the config block

Emit a complete, paste-ready section:

```toml
[drift_detection]
detector_name = "ADWINDetector"
detection_interval = 10
aggregation = "mean"
metric_index = 0
reset_after_learning = false
max_stream_updates = 20

adwin_delta = 0.002
adwin_minor_threshold = 0.3
adwin_moderate_threshold = 0.6
```

For an ensemble, list the sub-detectors and keep each one's hyperparameters in
the same block:

```toml
[drift_detection]
detector_name = "EnsembleDetector"
ensemble_detectors = ["ADWINDetector", "PageHinkleyDetector"]
ensemble_voting = "unanimous"
detection_interval = 10
aggregation = "mean"
metric_index = 0
reset_after_learning = false
max_stream_updates = 20

# Sub-detectors read their usual hyperparameters from this same block
adwin_delta = 0.002
ph_threshold = 30
ph_delta = 0.5
```

If the user gave a config path, patch that file's `[drift_detection]` section.
Keep the keys that do not belong to the chosen detector untouched, or drop the
unused detector-specific keys — whichever matches the existing file style.

### 5. Validate that it loads (no full run)

Build the config and instantiate the detector. This confirms the TOML parses,
the dataclass validates, and the detector name and params are accepted, without
a training run:

```bash
cd "$APEIRON_ROOT" && PYTHONPATH=src poetry run python -c "
from apeiron.config.configuration import build_config
from apeiron.drift_detection.load_drift_detector import load_drift_detector
cfg = build_config(['--config', '<config_path>'])
d = load_drift_detector(cfg)
print('OK:', type(d).__name__)
print(getattr(d, 'voting', ''), [type(s).__name__ for s in getattr(d, 'detectors', [])])
print(cfg.drift_detection)
"
```

`PYTHONPATH=src` is required so `import apeiron` resolves — the package lives
under `src/apeiron` and the import fails without it.

For an ensemble this is worth more than a syntax check: it is where an empty
`ensemble_detectors`, a nested `EnsembleDetector`, an unknown voting name, or an
unknown sub-detector name surfaces as a `ValueError` instead of at run time. The
second print confirms the resolved voting rule and that every sub-detector
built.

For a standalone block with no config file, write it to a temp file first and
validate that. A full `Config` still needs the other required sections
(`[model]`, `[data]`, `[train]`), so if the user has no config yet, validate
against an example TOML with `--set drift_detection.*` overrides instead, or just
confirm the detector loads via `load_drift_detector` with an example config.

Report the outcome plainly: the recommended detector, why, the settings that
differ from defaults, and that the config loaded successfully. To actually
observe detection behavior, hand off to `apeiron-explore-examples` or
`apeiron-custom-experiment`.

## Useful commands

A/B a detector on a shipped example without editing files:

```bash
cd "$APEIRON_ROOT" && poetry run python -m src.main \
  --config "$APEIRON_ROOT/examples/mnist/mnist.toml" \
  --set drift_detection.detector_name=PageHinkleyDetector \
  --set drift_detection.ph_threshold=5
```

`--set` values go through `json.loads`, so a list needs JSON syntax and shell
quoting:

```bash
--set 'drift_detection.ensemble_detectors=["ADWINDetector","KSWINDetector"]'
```

## Notes

- Precedence when sources disagree: the code in
  `$APEIRON_ROOT/src/apeiron/drift_detection/` wins, then
  `$APEIRON_ROOT/docs/drift_detectors.md`, then this skill. Fix whichever is
  stale rather than working around it — this file has been wrong about detector
  wiring before.
- This skill is vendored from the apeiron project; see the bundle's
  `ATTRIBUTION.md` for where it is developed.
