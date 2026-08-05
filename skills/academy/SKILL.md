---
name: academy
description: Academy agent framework for distributed scientific computing. Use when building agents with @action decorators, configuring exchanges and managers, creating HPC integrations, or designing multi-agent scientific workflows.
---

# Academy Agent Framework

Academy is middleware for deploying autonomous agents across federated research ecosystems, including HPC systems, experimental facilities, and data repositories.

## When to Use Academy

Use Academy when you need:
- **Distributed execution** across multiple machines or HPC systems
- **Stateful agents** that maintain state across interactions
- **Inter-agent coordination** via message passing
- **Federation** across institutional boundaries (via Globus)
- **Long-running autonomous workflows** for scientific discovery

## Core Concepts

### Agents
Python classes inheriting from `Agent` with `@action`-decorated async methods:

```python
from academy.agent import Agent, action

class SimulationAgent(Agent):
    @action
    async def run_simulation(self, parameters: dict) -> dict:
        # Perform computation
        return {"energy": -127.5, "status": "completed"}
```

### Actions
Methods decorated with `@action` can be invoked remotely by users or other agents. They must be `async` and can accept/return serializable data.

### Loops
Methods decorated with `@loop` run autonomously and continuously. A loop
receives a `shutdown` event and must check it every iteration (and yield
control, e.g. by sleeping), or the agent will hang at shutdown:

```python
import asyncio
from academy.agent import Agent, action, loop

class MonitorAgent(Agent):
    @loop
    async def monitor(self, shutdown: asyncio.Event) -> None:
        while not shutdown.is_set():
            data = await self.collect_data()
            if self.should_alert(data):
                await self._coordinator.notify(data)
            await asyncio.sleep(1)
```

### Handles
Proxy objects for inter-agent communication. When you receive a Handle, you can call its actions as if it were local:

```python
@action
async def set_analyzer(self, analyzer: Handle) -> None:
    self._analyzer = analyzer

@action
async def process(self, data: dict) -> dict:
    # Call remote agent's action
    return await self._analyzer.analyze(data)
```

### Manager and Exchange
The Manager launches and coordinates agents. The Exchange handles message transport:

```python
from concurrent.futures import ThreadPoolExecutor
from academy.manager import Manager
from academy.exchange import LocalExchangeFactory
from academy.logging.recommended import recommended_logging

async with await Manager.from_exchange_factory(
    factory=LocalExchangeFactory(),  # Local dev
    executors=ThreadPoolExecutor(),  # Where agents run (default: event loop)
    log_config=recommended_logging(),
) as manager:
    agent = await manager.launch(SimulationAgent)
    result = await agent.run_simulation({"temp": 300})
```

## Installation

```bash
pip install "academy-py==0.5.*"
```

## Additional Resources

- For detailed agent patterns, see [agents.md](agents.md)
- For communication patterns, see [communication.md](communication.md)
- For orchestration patterns, see [patterns.md](patterns.md)
- For scientific workflow examples, see [examples.md](examples.md)

## Quick Reference

| Decorator | Purpose |
|-----------|---------|
| `@action` | Remote-callable method |
| `@loop` | Autonomous continuous execution |

| Exchange Type | Use Case |
|---------------|----------|
| `LocalExchangeFactory` | Single-process development/testing |
| `RedisExchangeFactory` | Multi-machine deployment via a Redis server |
| `HttpExchangeFactory` | Hosted cloud exchange; cross-site/federated (Globus auth) |

To run agents on HPC, pass a Globus Compute `Executor` to the Manager's
`executors=` — the exchange moves messages; executors decide where agents run.

## Links

- Documentation: https://docs.academy-agents.org/stable/
- Tutorial: https://docs.academy-agents.org/stable/guides/tutorial/
- Agents4Science: https://agents4science.github.io/Capabilities/
