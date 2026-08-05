# perlmutter-nemo-generate

A Claude Code agent skill that runs [`ns generate`](https://github.com/NVIDIA/NeMo-Skills) on NERSC Perlmutter using an external OpenAI-compatible API endpoint. The agent handles the full lifecycle: SSH certificate, preflight checks, optional container image build, job submission, polling, and result retrieval.

## What it does

Submits a single-node Slurm job on Perlmutter that runs `nemo_skills.inference.generate` inside a `podman-hpc` container against an external API endpoint (no GPU, no self-hosted model). The job reads an `input.jsonl` and a `prompt.yaml` from a mounted workspace and writes `output.jsonl` when done.

## Prerequisites

The local machine (the one running Claude Code) needs:

| Tool | Purpose |
|---|---|
| `python3` | Creates the managed virtualenv |
| `ssh` / `scp` | Connects to Perlmutter |
| `sshproxy` | Acquires NERSC MFA certificate |

A NERSC account with access to `pscratch` and permission to run `podman-hpc` on Perlmutter is also required.

## Setup

See the [root README](../README.md) for the one-time clone and symlink steps, and for the NeMo-Skills submodule setup.

**Create your env file**

```bash
cp perlmutter-nemo-generate/env_vars.example my_generate_env_vars
# edit my_generate_env_vars — fill in all replace-me values
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
| `REMOTE_WORKSPACE_ROOT` | Remote path for input/output files |
| `PERLMUTTER_IMAGE_NAME` | `podman-hpc` image tag to use or build |
| `NEMO_SKILLS_REPO_DIR` | Absolute local path to the Skills fork |

See `env_vars.example` for the full list including optional overrides.

**3. Prepare your inputs**

`input.jsonl` — one JSON object per line. Each object may contain any fields; the prompt template references them by name:

```json
{"prompt": "Summarize the following paper abstract: ..."}
{"prompt": "Translate this sentence to French: ..."}
```

`prompt.yaml` — a NeMo-Skills `PromptConfig`. The minimum is a `user` field with a Jinja2 template referencing your input fields:

```yaml
user: |-
  {prompt}
```

For a system prompt add:

```yaml
system: "You are a helpful assistant."
user: |-
  {prompt}
```

## Invoking the skill

Open a Claude Code session and paste (see `user_prompt` for the copy-paste template):

```
Use the Perlmutter NeMo generation skill. My env file is /abs/path/my_env_vars,
my input file is /abs/path/input.jsonl, my prompt file is /abs/path/prompt.yaml,
and my model is <MODEL_NAME>. Do not print secrets.
```

All paths must be **absolute**. The model must appear in `config/supported_models.txt`.

## Supported models

```
claude-haiku-4-5        claude-sonnet-4-5       claude-opus-4-5
claude-haiku-4-5-high   claude-sonnet-4-5-high  claude-opus-4-5-high
claude-sonnet-4-6       claude-opus-4-6         devstral-2
mistral-large-3         nemotron-nano-3         nova-pro-1 / nova-micro-1
llama-4-maverick        llama-4-scout           gpt-oss-120b / gpt-oss-20b
... (see config/supported_models.txt for the full list)
```

## Output

Results land in a timestamped run directory under `runs/` (gitignored):

```
runs/20260409-174753/
  manifest.json        # run metadata and status
  perlmutter.yaml      # rendered cluster config
  run.sh               # rendered ns generate script
  results/
    output.jsonl       # one JSON object per input line
    output.jsonl.done  # empty marker written on success
    generation-logs/   # remote stdout/stderr logs
    job-logs/          # Slurm sbatch and srun logs
```

Each line of `output.jsonl` contains the original input fields plus:

| Field | Description |
|---|---|
| `generation` | Model response text |
| `num_input_tokens` | Prompt token count |
| `num_generated_tokens` | Response token count |
| `finish_reason` | `stop`, `length`, etc. |
| `generation_time` | Wall-clock seconds for this request |

## Container image

On first run the skill checks for `PERLMUTTER_IMAGE_NAME` in your Perlmutter account. If missing it builds and migrates a minimal image using `templates/Containerfile.minimal.tmpl` — this takes several minutes but only happens once. Subsequent runs reuse the cached image.

## Local virtualenv

On first run the skill creates an isolated virtualenv under `~/.cache/perlmutter-nemo-generate/` and installs the Skills fork editable. This takes a few minutes (downloads nemo_skills dependencies) but is reused on subsequent runs as long as `pyproject.toml` and requirements files are unchanged.
