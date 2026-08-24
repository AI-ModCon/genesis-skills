# Harness output formats

What each supported harness writes, where the parser reads it from, and the
traps. All observations verified against real runs, vendored as fixtures in the
development repository's test suite.

---

## lm-evaluation-harness (EleutherAI)

**Layout** — `lm_eval --output_path <out> [--log_samples]`:

```
<out>/<model_name_sanitized>/
├── results_<ISO>.json                     # scores + full provenance
├── samples_<task>_<ISO>.jsonl             # per-item records (--log_samples)
└── llm_judge_<task>_<judge>_<ISO>.jsonl   # judge scores (--run_llm_judge)
```

**Detection**: a `results_*.json` with a top-level `lm_eval_version` key.

**Scores** live in `results.<task>`, keyed `"<metric>,<filter>"`:

```json
"arc_easy": {"acc,none": 0.771, "acc_stderr,none": 0.0086, "acc_norm,none": 0.749}
```

Stderr arrives as a sibling key, not a nested field. The parser pairs
`<metric>_stderr,<filter>` with `<metric>,<filter>` and never emits `*_stderr`
as a metric in its own right.

**Provenance** — the richest of the three:

| Bundle field | Source |
|---|---|
| `harness_version` | `lm_eval_version` |
| `date` | `date` (epoch seconds → ISO) |
| `runtime_seconds` | `total_evaluation_time_seconds` |
| `model.id` | `model_name`, else `config.model_args.pretrained` |
| `model.num_parameters` / `dtype` | `config.model_num_parameters` / `model_dtype` |
| `compute.device` / `batch_size` | `config.device` / `config.batch_size` |
| `num_fewshot` | `n-shot.<task>` |
| `num_samples` / `num_samples_total` | `n-samples.<task>.effective` / `.original` |
| `higher_is_better` | `higher_is_better.<task>.<metric>` |
| `dataset_path` / `dataset_name` | `configs.<task>` |
| `seeds` | `config.{random,numpy,torch}_seed` |

**Partial detection**: `config.limit` non-null, or `effective < original`.

**Traps**

- `config.model_args` is a dict in recent versions and a comma-separated string
  in older ones. The parser handles both.
- `--include_path` custom tasks are not recorded as a file path anywhere in
  `results_*.json`. The fully-resolved task config *is* inlined under
  `configs.<task>`, which is the reproducibility record; `dataset_path` is
  captured but `task_yaml` stays null. Keep the task YAML alongside the run.
- LLM-judge sidecars are detected by filename and recorded in
  `audit.llm_judge_names`. Their per-item scores are **not** aggregated here —
  computing a mean would be a derived number with no artifact behind it. If
  lm-eval aggregated a judge metric into `results`, it appears there normally.

---

## nemo-evaluator-launcher (NVIDIA Eval Factory)

**Layout**:

```
<root>/<TIMESTAMP>-<hash>/<task_dir>/
├── artifacts/
│   ├── results.yml                  # scores
│   ├── run_config.yml               # framework_name + params  ← not results.yml
│   ├── metadata.yaml                # resolved launcher config
│   ├── metrics.json                 # flat per-framework scores
│   ├── eval_factory_metrics.json    # runtime, latency, finish reasons, HTTP status
│   └── report.{json,html}, predictions.json
└── logs/
```

`<task_dir>` naming is inconsistent: bare (`mbpp`) in some runs,
`<framework>.<task>` (`simple_evals.gpqa_diamond`) in others. Never parse it.

**Detection**: any `*/artifacts/run_config.yml` under the given path.

**Coverage across the ~23 harnesses Eval Factory wraps.** `results.yml` is Eval
Factory's *normalized* output — that is the point of the abstraction — so the
adapter is written against that schema rather than against any one
sub-framework, and iterates `(metric, score_key)` pairs generically instead of
assuming names. Verified against three real sub-frameworks
(`bigcode-evaluation-harness`, `lm-evaluation-harness`, `simple_evals`) plus a
hand-written fixture standing in for an unseen one. An unrecognized
`framework_name` passes straight through.

The one assumption that does not generalize is scale: most harnesses emit rates
in [0,1], but some emit perplexity, BLEU on 0-100, token counts or latency.
Values outside [0,1] are marked `scale: "raw"`, rendered in the harness's own
units and footnoted, so they are never read as fractions. If you run a harness
we have not seen, spot-check the first bundle — particularly the metric labels
and whether any score should have been a rate.

**Scores** — `results.tasks.<task>.metrics.<M>.scores.<S>.{value, stats.{stderr,stddev}}`.

