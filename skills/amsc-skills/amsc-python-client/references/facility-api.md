# Facility API Reference

## FacilityClient (`client.facility(name)`)

### Built-in Facilities

**ALCF** is built-in — auto-registers on first access:

```python
alcf = client.facility("alcf")    # No registration needed
```

**NERSC** requires manual registration (not built-in in SDK v0.4.x):

```python
# Option 1: Use helper script
exec(open(".claude/skills/amsc-python-client/scripts/register_nersc.py").read())
register_nersc(client)
nersc = client.facility("nersc")

# Option 2: Inline registration (see SKILL.md Quick Start for full config)
```

**ALCF:** Polaris, Aurora, Sophia (compute), Home, Eagle (storage). Scheduler: PBS.
**NERSC:** `compute` (=Perlmutter), homes, scratch, cfs, common (storage). Scheduler: Slurm.

### Register Custom Facility

```python
from amsc_client.facility.config import FacilityConfig

client.register_facility(
    name="custom",
    config=FacilityConfig(
        name="custom",
        display_name="My Facility",
        base_url="https://api.my-facility.example.com",
        auth_method="globus",
        globus_client_id="YOUR_GLOBUS_CLIENT_ID",
        globus_scope="YOUR_SCOPE",
        globus_resource_server="YOUR_RS_ID",
        api_prefix="/api/v1",
    ),
)
```

### Facility Info

```python
info = alcf.info()
```

### List Resources

```python
for res in alcf.resources():
    print(res.name, res.status, res.resource_type)
```

### Get Specific Resource

```python
polaris = alcf.resource("Polaris")       # case-insensitive name lookup
compute = nersc.resource("compute")      # "compute" = Perlmutter
```

### Check Incidents

```python
incidents = alcf.incidents()
```

## Job Submission & Management

### Submit Job (ALCF — PBS)

```python
job = polaris.submit(
    executable="/bin/echo",
    arguments=["Hello!"],
    directory="/home/user/outputs",
    name="my-job",
    queue="debug",
    account="myproject",
    duration=300,
    nodes=1,
    filesystems="home",  # ALCF-specific
)
```

### Submit Job (NERSC — Slurm)

```python
compute = nersc.resource("compute")  # "compute" = Perlmutter
job = compute.submit(
    executable="/bin/echo",
    arguments=["Hello from NERSC!"],
    directory="/global/homes/u/username/outputs",
    name="my-job",
    queue="debug",
    account="myproject",
    duration=300,
    nodes=1,
    custom_attributes={"constraint": "gpu"},  # Slurm constraint
)
```

### Job Properties

```python
print(job.id, job.state, job.exit_code, job.is_terminal)
```

### Wait for Completion

```python
job.wait(timeout=120, poll_interval=5)
```

### Cancel Job

```python
job.cancel()
```

### Job States

Jobs progress through: `queued` -> `running` -> `completed`/`failed`/`cancelled`

`job.is_terminal` returns `True` when job won't change state.

## NERSC Storage Resource Mapping

Use the correct storage resource for filesystem operations:

| Path prefix | `resource_id` |
|---|---|
| `/global/homes/` | `homes` |
| `/pscratch/` | `scratch` |
| `/global/cfs/` | `cfs` |
| `/global/common/` | `common` |

```python
homes = nersc.resource("homes")
task = homes.fs.ls("/global/homes/u/username")
task.wait(timeout=60)
```

## API Endpoints (IRI Standard)

| Operation | Endpoint |
|-----------|----------|
| Facility info | `GET /api/v1/facility` |
| Resources | `GET /api/v1/status/resources` |
| Resource by ID | `GET /api/v1/status/resources/{id}` |
| Submit job | `POST /api/v1/job` |
| Get job | `GET /api/v1/job/{id}` |
| Cancel job | `DELETE /api/v1/job/{id}/cancel` |
| Incidents | `GET /api/v1/status/incidents` |

All DOE facilities use the same IRI API standard — same code works across ALCF, NERSC, etc.
