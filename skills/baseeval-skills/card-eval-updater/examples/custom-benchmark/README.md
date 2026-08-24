# Worked example: custom benchmark → custom model → model card

An end-to-end run chaining the two BaseEval skill groups:

```
lm-eval-harness-skills            card-eval-updater
─────────────────────             ─────────────────
configuration-planner   ┐
data-exploration        ├─→ tasks/beamline_qa.yaml
configuration-implementor┘         │
configuration-tester ────→ lm_eval ┴─→ results_*.json ──→ parse ──→ bundle.json
                                                            │
                                                            ├─→ update_card ──→ model card
                                                            └─→ validate
```

Everything here really runs. The numbers below were produced by the commands
below, not written by hand.

## What is being evaluated

**Benchmark** — `beamline_qa`, 24 four-way multiple-choice questions on
synchrotron light-source science (accelerator physics, beamline optics, X-ray
techniques). Correct-answer positions were shuffled with a fixed seed, so
guessing the majority position scores 8/24 and random guessing scores 25%.
[`tasks/beamline_qa.yaml`](tasks/beamline_qa.yaml) is the kind of file
`configuration-implementor` produces; [`data/beamline_qa.jsonl`](data/beamline_qa.jsonl)
is the dataset.

**Model** — `lexical-overlap`, a custom lm-eval model class
([`models/lexical_overlap.py`](models/lexical_overlap.py)) that picks the answer
sharing the most content words with the question. It needs no weights, no GPU
and no network, so the example is exactly reproducible — and it is a meaningful
control rather than a toy: any real model on this benchmark should beat it, and
one that does not has learned nothing beyond surface word matching.

## Run it

```bash
# 1. install lm-evaluation-harness (once)
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e /path/to/lm-evaluation-harness

# 2. run the custom benchmark against the custom model
.venv/bin/python run_eval.py

# 3. distill the run into a model card
python3 ../../scripts/parse_eval_results.py results/beamline_qa \
    --model-id "lexical-overlap-baseline v1.0" -o bundle.json
python3 ../../scripts/update_card.py \
    --template ../../../modcon-bpsw/cards/templates/model-card.md \
    bundle.json -o beamline_qa_model-card.md
python3 ../../scripts/validate_card_eval.py beamline_qa_model-card.md bundle.json
```

`run_eval.py` exists for two reasons, both worth knowing if you adapt this:

1. **`--include_path` registers custom *tasks*, not custom *models*.** A model
   class has to be imported before lm-eval builds its registry, so
   `PYTHONPATH=models lm_eval --model lexical-overlap ...` fails with
   `Unknown model 'lexical-overlap'`. The wrapper imports the module, then hands
   off to the ordinary lm-eval CLI.
2. **`data_files: data/beamline_qa.jsonl` in the task YAML resolves against the
   current working directory**, not against the YAML's own location, so the
   wrapper `chdir`s to the example directory first. Without that the example only
   runs from inside its own folder.

Every flag it passes is stock lm-eval, so the output layout is the standard one —
`configuration-tester`'s `test_config.sh` produces the same thing.

## Result

```
|   Tasks   |Version|Filter|n-shot|Metric|   |Value |   |Stderr|
|-----------|------:|------|-----:|------|---|-----:|---|-----:|
|beamline_qa|      1|none  |     0|acc   |↑  |0.2083|±  |0.0847|
```

5/24 — slightly *below* the 25% random baseline. That is the honest reading:
lexical overlap is not merely uninformative on this benchmark, it is mildly
anti-correlated, because distractors were written using the question's own
vocabulary while several correct answers use different terms. Exactly the sort
of thing a benchmark should reveal about a weak baseline.

## What lands in the card

`## Evaluation data` picks up the resolved data file and the benchmark's own
description:

> | Benchmark | Dataset | Items evaluated |
> |---|---|---|
> | beamline_qa | data/beamline_qa.jsonl | 24 of 24 |
>
> **beamline_qa** — 24 four-way multiple-choice questions on synchrotron
> light-source science…

`## Evaluation results`:

> | Benchmark | Metric | Value | Std. error | Samples |
> |---|---|---|---|---|
> | beamline_qa | acc | 0.2083 | 0.0847 | 24 |

plus `## Evaluation Procedure` (harness version, few-shot count, seeds, runtime,
artifact path), `## Uncertainty Quantification` (the standard error), and a
`beamline_qa/acc` entry in the `metrics:` frontmatter.

The finished card is [`beamline_qa_model-card.md`](beamline_qa_model-card.md). The
absolute artifact path it records has been redacted to a
`/path/to/card-eval-updater/...` placeholder; re-running regenerates it with
your own checkout path.

## Two things this example surfaced

Both were found by running it, and both are now handled:

**1. A custom model gets a random name.** lm-eval derives `model_name` from
`pretrained`/`model`/`path`/`engine` in `model_args`; a custom class with no
`model_args` falls back to `random_name_id()` — 8 random characters. This run
was labelled `41pjso2k`. Writing that into a card as the model identity would be
worse than admitting ignorance, so the parser detects the fallback, reports no
identity, and asks for `--model-id`. The resulting card discloses that the
identity was operator-supplied and unverified.

**2. `dataset_path: json` names a loader, not a dataset.** Custom tasks load
local files through a generic loader, so the real source is in
`dataset_kwargs.data_files`. The parser sees through `json`, `csv`, `parquet`,
`text`, `arrow`, `pandas` and `generator` to the actual path, and also picks up
`metadata.description` so a custom benchmark documents itself in the card.

## Known limitation

lm-eval does not record the `--include_path` task YAML location anywhere in
`results_*.json`, so `task_yaml` stays null even here. The fully-resolved task
config *is* inlined under `configs.<task>`, which is the reproducibility record —
but the card cannot cite a YAML path. Keep the task file alongside the run.
