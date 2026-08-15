"""ruflo: goal-oriented agent execution framework.

Exposes the core runtime modules plus the progressive-disclosure skill
sets under `skills/ruflo/skills/` (see SKILL.md).
"""

from .goal_engine import Goal, GoalEngine
from .task_planner import Task, TaskPlanner
from .goap_planner import Action, GoapPlanner, Plan, WorldState
from .self_optimizer import SelfOptimizer
from .memory import VectorMemory, bag_of_tokens

skill_info = {
    "name": "ruflo",
    "version": "1.1.0",
    "description": (
        "Goal-oriented agent execution and self-optimization framework "
        "with progressive-disclosure skill sets: orchestration & planning "
        "(swarm orchestration, GOAP, skill builder), memory & self-learning "
        "(AgentDB memory patterns, AgentDB learning), and development & "
        "analysis (code analyzer, SPARC methodology)."
    ),
    "entry_point": "goal_engine:GoalEngine",
    "skills": [
        "orchestration/swarm-orchestration",
        "orchestration/goal-planner-goap",
        "orchestration/skill-builder",
        "memory/agentdb-memory-patterns",
        "memory/agentdb-learning",
        "analysis/code-analyzer",
        "analysis/sparc-methodology",
    ],
}

__all__ = [
    "skill_info",
    "Goal",
    "GoalEngine",
    "Task",
    "TaskPlanner",
    "Action",
    "GoapPlanner",
    "Plan",
    "WorldState",
    "SelfOptimizer",
    "VectorMemory",
    "bag_of_tokens",
]


def __getattr__(name: str):
    """Lazy import CLI-tool modules (skill_builder, code_analyzer).

    Keeps the bot's startup imports lean and avoids the runpy
    "found in sys.modules" warning when running `python -m skills.ruflo.x`.
    """
    if name == "build_skill":
        from .skill_builder import build_skill
        return build_skill
    if name == "audit":
        from .code_analyzer import audit
        return audit
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
