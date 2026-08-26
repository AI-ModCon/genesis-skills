# card-eval-updater

[![CI](https://github.com/AI-ModCon/BaseEval_card-eval-updater_DEV/actions/workflows/ci.yml/badge.svg)](https://github.com/AI-ModCon/BaseEval_card-eval-updater_DEV/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

An [Agent Skill](https://agentskills.io) that distills evaluation-harness output
into the evaluation sections of a Genesis/BPSW model card.

Three harnesses in use across BASE emit three unrelated result formats, with
three metric-naming conventions and two numeric scales. The tool parses any of
them into one canonical **eval bundle**, then renders that into a model card.

**Benchmark numbers are extracted deterministically and never pass through a
language model's context.** The validator re-renders from the bundle and diffs
against the card, so any figure that has drifted from its source artifact is
reported as `UNTRACED`.

## Install

No installation. Expose this directory to your agent, either through the
repository's `unpack.sh` or by symlinking it directly:

```bash
ln -sfn "$PWD" ~/.claude/skills/card-eval-updater      # Claude Code
ln -sfn "$PWD" ~/.agents/skills/card-eval-updater      # other clients
```

Requires `python3` and `pyyaml`. Install `jsonschema` to enable bundle
validation.

## Usage

```bash
python3 scripts/parse_eval_results.py <run_dir> -o bundle.json
python3 scripts/update_card.py card.md bundle.json -o card.out.md --dry-run
python3 scripts/update_card.py card.md bundle.json -o card.out.md
python3 scripts/validate_card_eval.py card.out.md bundle.json
```

Fills `Evaluation data`, `Evaluation Procedure`, `Uncertainty Quantification`
and `Evaluation results`, and adds `<benchmark>/<metric>` entries to the card's
`metrics:` frontmatter. Pass `--template` instead of a card to create one.

## Supported harnesses

| Harness | Detected by | Notes |
|---|---|---|
| lm-evaluation-harness | `results_*.json` containing `lm_eval_version` | Richest provenance. Covers runs from the `lm-eval-harness-skills` configuration skills |
| nemo-evaluator-launcher (Eval Factory) | `*/artifacts/results.yml` | Targets Eval Factory's normalized output; 3 of ~23 sub-frameworks verified |
| NeMo-Skills | `metrics.json` from `ns eval` / `ns robust_eval` | Reports percentages; records no model identity, so `--model-id` is required |

Formats and their traps: [references/harness-formats.md](references/harness-formats.md).

## Design

Parsing is shared; distillation is not. A model card wants benchmark values with
provenance and standard errors; drift detection wants series across runs; safety
analysis wants the failure and refusal tail. These are different reductions of
the same run.

The eval bundle is therefore a **versioned contract**
([`references/eval-bundle.schema.json`](references/eval-bundle.schema.json)),
not an internal step, and `scripts/render_card_sections.py` is one renderer over
it. Additional consumers should add sibling renderers against the same schema
rather than re-parsing raw harness output.

## Guardrails

- **Partial runs are refused by default.** A five-sample smoke test is not a
  benchmark result. `--allow-partial` records one, labelled partial wherever a
  number appears.
- **Hand-written prose is never overwritten.** Only the
  `### Automated benchmark results` subtree is written or replaced; re-runs are
  idempotent.
- **Unverified model identity is disclosed** in the card rather than assumed.
- **Generated card directories are flagged**, since the BPSW pipeline
  regenerates them from `cards/resources/`.

## Examples

[`examples/skill-chain/`](examples/skill-chain/) runs the full workflow by
invoking the `lm-eval-harness-skills` configuration skills and then this one, on
a custom benchmark evaluated with a custom model class. No weights, GPU or
network required. [`examples/custom-benchmark/`](examples/custom-benchmark/) is
the same benchmark with hand-written artifacts.

## Development

Develop this skill in its development repository,
[`AI-ModCon/BaseEval_card-eval-updater_DEV`](https://github.com/AI-ModCon/BaseEval_card-eval-updater_DEV), which carries the test
suite, `Makefile`, `pyproject.toml`, the lockfile, and CI (`make install`, `make
test`, `make lint`, `make format`). This copy is vendored and carries no tests;
changes land there first and are re-vendored here.

The suite runs against real harness output, including a task whose scoring
failed and produced no results file.

## Documentation

- [Getting started](docs/getting_started.md)
- [FAQ](docs/faq.md)
- [Harness formats](references/harness-formats.md)
- [Bundle → card mapping](references/card-mapping.md)
- [Contributing](https://github.com/AI-ModCon/BaseEval_card-eval-updater_DEV/blob/main/CONTRIBUTING.md) (upstream)

## Attribution

`normalize_heading` and the fence-aware heading scan in `scripts/card_text.py`
are adapted from `modcon-bpsw/scripts/analyze_cards.py`, so section matching
agrees with the existing BPSW analysis pipeline.

Author: Fernando Llorente, Brookhaven National Laboratory.

This directory is a vendored copy of
[`AI-ModCon/BaseEval_card-eval-updater_DEV`](https://github.com/AI-ModCon/BaseEval_card-eval-updater_DEV)
@ `c565305`, which remains the place to develop and test the skill. `SKILL.md`,
`scripts/`, `references/`, and `examples/` are unmodified. The upstream `tests/`
directory is not vendored — it lives in the development repository — so this
file, `docs/getting_started.md`, and one line of `SKILL.md`'s References section
are adapted to this layout. Licensed Apache-2.0 — see [`LICENSE`](LICENSE), which governs this
directory in place of the repository's root BSD-2-Clause, as described in the
root [`NOTICE`](../../../NOTICE).
