---
name: globus-compute
description: >
  Submit Python functions as jobs to NERSC Perlmutter via Globus Compute.
  Use this skill when the user wants to login to Globus, send a compute job,
  check task status, or get results from a remote HPC endpoint. Covers auth,
  endpoint configuration via Jinja2 templates, job submission with user_endpoint_config,
  and result retrieval.
compatibility: Requires globus-sdk >= 4 and globus-compute-sdk >= 2.31 (see scripts/requirements.txt); client Python should match the endpoint workers (Python 3.13 on the NERSC template endpoints) for dill serialization
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# Globus Compute (NERSC)

Submit Python functions to NERSC Perlmutter via `globus-compute-sdk` using
template-capable endpoints and `user_endpoint_config` for per-job customization.

## Setup

```bash
uv venv .venv --python 3.13
uv pip install globus-compute-sdk globus-sdk
```

Python version MUST match the endpoint workers (Perlmutter default: 3.13).
Globus Compute serializes functions as bytecode via `dill` — version mismatch = opcode errors.

## CRITICAL: Login requires interactive terminal

Auth uses browser-based OAuth. `input()` does NOT work from Claude Code.
Tell user to run login commands directly in their terminal (not via `!` prefix).

## Architecture

```
Local (gc_run.py)                    Globus Compute Service           NERSC Perlmutter
─────────────────                    ──────────────────────           ────────────────
Executor.submit(func,                Routes task to endpoint          Endpoint receives task
  user_endpoint_config={             via AMQP queue                   ↓
    NERSC_ACCOUNT: "m0000",                                          Renders config.yaml from
    OPTIONS: "#SBATCH ...",                                          user_config_template.yaml.j2
    COMMAND: "module load ..."                                       + user_endpoint_config
  })                                                                 ↓
     ↓                                                               sbatch → SLURM allocates node
polls for result ←──────────────── result returns ←───────────────── worker executes func → result
```

## Template-capable endpoint (on Perlmutter)

The endpoint uses `user_config_template.yaml.j2` with Jinja2 variables.
Users pass values at submit time via `user_endpoint_config` dict — no need to
SSH and edit config.yaml for each job.

### Endpoint setup (one-time, on Perlmutter)

```bash
ssh <username>@perlmutter.nersc.gov
module load python
pip install --user globus-compute-endpoint

globus-compute-endpoint configure perlmutter
# If prompted, run: globus-compute-endpoint migrate-to-template-capable perlmutter
```

Edit `~/.globus_compute/perlmutter/user_config_template.yaml.j2`:

```yaml
engine:
  type: GlobusComputeEngine
  worker_debug: False

  address:
    type: address_by_interface
    ifname: hsn0

  provider:
    type: SlurmProvider

    launcher:
      type: SrunLauncher
      overrides: -c 128

    scheduler_options: {{ OPTIONS }}
    account: {{ NERSC_ACCOUNT }}
    worker_init: {{ COMMAND }}
    cmd_timeout: 120

    nodes_per_block: 2
    init_blocks: 0
    min_blocks: 0
    max_blocks: 1
    walltime: 00:10:00
```

Do NOT set `partition` — Perlmutter auto-selects from the `-C` constraint in `OPTIONS`.

Start it:
```bash
globus-compute-endpoint start perlmutter
# → Endpoint UUID: <uuid>
```

### Template variables

| Variable | Example | Purpose |
|----------|---------|---------|
| `NERSC_ACCOUNT` | `m0000` | NERSC allocation (required) |
| `OPTIONS` | `#SBATCH -C cpu\n#SBATCH -q debug` | SLURM scheduler directives |
| `COMMAND` | `module load python; source activate myenv` | Worker init commands |

## Quick start

### 1. First-time login (user runs in terminal)
```bash
.venv/bin/python scripts/gc_auth.py login
```

### 2. Configure default endpoint (one-time)
```bash
.venv/bin/python scripts/gc_run.py config set-endpoint <endpoint_uuid> --name "perlmutter"
```

### 3. Run sample test (get_hostname)
```bash
.venv/bin/python scripts/gc_run.py sample \
  --account m0000 \
  --options "#SBATCH -C cpu\n#SBATCH -q debug" \
  --worker-init "module load python"
```
Expected: `SUCCESS: hostname = nid001234` (a Perlmutter compute node)

### 4. Run a custom function
```bash
.venv/bin/python scripts/gc_run.py run my_func.py \
  --account m0000 \
  --options "#SBATCH -C cpu\n#SBATCH -q debug" \
  --worker-init "module load python"
```

### 5. Check status / get result
```bash
.venv/bin/python scripts/gc_run.py status
.venv/bin/python scripts/gc_run.py result <task_id>
```

## Python API (inline use)

```python
from globus_compute_sdk import Executor

def get_hostname():
    import socket
    return socket.gethostname()

endpoint_id = "<endpoint_uuid>"
user_endpoint_config = {
    "NERSC_ACCOUNT": "m0000",
    "OPTIONS": "#SBATCH -C cpu\n#SBATCH -q debug",
    "COMMAND": "module load python",
}

with Executor(endpoint_id=endpoint_id, user_endpoint_config=user_endpoint_config) as ex:
    future = ex.submit(get_hostname)
    print(future.result())  # nid001234
```

## NERSC-specific notes

| Item | Detail |
|------|--------|
| **Account** | Always pass `NERSC_ACCOUNT` — no default, jobs fail without it |
| **No partition** | Never set `partition` — SLURM picks from `-C` constraint |
| **Network** | `ifname: hsn0` (high-speed fabric) in template, not `bond0` |
| **Python version** | Local and endpoint must match (both 3.13) — bytecode serialization |
| **GPU nodes** | Use `OPTIONS: "#SBATCH -C gpu\n#SBATCH -q debug\n#SBATCH --gpus=4"` |
| **CPU nodes** | Use `OPTIONS: "#SBATCH -C cpu\n#SBATCH -q debug"` |
| **Debug QOS** | 30 min max, 8 nodes max, high priority — good for testing |
| **Regular QOS** | 48h max — use for real workloads |

## Auth helper (`scripts/gc_auth.py`)

```bash
.venv/bin/python scripts/gc_auth.py status      # check token (non-interactive)
.venv/bin/python scripts/gc_auth.py login        # interactive login
.venv/bin/python scripts/gc_auth.py token        # print access token
.venv/bin/python scripts/gc_auth.py logout       # remove tokens
```

## Endpoint management (on Perlmutter)

```bash
globus-compute-endpoint list
globus-compute-endpoint start perlmutter
globus-compute-endpoint stop perlmutter
globus-compute-endpoint restart perlmutter
```

## Scope

Handles Globus Compute job submission, auth, endpoint config via templates.
Does NOT handle: Globus Transfer, Globus Search, other Globus services,
academy/exchange framework integration, or endpoint provisioning automation.

## Security

Never log or expose access/refresh tokens. Token files are mode 600.
Do not commit token databases or config files containing endpoint IDs to git.
