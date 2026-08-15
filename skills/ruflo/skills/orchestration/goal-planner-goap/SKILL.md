---
name: goal-planner-goap
description: Builds dynamic action sequences for complex objectives using Goal-Oriented Action Planning with A* search over actions that declare preconditions and effects. Use when a goal can be reached by multiple action orderings and the cheapest valid plan should be chosen.
---

# Goal Planner (GOAP)

Part of the Ruflo **Orchestration & Planning** skill set.

## When to use
- A goal has several possible action sequences (not a fixed chain).
- You want the *cheapest* plan (costs, not just any order).
- You want planning separated from execution.

## Activation
```python
from skills.ruflo.goap_planner import Action, GoapPlanner

actions = [
    Action("collect", {"has_bill": False}, {"has_bill": True, "parsed": False}),
    Action("parse", {"has_bill": True, "parsed": False}, {"parsed": True}, cost=2),
    Action("store", {"parsed": True, "stored": False}, {"stored": True}, cost=1),
]
plan = GoapPlanner().plan(actions, start={"has_bill": False}, goal={"stored": True})
assert plan.names == ["collect", "parse", "store"]
```

## Core concepts
- **WorldState** — immutable key/value snapshot; hashing enables A* dedup.
- **Action** — `preconditions`, `effects`, `cost`, optional `run` callable.
- **Heuristic** — count of unmet goal conditions (admissible).
- **Plan** — ordered actions + total cost; `execute()` runs `run` callables.

## Details
See [REFERENCE.md](REFERENCE.md) for the A* mechanics and STRIPS
background (loaded on demand).
