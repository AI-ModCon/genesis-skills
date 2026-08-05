# Academy Communication Patterns

## Handles

Handles are proxy objects that enable transparent remote method invocation. When you have a Handle to an agent, you can call its actions as if it were a local object.

### Receiving Handles

```python
from academy.agent import Agent, action, Handle

class CoordinatorAgent(Agent):
    def __init__(self):
        super().__init__()
        self._workers: dict[str, Handle] = {}

    @action
    async def register_worker(self, name: str, worker: Handle) -> None:
        """Store a Handle for later use."""
        self._workers[name] = worker

    @action
    async def call_worker(self, name: str, task: str) -> dict:
        """Use the stored Handle to call a remote action."""
        worker = self._workers[name]
        return await worker.process(task)
```

### Handle Transparency

Handles abstract away location - the same code works whether the target agent is local or remote:

```python
# This works regardless of where analyzer_agent runs
result = await self._analyzer.analyze(data)
```

## Manager

The Manager is the runtime that launches and coordinates agents.

### Basic Setup

```python
from academy.manager import Manager
from academy.exchange import LocalExchangeFactory

async def main():
    async with await Manager.from_exchange_factory(
        factory=LocalExchangeFactory(),
    ) as manager:
        # Launch agents
        agent = await manager.launch(MyAgent)

        # Call actions
        result = await agent.do_work("task")
```

### Launching Multiple Agents

```python
async with await Manager.from_exchange_factory(
    factory=LocalExchangeFactory(),
) as manager:
    # Launch multiple agents
    coordinator = await manager.launch(CoordinatorAgent)
    worker1 = await manager.launch(WorkerAgent)
    worker2 = await manager.launch(WorkerAgent)

    # Connect them via Handles
    await coordinator.register_worker("sim", worker1)
    await coordinator.register_worker("analysis", worker2)

    # Run workflow
    result = await coordinator.run_workflow(task)
```

## Exchanges

Exchanges handle the underlying message transport between agents.

### LocalExchangeFactory

For development and testing on a single machine:

```python
from academy.exchange import LocalExchangeFactory

factory = LocalExchangeFactory()
```

### RedisExchangeFactory

For multi-machine deployment within a cluster:

```python
from academy.exchange import RedisExchangeFactory

factory = RedisExchangeFactory(
    hostname="redis.example.com",
    port=6379,
)
```

### HttpExchangeFactory

The hosted cloud exchange, for cross-site and federated deployments
(authenticates with Globus):

```python
from academy.exchange import HttpExchangeFactory

# Defaults to the Academy-hosted exchange
factory = HttpExchangeFactory(auth_method="globus")
```

Note the separation of concerns: the **exchange** moves messages between
agents; **executors** (passed to the Manager) decide where agents run. To run
agents on HPC, pass a Globus Compute `Executor` from `globus_compute_sdk` as
the Manager's `executors=` argument.

## Message Patterns

### Request-Response

The default pattern - call an action and await the result:

```python
result = await agent.process(data)
```

### Fire-and-Forget

When you don't need to wait for a response:

```python
@action
async def notify(self, event: dict) -> None:
    """Receive notification without returning data."""
    self._events.append(event)
    await self._process_event(event)
```

### Callback Pattern

Pass your Handle so the callee can respond later:

```python
@action
async def submit_job(self, job: dict, callback: Handle) -> str:
    """Accept a job and callback Handle."""
    job_id = self._queue_job(job)
    self._callbacks[job_id] = callback
    return job_id

@loop
async def process_jobs(self, shutdown: asyncio.Event) -> None:
    """Process jobs and notify via callbacks."""
    while not shutdown.is_set():
        job_id, result = await self._complete_next_job()
        callback = self._callbacks.pop(job_id)
        await callback.on_complete(job_id, result)
```

## Federation Patterns

### Cross-Site Communication

Academy enables agents to communicate across institutional boundaries:

```python
# Agent at Site A (e.g., Argonne)
class DataCollector(Agent):
    @action
    async def set_processor(self, processor: Handle) -> None:
        # processor might be at Site B (e.g., NERSC)
        self._processor = processor

    @action
    async def collect_and_process(self) -> dict:
        data = await self._collect_from_instrument()
        # Transparent call to remote site
        return await self._processor.analyze(data)
```

### Globus Authentication

Federation uses Globus Auth for secure cross-site identity. Use the hosted
HTTP exchange for messaging, and Globus Compute executors to place agents at
specific facilities:

```python
from concurrent.futures import Executor

from academy.exchange import HttpExchangeFactory
from globus_compute_sdk import Executor as GCExecutor

async with await Manager.from_exchange_factory(
    factory=HttpExchangeFactory(auth_method="globus"),
    executors={
        "polaris": GCExecutor("polaris-endpoint-uuid"),      # Argonne
        "perlmutter": GCExecutor("perlmutter-endpoint-uuid"),  # NERSC
    },
) as manager:
    agent = await manager.launch(DataProcessor, executor="polaris")
```

## Best Practices

1. **Pass Handles explicitly** - Don't rely on global state for agent references
2. **Use appropriate exchanges** - LocalExchange for dev, Redis/HTTP for production
3. **Handle network failures** - Remote calls can fail; implement retries or fallbacks
4. **Minimize message size** - Large data should be passed by reference (e.g., file paths)
5. **Design for async** - All inter-agent communication is asynchronous
6. **Consider latency** - Remote calls have network overhead; batch when possible
