---
name: agentdb-learning
description: Handles adaptive pattern learning, curriculum learning, and neural optimization (SONA) over the agent_log. Use when tuning agent behavior from past runs, flagging underperforming agents, or scheduling progressive learning stages.
---

# AgentDB Learning

Part of the Ruflo **Memory & Self-Learning** skill set.

## When to use
- Turning accumulated `agent_log` data into behavioral hints.
- Flagging agents whose success rate is dropping.
- Running `/optimize` or scheduling periodic learning passes.

## Activation
```python
from skills.flow_nexus_swarm.shared_memory import AgentDB
from skills.ruflo.self_optimizer import SelfOptimizer

optimizer = SelfOptimizer(AgentDB("data/swarm_memory.db"))
report = optimizer.optimize()
```

## Learning modes
1. **Adaptive pattern learning** — per-agent success rates from
   `agent_log`; hints written back to `agent_state` (`optimization_hint`,
   `total_runs`, `success_rate`).
2. **Curriculum learning** — stage the difficulty of ingested material
   (text bills → simple receipts → complex multi-item receipts) so the
   pipeline learns in order.
3. **Neural optimization (SONA)** — future: neural net that predicts
   per-agent success and suggests parameter deltas; the storage
   (`agent_state`) is already in place for its inputs/outputs.

## Details
See [REFERENCE.md](REFERENCE.md) for thresholds, the hint vocabulary,
and extending the learning loop (loaded on demand).
