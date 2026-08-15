"""Swarm Orchestrator — routes messages through the agent pipeline in Hunger Mode.

Pipeline:
  BillCollector → BillParser → BillStorage → BillResponder

Equipped with animated progress bar indicators for realistic Telegram processing.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .agents import (
    BaseAgent,
    BillCollectorAgent,
    BillParserAgent,
    BillResponderAgent,
    BillStorageAgent,
)
from .shared_memory import AgentDB
from .topology import HierarchicalTopology

log = logging.getLogger("swarm.orchestrator")


class SwarmOrchestrator:
    """Manages the Hunger Bill processing pipeline with real-time progress simulation."""

    def __init__(self, db: Optional[AgentDB] = None) -> None:
        self.db = db or AgentDB()
        self.topology = HierarchicalTopology()

        self.collector = BillCollectorAgent(self.db)
        self.parser = BillParserAgent(self.db)
        self.storage = BillStorageAgent(self.db)
        self.responder = BillResponderAgent(self.db)

        for agent in (self.collector, self.parser, self.storage, self.responder):
            self.topology.add_agent(agent)

        log.info("Hunger SwarmOrchestrator ready — %d agents", len(self.topology.agents))

    async def process_message(
        self,
        update: Any,
        context: Any,
        image_path: str = "",
        progress_msg: Any = None,
    ) -> Dict[str, Any]:
        """Run message through the Hunger Swarm pipeline with animated loading stages."""
        log.info("HUNGER ORCHESTRATOR starting pipeline (image=%s)", image_path)

        data: Dict[str, Any] = {
            "update": update,
            "context": context,
            "image_path": image_path,
        }

        try:
            # ── 1. Collect (25%) ──
            if progress_msg:
                try:
                    await progress_msg.edit_text(
                        "⚡ *[■■□□□□□□□□] 20%* — `[Swarm: BillCollector]` Ingesting data & OCR scanning...",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            data = await self.collector.process(data)

            if not data.get("text") and not data.get("has_photo") and not data.get("combined_text"):
                log.info("HUNGER ORCHESTRATOR skip — empty message")
                return {"response": "", "skipped": True}

            # ── 2. Parse (50%) ──
            if progress_msg:
                try:
                    await progress_msg.edit_text(
                        "🔍 *[■■■■■□□□□□] 50%* — `[Swarm: BillParser]` Extracting prices, items & currency...",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            data = await self.parser.process(data)

            # If plain conversation with no numbers and not a photo, let conversational handler take over
            if not data.get("parsed") and not data.get("has_photo"):
                log.info("HUNGER ORCHESTRATOR skip — no price detected")
                return {"response": "", "skipped": True}

            # ── 3. Store (80%) ──
            if progress_msg:
                try:
                    await progress_msg.edit_text(
                        "💾 *[■■■■■■■■□□] 80%* — `[Swarm: BillStorage]` Saving to SQLite AgentDB...",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            data = await self.storage.process(data)

            # ── 4. Respond (100%) ──
            if progress_msg:
                try:
                    await progress_msg.edit_text(
                        "✨ *[■■■■■■■■■■] 100%* — `[Swarm: BillResponder]` Finalizing confirmation...",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            data = await self.responder.process(data)
            log.info("HUNGER ORCHESTRATOR complete — bill_id=%s", data.get("bill_id"))
            return data

        except Exception as exc:
            log.error("HUNGER ORCHESTRATOR error: %s", exc, exc_info=True)
            self.db.log_action("orchestrator", "pipeline_error", "", str(exc), success=False, error=str(exc))
            return {"response": f"⚠️ Swarm Processing Error: {exc}", "error": True}
