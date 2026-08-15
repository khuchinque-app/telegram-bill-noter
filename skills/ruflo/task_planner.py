from dataclasses import dataclass
from typing import List, Any
import logging
import uuid

logger = logging.getLogger(__name__)

@dataclass
class Task:
    id: str
    goal_id: str
    name: str
    agent_name: str
    input_data: Any
    output_data: Any = None
    status: str = "pending"
    order: int = 0

class TaskPlanner:
    def plan(self, goal, message_data) -> List[Task]:
        tasks = []
        
        tasks.append(Task(
            id=str(uuid.uuid4()),
            goal_id=goal.id,
            name="Collect Bill",
            agent_name="BillCollectorAgent",
            input_data=message_data,
            order=1
        ))
        
        tasks.append(Task(
            id=str(uuid.uuid4()),
            goal_id=goal.id,
            name="Parse Bill",
            agent_name="BillParserAgent",
            input_data=None,
            order=2
        ))
        
        tasks.append(Task(
            id=str(uuid.uuid4()),
            goal_id=goal.id,
            name="Store Bill",
            agent_name="BillStorageAgent",
            input_data=None,
            order=3
        ))
        
        tasks.append(Task(
            id=str(uuid.uuid4()),
            goal_id=goal.id,
            name="Respond to User",
            agent_name="BillResponderAgent",
            input_data=None,
            order=4
        ))
        
        return tasks
        
    async def execute_plan(self, tasks: List[Task], orchestrator) -> None:
        current_input = None
        for task in sorted(tasks, key=lambda t: t.order):
            logger.info(f"Executing task: {task.name} with agent {task.agent_name}")
            task.status = "active"
            
            input_to_agent = task.input_data if task.order == 1 else current_input
            
            # Using orchestrator process. Assuming it has an async interface.
            # Replace with orchestrator.process if it's sync.
            result = None
            if hasattr(orchestrator, 'process_async'):
                result = await orchestrator.process_async(task.agent_name, input_to_agent)
            elif hasattr(orchestrator, 'process'):
                result = orchestrator.process(task.agent_name, input_to_agent)
                
            task.output_data = result
            task.status = "completed"
            current_input = result
