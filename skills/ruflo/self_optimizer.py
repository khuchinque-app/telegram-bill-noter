"""Ruflo Self-Optimizer — learns from prior agent runs.

Reads real statistics from the AgentDB agent_log table, calculates
success rates, and stores optimization hints back into agent_state.
"""

import logging
from typing import Dict, Any

from skills.flow_nexus_swarm.shared_memory import AgentDB

log = logging.getLogger("ruflo.optimizer")


class SelfOptimizer:
    """Analyzes agent performance history and adjusts behavior hints."""

    def __init__(self, db: AgentDB) -> None:
        self.db = db

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Return real stats from the agent_log table."""
        return self.db.get_agent_stats()

    def optimize(self) -> str:
        """Run optimization — analyze past runs, update agent hints.

        Returns a human-readable report.
        """
        stats = self.get_stats()
        if not stats:
            log.info("No agent activity to optimize.")
            return "No agent activity recorded yet. Send some bills first!"

        lines = []
        for agent_id, s in stats.items():
            rate = s["success_rate"]
            runs = s["runs"]

            if rate < 0.7:
                hint = "needs_attention"
                action = f"⚠️ *{agent_id}*: {rate*100:.1f}% — flagged for review"
            elif rate < 0.9:
                hint = "monitor"
                action = f"🟡 *{agent_id}*: {rate*100:.1f}% — monitoring"
            else:
                hint = "optimal"
                action = f"🟢 *{agent_id}*: {rate*100:.1f}% — optimal"

            # Store the hint in agent_state for future reference
            self.db.set_agent_state(agent_id, "optimization_hint", hint)
            self.db.set_agent_state(agent_id, "total_runs", runs)
            self.db.set_agent_state(agent_id, "success_rate", rate)

            lines.append(action)
            log.info("OPTIMIZE %s: hint=%s rate=%.2f runs=%d",
                     agent_id, hint, rate, runs)

        return "\n".join(lines)
