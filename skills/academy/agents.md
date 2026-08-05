# Academy Agents Reference

## Agent Class Structure

Every Academy agent inherits from the `Agent` base class:

```python
import asyncio
from academy.agent import Agent, action, loop

class MyAgent(Agent):
    def __init__(self):
        super().__init__()
        # Initialize instance state
        self._results = []

    @action
    async def do_work(self, task: str) -> dict:
        """Actions are remote-callable methods."""
        result = await self._process(task)
        self._results.append(result)
        return result

    @loop
    async def background_task(self, shutdown: asyncio.Event) -> None:
        """Loops run continuously and autonomously."""
        while not shutdown.is_set():
            await self._check_conditions()
            await asyncio.sleep(1)
```

## Actions

**Overrides must be re-decorated.** When a subclass overrides an `@action`
method (including abstract ones), the override must itself be decorated with
`@action` — otherwise the live agent raises `AttributeError: ... does not have
an action named "..."` when the action is called through a real handle.
`ProxyHandle` does NOT catch this (it calls the method directly), so test it
through a launched agent at least once.

### Basic Action Pattern

```python
@action
async def calculate(self, expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: Math expression like "2 + 2"

    Returns:
        Result as formatted string
    """
    result = eval(expression, {"__builtins__": {}}, {})
    return f"{expression} = {result}"
```

### Action with Complex Parameters

```python
@action
async def run_simulation(
    self,
    structure: dict,
    temperature: float = 300.0,
    pressure: float = 1.0,
    steps: int = 1000
) -> dict:
    """Run molecular dynamics simulation.

    Args:
        structure: Molecular structure definition
        temperature: Temperature in Kelvin
        pressure: Pressure in atmospheres
        steps: Number of simulation steps

    Returns:
        Simulation results with energy and trajectory
    """
    # Validate inputs
    if temperature <= 0:
        return {"error": "Temperature must be positive"}

    # Run simulation
    trajectory = await self._run_md(structure, temperature, pressure, steps)

    return {
        "final_energy": trajectory[-1]["energy"],
        "trajectory": trajectory,
        "converged": self._check_convergence(trajectory)
    }
```

### Action Receiving Handles

```python
from academy.handle import Handle

@action
async def register_worker(self, name: str, worker: Handle) -> None:
    """Register a worker agent for later use.

    Args:
        name: Identifier for this worker
        worker: Handle to the worker agent
    """
    self._workers[name] = worker

@action
async def delegate_task(self, worker_name: str, task: dict) -> dict:
    """Delegate work to a registered worker."""
    worker = self._workers.get(worker_name)
    if not worker:
        return {"error": f"Unknown worker: {worker_name}"}

    # Call the worker's action via its Handle
    return await worker.process(task)
```

## Loops

Every loop has the exact signature `(self, shutdown: asyncio.Event)` and must
check the shutdown event each iteration — a loop that ignores it will hang the
agent at shutdown.

### Basic Monitoring Loop

```python
@loop
async def monitor(self, shutdown: asyncio.Event) -> None:
    """Continuously monitor a data source."""
    while not shutdown.is_set():
        data = await self._collect_data()

        if self._should_trigger(data):
            await self._handle_trigger(data)

        await asyncio.sleep(self._poll_interval)
```

### Loop with State Updates

```python
@loop
async def autonomous_search(self, shutdown: asyncio.Event) -> None:
    """Autonomously search for optimal parameters."""
    while not shutdown.is_set() and not self._converged:
        # Generate next candidate
        candidate = self._suggest_next()

        # Evaluate (possibly via remote worker)
        if self._evaluator:
            result = await self._evaluator.evaluate(candidate)
        else:
            result = await self._local_evaluate(candidate)

        # Update search state
        self._update_model(candidate, result)
        self._check_convergence()
```

## Agent Lifecycle

### Initialization

```python
class ScientificAgent(Agent):
    def __init__(self, config: dict = None):
        super().__init__()
        self._config = config or {}
        self._initialized = False
        self._resources = {}

    @action
    async def initialize(self, resources: dict) -> bool:
        """One-time setup after launch."""
        self._resources = resources
        await self._load_models()
        self._initialized = True
        return True
```

### Startup and Shutdown Hooks

Use the built-in lifecycle hooks rather than custom actions (do not define an
action named `shutdown` — handles already have a real `shutdown()` method):

```python
class ScientificAgent(Agent):
    async def agent_on_startup(self) -> None:
        """Runs when the agent starts, before it serves requests.

        Do first contact with other agents here, never in __init__.
        """
        await self._load_models()

    async def agent_on_shutdown(self) -> None:
        """Runs when the agent is shutting down."""
        await self._save_state()
        await self._release_resources()
```

## Error Handling

### Return Errors as Data

Prefer returning error information over raising exceptions:

```python
@action
async def process_file(self, path: str) -> dict:
    """Process a data file."""
    try:
        data = await self._load_file(path)
        result = await self._analyze(data)
        return {"status": "success", "result": result}
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Validation Pattern

```python
@action
async def validate_and_run(self, params: dict) -> dict:
    """Validate parameters before execution."""
    # Validation
    errors = self._validate_params(params)
    if errors:
        return {"status": "validation_error", "errors": errors}

    # Execution
    result = await self._execute(params)
    return {"status": "success", "result": result}
```

## State Management

### Persistent State

```python
class StatefulAgent(Agent):
    def __init__(self):
        super().__init__()
        self._history = []
        self._model_state = None

    @action
    async def get_state(self) -> dict:
        """Return current agent state for checkpointing."""
        return {
            "history": self._history,
            "model_state": self._model_state
        }

    @action
    async def restore_state(self, state: dict) -> bool:
        """Restore agent from checkpoint."""
        self._history = state.get("history", [])
        self._model_state = state.get("model_state")
        return True
```

## Testing Agents with ProxyHandle

`ProxyHandle` wraps an agent instance in-process so tests can await its actions
directly — no manager or exchange needed. Call it exactly like a real handle:

```python
from academy.handle import ProxyHandle

async def test_simulation():
    agent = ProxyHandle(SimulationAgent())
    result = await agent.run_simulation({"temp": 300})
    assert result["status"] == "completed"
```

## Best Practices

1. **Keep actions focused** - Each action should do one thing well
2. **Use type hints** - Helps with serialization and documentation
3. **Document parameters** - Docstrings help when debugging distributed systems
4. **Return structured data** - Use dicts with consistent keys
5. **Handle errors gracefully** - Return error info rather than raising
6. **Initialize lazily** - Heavy resources can be loaded on first use
7. **Make state serializable** - Enables checkpointing and recovery
