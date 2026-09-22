---
name: apeiron-explore-examples
description: >-
  Run a bundled apeiron example experiment to see the continual-learning
  framework end to end. Use when the user wants to try apeiron, run a demo
  experiment, watch drift detection and continual learning in action, or pick
  from the shipped MNIST/CIFAR configs. Presents a menu of example configs, runs
  the chosen one, and reports drift events, accuracy and the metrics CSV. For
  the user's own data, use apeiron-custom-experiment.
compatibility: >-
  Requires a local clone of the apeiron repository
  (https://github.com/AI-ModCon/BaseSIM_APEIRON), Python 3.13, and Poetry.
metadata:
  short-description: Run a bundled apeiron example experiment
  upstream: https://github.com/AI-ModCon/BaseSIM_APEIRON
allowed-tools: Bash Read Glob Grep
---

# Run a bundled apeiron example

Run one of apeiron's bundled examples end to end so the user can see the
framework working.

## Inputs

- Optional config path: if the user provides one, skip the menu and run that
  config directly, still applying steps 3–5.
- If no config path is given, discover the available configs and let the user
  choose.

## Locate the apeiron checkout

The bundled examples live in the repository, so this skill needs a checkout.
Resolve it once and reuse it as `APEIRON_ROOT`:

```bash
grep -qm1 'name = "apeiron"' pyproject.toml 2>/dev/null && echo "APEIRON_ROOT=$PWD"
```

If that does not match, ask the user where their checkout is. If they do not
have one, offer to clone it:

```bash
git clone https://github.com/AI-ModCon/BaseSIM_APEIRON.git
```

Run the commands below from `APEIRON_ROOT` — `poetry run` and
`python -m src.main` both resolve relative to it. If Poetry is not set up there
yet, complete the repository's development install (`poetry install`) first.

## Procedure

### 1. Build the menu dynamically

Do not hardcode the list of examples — it rots. Discover the shipped configs and
summarize each from its own contents:

```bash
find "$APEIRON_ROOT/examples" -name "*.toml" -type f | sort
```

For each config, read the key fields to describe it: `data.name`, `model.name`,
`drift_detection.detector_name`, `continual_learning.update_mode`. Present a
numbered menu like:

```text
1) <apeiron>/examples/mnist/mnist.toml — MNIST, ADWIN detector, base updater
2) <apeiron>/examples/cifar/cifar.toml — CIFAR-10, ViT, KSWIN, ewc_online updater
```

Then ask the user which to run.

### 2. Default to MNIST; flag missing pretrained weights for others

- **MNIST is the guaranteed hands-off path** — its pretrained weights
  (`$APEIRON_ROOT/examples/mnist/mnist.pth`) ship with the repository.
  Recommend it for a first run.
- For any non-MNIST choice (for example CIFAR), check the config's
  `pretrained_path` before running:

  ```bash
  ls -la <pretrained_path> 2>/dev/null || echo "MISSING"
  ```

  If the weight file is missing, tell the user plainly: this example needs
  weights that do not ship with the repository, so the run will train from
  scratch (slow) or fail to load them. Let them decide whether to continue or
  switch to MNIST.

### 3. Ask which metrics-logging backend to use

The config default is `wandb`. Before running, ask the user to choose, and pass
it as an override so no file edits are needed:

- **none** — `--set logging.backend=none` (no account or network; best for a
  quick local look, and the default to suggest for a first run)
- **wandb** — `--set logging.backend=wandb` (run `wandb login` first if not
  authenticated)
- **mlflow** — `--set logging.backend=mlflow` (local tracking by default)

### 4. Show the config and run it

Briefly summarize the chosen config — dataset, model, detector, updater, device,
batch size — so the user can confirm. Then run:

```bash
cd "$APEIRON_ROOT" && poetry run python -m src.main \
  --config <config_path> --set logging.backend=<choice>
```

This is a real training and monitoring run and may take a while. Stream the
output; do not silently background it.

### 5. Report results

Summarize from the run output:

- whether drift was detected, and how many times
- final accuracy
- the output CSV path (the config's `visualization.input`)

The package emits this CSV for inspection; it does not ship a built-in dashboard
renderer, so point the user at the CSV for further plotting.

The CSV carries one row per drift event for `eval/fwt` (what adapting gained on
the triggering window) and `eval/bwt` (how far past tasks moved since they were
learned; absent on the first event). They are the quickest read on whether
adaptation is trading history away — worth quoting alongside
`eval/test_curr_acc` and `eval/test_hist_acc`. The sign follows the metric's
direction, so for the accuracy examples a negative `bwt` means forgetting. See
`$APEIRON_ROOT/docs/tracking.md` "Transfer Metrics".

## Useful commands

Quick first run, copy-paste safe:

```bash
cd "$APEIRON_ROOT" && poetry run python -m src.main \
  --config "$APEIRON_ROOT/examples/mnist/mnist.toml" --set logging.backend=none
```

Overrides that demonstrate other capabilities:

```bash
--set drift_detection.detector_name=PageHinkleyDetector
--set continual_learning.update_mode=ewc_online
--set device=cpu
```

## Notes

- To choose and tune a detector before running, use `apeiron-choose-detector`.
- To run on the user's own dataset and model, use `apeiron-custom-experiment`.
- This skill is vendored from the apeiron project; see the bundle's
  `ATTRIBUTION.md` for where it is developed.
