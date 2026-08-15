"""Goal-Oriented Action Planning (GOAP) with A* search.

GOAP is a planning technique (canonically demonstrated by the AI of
F.E.A.R.) where an agent, given a current *world state* and a desired
*goal state*, searches a graph of actions — each with preconditions and
effects — to find the cheapest sequence that reaches the goal.

This module implements the planner. The concrete action set lives in the
goal-planner-goap skill unit (`skills/ruflo/skills/goal-planner-goap/`).

Example
-------
    from skills.ruflo.goap_planner import GoapPlanner, Action, WorldState

    actions = [
        Action("collect", {"has_bill": False}, {"has_bill": True, "parsed": False}, cost=1),
        Action("parse",   {"has_bill": True, "parsed": False}, {"parsed": True}, cost=2),
        Action("store",   {"parsed": True, "stored": False}, {"stored": True}, cost=1),
    ]
    plan = GoapPlanner().plan(actions, start={"has_bill": False}, goal={"stored": True})
    # plan == ["collect", "parse", "store"]
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

log = logging.getLogger("ruflo.goap")


@dataclass(frozen=True)
class WorldState:
    """An immutable snapshot of agent world-state key/values.

    Immutability is what makes A* over states safe: the same state can
    be reached via different paths and deduplicated in the visited set.
    """

    values: Dict[str, Any] = field(default_factory=dict)

    def _matches(self, key: str, expected: Any) -> bool:
        """GOAP convention: an absent key reads as falsy.

        A condition like {"stored": False} matches a state that has no
        "stored" key at all — absence means False/0/""/None. This keeps
        action authoring ergonomic: you only ever set True-ish facts.
        """
        actual = self.values.get(key)
        if actual is None:
            return not expected
        return actual == expected

    def satisfies(self, condition: Dict[str, Any]) -> bool:
        """True if every key in `condition` matches this state."""
        return all(self._matches(k, v) for k, v in condition.items())

    def apply(self, effects: Dict[str, Any]) -> "WorldState":
        """Return a new state with `effects` merged over this one."""
        merged = dict(self.values)
        merged.update(effects)
        return WorldState(merged)

    def unmet(self, goal: Dict[str, Any]) -> int:
        """Number of goal conditions not yet satisfied (A* heuristic).

        Uses the same absent-key-is-falsy rule as `satisfies` so the
        heuristic stays admissible and consistent with goal checks.
        """
        return sum(1 for k, v in goal.items() if not self._matches(k, v))

    def __hash__(self) -> int:
        return hash(frozenset(sorted(self.values.items(), key=lambda kv: kv[0])))


@dataclass
class Action:
    """A single planner action.

    run is optional: when provided it is executed by the runner after
    planning; planning itself only reasons about preconditions/effects.
    """

    name: str
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    run: Optional[Callable[[Dict[str, Any]], Any]] = None

    def applicable(self, state: WorldState) -> bool:
        return state.satisfies(self.preconditions)


@dataclass
class Plan:
    actions: List[Action] = field(default_factory=list)
    cost: float = 0.0

    @property
    def names(self) -> List[str]:
        return [a.name for a in self.actions]


class GoapPlanner:
    """A* search that returns the cheapest action sequence to a goal."""

    def plan(
        self,
        actions: Sequence[Action],
        start: Dict[str, Any],
        goal: Dict[str, Any],
        max_depth: int = 32,
    ) -> Optional[Plan]:
        """Find the cheapest sequence of actions from `start` to `goal`.

        Returns None when no sequence exists within `max_depth` steps.
        """
        if not goal:
            return Plan()

        start_state = WorldState(start)
        if start_state.satisfies(goal):
            return Plan(cost=0.0)

        # Priority queue entries: (f_score, tiebreak, state, path)
        tiebreak = 0
        frontier: List[tuple] = []
        heapq.heappush(
            frontier,
            (start_state.unmet(goal), tiebreak, start_state, tuple(), 0.0),
        )
        tiebreak += 1

        visited: Dict[WorldState, float] = {start_state: 0.0}

        while frontier:
            f, _, state, path, g = heapq.heappop(frontier)
            if g > visited.get(state, float("inf")):
                continue  # stale entry — a cheaper path exists

            # A* optimality: return only when the goal is POPPED with the
            # smallest f (h(goal)=0, so f==g is minimal at this point).
            if state.satisfies(goal):
                log.info(
                    "GOAP plan found: %s (cost=%.2f, depth=%d)",
                    [a.name for a in path], g, len(path),
                )
                return Plan(actions=list(path), cost=g)

            if len(path) >= max_depth:
                continue

            for action in actions:
                if not action.applicable(state):
                    continue
                next_state = state.apply(action.effects)
                new_path = path + (action,)
                new_g = g + action.cost

                if new_g >= visited.get(next_state, float("inf")):
                    continue
                visited[next_state] = new_g

                h = next_state.unmet(goal)
                heapq.heappush(
                    frontier,
                    (new_g + h, tiebreak, next_state, new_path, new_g),
                )
                tiebreak += 1

        log.info("GOAP no plan found from %s to %s", start, goal)
        return None

    def execute(
        self,
        plan: Plan,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Run each action's `run` callable in order, feeding a shared context."""
        ctx: Dict[str, Any] = dict(context or {})
        results: List[Any] = []
        for action in plan.actions:
            if action.run is None:
                continue
            try:
                results.append(action.run(ctx))
            except Exception as exc:  # keep pipeline resilient
                log.error("GOAP action %s failed: %s", action.name, exc)
                results.append(exc)
        return results
