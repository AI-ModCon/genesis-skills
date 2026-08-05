# Academy Orchestration Patterns

## Pipeline Pattern

Sequential data flow through a chain of agents. Each agent processes data and passes it to the next.

```python
class PipelineAgent(Agent):
    def __init__(self):
        super().__init__()
        self._next: Handle = None

    @action
    async def set_next(self, next_agent: Handle) -> None:
        """Set the next agent in the pipeline."""
        self._next = next_agent

    @action
    async def process(self, data: dict) -> dict:
        """Process and forward to next stage."""
        result = await self._do_processing(data)

        if self._next:
            return await self._next.process(result)
        return result
```

### Building the Pipeline

```python
async def build_pipeline(manager):
    # Create stages
    ingest = await manager.launch(IngestAgent)
    validate = await manager.launch(ValidationAgent)
    transform = await manager.launch(TransformAgent)
    store = await manager.launch(StorageAgent)

    # Connect pipeline
    await ingest.set_next(validate)
    await validate.set_next(transform)
    await transform.set_next(store)

    return ingest  # Return head of pipeline
```

## Hub-and-Spoke Pattern

Central coordinator that orchestrates multiple specialized workers.

```python
class HubAgent(Agent):
    def __init__(self):
        super().__init__()
        self._workers: dict[str, Handle] = {}

    @action
    async def register_worker(self, role: str, worker: Handle) -> None:
        """Register a specialized worker."""
        self._workers[role] = worker

    @action
    async def orchestrate(self, task: dict) -> dict:
        """Coordinate workers to complete a task."""
        # Step 1: Scout analyzes the task
        opportunities = await self._workers["scout"].survey(task)

        # Step 2: Planner creates execution plan
        plan = await self._workers["planner"].design(opportunities)

        # Step 3: Operator executes the plan
        results = await self._workers["operator"].execute(plan)

        # Step 4: Analyst interprets results
        analysis = await self._workers["analyst"].interpret(results)

        return analysis
```

### Hub Setup

```python
async def setup_hub(manager):
    hub = await manager.launch(HubAgent)

    # Launch specialized workers
    scout = await manager.launch(ScoutAgent)
    planner = await manager.launch(PlannerAgent)
    operator = await manager.launch(OperatorAgent)
    analyst = await manager.launch(AnalystAgent)

    # Register with hub
    await hub.register_worker("scout", scout)
    await hub.register_worker("planner", planner)
    await hub.register_worker("operator", operator)
    await hub.register_worker("analyst", analyst)

    return hub
```

## Coordinator + Tool Provider Pattern

One agent provides tools/services, another coordinates their use.

```python
class ToolProviderAgent(Agent):
    """Provides computational tools as actions."""

    @action
    async def run_dft(self, structure: dict) -> dict:
        """Run DFT calculation."""
        return await self._execute_dft(structure)

    @action
    async def run_md(self, structure: dict, params: dict) -> dict:
        """Run molecular dynamics."""
        return await self._execute_md(structure, params)


class CoordinatorAgent(Agent):
    """Orchestrates tool usage."""

    @action
    async def register_tools(self, provider: Handle) -> None:
        self._tools = provider

    @action
    async def run_workflow(self, structure: dict) -> dict:
        # Use tools as needed
        optimized = await self._tools.run_dft(structure)
        dynamics = await self._tools.run_md(optimized, {"steps": 1000})
        return {"optimized": optimized, "trajectory": dynamics}
```

## Pool Pattern

Distribute work across a pool of identical workers.

