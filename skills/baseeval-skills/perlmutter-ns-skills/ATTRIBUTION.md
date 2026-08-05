# Attribution

The skills in this directory were sourced from the **perlmutter-ns-skill**
project.

**Original repository:** https://github.com/FLlorente/perlmutter-ns-skill

**Authors:**
- Fernando Llorente, Brookhaven National Laboratory (BNL)
- Eric Chagnon, Lawrence Berkeley National Laboratory (LBNL)

These skills were retrieved from the upstream repository and are included here as
retrieved, unmodified. They provide Claude Code agent workflows for running
[NeMo-Skills](https://github.com/NVIDIA/NeMo-Skills) jobs on NERSC Perlmutter
against an external OpenAI-compatible API endpoint. Each skill handles the full
lifecycle: sshproxy MFA certificate, remote preflight checks, optional container
image build, job submission, polling, and result retrieval.

> **Note:** The upstream repository references a NeMo-Skills fork as a git
> submodule (`Skills/`). That submodule is **not** vendored here; follow the
> upstream README to initialise it if you intend to run these skills. The
> `env_vars.example` files included here are templates only and contain no
> secrets.

Skills included:
- `perlmutter-nemo-eval` — Runs API-backed NeMo-Skills benchmark evaluation
  (`ns eval` / `ns robust_eval`) on NERSC Perlmutter; produces `metrics.json`.
- `perlmutter-nemo-generate` — Runs API-backed NeMo-Skills generation
  (`ns generate`) on NERSC Perlmutter over an `input.jsonl` with a `prompt.yaml`.
