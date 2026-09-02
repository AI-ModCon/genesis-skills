# Benchmark Summary

`beamline_qa` measures factual knowledge of synchrotron light-source science —
accelerator physics, beamline optics, and X-ray characterization techniques —
via four-way multiple choice. It is a small domain-knowledge probe, not a
reasoning benchmark: each item has a single unambiguous correct answer that a
practitioner in the field would answer without calculation.

---

# Configuration Details

## Basic Information

*Benchmark name:* `beamline_qa`

*Data source location:*
- Local JSONL, loaded through the HuggingFace `json` loader:
  `dataset_path: "json"`
- `dataset_kwargs.data_files.test:` absolute path to
  `card-eval-updater/examples/custom-benchmark/data/beamline_qa.jsonl`
- `dataset_name: null`

*Data splits:*
- `test_split: "test"` — the only split; all 24 items
- `validation_split: null`
- `training_split: null`
- `fewshot_split: null` — no few-shot examples (see assumptions)

*Record schema:*
- `id` (str) — stable item identifier, e.g. `bl-001`
- `question` (str) — the question stem
- `choices` (list[str]) — exactly 4 answer options
- `answer_index` (int) — 0-based index into `choices`

## Task Configuration

*Task output format:* `output_type: multiple_choice`

The harness scores each of the 4 options by loglikelihood and picks the
highest. This suits a fixed option set and avoids any answer-extraction
parsing, which is the main source of spurious failure in free-form configs.

*Prompt template:*

```
Question: What particle is accelerated in a synchrotron light source to produce X-rays?
Answer:
```

Options are scored as continuations (` Alpha particle`, ` Electron`, ` Muon`,
` Neutron`) rather than being enumerated as lettered choices in the prompt.
This is the `arc_easy` convention and keeps the config free of letter-parsing.

*Target extraction:* `doc_to_target: "{{answer_index}}"` — the integer index is
already 0-based and aligns with the order of `doc_to_choice`, so no
transformation is needed.

*Output post-processing:* None required. `multiple_choice` compares option
loglikelihoods internally; there is no generated text to parse, so empty or
malformed output is not a failure mode here.

*Metrics / process_results:*
- Built-in `acc` (exact match on the argmax option), `aggregation: mean`,
  `higher_is_better: true`
- No custom metric code

**Revised after data exploration**: `acc_norm` (byte-length-normalized) is now
included as well, and is the metric to trust. See the Decision Log.

## Implementation Plan

*Custom code required:* none. No `utils.py` is needed.
- [ ] `process_docs` — not needed; records are already in final shape
- [ ] `doc_to_text` — simple Jinja, stays in YAML
- [ ] `doc_to_target` — direct field access
- [ ] `filter` — not needed
- [ ] Custom metrics — not needed
- [ ] Helper functions — not needed

*Validation plan:*
1. Run with `--limit 5` to confirm the task loads and prompts render
2. Inspect rendered prompts in the samples JSONL for correct question text
3. Confirm all 4 choices are scored per item
4. Confirm `acc` lands in [0, 1]
5. Spot-check 5 samples: predicted index vs `answer_index`
6. Compare against the known baselines below

*Baselines for sanity-checking:*
- Random guessing: 0.25
- Always-first-option: 8/24 = 0.333 (answer positions were shuffled with a
  fixed seed; distribution is 8/4/4/8 across indices 0-3)

*Open questions / assumptions:*

- **Assumption**: zero-shot. The questions are self-contained factual items
  with no format ambiguity, so few-shot examples would mostly consume context.
  - *Risk if wrong*: a model may under-perform because it does not infer the
    expected answer style — low risk for `multiple_choice`, which does not
    depend on output formatting.
  - *Validation*: compare 0-shot and 5-shot on one model if a discrepancy is
    suspected.

- **Assumption**: report `acc` only, not `acc_norm`. Options are short noun
  phrases of comparable length, so length normalization mostly adds noise and a
  second number to explain.
  - *Risk if wrong*: models biased toward longer options would be flattered by
    `acc` alone. The dataset was written with distractors of similar length to
    the correct answer, which limits this.
  - *Validation*: check option length correlation with correctness during data
    exploration.

