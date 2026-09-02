---
name: card-eval-updater
description: "Distill evaluation-harness output into the evaluation sections of a Genesis/BPSW model card. Parses lm-evaluation-harness (results_*.json), nemo-evaluator-launcher / Eval Factory (artifacts/results.yml), and NeMo-Skills (ns eval / ns robust_eval metrics.json) into a canonical eval bundle, then writes Evaluation data, Evaluation Procedure, Uncertainty Quantification, and Evaluation results into the card plus benchmark entries in the metrics: frontmatter. Use when the user asks to update or create a model card from an evaluation run, record benchmark results in a card, or report harness output as documentation."
license: Apache-2.0
compatibility: "Requires python3 with pyyaml. jsonschema optional (enables bundle validation). No network access needed."
allowed-tools: Bash(python3 *) Read Glob Grep
---

# Updating a model card from an evaluation run

Turn the output of an evaluation harness into the evaluation sections of a
Genesis/BPSW model card, with every number traceable to a run artifact.

**The one rule that governs this skill: benchmark numbers are extracted by
script and never retyped, recomputed, or estimated by you.** If a number is not
in the bundle, it does not go in the card. Your job is the surrounding judgment —
which run to use, which card, whether the run is even reportable — not the
arithmetic.

## Workflow

Copy this checklist and check off steps as you go.

```
Progress:
- [ ] 1. Locate the run and identify the harness
- [ ] 2. Parse to a bundle
- [ ] 3. Resolve model identity
- [ ] 4. Decide whether the run is reportable
- [ ] 5. Pick the target card
- [ ] 6. Preview the edit (--dry-run)
- [ ] 7. Write the card
- [ ] 8. Validate
- [ ] 9. Report what changed
```

### 1. Locate the run and identify the harness

Ask for the run directory if you weren't given one. Detection is automatic, but
knowing which harness you have tells you what to expect:

| Harness | Signature | Notes |
|---|---|---|
| lm-evaluation-harness | `results_*.json` with `lm_eval_version` | Richest provenance; nearly everything the card needs is in this one file |
| nemo-evaluator-launcher | `<task>/artifacts/results.yml` | Wraps three sub-frameworks; `framework_name` is in `run_config.yml` |
| NeMo-Skills | `metrics.json` from `ns eval` / `ns robust_eval` | No model identity anywhere; percentages not fractions |

Point at **one** run. Detection searches the whole tree, so a parent directory
holding two runs is refused rather than parsed as whichever harness matched
first — a bundle records a single run, and the other one could only be dropped
silently.

Runs produced by the `lm-eval-harness-skills` configuration skills need nothing
special — they shell out to stock `lm_eval --output_path ... --log_samples`.

### 2. Parse to a bundle

```bash
python3 scripts/parse_eval_results.py <run_dir> -o bundle.json
```

The bundle conforms to `references/eval-bundle.schema.json` and is validated on
write. Read it. Do not proceed on a bundle you have not looked at.

### 3. Resolve model identity

If the parser refuses because no model identity was found — always the case for
NeMo-Skills — **ask the user** which model was evaluated and re-run with
`--model-id`. Do not guess it from the directory name. If the user genuinely
does not know, `--allow-unknown-model` records the identity as unknown in the
card; never invent one to get past the error.

A user-supplied id is recorded as `id_provenance: "user"` and the card
discloses that it could not be verified against the run. That disclosure is not
optional; do not strip it.

### 4. Decide whether the run is reportable

The parser refuses sample-limited runs by default. **This refusal is usually
correct — treat `--allow-partial` as a last resort, not a way past an error.**

A 2-sample or 5-sample run scoring 1.0 is a smoke test, not a benchmark result,
and putting it in a card creates a citable claim that the model does not support.
`lm-eval-harness-skills`' tester defaults to `--limit 5`, so this comes up often.

When you hit the refusal:

1. Tell the user the run was sample-limited and say by how much.
2. Recommend re-running the eval without a limit.
3. Only if they explicitly want the partial run recorded, use `--allow-partial` —
   it is labelled partial in every section that shows a number.

### 5. Pick the target card

Raw cards live in `modcon-bpsw/cards/resources/`. The `ai-resource-hub/_models/`
copies are **generated** by `sync_and_classify_cards.py` and will be overwritten —
never target those (the tool warns if you try).

If no card exists yet, start from the template:

