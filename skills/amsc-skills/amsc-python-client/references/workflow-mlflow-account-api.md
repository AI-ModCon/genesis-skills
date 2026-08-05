# Workflow, MLflow & Account API Reference

## Workflow Client (`client.workflow`)

### Templates

```python
# List all templates
templates = client.workflow.templates.list()

# Filter by tags
templates = client.workflow.templates.list(tags=["ml", "training"])

# Get specific template
template = client.workflow.templates.get("template-id")
```

### Runs

```python
# List runs (optional status filter)
from amsc_api_autogen.models import WorkflowRunStatus
runs = client.workflow.runs.list(status=WorkflowRunStatus.RUNNING)

# Create run
run = client.workflow.runs.create(run_body)

# Get run details
run = client.workflow.runs.get("run-id")

# Cancel run
client.workflow.runs.cancel("run-id")

# Get outputs
outputs = client.workflow.runs.get_outputs("run-id")
```

### Run Monitoring

```python
monitor = client.workflow.runs.monitor("run-id", poll_interval=5.0)
final_run = monitor.wait(timeout=300)  # blocks until terminal
```

### API Endpoints

| Operation | Endpoint |
|-----------|----------|
| List templates | `GET /workflow/templates` |
| Get template | `GET /workflow/templates/{id}` |
| List runs | `GET /workflow/runs` |
| Create run | `POST /workflow/runs` |
| Get run | `GET /workflow/runs/{id}` |
| Cancel run | `DELETE /workflow/runs/{id}` |
| Run outputs | `GET /workflow/runs/{id}/outputs` |

---

## MLflow Client (`client.mlflow`)

Proxied through AmSC gateway at `/mlflow/*` endpoints. Uses `PassthroughTransport` (httpx).

### Experiments

```python
# Create experiment
result = client.mlflow.experiments.create("my-experiment")

# Get experiment
exp = client.mlflow.experiments.get("experiment-id")
```

### Runs

```python
# Create run
run = client.mlflow.runs.create("experiment-id", run_name="run-1")

# Log metrics and params
client.mlflow.runs.log_metric("run-id", key="rmse", value=0.89, step=1)
client.mlflow.runs.log_param("run-id", key="lr", value="0.01")
```

### Registered Models

```python
# Create model
model = client.mlflow.models.create("my-model")

# Create model version
version = client.mlflow.models.create_version("my-model", source="s3://...")
```

---

## Account Client (`client.account`)

### Capabilities

```python
capabilities = client.account.capabilities.list()
```

### Projects

```python
projects = client.account.projects.list()
```

### Allocations

```python
allocations = client.account.projects.list_allocations("project-id")
```

### API Endpoints

| Operation | Endpoint |
|-----------|----------|
| Capabilities | `GET /account/capabilities` |
| Projects | `GET /account/projects` |
| Allocations | `GET /account/projects/{id}/allocations` |