```python
class PoolCoordinator(Agent):
    def __init__(self):
        super().__init__()
        self._workers: list[Handle] = []
        self._next_worker = 0

    @action
    async def add_worker(self, worker: Handle) -> int:
        """Add a worker to the pool."""
        self._workers.append(worker)
        return len(self._workers)

    @action
    async def submit(self, task: dict) -> dict:
        """Submit task to next available worker (round-robin)."""
        worker = self._workers[self._next_worker]
        self._next_worker = (self._next_worker + 1) % len(self._workers)
        return await worker.process(task)

    @action
    async def map(self, tasks: list[dict]) -> list[dict]:
        """Distribute tasks across all workers."""
        import asyncio

        # Assign tasks round-robin
        assignments = [[] for _ in self._workers]
        for i, task in enumerate(tasks):
            assignments[i % len(self._workers)].append(task)

        # Execute in parallel
        async def run_batch(worker, batch):
            return [await worker.process(t) for t in batch]

        results = await asyncio.gather(*[
            run_batch(w, batch)
            for w, batch in zip(self._workers, assignments)
        ])

        # Flatten results
        return [r for batch in results for r in batch]
```

## Publish-Subscribe Pattern

Agents subscribe to events and receive notifications.

```python
class EventBroker(Agent):
    def __init__(self):
        super().__init__()
        self._subscribers: dict[str, list[Handle]] = {}

    @action
    async def subscribe(self, topic: str, subscriber: Handle) -> None:
        """Subscribe to a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(subscriber)

    @action
    async def publish(self, topic: str, event: dict) -> int:
        """Publish event to all subscribers."""
        subscribers = self._subscribers.get(topic, [])
        for subscriber in subscribers:
            await subscriber.on_event(topic, event)
        return len(subscribers)


class SubscriberAgent(Agent):
    @action
    async def on_event(self, topic: str, event: dict) -> None:
        """Handle received event."""
        await self._process_event(topic, event)
```

## Scatter-Gather Pattern

Distribute work, then collect and aggregate results.

```python
class ScatterGatherAgent(Agent):
    def __init__(self):
        super().__init__()
        self._workers: list[Handle] = []

    @action
    async def scatter_gather(self, tasks: list[dict]) -> dict:
        """Scatter tasks to workers, gather results."""
        import asyncio

        # Scatter: send one task to each worker
        futures = [
            worker.process(task)
            for worker, task in zip(self._workers, tasks)
        ]

        # Gather: collect all results
        results = await asyncio.gather(*futures)

        # Aggregate
        return self._aggregate(results)

    def _aggregate(self, results: list[dict]) -> dict:
        """Combine results from all workers."""
        return {
            "count": len(results),
            "results": results,
            "summary": self._summarize(results)
        }
```

## Supervisor Pattern

Monitor and restart failed workers.

```python
class SupervisorAgent(Agent):
    def __init__(self):
        super().__init__()
        self._workers: dict[str, Handle] = {}
        self._worker_classes: dict[str, type] = {}

    @action
    async def supervise(self, name: str, worker: Handle, worker_class: type) -> None:
        """Register a worker for supervision."""
        self._workers[name] = worker
        self._worker_classes[name] = worker_class

    @loop
    async def health_check(self, shutdown: asyncio.Event) -> None:
        """Monitor worker health."""
        while not shutdown.is_set():
            for name, worker in list(self._workers.items()):
                try:
                    await asyncio.wait_for(worker.ping(), timeout=5.0)
                except (asyncio.TimeoutError, Exception):
                    # Worker failed, restart it
                    await self._restart_worker(name)
            await asyncio.sleep(10)

    async def _restart_worker(self, name: str) -> None:
        """Restart a failed worker."""
        worker_class = self._worker_classes[name]
        new_worker = await self.agent_launch_alongside(worker_class)
        self._workers[name] = new_worker
```

## Choosing a Pattern

| Pattern | Use When |
|---------|----------|
| **Pipeline** | Data flows through sequential transformations |
| **Hub-and-Spoke** | Central coordination of specialized workers |
| **Coordinator + Tools** | Separating tool execution from orchestration logic |
| **Pool** | Parallelizing identical work across workers |
| **Pub-Sub** | Decoupled event-driven communication |
| **Scatter-Gather** | Parallel execution with result aggregation |
| **Supervisor** | Fault tolerance for long-running systems |
