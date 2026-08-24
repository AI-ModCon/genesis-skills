# Bundle → card mapping

How eval bundle fields land in the BPSW model card
(`modcon-bpsw/cards/templates/model-card.md`).

## Sections written

Each section receives one `### Automated benchmark results` block, appended
below any existing hand-written prose.

### `## Evaluation data`

One row per benchmark/variant — a benchmark scored on several metrics is still a
single dataset, so rows are deduplicated.

| Column | Bundle field |
|---|---|
| Benchmark | `benchmark` (+ `variant`) |
| Dataset | `dataset_path` (+ `dataset_name`), else `task_yaml` |
| Items evaluated | `num_samples` of `num_samples_total` |

Non-registered tasks get a trailing line listing their `task_yaml` paths.

### `## Evaluation Procedure`

A definition list, omitting anything the harness did not record:

`harness` + `harness_version` + `framework` · `model.id` + `num_parameters` +
`dtype` + `endpoint_url` + `api_type` · `num_fewshot` · `temperature` / `top_p` /
`max_new_tokens` · `compute.device` + `batch_size` · `seeds` · `num_runs` ·
`git_hash` · `runtime_seconds` · `run.artifact_root`

When no decoding parameters were recorded the line says so explicitly rather
than being dropped — a reader should be able to tell "greedy" from "not
recorded".

### `## Uncertainty Quantification`

| Column | Bundle field |
|---|---|
| Value / Std. error / Std. dev. / Runs | `value` / `stderr` / `stddev` / `num_runs` |

`prompt_sensitivity` gets a sentence explaining what it measures, not just a
number. When the harness reported no dispersion statistics at all, the section
says the scores are single point estimates instead of rendering an empty table.

### `## Evaluation results`

| Column | Bundle field |
|---|---|
| Value / Std. error / Samples | `value` / `stderr` / `num_samples` |

Plus a **Run diagnostics** line from `audit` (`no_answer_rate`, `finish_reason`,
`status_codes`, `avg_latency_ms`) and the evaluation runtime.

## Frontmatter

`metrics:` gains one `<benchmark>/<metric>` entry per distinct result
(`arc_easy/acc`, `mbpp/pass@1`, `gpqa/symbolic_correct`), deduplicated across
variants.

This form needs no change on the BPSW side: `ai-resource-hub/_layouts/model.html`
already renders `page.metrics` as a list, and `generate_model_inventory.py`
exports the same field.

Existing entries are preserved — cards legitimately carry training-time metrics
such as `validation_loss` alongside benchmark scores. Comment-only template
placeholders (`- # list of metrics used to...`) are dropped.

## Caveat notes

Rendered into the sections that show numbers, so a reader meets the caveat where
they meet the figure:

| Note | Trigger |
|---|---|
| **Partial run** | any `is_partial` result |
| **LLM-judged** | `audit.llm_judge_names` present |
| **Model identity supplied by the operator** | `model.id_provenance == "user"` |
| **Model identity unknown** | `model.id` is null |

## Heading matching

Sections are located by normalized heading, using the same
`normalize_heading()` rule as `modcon-bpsw/scripts/analyze_cards.py` — lowercase,
strip emphasis and punctuation, collapse whitespace — so real-world variants all
resolve. Across the 346 cards in `cards/resources/`:

| Variant | Count |
|---|---|
| `## Uncertainty Quantification.` (trailing period) | 77 |
| `## Uncertainty Quantification` | 77 |
| `## Evaluation Data` (capitalized) | 8 |
| `## Evaluation Results` (capitalized) | 7 |

Headings inside fenced code blocks are ignored.

Sections absent from a card are created under `# Evaluation details`; if the
card has no such heading, the whole block is appended at the end.

## Constraints imposed by the BPSW ingestion pipeline

`sync_and_classify_cards.py` rewrites raw cards on the way into
`ai-resource-hub/_models/`. Generated content must survive that pass:

1. **No HTML or YAML comments** — they are stripped, so a comment anchor would
   vanish and every re-run would append a duplicate block. The anchor is a
   visible `###` heading.
2. **No `{{`** — escaped to `{ {` as Liquid protection. Tested.
3. **Do not disturb "Papers and Scientific Outputs"** — that section gets
   wrapped in code fences.
4. **Edit `cards/resources/`, not `ai-resource-hub/_models/`** — the latter is
   generated output and is overwritten. `update_card.py` warns on such paths.
