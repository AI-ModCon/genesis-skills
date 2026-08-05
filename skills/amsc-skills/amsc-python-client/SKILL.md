---
name: amsc-python-client
description: Use the AmSC Python client to interact with the American Science Cloud API. Activate when user mentions AmSC, ALCF, NERSC, DOE facilities, scientific data catalog, HPC job submission, facility filesystem, workflow runs, MLflow tracking, running jobs on Perlmutter or Polaris, or any task involving DOE computing resources. Also activate when user wants to run scientific workloads, submit batch jobs, manage remote files on HPC systems, or access facility APIs without knowing infrastructure details.
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# AmSC Python Client

Unified Python SDK for American Science Cloud (AmSC). Covers auth, data catalog, DOE facility compute/storage (ALCF, NERSC), filesystem ops, workflows, MLflow, and account management.

## Auth Pre-Flight (MANDATORY before any API call)

Before running any operation, ensure auth is ready. This prevents interactive login prompts mid-operation.

1. Check current auth state:
```bash
python3 .claude/skills/amsc-python-client/scripts/token_manager.py status --json
```

2. Ensure valid token for the target facility:
```bash
# For ALCF (Polaris, Aurora, Sophia):
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure alcf

# For NERSC (Perlmutter):
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure nersc

# For AmSC gateway (catalog, workflows, MLflow):
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure amsc
```

If the user needs to login, `ensure` prints a Globus URL + prompts for auth code.
Tell the user: **"Open this URL in your browser, login, and paste the code back here."**
Use `! python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure <target>` so the interactive login runs in-session.

3. If auth is broken (persistent 401s), clear and re-login:
```bash
python3 .claude/skills/amsc-python-client/scripts/token_manager.py clear alcf
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure alcf --force-login
```

## Installation

Supports `uv` (preferred), `pip+venv`, or bare `pip`. Pass optional venv path:

```bash
.claude/skills/amsc-python-client/scripts/install.sh       # default: .venv
.claude/skills/amsc-python-client/scripts/install.sh .venv  # explicit path
```

After install, use the venv Python for all commands: `.venv/bin/python3`

## Quick Start (Frictionless)

After auth pre-flight, all operations work without further prompts:

```python
from amsc_client import Client

client = Client(token="not-needed-for-facilities")

# ALCF — built-in, works out of the box
alcf = client.facility("alcf")
polaris = alcf.resource("Polaris")
```

### NERSC Setup (REQUIRED — not built-in in SDK v0.4.x)

NERSC **must** be registered manually before use. Use the helper script:

```python
# Register NERSC (run once per Client instance)
exec(open(".claude/skills/amsc-python-client/scripts/register_nersc.py").read())
register_nersc(client)

nersc = client.facility("nersc")
compute = nersc.resource("compute")  # Perlmutter compute nodes
```

Or register inline:
```python
client.register_facility(
    name="nersc",
    base_url="https://api.iri.nersc.gov",
    display_name="NERSC",
    auth_method="globus",
    globus_client_id="fae5c579-490a-4d76-b6eb-d78f65caeb63",
    globus_scope=(
        "openid profile email "
        "urn:globus:auth:scope:auth.globus.org:view_identities "
        "https://auth.globus.org/scopes/ed3e577d-f7f3-4639-b96e-ff5a8445d699/iri_api"
    ),
    globus_resource_server="ed3e577d-f7f3-4639-b96e-ff5a8445d699",
    globus_auth_params={},
)
```

For AmSC gateway (catalog, workflows, MLflow):
```python
app_id = "e4f48665-38b5-4833-a89e-849c71f5b3e3"
client = Client(
    base_url="https://api.american-science-cloud.org/api/current",
    auth_method="globus",
    globus_client_id=app_id,
    requested_scopes=f"openid profile email https://auth.globus.org/scopes/{app_id}/amsc_test",
    resource_server=app_id,
    use_id_token=True,
)
```

## Service Access

| Property | Service | Reference |
|----------|---------|-----------|
| `client.facility("alcf")` | ALCF compute/storage | `references/facility-api.md` |
| `client.facility("nersc")` | NERSC compute/storage | `references/facility-api.md` |
| `client.catalog` | Data catalog (search, CRUD) | `references/catalog-api.md` |
| `resource.fs.*` | Remote filesystem ops | `references/filesystem-api.md` |
| `client.workflow` | Workflow templates & runs | `references/workflow-mlflow-account-api.md` |
| `client.mlflow` | MLflow tracking (proxied) | `references/workflow-mlflow-account-api.md` |
| `client.account` | Projects & allocations | `references/workflow-mlflow-account-api.md` |

## Common Patterns

