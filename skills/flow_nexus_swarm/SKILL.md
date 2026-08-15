---
name: flow-nexus-swarm
description: Multi-agent swarm orchestrator for Telegram bill processing with SQLite shared memory
---

# Flow-Nexus-Swarm Skill

An orchestration skill that deploys, manages, and scales multi-agent swarm
topologies for complex bill capture and processing in the Telegram payment bot.

## Architecture

```
[Telegram Message]
        │
        ▼
┌──────────────────┐
│  BillCollector    │  ← Extracts text, photo, bill type, metadata
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  BillParser       │  ← Parses prices via bill_noter.price_parser
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  BillStorage      │  ← Persists to SQLite (data/swarm_memory.db)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  BillResponder    │  ← Formats ✅ reply with date, time, amount
└──────────────────┘
```

## Shared Memory (AgentDB)

SQLite-backed persistence at `data/swarm_memory.db`:

| Table        | Purpose                                    |
|--------------|--------------------------------------------|
| `bills`      | Every captured bill (text or photo)        |
| `agent_state`| Per-agent key/value hints and config       |
| `agent_log`  | Audit trail of every agent action          |

## Topology Types

| Type          | Description                                     |
|---------------|-------------------------------------------------|
| Hierarchical  | Sequential pipeline (default for bill capture)  |
| Mesh          | All agents communicate with all others           |
| Ring          | Each agent passes output to next in a ring       |

## Bill Type Detection

Automatically detects: `grab`, `foodpanda`, `shopee`, `lazada`, `gojek`, `lineman`, or `local_bill`.

## Usage

The skill is loaded automatically by `bill_noter/bot.py` at startup.
Use `/swarm` to check agent stats and `/optimize` to run self-optimization.
