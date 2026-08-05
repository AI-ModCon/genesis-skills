---
name: "perlmutter-nemo-eval"
description: "Use when the user wants to run API-backed NeMo-Skills benchmark evaluation (ns eval or ns robust_eval) on NERSC Perlmutter. Requires an absolute env file, a benchmark name, a model, and for robust_eval an absolute local prompt_set_config.yaml path."
---

# Perlmutter NeMo Eval

Use this skill for benchmark evaluation jobs only:
- `ns eval` (standard benchmark, single prompt config)
- `ns robust_eval` (prompt-robustness evaluation across multiple prompt configs)
- `server_type=openai`
- Perlmutter `executor: slurm`
- Perlmutter `runtime: podman-hpc`
- external OpenAI-compatible endpoint

Do not use this skill for `ns generate`, sidecars, self-hosted vLLM, or multi-component jobs.
For raw generation use the sibling `perlmutter-nemo-generate` skill.

## Inputs

The user must provide:
- an absolute local env file path
- a benchmark name (e.g. `gsm8k`, `gpqa`, `human-eval`)
- a supported `model`
- for `robust_eval` only: an absolute local `prompt_set_config.yaml` path

Supported models live in [config/supported_models.txt](./config/supported_models.txt).

## Env var contract

Require the same core variables as the generate skill, plus:

- `BENCHMARK` — benchmark name passed to `ns eval` (e.g. `gsm8k`); also used to locate the pre-bundled data at `$NEMO_SKILLS_REPO_DIR/nemo_skills/dataset/$BENCHMARK/`

Optional vars (with defaults):
- `JOB_TYPE` default `eval` — `eval` or `robust_eval`
- `NUM_SAMPLES` default `0` — number of random seeds; `0` = full dataset; use e.g. `8` for robust_eval
- `MAX_CONCURRENT_REQUESTS` default `32` — parallel API requests during eval; consider `16` for robust_eval
- `NEMO_SKILLS_DATA_DIR` default `/workspace/ns-data` — container-side path where `ns prepare_data` downloads benchmark data; maps to `$REMOTE_RUN_DIR/ns-data`
- `NERSC_HOST` default `perlmutter.nersc.gov`
- `SSH_IDENTITY` defaults to `<SSH_LOGIN_IDENTITY>-cert.pub`
- `NODES` default `1`
- `NTASKS_PER_NODE` default `1`
- `DEFAULT_TIMEOUT` default `00:20:00`
- `HF_HOME_IN_WORKSPACE` default `/workspace/hf-cache`
- `REMOTE_IMAGE_BUILD_DIR` default `$HOME/ns-image-build`
- `STATUS_POLL_INTERVAL` default `30`
- `PERLMUTTER_BASE_IMAGE` default `docker.io/library/python:3.11`
- `PERLMUTTER_AGENT_RUNS_DIR` to override where local run artifacts are stored
- `PERLMUTTER_AGENT_STATE_DIR` to override where the managed local virtualenv is stored

## Source of truth

Same as the generate skill — resolve from `NEMO_SKILLS_REPO_DIR`:
- `<repo_dir>/docs/basics/perlmutter.md`
- `<repo_dir>/nemo_skills/pipeline/eval.py`
- `<repo_dir>/nemo_skills/pipeline/robust_eval.py`
- `<repo_dir>/ns-tests/quick_bench.sh`
- `<repo_dir>/ns-tests/quick_robust.sh`

## Workflow

1. Validate inputs.
   - Require absolute local paths for the env file.
   - Require `BENCHMARK` and `MODEL`.
   - If `JOB_TYPE=robust_eval`, also require an absolute local path for `prompt_set_config.yaml`.
   - Reject unsupported models with the allowlist file.

2. Validate the explicit repo path from the env file.
   - Load `NEMO_SKILLS_REPO_DIR` from the env file.
   - Reject the run if the repo path is missing, not absolute, or does not contain the required Perlmutter-enabled files.
   - Never assume a sibling `Skills/` checkout.
   - Never clone or install the repo automatically.

3. Ensure MFA-backed SSH access is live.
   - Run [scripts/ensure_sshproxy.sh](./scripts/ensure_sshproxy.sh).
   - Treat `sshproxy` as interactive and wait for the user to complete MFA.

4. Run preflight checks before every submission.
   - Run [scripts/check_remote_access.sh](./scripts/check_remote_access.sh) without `--require-image`.
   - Then run it with `--require-image`.
   - If it exits with code `3`, the target image is missing.

5. If the image is missing, build it.
   - Run [scripts/build_remote_image.sh](./scripts/build_remote_image.sh).
   - Re-run the image preflight check after build and migration.

6. Prepare the run bundle.
   - Run [scripts/prepare_run.sh](./scripts/prepare_run.sh) with `--benchmark`, `--model`, and optionally `--job-type`, `--num-samples`, `--max-concurrent-requests`, `--prompt-set-config`.
   - This renders:
     - `perlmutter.yaml`
     - `run.sh` (calls `ns eval` or `ns robust_eval`)
     - `manifest.json`

7. Stage config files.
   - Run [scripts/stage_inputs.sh](./scripts/stage_inputs.sh).
   - Creates remote eval output directories.
   - For `robust_eval` only: uploads `prompt_set_config.yaml` to the remote workspace.

8. Submit the job.
   - Run [scripts/submit_run.sh](./scripts/submit_run.sh).

9. Poll until completion.
   - Run [scripts/check_status.sh](./scripts/check_status.sh) with `--wait`.
   - Primary success signal: `metrics.json` written by the `summarize_results` Slurm job (second of two jobs submitted by `ns eval`).
   - Fallback: if that exact path is absent but `metrics.json` is found anywhere under `remote_output_dir` (maxdepth 4), treat as complete and warn.

10. Fetch outputs.
    - Run [scripts/fetch_results.sh](./scripts/fetch_results.sh).
    - Downloads the full eval output directory recursively (includes `metrics.json`, `output*.jsonl`, and for robust_eval the `summarize_robustness/` aggregation).

## Behavior constraints

- Never print the contents of the env file.
- Never echo secret values from API keys or SSH settings.
- Always keep `perlmutter.yaml` run-specific; do not edit shared checked-in templates in place.
- Always mount the run-specific remote directory to `/workspace`.
- The `run.sh` template uses `cd /tmp` before invoking `ns eval`/`ns robust_eval`. Do not change this — same CWD constraint as the generate skill applies.
- Preflight checks are mandatory on every run. Do not treat them as optional.
- `NEMO_SKILLS_DATA_DIR` defaults to `/workspace/ns-data`, which maps to `$REMOTE_RUN_DIR/ns-data` inside the container. Benchmark data (pre-bundled `*.jsonl` files from the local `NEMO_SKILLS_REPO_DIR/nemo_skills/dataset/` tree) is staged to the remote workspace via SCP during `stage_inputs.sh`, before job submission.

## Final response

The final user-facing reply must include:
- whether the job succeeded or failed
- the local `results/eval-output/` directory path
- the path to `metrics.json` (or the `summarize_robustness/` directory for robust_eval)
- the local log directory or submission log path
- the image tag used
- a short failure summary if any step failed
