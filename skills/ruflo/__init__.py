"""ruflo: goal-oriented agent execution framework."""

from .goal_engine import Goal, GoalEngine
from .task_planner import Task, TaskPlanner
from .self_optimizer import SelfOptimizer

skill_info = {
    "name": "ruflo",
    "version": "1.0.0",
    "description": "Goal-oriented agent execution and self-optimization framework",
    "entry_point": "goal_engine:GoalEngine",
}

__all__ = [
    "skill_info",
    "Goal",
    "GoalEngine",
    "Task",
    "TaskPlanner",
    "SelfOptimizer",
]
