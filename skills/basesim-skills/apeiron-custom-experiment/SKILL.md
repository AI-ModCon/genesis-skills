---
name: apeiron-custom-experiment
description: >-
  Run an apeiron continual-learning experiment on the user's own dataset and
  model. Use when bringing custom data and architecture beyond the shipped
  MNIST/CIFAR examples: scaffolds a model harness, data utilities and TOML
  config, registers them in the example factory, smoke-tests, and runs. For the
  bundled demos use apeiron-explore-examples; to add apeiron to an existing
  training loop use integrate-apeiron.
compatibility: >-
  Requires a local clone of the apeiron repository
  (https://github.com/AI-ModCon/BaseSIM_APEIRON), Python 3.13, and Poetry. This
  skill writes files into the checkout.
metadata:
  short-description: Build and run a custom apeiron experiment
  upstream: https://github.com/AI-ModCon/BaseSIM_APEIRON
allowed-tools: Bash Read Write Edit Glob Grep
---

# Build a custom apeiron experiment

Scaffold and run an apeiron experiment on the user's own data and model.

## Inputs

- **Short name**: a lowercase identifier such as `fashionmnist` or `mytabular`.
  Used for the `$APEIRON_ROOT/examples/<name>/` directory and the `data.name`
  factory key.
- **Optional config output path**: defaults to
  `$APEIRON_ROOT/examples/<name>/<name>.toml`.

Ask only for details that cannot be inferred:

- dataset source and how to load it (torchvision, Hugging Face, local files, a
  custom `Dataset`)
- model architecture (CNN, MLP, ViT, …), input shape, number of classes or
  outputs
- the drift to simulate on the stream (affine transforms for images, feature
  noise for tabular); apeiron's examples simulate drift inside
  `update_data_stream()`
- pretrained weights and their path, if any — the harness should tolerate their
  absence
- which drift detector and CL updater to start with, defaulting to
  `ADWINDetector` and `base`

## Locate the apeiron checkout

This skill registers the new experiment in the repository's example factory, so
it writes into a checkout. Resolve it once and reuse it as `APEIRON_ROOT`:

```bash
grep -qm1 'name = "apeiron"' pyproject.toml 2>/dev/null && echo "APEIRON_ROOT=$PWD"
```

If that does not match, ask the user where their checkout is. If they do not
have one, offer to clone it:

```bash
git clone https://github.com/AI-ModCon/BaseSIM_APEIRON.git
```

Every command and path below is relative to `APEIRON_ROOT`. If the user does not
want to edit an apeiron checkout at all, `integrate-apeiron` is the right skill
instead.

## Procedure

### 1. Read the current patterns

Do not hardcode signatures — they rot. Mirror the live source:

```bash
cat "$APEIRON_ROOT/src/apeiron/model/torch_model_harness.py"  # the ABC + abstract methods
cat "$APEIRON_ROOT/examples/mnist/model.py"                   # canonical harness
cat "$APEIRON_ROOT/examples/mnist/utils.py"                   # data loading + drift simulation
cat "$APEIRON_ROOT/examples/utils.py"                         # get_example() factory to extend
grep -nA6 "class .*Cfg" "$APEIRON_ROOT/src/apeiron/config/configuration.py"
```

Implement exactly the `@abstractmethod`s the ABC declares. At the time of
writing that is `get_optmizer` (preserve that spelling if the source still
declares it that way), `update_data_stream`, `get_stream_dataloader`,
`get_hist_dataloaders`, `get_train_dataloaders` and `get_criterion` — but read
the source rather than trusting this list. Set `self.eval_metrics` with at least
an `accuracy` entry from `apeiron.evaluation.metrics` for a classification task.

### 2. Scaffold the files

Create:

- `$APEIRON_ROOT/examples/<name>/__init__.py` — empty.
- `$APEIRON_ROOT/examples/<name>/model.py` — a `BaseModelHarness` subclass that calls
  `super().__init__(cfg=cfg, model=<nn.Module>)`, implements every abstract
  method, applies cumulative drift in `update_data_stream()`, and returns
  `(None, None)` from `get_hist_dataloaders()` on the first task when no history
  exists.
- `$APEIRON_ROOT/examples/<name>/utils.py` — dataset loaders, a deterministic
  drift transform, a `TransformedView` wrapper, and a `make_loader(...)`
  factory, following the MNIST utils structure.
- The config TOML at the requested output path (default
  `$APEIRON_ROOT/examples/<name>/<name>.toml`) with `[model]`, `[data]`
  (`name = "<name>"`), `[train]`, `[drift_detection]`, optional
  `[continual_learning]`, and `[visualization]`. Read an existing config for the
  exact key set.

### 3. Register in the example factory

Add a branch to `get_example()` in `$APEIRON_ROOT/examples/utils.py`, matching
the surrounding factory style exactly:

```python
elif cfg.data.name == "<name>":
    from examples.<name>.model import <HarnessClass>
    return <HarnessClass>(cfg=cfg)
```

### 4. Validate

```bash
python -c "import tomllib; tomllib.load(open('<config_path>','rb')); print('TOML OK')"
cd "$APEIRON_ROOT" && poetry run python -c "from examples.utils import get_example; print('factory OK')"
```

If `pretrained_path` is set, confirm the file exists. Warn if it is missing and
make the harness tolerate training from scratch where possible.

### 5. Smoke-test before the full run

Run a tiny, fast pass to catch wiring errors cheaply:

```bash
cd "$APEIRON_ROOT" && poetry run python -m src.main --config <config_path> \
  --set train.max_iter=2 \
  --set drift_detection.max_stream_updates=2 \
  --set drift_detection.detection_interval=1 \
  --set device=cpu \
  --set logging.backend=none
```

If it fails, read the traceback, fix the harness or config, and re-run the smoke
test. Do not proceed until it completes cleanly, and confirm with the user
before starting the real run.

### 6. Full run and report

```bash
cd "$APEIRON_ROOT" && poetry run python -m src.main --config <config_path>
```

Report the drift events, final accuracy, and the output CSV path (the config's
`visualization.input`). The package emits this CSV for inspection; it does not
ship a built-in dashboard renderer.

The CSV also carries `eval/fwt` and `eval/bwt` per drift event — the gain
adapting made on the triggering window, and how far past tasks moved since they
were learned. Both come free from `BaseModelHarness`, so a custom harness gets
them without extra work. The sign follows the metric's direction, so for a
lower-is-better metric a positive `bwt` means forgetting. See
`$APEIRON_ROOT/docs/tracking.md` "Transfer Metrics".

## Notes

- This skill uses the in-repo example factory pattern. To drive apeiron from the
  user's *own* project without editing an apeiron checkout, use
  `integrate-apeiron`.
- To pick and tune the detector first, use `apeiron-choose-detector`.
- This skill is vendored from the apeiron project; see the bundle's
  `ATTRIBUTION.md` for where it is developed.
