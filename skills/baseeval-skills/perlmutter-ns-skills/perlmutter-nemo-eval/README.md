# perlmutter-nemo-eval

A Claude Code agent skill that runs [`ns eval`](https://github.com/NVIDIA/NeMo-Skills) and `ns robust_eval` on NERSC Perlmutter using an external OpenAI-compatible API endpoint. The agent handles the full lifecycle: SSH certificate, preflight checks, optional container image build, benchmark data staging, job submission, polling, and result retrieval.

## What it does

Submits Slurm jobs on Perlmutter that evaluate a model against a benchmark dataset inside a `podman-hpc` container. `ns eval` runs standard evaluation (single prompt config); `ns robust_eval` runs prompt-robustness evaluation across multiple prompt configs. Results include `metrics.json` with pass@1 scores and `output.jsonl` with per-sample predictions.

## Setup

See the [root README](../README.md) for the one-time clone and symlink steps.

**Create your env file**

```bash
cp perlmutter-nemo-eval/env_vars.example my_eval_env_vars
# edit my_eval_env_vars — fill in all replace-me values
```

Env files are gitignored. Never commit them. Required variables:

| Variable | Description |
|---|---|
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint, e.g. `https://api.example.com/v1` |
| `OPENAI_API_KEY` or `NVIDIA_API_KEY` | At least one must be set |
| `NERSC_USER` | Your NERSC username |
| `SSH_LOGIN_IDENTITY` | Absolute path to your NERSC SSH private key |
| `NERSC_ACCOUNT` | Slurm account to charge |
| `NERSC_QOS` | Slurm QOS (`debug`, `regular`, `premium`, …) |
| `NERSC_CONSTRAINT` | Node constraint (`gpu` or `cpu`) |
| `NERSC_JOB_DIR` | Remote path for NeMo-Run experiment artifacts |
| `REMOTE_WORKSPACE_ROOT` | Remote path for workspace files |
| `PERLMUTTER_IMAGE_NAME` | `podman-hpc` image tag to use or build |
| `NEMO_SKILLS_REPO_DIR` | Absolute local path to the Perlmutter-enabled NeMo-Skills fork |

Eval-specific variables (see `env_vars.example` for defaults and optional overrides):

| Variable | Default | Description |
|---|---|---|
| `BENCHMARK` | *(required)* | Benchmark name, e.g. `gsm8k`, `gpqa`, `human-eval` |
| `JOB_TYPE` | `eval` | `eval` or `robust_eval` |
| `NUM_SAMPLES` | `0` | Random seeds for repeated sampling; `0` = full dataset greedy |
| `MAX_CONCURRENT_REQUESTS` | `32` | Parallel API requests during eval |

For `robust_eval` only: an absolute local path to `prompt_set_config.yaml` is required (passed to the skill at invocation time).

## Invoking the skill

Open a Claude Code session and paste (see `user_prompt` for the copy-paste template):

```
Use the Perlmutter NeMo eval skill. My env file is /abs/path/my_eval_env_vars,
my benchmark is gsm8k, and my model is <MODEL_NAME>. Do not print secrets.
```

For `robust_eval`, add: `My job type is robust_eval and my prompt_set_config is /abs/path/prompt_set_config.yaml.`

All paths must be **absolute**. The model must appear in `config/supported_models.txt`.

## Output

Results land in a timestamped run directory (location controlled by `PERLMUTTER_AGENT_RUNS_DIR`, defaulting to `.perlmutter-nemo-generate-runs/` in the CWD):

```
<run-id>/
  manifest.json                          # run metadata and status
  perlmutter.yaml                        # rendered cluster config
  run.sh                                 # rendered ns eval script
  logs/
    submission.log                       # full ns eval submission output
  results/
    eval-output/
      eval-results/<benchmark>/
        output.jsonl                     # per-sample predictions
        output.jsonl.done                # written when inference completes
        metrics.json                     # pass@1 scores (written last)
      eval-logs/                         # Slurm sbatch and srun logs
```

For `robust_eval` the `eval-output/` tree also contains per-prompt-config subdirectories and a `summarize_robustness/` aggregation directory.

## Benchmark data

Benchmark data is pre-bundled in the NeMo-Skills repo at `$NEMO_SKILLS_REPO_DIR/nemo_skills/dataset/<benchmark>/`. The skill stages these files to the remote workspace via SCP before submission — no separate `ns prepare_data` Slurm job is needed.

## Shared infrastructure

This skill shares `scripts/common.sh`, SSH helpers, image build scripts, `submit_run.sh`, and cluster config templates with `perlmutter-nemo-generate` via symlinks. The same managed virtualenv is reused if both skills point to the same `NEMO_SKILLS_REPO_DIR`.
