from dataclasses import dataclass, field
from typing import List, Optional, Any
import datetime
import uuid

@dataclass
class Goal:
    id: str
    name: str
    description: str
    status: str = "pending"
    sub_tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    completed_at: Optional[str] = None

class GoalEngine:
    def __init__(self):
        self.goals = {}

    def create_goal(self, name: str, description: str) -> Goal:
        goal_id = str(uuid.uuid4())
        goal = Goal(id=goal_id, name=name, description=description)
        self.goals[goal_id] = goal
        return goal

    async def execute_goal(self, goal: Goal, planner, orchestrator, message_data: dict):
        goal.status = "active"
        tasks = planner.plan(goal, message_data)
        await planner.execute_plan(tasks, orchestrator)
        self.complete_goal(goal.id)

    def complete_goal(self, goal_id: str):
        if goal_id in self.goals:
            goal = self.goals[goal_id]
            goal.status = "completed"
            goal.completed_at = datetime.datetime.now().isoformat()
