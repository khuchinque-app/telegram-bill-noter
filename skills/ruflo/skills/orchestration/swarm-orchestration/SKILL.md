---
name: swarm-orchestration
description: Orchestrates distributed multi-agent task allocation and parallel agent loops over Hierarchical, Mesh, and Ring topologies. Use when routing work through the Flow-Nexus-Swarm pipeline (Collector → Parser → Storage → Responder) or when scaling agent pipelines.
---

# Swarm Orchestration

Part of the Ruflo **Orchestration & Planning** skill set.

## When to use
- Routing a Telegram message/photo through the bill pipeline.
- Choosing or switching agent topology (hierarchical / mesh / ring).
- Adding a new agent to the swarm.

## Activation
```python
from skills.flow_nexus_swarm.orchestrator import SwarmOrchestrator
from skills.flow_nexus_swarm.shared_memory import AgentDB

orch = SwarmOrchestrator(AgentDB("data/swarm_memory.db"))
data = await orch.process_message(update, context, image_path="", progress_msg=None)
```

## Core flow
1. **Collect** — ingest text/photo/OCR + metadata.
2. **Parse** — extract prices, items, currency.
3. **Store** — persist into SQLite AgentDB.
4. **Respond** — format ✅ confirmation.

Each stage reports progress; a skipped stage returns `{"skipped": True}`.

## Details
See [REFERENCE.md](REFERENCE.md) for topologies, agent contracts, and
parallel-loop patterns (loaded on demand).