**Trap 1 — the inner score key is not the metric name.** Compare:

```yaml
# bigcode-evaluation-harness
metrics: {pass@1: {scores: {pass@1: {value: 0.0, stats: {stderr: 0.0}}}}}
# simple_evals
metrics: {score: {scores: {micro: {value: 0.5, stats: {stderr: 0.5, stddev: 0.5}}}}}
```

The parser iterates `(metric, score_key)` pairs. When they differ and there is
more than one score key, the metric is labelled `M[S]`.

**Trap 2 — `framework_name` is in `run_config.yml`, not `results.yml`.** Three
sub-frameworks appear in practice: `bigcode-evaluation-harness`,
`lm-evaluation-harness`, `simple_evals`. Note that Eval Factory *wraps*
lm-evaluation-harness but reshapes its output entirely, so it still needs its
own adapter.

**Trap 3 — a task can have `run_config.yml` but no `results.yml`** when scoring
fails. Covered by a real example in the development repository's
`tests/fixtures/eval_factory_multi/bigcode-evaluation-harness.mbpp/`.
Those tasks are skipped with a warning; if *every* task is missing results, the
parser errors rather than emitting an empty bundle.

**Partial detection**: `config.params.limit_samples` non-null.

**Auditing** — `eval_factory_metrics.json.response_stats` gives `finish_reason`
counts, HTTP `status_codes`, `avg_latency_ms`, `avg_completion_tokens`,
`successful_count`. These land in `audit` and are rendered as run diagnostics.

---

## NeMo-Skills (`ns eval` / `ns robust_eval`)

**Layout**:

```
eval-<name>/
├── metrics.json                                    # robust_eval aggregation
├── <bench>/<variant>/eval-results/<bench>/
│   ├── metrics.json                                # per-variant detail
│   └── output-rs<N>.jsonl
└── summarize_robustness/
```

**Detection**: a `metrics.json` that is not an Eval Factory one (the latter has
a top-level `config` key).

**Two shapes.** `robust_eval` aggregation:

```json
{"gpqa": {"aai_1": {"min": 39.4, "max": 42.9, "avg": 41.2, "std": 1.77,
                    "no_answer": 54.0, "num_seeds": 2},
          "aggregated": {"min": 34.8, "max": 42.9, "avg": 39.1, "std": 3.31,
                         "num_runs": 3, "prompt_sensitivity": 3.16}}}
```

Per-variant detail (much richer, and the only place the metric is *named*):

```json
{"gpqa": {"pass@1": {"num_entries": 198, "avg_tokens": 3059, "gen_seconds": 124,
                     "symbolic_correct": 41.16, "no_answer": 53.03},
          "pass@1[avg-of-2]": {"...": "...",
                     "reasoning_tokens_statistics": {"avg": 3002.1, "std_dev_across_runs": 3.65}}}}
```

**Trap 1 — percentages, not fractions.** Unlike the other two harnesses. Values
are divided by 100 into `value`, with the original kept in `value_raw` and
`scale: "percent"`. The card discloses the conversion.

**Trap 2 — the aggregation drops the metric name.** `avg`/`std`/`min`/`max` say
nothing about *what* was averaged. The parser recovers the name (e.g.
`symbolic_correct`) by scanning `eval-results/*/metrics.json`; without those it
falls back to `score`. Keep the whole run directory.

**Trap 3 — no model identity anywhere.** Not in `metrics.json`, not in the
sbatch logs, not in the `output-rs*.jsonl` records. `--model-id` is required,
and the resulting bundle marks `id_provenance: "user"` so the card can say the
identity was not verified against the run.

**Trap 4 — partial runs are not reliably detectable.** `num_entries` is
recorded but the benchmark's full size is not, so the partial guardrail is
weaker here than for the other two. Check `num_entries` against the benchmark
yourself.

**Aggregation modes** (`pass@1`, `pass@2`, `pass@1[avg-of-2]`) are folded into
the metric name: `symbolic_correct` for the plain `pass@1` case, and
`symbolic_correct[pass@2]` otherwise.

---

## Summary of the normalizations

| | lm-eval | Eval Factory | NeMo-Skills |
|---|---|---|---|
| Metric naming | `acc,none` | `pass@1` / `score`+`micro` | `symbolic_correct` |
| Scale | fraction | fraction | **percent** |
| Model identity | yes | yes | **no** |
| Stderr | yes | sometimes | no (stddev across seeds) |
| Partial detectable | yes | yes | weakly |
| Framework field | n/a | `run_config.yml` | n/a |
