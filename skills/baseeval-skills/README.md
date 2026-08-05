# BaseEval Skills

Agent skills for language-model evaluation workflows, sourced from two upstream
projects. The category is split into two sub-groups, each with its own
attribution.

## Sub-groups

### `lm-eval-harness-skills/` (5)

Skills for creating, implementing, and testing custom benchmark configurations
for the [EleutherAI lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness).
Authored by Emily Saldanha (PNNL). See
[`lm-eval-harness-skills/ATTRIBUTION.md`](lm-eval-harness-skills/ATTRIBUTION.md).

| Skill | Description |
|-------|-------------|
| [`configuration-creator`](lm-eval-harness-skills/configuration-creator/) | Orchestrates the end-to-end workflow for developing evaluation configurations for novel benchmark tasks. |
| [`configuration-planner`](lm-eval-harness-skills/configuration-planner/) | Clarifies benchmark details and drafts a high-level configuration plan. |
| [`data-exploration`](lm-eval-harness-skills/data-exploration/) | Writes Python scripts to ingest and analyze user-provided data. |
| [`configuration-implementor`](lm-eval-harness-skills/configuration-implementor/) | Creates the YAML file and `utils.py` code that define the benchmark configuration. |
| [`configuration-tester`](lm-eval-harness-skills/configuration-tester/) | Tests the generated configuration and identifies issues to correct. |

### `perlmutter-ns-skills/` (2)

Skills for running [NeMo-Skills](https://github.com/NVIDIA/NeMo-Skills) jobs on
NERSC Perlmutter against an external OpenAI-compatible API endpoint. Authored by
Fernando Llorente (BNL) and Eric Chagnon (LBNL). See
[`perlmutter-ns-skills/ATTRIBUTION.md`](perlmutter-ns-skills/ATTRIBUTION.md).

| Skill | NeMo-Skills command | Purpose |
|-------|---------------------|---------|
| [`perlmutter-nemo-eval`](perlmutter-ns-skills/perlmutter-nemo-eval/) | `ns eval` / `ns robust_eval` | Benchmark evaluation; produces `metrics.json`. |
| [`perlmutter-nemo-generate`](perlmutter-ns-skills/perlmutter-nemo-generate/) | `ns generate` | LLM inference over `input.jsonl` with a `prompt.yaml`. |

## Structure

```
baseeval-skills/
├── README.md                      
├── lm-eval-harness-skills/        
│   ├── ATTRIBUTION.md
│   ├── configuration-creator/
│   ├── configuration-planner/
│   ├── data-exploration/
│   ├── configuration-implementor/
│   └── configuration-tester/
└── perlmutter-ns-skills/          
    ├── ATTRIBUTION.md
    ├── perlmutter-nemo-eval/
    └── perlmutter-nemo-generate/
```
