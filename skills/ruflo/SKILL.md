---
name: ruflo
description: Goal-oriented agent execution and self-optimization framework with progressive-disclosure skill sets for orchestration, planning, memory, and development analysis. Use when planning agent work, recalling agent memory, or tuning agent behavior.
---

# Ruflo Skill

Ruflo is a goal-oriented execution framework that adds planning, task
decomposition, memory, and self-optimization to the flow-nexus-swarm
agent pipeline.

## Progressive disclosure skill sets

Ruflo organizes its capabilities into skill sets, each a folder of
**SKILL.md units** (loaded on demand — read only what the task needs):

### 🧭 Orchestration & Planning
- **Swarm Orchestration** — distributed multi-agent task allocation and
  parallel agent loops → [`skills/swarm-orchestration/SKILL.md`](skills/swarm-orchestration/SKILL.md)
- **Goal Planner (GOAP)** — Goal-Oriented Action Planning with A* search
  → [`skills/goal-planner-goap/SKILL.md`](skills/goal-planner-goap/SKILL.md)
- **Skill Builder** — scaffolds new modular Claude Code Skills
  → [`skills/skill-builder/SKILL.md`](skills/skill-builder/SKILL.md)

### 🧠 Memory & Self-Learning
- **AgentDB Memory Patterns** — persistent sessions, HNSW vector
  storage, long-term recall → [`skills/agentdb-memory-patterns/SKILL.md`](skills/agentdb-memory-patterns/SKILL.md)
- **AgentDB Learning** — adaptive pattern learning, curriculum learning,
  neural optimization (SONA) → [`skills/agentdb-learning/SKILL.md`](skills/agentdb-learning/SKILL.md)

### 🔬 Development & Analysis
- **Code Analyzer** — architecture audits, security scans, complexity
  evaluation → [`skills/code-analyzer/SKILL.md`](skills/code-analyzer/SKILL.md)
- **SPARC Methodology** — spec-driven design & feature building
  → [`skills/sparc-methodology/SKILL.md`](skills/sparc-methodology/SKILL.md)

## Core modules

| Module                 | Purpose                                            |
|------------------------|----------------------------------------------------|
| `goal_engine.py`       | Goals: pending → active → completed / failed       |
| `task_planner.py`      | Fixed Collect → Parse → Store → Respond chain      |
| `goap_planner.py`      | A* search over actions (preconditions/effects)     |
| `self_optimizer.py`    | Per-agent success rates → hints in `agent_state`   |
| `memory.py`            | Sessions + HNSW/brute-force vector recall          |
| `skill_builder.py`     | Scaffold new skill units                           |
| `code_analyzer.py`     | Security / health / complexity audit               |

## Integration

Ruflo is wired into the bot through `skills/bill_gateway_skill.py`, which
combines the GoalEngine + TaskPlanner + SwarmOrchestrator into unified
Telegram message handlers. Run `/optimize` to trigger the
SelfOptimizer.

## Skill set layout

```
skills/ruflo/
├── SKILL.md                     # this index
├── goal_engine.py  task_planner.py  goap_planner.py
├── self_optimizer.py  memory.py  skill_builder.py  code_analyzer.py
└── skills/                      # progressive-disclosure units
    ├── orchestration/{swarm-orchestration, goal-planner-goap, skill-builder}/
    ├── memory/{agentdb-memory-patterns, agentdb-learning}/
    └── analysis/{code-analyzer, sparc-methodology}/
```
