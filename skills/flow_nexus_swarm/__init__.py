"""flow-nexus-swarm: multi-agent orchestration skill for bill processing."""

from .orchestrator import SwarmOrchestrator
from .shared_memory import AgentDB
from .agents import (
    BaseAgent,
    BillCollectorAgent,
    BillParserAgent,
    BillStorageAgent,
    BillResponderAgent,
)
from .topology import TopologyType, HierarchicalTopology, MeshTopology, RingTopology

skill_info = {
    "name": "flow-nexus-swarm",
    "version": "1.0.0",
    "description": "Multi-agent swarm orchestrator for bill processing",
    "entry_point": "orchestrator:SwarmOrchestrator",
}

__all__ = [
    "skill_info",
    "SwarmOrchestrator",
    "AgentDB",
    "BaseAgent",
    "BillCollectorAgent",
    "BillParserAgent",
    "BillStorageAgent",
    "BillResponderAgent",
    "TopologyType",
    "HierarchicalTopology",
    "MeshTopology",
    "RingTopology",
]
