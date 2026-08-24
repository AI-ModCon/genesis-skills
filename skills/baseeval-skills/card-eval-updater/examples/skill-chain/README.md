# Skill-chain run: Emily's lm-eval skills → card-eval-updater

The same benchmark as [`../custom-benchmark/`](../custom-benchmark/), but built
by **invoking the skills** rather than hand-writing the artifacts. Both skill
groups were installed with:

```bash
cd genesis-skills
./unpack.sh baseeval-skills --target ~/.claude/skills --mode symlink
ln -sfn /path/to/card-eval-updater ~/.claude/skills/card-eval-updater
```

Skills became discoverable immediately — no session restart needed.

## What each step produced

| Step | Skill | Output |
|---|---|---|
| 1-2 | `configuration-creator` → `configuration-planner` | [`tasks/beamline_qa/plan.md`](tasks/beamline_qa/plan.md) |
| 3 | `data-exploration` | [`scratch/analyze_beamline_qa.py`](tasks/beamline_qa/scratch/analyze_beamline_qa.py) + Decision Log in `plan.md` |
| 4 | `configuration-implementor` | [`tasks/beamline_qa/beamline_qa.yaml`](tasks/beamline_qa/beamline_qa.yaml) |
| 5 | `configuration-tester` | `test_config.sh` run, then a full run → `results/` |
| 6 | `card-eval-updater` | [`bundle.json`](bundle.json) → [`beamline_qa_model-card.md`](beamline_qa_model-card.md) |

## The chain earned its keep

`data-exploration` found a real flaw the hand-written config missed: **the
correct answer is the longest option in 16 of 24 items (66.7%, vs 25% by
chance)**, mean gold length 38.8 chars against 27.3 for distractors. Raw `acc`
therefore rewards any model biased toward longer completions.

That finding changed the configuration — `acc_norm` was added as a control — and
then propagated all the way into the model card's Evaluation data section as a
documented benchmark limitation. A data-quality observation in step 3 became a
caveat a downstream reader of the card will see.

The artifact is a flaw in the dataset, not the config. A revision should rewrite
distractors to match the gold answer's specificity and length.

## Hand-written vs skill-produced

| | Hand-written | Skill-produced |
|---|---|---|
| `data_files` | relative (breaks outside its own dir) | absolute |
| `dataset_name` | omitted | explicit `null` |
| metrics | `acc` | `acc` + `acc_norm` |
| `metadata.description` | dataset summary | summary + baselines + the length artifact |
| result | `acc 0.2083 ± 0.0847` | `acc 0.2083 ± 0.0847`, `acc_norm 0.2500 ± 0.0903` |

`acc` agrees to four decimals across both configs — independent cross-validation
that the two paths describe the same task.

Both scores sit at or below the 0.25 random baseline. The `acc`/`acc_norm` gap
(0.042) is well inside the ~0.09 standard error, so on 24 items it is not
evidence of anything; the plan flags differences under ~0.18 as noise.

> **Portability note.** The absolute path the skill originally emitted pointed at
> the checkout it was generated on. It has been redacted to the placeholder
> `/path/to/card-eval-updater/...` in
> [`tasks/beamline_qa/beamline_qa.yaml`](tasks/beamline_qa/beamline_qa.yaml),
> in the recorded run config, and in the artifact paths carried by
> [`bundle.json`](bundle.json) and the model card. Substitute your own checkout
> path before re-running. The scores and every other field are untouched.

## Friction worth knowing about

**1. `configuration-tester` cannot test a custom model class.** Its
`test_config.sh` invokes bare `lm_eval`, which only registers custom *tasks* via
`--include_path`. Running it against `lexical-overlap` required a
`sitecustomize.py` on `PYTHONPATH` to import the model at interpreter start.

**2. Passing an empty `model_args` silently substitutes the script's default.**
`test_config.sh` uses `${4:-default}`, which treats `""` as unset — so
`test_config.sh ... lexical-overlap "" 5 false` ran with
`pretrained=mistralai/Mistral-7B-Instruct-v0.3`. Our custom model ignores those
kwargs, but **lm-eval derives `model_name` from `model_args.pretrained`**, so the
results file recorded:

```
config.model : lexical-overlap                      ← what actually ran
model_name   : mistralai/Mistral-7B-Instruct-v0.3   ← what the file claims
```

Left unchecked, `card-eval-updater` would have written a model that never ran
into a published card. It now rejects any `model_name` derived from `model_args`
when the model *type* is not one where `model_args` selects the weights, and
demands `--model-id`. Regression test:
`test_model_name_from_a_custom_model_type_is_rejected`.

**3. The `--limit 5` default trips the partial guardrail — correctly.**
`test_config.sh` defaults to 5 samples. Parsing that run refuses with
`PartialRunError` (5 of 24). That is the intended interaction: the tester's job
is to validate the config, not to produce a citable score. A full run followed.

**4. Version triangle for `hf` models.** lm-eval 0.4.10 passes `dtype=` to
`from_pretrained`, which needs transformers ≥4.56, which needs torch ≥2.6. With
torch 2.5 the tester's default `hf` path fails with
`GPT2LMHeadModel.__init__() got an unexpected keyword argument 'dtype'`. Not a
skill problem, but it blocks the tester's default model.
