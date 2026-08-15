from enum import Enum
from typing import List
import logging
from .agents import BaseAgent

logger = logging.getLogger(__name__)

class TopologyType(Enum):
    HIERARCHICAL = "hierarchical"
    MESH = "mesh"
    RING = "ring"

class BaseTopology:
    def __init__(self):
        self.agents: List[BaseAgent] = []

    def add_agent(self, agent: BaseAgent):
        self.agents.append(agent)

class HierarchicalTopology(BaseTopology):
    """A master agent coordinates a linear sequence of sub-agents."""
    def __init__(self):
        super().__init__()
        self.type = TopologyType.HIERARCHICAL

class MeshTopology(BaseTopology):
    """All agents can communicate with each other directly."""
    def __init__(self):
        super().__init__()
        self.type = TopologyType.MESH

class RingTopology(BaseTopology):
    """Each agent passes its output to the next in a ring."""
    def __init__(self):
        super().__init__()
        self.type = TopologyType.RING
