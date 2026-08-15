# Swarm Orchestration — Reference

## Contents
- Topology types
- Agent contract
- Parallel agent loops
- Failure handling

## Topology types
| Type          | Routing                                   | Use when                    |
|---------------|-------------------------------------------|-----------------------------|
| Hierarchical  | linear pipeline, master coordinates       | default bill capture        |
| Mesh          | every agent talks to every other          | high fan-out / fan-in       |
| Ring          | each agent passes output to next, wraps   | streaming transformations   |

## Agent contract
Every agent subclasses `BaseAgent` and implements:

```python
async def process(self, data: dict) -> dict:
    ...
    return {**data, "new_key": value}
```

Agents are **pure-ish**: they add keys to the shared `data` dict and log
via `self._log(action, inp, out, success, error)`.

## Parallel agent loops
For fan-out workloads, run independent agents concurrently:

```python
import asyncio
results = await asyncio.gather(
    *(agent.process(data) for agent in agents)
)
```

Merge results back into one dict before the next stage. Only parallelize
agents with no data dependency.

## Failure handling
- `SwarmOrchestrator.process_message` wraps the pipeline in try/except
  and logs `orchestrator/pipeline_error` into `agent_log`.
- An agent that throws must not kill the loop: catch per-agent, log with
  `success=False`, and continue with the data it already produced.
