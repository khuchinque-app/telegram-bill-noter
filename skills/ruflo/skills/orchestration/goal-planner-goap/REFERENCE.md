# Goal Planner (GOAP) — Reference

## Contents
- GOAP background
- A* search mechanics
- Action authoring rules
- Example: hunger bill capture

## GOAP background
Goal-Oriented Action Planning (canonically the AI of *F.E.A.R.*, 2005)
adapts STRIPS planning: given a world state and a goal state, find a
sequence of actions whose preconditions are met in order and whose
effects reach the goal. GOAP is dynamic — replanning happens whenever
state changes — unlike fixed behavior trees.

## A* search mechanics
`GoapPlanner.plan` treats each reachable world state as a node and each
applicable action as an edge:

```
f(state) = g(state) + h(state)
g = accumulated action cost along the path
h = number of unmet goal conditions (never overestimates → admissible)
```

- Frontier = min-heap on `f`, tie-broken by insertion order.
- `visited[state]` keeps the best `g` seen; worse re-arrivals are pruned.
- Search stops when a state satisfies the goal, or the frontier empties
  (returns `None`), or `max_depth` is exceeded.
- Because `WorldState` is immutable and hashable, the same state reached
  by two paths is deduplicated — this is what keeps A* polynomial-ish in
  practice for small action sets.

## Action authoring rules
1. Only use **exact** matches in preconditions/effects (this planner
   does not do numeric ranges).
2. Keep effects minimal — an action should change only what it must.
3. Give the goal only the conditions that truly matter; extra goal keys
   add heuristic cost and can hide valid plans.
4. Attach `run` callables for execution; planning ignores them.

## Example: hunger bill capture
```python
from skills.ruflo.goap_planner import Action, GoapPlanner

actions = [
    Action("collect", {}, {"has_bill": True}, cost=1),
    Action("ocr", {"has_bill": True, "parsed": False},
           {"parsed": True, "has_photo": True}, cost=5),
    Action("parse_text", {"has_bill": True, "parsed": False},
           {"parsed": True}, cost=2),
    Action("store", {"parsed": True, "stored": False},
           {"stored": True}, cost=1),
    Action("respond", {"stored": True, "responded": False},
           {"responded": True}, cost=1),
]
plan = GoapPlanner().plan(
    actions,
    start={"has_bill": True, "parsed": False},
    goal={"stored": True, "responded": True},
)
```
The planner will prefer `parse_text` (cost 2) over `ocr` (cost 5) when
the bill is already text — exactly the dynamic behavior GOAP is for.
