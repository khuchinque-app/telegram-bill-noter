"""Bill Gateway Skill — Hunger Mode & Interactive Conversation.

Features:
  • Hunger-mode bill capture: Scans text + photos (Grab, FoodPanda, Shopee, etc.) with OCR
  • Interactive conversational responses: Answers chat questions without just standing still
  • Animated progress bars: Real-time Telegram progress bar during OCR & swarm processing
  • Checkmark format with timestamps and itemization
"""

import logging
import os
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from skills.flow_nexus_swarm.orchestrator import SwarmOrchestrator
from skills.flow_nexus_swarm.shared_memory import AgentDB
from skills.ruflo.goal_engine import GoalEngine
from skills.ruflo.task_planner import TaskPlanner
from skills.ruflo.self_optimizer import SelfOptimizer

log = logging.getLogger("bill_gateway")

_PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "photos")


class BillGatewaySkill:
    """Gateway skill in Hunger Mode with conversational intelligence."""

    def __init__(self, db_path: str = "data/swarm_memory.db") -> None:
        self.db = AgentDB(db_path)
        self.orchestrator = SwarmOrchestrator(self.db)
        self.goal_engine = GoalEngine()
        self.planner = TaskPlanner()
        self.optimizer = SelfOptimizer(self.db)

        self.primary_goal = self.goal_engine.create_goal(
            name="Hunger Bill Capture",
            description="Relentlessly seek, scan, OCR, and capture all bills across Telegram.",
        )

        os.makedirs(_PHOTO_DIR, exist_ok=True)
        log.info("BillGatewaySkill (Hunger Mode) initialized")

    # ── Conversational Intelligence ───────────────────────────────────────

    def _generate_chat_reply(self, text: str, user_name: str, chat_id: int) -> str:
        """Intelligently respond when the user talks to the bot."""
        text_lower = text.lower()

        # Check total bills in chat for context
        totals = self.db.total_bills(chat_id)
        count = totals["count"]
        sum_amt = totals["total"]

        if any(w in text_lower for w in ["who are you", "what are you", "introduce"]):
            return (
                f"🤖 *I am the Telegram Bill Gateway (Hunger Mode!)*\n\n"
                f"I am connected to the **Flow-Nexus-Swarm** & **Ruflo** orchestration engine.\n"
                f"I constantly standby to hunt and capture every bill, invoice, or receipt you send:\n"
                f"• 📸 *Photos & Invoices:* Grab, FoodPanda, Shopee, Lazada, Supermarkets, Utilities (Auto-OCR enabled)\n"
                f"• ✍️ *Text:* Send any amount like `GrabFood lunch 15.50 USD` or `Coffee 4.00`\n\n"
                f"Currently holding *{count}* bills (*{sum_amt:,.2f}* total) in this chat!"
            )

        if any(w in text_lower for w in ["look", "see", "why you not take", "search", "where", "find", "check"]):
            return (
                f"👀 *I am actively scanning with hunger!* 🔍\n\n"
                f"Send me any image/receipt photo or type an amount with a label (e.g. `Grab 25`, `Foodpanda 14.50`, `Dinner 45.00`).\n\n"
                f"I will process it immediately with my multi-agent swarm and save it into my persistent memory!"
            )

        if any(w in text_lower for w in ["hello", "hi", "hey", "halo"]):
            return (
                f"👋 Hello {user_name}! I'm on standby in **Hunger Bill Mode**.\n"
                f"Drop any bill, invoice screenshot, or expense text here and I'll catch it immediately!"
            )

        if any(w in text_lower for w in ["how many", "count", "stat", "status", "summary"]):
            return (
                f"📊 *Quick Status for {user_name}:*\n"
                f"• 🧾 *Recorded Bills:* `{count}`\n"
                f"• 💰 *Total Value:* `{sum_amt:,.2f}`\n"
                f"• ⚡ *Swarm State:* `Optimal`\n\n"
                f"Use `/recent` to inspect latest or `/total` for summary!"
            )

        return (
            f"⚡ *Hunger Gateway is listening, {user_name}!* 🎯\n\n"
            f"Send me a bill photo (Grab/FoodPanda/Receipt) or a text with a price (e.g. `Taxi 12.50`), "
            f"and the Swarm will immediately parse and confirm it!"
        )

    # ── Text bill handler ─────────────────────────────────────────────────

    async def handle_text_bill(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle text messages with hunger detection & conversational fallback."""
        msg = update.effective_message
        user = update.effective_user
        chat = update.effective_chat
        if not msg or not msg.text:
            return

        text = msg.text.strip()
        user_name = user.first_name if user else "Friend"
        chat_id = chat.id if chat else 0

        # Check if message contains a command (skip commands handled elsewhere)
        if text.startswith("/"):
            return

        # Attempt swarm parse
        from bill_noter.price_parser import parse_prices
        prices = parse_prices(text)

        if prices:
            # Show active progress bar
            progress_msg = await msg.reply_text(
                "⚡ *[■■□□□□□□□□] 20%* — `[Swarm: BillCollector]` Ingesting text bill...",
                parse_mode="Markdown"
            )
            result = await self.orchestrator.process_message(update, context, progress_msg=progress_msg)
            response = result.get("response", "")
            if response:
                await progress_msg.edit_text(response, parse_mode="Markdown")
                log.info("TEXT BILL replied: bill_id=%s", result.get("bill_id"))
            return

        # If no price in text, provide smart conversational response
        chat_reply = self._generate_chat_reply(text, user_name, chat_id)
        await msg.reply_text(chat_reply, parse_mode="Markdown")

    # ── Photo bill handler ────────────────────────────────────────────────

    async def handle_photo_bill(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Hunger Photo Bill: Download, OCR scan with progress bar, parse & record."""
        msg = update.effective_message
        if not msg or not msg.photo:
            return

        # 1. Send initial progress bar
        progress_msg = await msg.reply_text(
            "⏳ *[■□□□□□□□□□] 10%* — `[Gateway]` Downloading receipt image...",
            parse_mode="Markdown"
        )

        try:
            # Download highest resolution photo
            photo = msg.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            now = datetime.now(timezone.utc)
            filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{photo.file_id[:8]}.jpg"
            filepath = os.path.join(_PHOTO_DIR, filename)
            await photo_file.download_to_drive(filepath)
            log.info("PHOTO downloaded: %s", filepath)

            # 2. Feed into Hunger Swarm with progress updates
            result = await self.orchestrator.process_message(
                update, context, image_path=filepath, progress_msg=progress_msg
            )

            response = result.get("response", "")
            if response:
                await progress_msg.edit_text(response, parse_mode="Markdown")
                if result.get("bill_id"):
                    log.info("PHOTO BILL finalized: bill_id=%s", result.get("bill_id"))
            elif result.get("skipped"):
                # Photo handled above with a helpful message; nothing to do.
                log.info("PHOTO BILL skipped: %s", result.get("skipped"))
            else:
                await progress_msg.edit_text(
                    "✅ *Bill Image Captured & Stored!*\n"
                    "🖼️ Photo archived in memory. Send amount if you want to update the total.",
                    parse_mode="Markdown"
                )

        except Exception as exc:
            log.error("PHOTO PROCESSING error: %s", exc, exc_info=True)
            await progress_msg.edit_text(f"⚠️ OCR / Photo Processing issue: {exc}")

    # ── /swarm command ────────────────────────────────────────────────────

    async def handle_swarm_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        stats = self.db.get_agent_stats()
        lines = [
            "⚡ *HUNGER SWARM STATUS & TOPOLOGY*\n",
            "🔄 *Mode:* `Hunger Bill Gateway (Continuous Active Scan)`",
            "🧠 *Orchestrator:* `Hierarchical (4 Specialized Agents)`",
            "🗄️ *Memory Backend:* `SQLite AgentDB (data/swarm_memory.db)`\n",
        ]
        if stats:
            lines.append("🤖 *Agent Metrics:*")
            for agent_id, s in stats.items():
                pct = s["success_rate"] * 100
                bar = "🟢" if pct >= 90 else "🟡" if pct >= 70 else "🔴"
                lines.append(f" {bar} *{agent_id}*: `{pct:.1f}%` ({s['runs']} runs)")
        else:
            lines.append("🤖 *Agent Metrics:* All 4 agents standing by in Hunger Mode.")

        chat = update.effective_chat
        if chat:
            totals = self.db.total_bills(chat.id)
            lines.append(f"\n📊 *Chat Total:* `{totals['count']}` bills noted | `💰 {totals['total']:,.2f}`")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    # ── /optimize command ─────────────────────────────────────────────────

    async def handle_optimize(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        report = self.optimizer.optimize()
        await update.message.reply_text(
            f"🔧 *Swarm Self-Optimization Report*\n\n{report}\n\n"
            f"🚀 *Hunger Parameters:* Max OCR sensitivity, Multi-currency recognition active.",
            parse_mode="Markdown",
        )
