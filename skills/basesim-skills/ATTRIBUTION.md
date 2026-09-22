# Attribution

The skills in this directory were sourced from the **BaseSim Framework
(APEIRON)** project.

**Original repository:** https://github.com/AI-ModCon/BaseSIM_APEIRON

**Authors:**
- Andrew Ayres, Oak Ridge National Laboratory (ORNL)
- Ana Gainaru, Los Alamos National Laboratory (LANL)
- Anna Quach, Idaho National Laboratory (INL)
- Krishnan Raghavan, Argonne National Laboratory (ANL)
- Alvaro Sanchez-Villar, Princeton Plasma Physics Laboratory (PPPL)
- Rafael Zamora-Resendiz, Lawrence Berkeley National Laboratory (LBNL)

These skills were retrieved from the upstream repository at commit `dc6db55`.
They provide agent workflows for apeiron, a PyTorch framework for continual
learning on non-stationary data streams: it monitors a metric over a data
stream, detects concept drift, and dispatches a continual-learning update to
adapt the model. In this catalog they are also covered by the Apache-2.0
LICENSE at `./LICENSE`, which matches the upstream project's license.

The upstream repository maintains two parallel skill trees, `.claude/skills/`
and `.codex/skills/`, hand-synchronised. This catalog keeps a single `SKILL.md`
per skill, because `unpack.sh --harness all` already installs one source tree
into both `.claude/skills` and `.agents/skills`. The vendored content therefore
required adaptation rather than a verbatim copy. Every change is listed here:

- **Merged the two upstream trees.** Each skill here is the `.claude` variant —
  the more current of the two — with the `.codex` variant's structure folded in
  (a title heading, an `## Inputs` section in place of `## Arguments`, and
  `## Useful commands`). At the time of vendoring the `.codex` tree was one
  content commit behind `.claude` (it was missing the `eval/fwt` and `eval/bwt`
  transfer-metric reporting added upstream in `5d756e1`); the merged copy keeps
  the newer `.claude` content.
- **Normalised frontmatter to the Agent Skills specification.** Dropped
  `argument-hint` and `user-invocable`, which are not specification keys;
  `user-invocable: true` is the default behavior, so nothing is lost. Converted
  `allowed-tools` from a YAML list to the specification's space-separated
  string. Carried `metadata.short-description` over from the `.codex` variants
  and added `metadata.upstream`.
- **Renamed three skills** to disambiguate them in a shared catalog, since
  `unpack.sh` flattens every skill into one directory: `choose-detector` →
  `apeiron-choose-detector`, `custom-experiment` → `apeiron-custom-experiment`,
  `explore-examples` → `apeiron-explore-examples`. `install-apeiron` and
  `integrate-apeiron` keep their upstream names. Cross-references between the
  skills were updated to match.
- **Added a "Locate the apeiron checkout" step** to the three skills that need
  the repository. Upstream they run from the repository root and assume it is
  the working directory; here they resolve the checkout explicitly, using the
  `grep -m1 'name = "apeiron"' pyproject.toml` probe that `install-apeiron`
  already used, and offer to clone it. `integrate-apeiron` falls back to reading
  the installed package when no checkout is present.
- **Declared requirements** in `compatibility` frontmatter, since a catalog user
  will not already have the repository.
- **Fixed two dangling references** to skills deleted upstream in `4fb7939`:
  `install-apeiron` pointed at `/run-experiment`, now `apeiron-explore-examples`;
  `apeiron-custom-experiment` carried a note about `new-harness` / `new-config`,
  now removed.
- **Added ReadTheDocs URLs** (https://basesim-apeiron.readthedocs.io/) alongside
  the repository-relative documentation paths, so the guidance degrades
  gracefully without a checkout.

The skills' workflows, recommendations and commands are otherwise as provided.

Skills included:
- `apeiron-choose-detector` — Picks a drift detector (ADWIN, KSWIN,
  Page-Hinkley, or a voting ensemble), tunes its settings for the monitored
  metric, and emits or patches a validated `[drift_detection]` TOML block.
- `apeiron-custom-experiment` — Scaffolds a model harness, data utilities and
  config for the user's own dataset and architecture, registers them in the
  example factory, smoke-tests, and runs the experiment.
- `apeiron-explore-examples` — Runs a bundled example (MNIST/CIFAR) end to end
  to show drift detection and continual learning, and reports drift events,
  accuracy and the metrics CSV.
- `install-apeiron` — Installs apeiron as a path or git dependency in another
  Python project, handling package-manager detection, interpreter verification
  and CPU-vs-CUDA PyTorch wheel selection.
- `integrate-apeiron` — Adds apeiron's drift detection and continual-learning
  adaptation to an existing training loop (PyTorch, Lightning, Hugging Face
  Trainer, Accelerate), writing the lightest adapter that fits and smoke-testing
  it.
