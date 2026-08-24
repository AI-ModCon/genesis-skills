# Getting Started

## Requirements

- Python 3.10 or newer
- `pyyaml`
- `jsonschema` (optional; enables bundle schema validation)

No installation is required. The scripts are invoked by path.

## Install as a skill

```bash
# from a genesis-skills checkout
ln -sfn "$PWD/skills/baseeval-skills/card-eval-updater" \
    ~/.claude/skills/card-eval-updater          # Claude Code
```

Or use the repository's `unpack.sh` to flatten the whole catalog into your
client's skills directory.

Ask your agent to "update the model card from this evaluation run" and it will
load the skill and follow the workflow in [`SKILL.md`](../SKILL.md).

## Run it directly

The four steps below are what the skill performs.

### 1. Parse a run into a bundle

```bash
python3 scripts/parse_eval_results.py path/to/run -o bundle.json
```

The harness is detected automatically. The bundle is validated against
[`references/eval-bundle.schema.json`](../references/eval-bundle.schema.json)
before it is written.

Two flags matter:

- `--model-id ID` — required for NeMo-Skills runs, which record no model
  identity. The value is marked as operator-supplied and the card discloses that
  it could not be verified against the run.
- `--allow-partial` — permits sample-limited runs. Withheld by default; see
  [FAQ](./faq.md#why-was-my-run-refused-as-partial).

### 2. Preview the card edit

```bash
python3 scripts/update_card.py card.md bundle.json -o card.out.md --dry-run
```

Prints a unified diff. The edit should only add
`### Automated benchmark results` blocks and `metrics:` frontmatter entries.

### 3. Write

```bash
python3 scripts/update_card.py card.md bundle.json -o card.out.md
```

To create a card from scratch, pass the BPSW template instead of an existing
card:

```bash
python3 scripts/update_card.py --template path/to/model-card.md \
    bundle.json -o new-card.md
```

Writes only to the path you give. It never edits a repository checkout on its
own, and warns if the target sits in a directory the BPSW pipeline regenerates.

### 4. Validate

```bash
python3 scripts/validate_card_eval.py card.out.md bundle.json
```

Re-renders from the bundle and diffs against the card. Findings use structured
codes:

| Code | Severity | Meaning |
|---|---|---|
| `MISSING_SECTION` | error | An evaluation section has no generated block |
| `UNTRACED` | error | A block does not match a re-render of the bundle |
| `METRICS_MISMATCH` | warn | `metrics:` frontmatter omits a bundle entry |
| `PARTIAL_UNLABELLED` | error | A partial run is not disclosed as partial |
| `PLACEHOLDER` | warn | Template placeholder markup survived into the card |

Add `--json` for machine-readable output. Exit status is non-zero if any error
finding is present.

## What lands in the card

| Card section | Content |
|---|---|
| `Evaluation data` | Benchmark, dataset source, items evaluated, benchmark description |
| `Evaluation Procedure` | Harness and version, model, few-shot count, decoding parameters, compute, seeds, runtime, artifact path |
| `Uncertainty Quantification` | Standard errors, standard deviations, repeated runs, prompt sensitivity |
| `Evaluation results` | Scores with standard errors and sample counts, plus run diagnostics |
| frontmatter `metrics:` | `<benchmark>/<metric>` entries |

Full field-by-field mapping:
[references/card-mapping.md](../references/card-mapping.md).

## A complete worked example

[`examples/skill-chain/`](../examples/skill-chain/) builds a custom benchmark
with the `lm-eval-harness-skills` configuration skills, evaluates it with a
custom model class, and produces a card — with no weights, GPU or network.