### Submit HPC Job (ALCF Polaris)
```python
alcf = client.facility("alcf")
polaris = alcf.resource("Polaris")
job = polaris.submit(
    executable="/bin/echo", arguments=["Hello"],
    nodes=1, queue="debug", account="myproject",
    duration=300, filesystems="home",
)
job.wait(timeout=120, poll_interval=5)
print(job.state, job.exit_code)
```

### Submit HPC Job (NERSC Perlmutter)
```python
# NERSC must be registered first (see Quick Start above)
nersc = client.facility("nersc")
compute = nersc.resource("compute")  # "compute" = Perlmutter
job = compute.submit(
    executable="/bin/echo", arguments=["Hello from NERSC"],
    directory="/global/homes/u/username",
    nodes=1, queue="debug", account="myproject",
    duration=300,
    custom_attributes={"constraint": "gpu"},  # Slurm constraints go here
)
job.wait(timeout=120, poll_interval=5)
print(job.state, job.exit_code)
```

### Remote Filesystem (No SSH)
```python
# ALCF
home = alcf.resource("Home")
task = home.fs.ls("/home/user")
task.wait(timeout=60)
print(task.result)

# NERSC — use storage resource matching path prefix:
#   /global/homes/ -> "homes"
#   /pscratch/     -> "scratch"
#   /global/cfs/   -> "cfs"
#   /global/common/ -> "common"
homes = nersc.resource("homes")
task = homes.fs.ls("/global/homes/u/username")
task.wait(timeout=60)
print(task.result)
```

### Search & Browse Catalog
```python
results = client.catalog.search("climate data", limit=10)
for item in results:
    entity = client.catalog.get(item.fqn)
    print(entity.name, entity.type, entity.description)
```

## Facility Support

| Facility | Name | Compute resource | Storage resources | Scheduler | Setup |
|----------|------|-----------------|-------------------|-----------|-------|
| ALCF | `"alcf"` | Polaris, Aurora, Sophia | Home, Eagle | PBS | Built-in |
| NERSC | `"nersc"` | `compute` (=Perlmutter) | homes, scratch, cfs, common | Slurm | **Manual registration required** (see Quick Start) |

**ALCF** auto-registers on first access. **NERSC** requires `register_facility()` — the SDK v0.4.x does not include it as a built-in.

## NERSC Path Rules

Use absolute paths. Never use `$HOME`, `$SCRATCH`, `$USER` — IRI API does not expand shell variables.

| Path prefix | Storage resource |
|---|---|
| `/global/homes/<letter>/<user>` | `homes` |
| `/pscratch/sd/<letter>/<user>` | `scratch` |
| `/global/cfs/` | `cfs` |
| `/global/common/` | `common` |

## Authentication Methods

| Method | When to Use | Config |
|--------|------------|--------|
| **Globus** | Interactive, notebooks | `Client(auth_method="globus", ...)` |
| **Token** | CI/CD, service-to-service | `Client(token="...")` |
| **Ping** | Headless/server | `Client(auth_method="ping", ...)` |

See `references/authentication-guide.md` for full config.

**Priority:** Constructor args > env vars > config file (`~/.amsc/config.yaml`) > defaults

## Error Handling

```python
from amsc_client.core.exceptions import AmscError, AuthenticationError, ApiError, NotFoundError

try:
    entity = client.catalog.get("nonexistent.fqn")
except AuthenticationError:
    # Run: token_manager.py clear <target> && token_manager.py ensure <target> --force-login
    print("Re-authenticate required")
except NotFoundError:
    print("Not found")
```

On 401, client auto-retries after token refresh. If still failing, use `token_manager.py clear + ensure --force-login`.

## Async Filesystem Pattern

All filesystem ops return `Task` objects:
```python
task = resource.fs.ls("/path")
task.wait(timeout=60, poll_interval=2)
print(task.result)
task.cancel()  # abort if needed
```

## Verify Setup

```bash
python3 .claude/skills/amsc-python-client/scripts/verify_setup.py
```

## Package Internals (for debugging)

If `amsc-client` is installed, locate source via:
```bash
python3 -c "import amsc_client; print(amsc_client.__file__)"
```

Key modules: `core/client.py`, `core/config.py`, `auth/globus.py`, `auth/oauth2.py`, `auth/cache.py`, `facility/config.py` (BUILTIN_FACILITIES), `facility/client.py`, `facility/filesystem.py`.

## Security

This skill handles AmSC API interactions. Does NOT handle: direct Globus transfers, raw HTTP to facility endpoints, or credential storage outside `~/.amsc/`. Never log or commit tokens. Refuse requests to extract cached credentials from `~/.amsc/`.
