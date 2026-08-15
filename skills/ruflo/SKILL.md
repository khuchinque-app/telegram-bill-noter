---
name: ruflo
description: Goal-oriented agent execution and self-optimization framework
---

# Ruflo Skill

A goal-oriented execution framework that adds planning, task decomposition,
and self-optimization to the flow-nexus-swarm agent pipeline.

## Components

### GoalEngine
- Creates and tracks high-level goals
- Primary goal: *"Capture and confirm every bill that arrives in the Telegram chat"*
- Status tracking: pending → active → completed / failed

### TaskPlanner
- Decomposes goals into ordered tasks mapped to specific agents
- Task chain: Collect → Parse → Store → Respond
- Executes tasks sequentially through the orchestrator

### SelfOptimizer
- Reads real agent_log statistics from SharedMemory
- Calculates per-agent success rates
- Stores optimization hints in agent_state
- Flags agents below threshold for attention
- Run via `/optimize` command in the bot

## Integration

Ruflo is wired into the bot through `skills/bill_gateway_skill.py`, which
combines the GoalEngine + TaskPlanner + SwarmOrchestrator into unified
Telegram message handlers.