- **Assumption**: absolute path in `data_files`. HuggingFace `datasets`
  resolves `data_files` against the **current working directory**, not against
  the task YAML, so a relative path silently breaks whenever the harness is
  invoked from anywhere but the task directory.
  - *Risk if wrong*: none; an absolute path is strictly more robust. The cost
    is that the YAML is not portable between machines without an edit.
  - *Validation*: run `lm_eval` from a different cwd and confirm it loads.

---

# Definition of Done (Planner)

- [x] All configuration fields filled out
- [x] Concrete prompt example shown
- [x] Output parsing strategy defined (not applicable — multiple_choice)
- [x] Metric implementation approach specified (built-in `acc`)
- [x] High-risk assumptions documented with validation plans
- [x] No unresolved questions that would change task semantics

---

# Verification Checklists

## Data Analysis Checklist

**Data Quality & Structure**
- [x] Null/missing values — none
- [x] Field consistency — all 24 records have `id`/`question`/`choices`/`answer_index` with correct types
- [x] Record count — 24, all ids unique
- [x] Split distribution — single `test` split

**Input Data**
- [x] Format variations — uniform; all stems end with "?"
- [x] Length distribution — 34 / 78 / 135 chars (min/median/max)
- [x] Special characters — no newlines, no LaTeX or code notation
- [x] Encoding — pure ASCII

**Target Data**
- [x] Answer format — 0-based int index, all in range
- [x] Multiple correct answers — none; single gold per item
- [x] Answer variations — n/a (index, not free text)
- [x] Numeric answers — n/a
- [x] List/structured answers — n/a

**Multiple Choice Specific**
- [x] Number of choices — exactly 4 for all 24 items
- [x] Choice labels — none in data; harness scores option text directly
- [x] Correct answer encoding — index into `choices`
- [x] Distractor quality — **problem found, see Decision Log**

**Edge Cases**
- [x] Empty answers — none
- [x] Long answers — none needing truncation
- [x] Ambiguous cases — none identified
- [x] Context dependencies — no item references a figure or external context
- [x] Code/math/special formatting — none

**Metric Implementation**
- [x] Exact match feasibility — n/a; `multiple_choice` compares loglikelihoods
- [x] Normalization needs — **byte-length normalization required** (see below)
- [x] Parsing complexity — none; no generated text to parse
- [x] Metric appropriateness — `acc` + `acc_norm` both reported

## Data Exploration Decision Log

**Date**: 2026-07-30

**Key Findings**:
- All 24 records are structurally clean: no nulls, no type errors, no duplicate
  options, every `answer_index` in range, pure ASCII, no external-context items.
- Answer positions are 8/4/4/8 across indices 0-3, so the always-pick-one-position
  baseline is 0.333 and random is 0.250.
- **Length artifact**: the correct answer is the *longest* option in 16 of 24
  items (66.7%, against 25% by chance) and the shortest in only 3. Mean gold
  option is 38.8 characters against 27.3 for distractors.

**Decisions Made**:
- Report **both `acc` and `acc_norm`** — *Why*: the length artifact means raw
  `acc` rewards any model biased toward longer completions. `acc_norm` divides
  loglikelihood by byte length and is the honest headline number. Reporting both
  makes the gap visible rather than hiding it.
- Keep zero-shot — *Why*: unaffected by the finding; items are self-contained
  and `multiple_choice` does not depend on output formatting.
- Keep the absolute `data_files` path — *Why*: confirmed necessary;
  `datasets` resolves it against cwd, not against the YAML.

**Implementation Impact**:
- `doc_to_target`: unchanged — `{{answer_index}}`
- Output parsing: unchanged — none needed
- Metrics: **add `acc_norm`** alongside `acc`

**Edge Cases Identified**:
- Length leakage — **Handling**: report `acc_norm`; flag the artifact as a
  benchmark limitation so downstream readers of the model card do not read a
  high `acc` as domain knowledge.

**Assumptions**:
- The `acc`/`acc_norm` gap is interpretable as length bias — *Risk*: on a
  24-item set both metrics carry a standard error near 0.09, so a small gap is
  not evidence of anything. Treat differences under ~0.18 as noise.

**Benchmark limitation to carry forward**: this artifact is a flaw in the
dataset, not in the configuration. A revision should rewrite distractors to
match the gold answer's specificity and length.

---

# Implementation Notes

*Updated by implementation and testing stages.*
