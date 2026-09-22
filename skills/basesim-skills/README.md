# BaseSim Skills

Agent skills for **apeiron**, the BaseSim Framework (SIM: Self Improving Model) —
a PyTorch framework for continual learning on non-stationary data streams. It
monitors a metric over a stream, detects concept drift with a configurable
detector, and dispatches a continual-learning update to adapt the model before
resuming. The `skills/basesim-skills/` subtree is licensed Apache-2.0; see
[`LICENSE`](LICENSE). All five skills are sourced from the upstream project; see
[`ATTRIBUTION.md`](ATTRIBUTION.md).

## Skills

| Skill | Description |
|-------|-------------|
| [`apeiron-choose-detector`](apeiron-choose-detector/) | Picks a drift detector (ADWIN, KSWIN, Page-Hinkley, or a voting ensemble), tunes it for the monitored metric, and emits or patches a validated `[drift_detection]` TOML block. |
| [`apeiron-explore-examples`](apeiron-explore-examples/) | Runs a bundled MNIST/CIFAR example end to end to show drift detection and continual learning, then reports drift events, accuracy and the metrics CSV. |
| [`apeiron-custom-experiment`](apeiron-custom-experiment/) | Scaffolds a harness, data utilities and config for the user's own dataset and model, registers them in the example factory, smoke-tests, and runs. |
| [`install-apeiron`](install-apeiron/) | Installs apeiron as a path or git dependency in another Python project, handling manager detection, interpreter checks and CPU-vs-CUDA PyTorch selection. |
| [`integrate-apeiron`](integrate-apeiron/) | Adds apeiron's drift detection and CL adaptation to an existing training loop (PyTorch, Lightning, HF Trainer, Accelerate) with the lightest adapter that fits. |

The five compose into one path through the framework: `install-apeiron` makes
`import apeiron` work, `apeiron-explore-examples` demonstrates it on shipped
data, `apeiron-choose-detector` tunes the detection stage, and then either
`apeiron-custom-experiment` (adopt apeiron's runner on your own data) or
`integrate-apeiron` (keep your own runner) takes it into real use.

## Requirements

`install-apeiron` and `integrate-apeiron` operate on the user's own project.
The other three need a clone of the upstream repository, since they run the
bundled examples and read the framework's source and docs:

```bash
git clone https://github.com/AI-ModCon/BaseSIM_APEIRON.git
```

apeiron requires Python 3.13 and uses Poetry. Each skill declares its own
requirements in its `compatibility` frontmatter and resolves the checkout at run
time rather than assuming the working directory.

## Development

These skills are developed in the apeiron project,
[`AI-ModCon/BaseSIM_APEIRON`](https://github.com/AI-ModCon/BaseSIM_APEIRON),
where they live under `.claude/skills/` and `.codex/skills/` alongside the
framework they describe. Changes land there first and are periodically re-ported
here. This copy is vendored and adapted for the catalog — `ATTRIBUTION.md`
records the upstream commit and every adaptation, so a later re-port can be
replayed against it.

## Structure

```
basesim-skills/
├── LICENSE                        # Apache-2.0, governs this subtree
├── README.md
├── ATTRIBUTION.md
├── apeiron-choose-detector/
│   └── SKILL.md
├── apeiron-custom-experiment/
│   └── SKILL.md
├── apeiron-explore-examples/
│   └── SKILL.md
├── install-apeiron/
│   └── SKILL.md
└── integrate-apeiron/
    └── SKILL.md
```