```bash
python3 scripts/update_card.py --template <modcon-bpsw>/cards/templates/model-card.md \
    bundle.json -o new-card.md
```

### 6. Preview

```bash
python3 scripts/update_card.py card.md bundle.json -o card.out.md --dry-run
```

Read the diff. Confirm it only adds `### Automated benchmark results` blocks and
`metrics:` entries, and does not disturb prose.

### 7. Write

```bash
python3 scripts/update_card.py card.md bundle.json -o card.out.md
```

Writes to a path you choose; never edits a repository checkout on its own.

### 8. Validate

```bash
python3 scripts/validate_card_eval.py card.out.md bundle.json
```

This re-renders from the bundle and diffs against the card, so any number that
drifted from its artifact shows up as `UNTRACED`. Resolve every `error` before
reporting done. Codes: `MISSING_SECTION`, `UNTRACED`, `METRICS_MISMATCH`,
`PARTIAL_UNLABELLED`, `PLACEHOLDER`. Use `--json` for machine-readable output.

### 9. Report

Tell the user: which run, which harness, how many results, what sections
changed, what frontmatter entries were added, and any caveat the card now
carries (partial, LLM-judged, unverified model identity).

## Gotchas

1. **Never hand-edit a generated block.** It is regenerated on the next run and
   the validator reports it as `UNTRACED`. To change what it says, change the
   renderer.

2. **The anchor is a visible heading, not an HTML comment.**
   `sync_and_classify_cards.py` strips HTML and YAML comments, so a
   `<!-- eval:start -->` marker would vanish downstream and every re-run would
   append a second copy. `### Automated benchmark results` is the anchor.

3. **`metrics:` frontmatter accumulates and is never pruned.** Re-running with a
   different benchmark adds entries but does not remove superseded ones — the
   tool cannot distinguish an entry it added from one a human added, and
   deleting someone's metric silently is worse than carrying a stale one. Prune
   by hand if it matters.

4. **NeMo-Skills reports percentages.** They are divided by 100 on ingest, with
   the original kept in `value_raw`. The card discloses the rescale. If you ever
   see a "score" above 1.0 in a card, that conversion was skipped.

5. **NeMo-Skills `robust_eval` drops the metric name** from its top-level
   aggregation. The parser recovers it from the per-variant
   `eval-results/*/metrics.json`; if those are absent the metric is labelled
   `score`. Prefer keeping the full run directory, not just `metrics.json`.

6. **An Eval Factory task can have `run_config.yml` but no `results.yml`** when
   scoring failed. Those tasks are skipped with a warning rather than silently
   dropped — surface that warning to the user, it means a benchmark did not run.

7. **A custom lm-eval model gets a random name.** lm-eval derives `model_name`
   from `pretrained`/`model`/`path`/`engine` in `model_args`; a custom model
   class with none of those falls back to an 8-character nonce. The parser
   detects this and refuses rather than writing the nonce into a card — supply
   `--model-id`, or `--allow-unknown-model` to record it as unknown.

8. **Eval Factory wraps ~23 harnesses; three are verified.** The adapter targets
   Eval Factory's normalized `results.yml`, so it should generalize, and
   non-rate metrics (perplexity, BLEU, token counts) are marked `raw` rather
   than shown as fractions. Still, spot-check the first bundle from a harness
   you have not run before.

9. **Agent cards are out of scope.** The BPSW agent template has no
   evaluation-results section, and there is no agentic-eval harness output to
   draw from. Do not improvise one.

## Design note: one parse layer, many renderers

`render_card_sections.py` is the **model-card** renderer. It is deliberately
separable from the parser: a model card wants benchmark values with provenance
and stderr, whereas SIM wants drift-relevant series across runs, and SAFE wants
the failure and refusal tail. Those are different reductions of the same run and
belong in sibling renderers reading the same
`references/eval-bundle.schema.json` contract — not in this file, and not by
re-parsing raw harness output.

## References

- Bundle contract: [references/eval-bundle.schema.json](references/eval-bundle.schema.json)
- What each harness emits, and where: [references/harness-formats.md](references/harness-formats.md)
- Bundle field → card section: [references/card-mapping.md](references/card-mapping.md)
- Tests (real harness output): run `make test` in the development repository, [AI-ModCon/BaseEval_card-eval-updater_DEV](https://github.com/AI-ModCon/BaseEval_card-eval-updater_DEV)
