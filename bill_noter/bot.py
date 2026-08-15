"""Telegram bill/price noter bot.

Auto-parses prices from group messages, stores them as notes in a local JSON file,
and replies in-chat so members can see the bot is alive and working.

Extended with flow-nexus-swarm + ruflo skills for:
  • Multi-agent bill processing pipeline (Collector → Parser → Storage → Responder)
  • SQLite shared memory for persistent state
  • Photo bill capture (Grab, FoodPanda, local bill images)
  • Goal-oriented execution and self-optimization
"""

import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .notes_store import Note, NotesStore
from .price_parser import extract_label, parse_prices

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bill_noter")

STORE_PATH = os.environ.get("BILL_NOTER_STORE", "notes.json")
TOKEN = os.environ.get("BILL_NOTER_TOKEN", "")
WATCH_ANNOUNCED: set = set()


def _load_env_file(path: str = ".env") -> None:
    """Minimal .env loader (no extra dependency)."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def _fmt(value: float, currency: str) -> str:
    if currency:
        return f"{value:,.2f} {currency}"
    return f"{value:,.2f}"


async def _announce_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or chat.id in WATCH_ANNOUNCED:
        return
    WATCH_ANNOUNCED.add(chat.id)
    await context.bot.send_message(
        chat.id,
        "🤖 *Bill Noter is now watching this chat.*\n"
        "I auto-note any price I see and reply to confirm. "
        "Try: `Lunch 12.50` or `/recent` to review.\n\n"
        "🔧 *Swarm skills loaded:* flow-nexus-swarm, ruflo\n"
        "📸 Send photos of bills (Grab, FoodPanda, etc.) and I'll capture them too!",
        parse_mode="Markdown",
    )
    log.info("ACTION announced watch in chat %s (%s)", chat.id, chat.title)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None or not msg.text:
        return

    text = msg.text
    log.info("ACTION recv msg chat=%s user=%s text=%r",
             chat.id, user.full_name, text)

    # ── Route through Hunger Gateway Skill ────────────────────────────
    gateway = context.bot_data.get("gateway")
    if gateway:
        await gateway.handle_text_bill(update, context)
        await _announce_watch(update, context)
        return

    # ── Fallback: original behavior ───────────────────────────────────
    prices = parse_prices(text)
    if not prices:
        return
    store: NotesStore = context.bot_data["store"]
    for price in prices:
        label = extract_label(text, [price])
        note = Note(
            chat_id=chat.id,
            chat_title=chat.title or "",
            message_id=msg.id,
            author_id=user.id,
            author_name=user.full_name or user.username or "unknown",
            label=label,
            value=price.value,
            currency=price.currency,
            raw=text,
        )
        added = store.add(note)
        if not added:
            await msg.reply_text(
                f"⚠️ *Duplicate Rejected:* `{label}` {_fmt(price.value, price.currency)} "
                "was already recorded — nothing duplicated.",
                parse_mode="Markdown",
            )
            log.info("ACTION rejected duplicate id=%s label=%r", msg.id, label)
            continue
        confirmation = (
            f"✅ *Noted:* {label}\n"
            f"💰 {_fmt(price.value, price.currency)}\n"
            f"👤 by {note.author_name}"
        )
        await msg.reply_text(confirmation, parse_mode="Markdown")
        log.info("ACTION noted id=%s label=%r amount=%s",
                 msg.id, label, _fmt(price.value, price.currency))
    await _announce_watch(update, context)



async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages through the swarm gateway."""
    gateway = context.bot_data.get("gateway")
    if gateway:
        await gateway.handle_photo_bill(update, context)
        await _announce_watch(update, context)


async def cmd_recent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return

    gateway = context.bot_data.get("gateway")
    if gateway:
        bills = gateway.db.list_bills(chat_id=chat.id, limit=10)
        if not bills:
            await update.message.reply_text("📭 No notes yet in this chat.")
            return
        lines = ["📒 *Recent notes (Swarm Memory):*"]
        for b in bills:
            dt = b.get("created_at", "")
            ts = dt[11:16] if len(dt) >= 16 else dt
            amt_str = f"{b['amount']:,.2f} {b['currency']}".strip()
            lines.append(f"• {amt_str} — {b['label']} _{ts}_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        log.info("ACTION /recent chat=%s count=%d (AgentDB)", chat.id, len(bills))
        return

    # Fallback
    store: NotesStore = context.bot_data["store"]
    notes = store.recent(chat.id, limit=10)
    if not notes:
        await update.message.reply_text("📭 No notes yet in this chat.")
        return
    lines = ["📒 *Recent notes:*"]
    for n in reversed(notes):
        ts = n.timestamp[11:16]
        lines.append(f"• {_fmt(n.value, n.currency)} — {n.label} _{ts}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return

    gateway = context.bot_data.get("gateway")
    if gateway:
        totals = gateway.db.total_bills(chat.id)
        await update.message.reply_text(
            f"🧮 *Total noted:* {totals['total']:,.2f}\n📊 *Items:* {totals['count']}",
            parse_mode="Markdown",
        )
        log.info("ACTION /total chat=%s total=%.2f count=%d (AgentDB)",
                 chat.id, totals['total'], totals['count'])
        return

    # Fallback
    store: NotesStore = context.bot_data["store"]
    total = store.total(chat.id)
    count = store.count(chat.id)
    await update.message.reply_text(
        f"🧮 *Total noted:* {total:,.2f}\n📊 *Items:* {count}",
        parse_mode="Markdown",
    )
    log.info("ACTION /total chat=%s total=%.2f count=%d", chat.id, total, count)



async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    gateway = context.bot_data.get("gateway")
    swarm_status = "🟢 Active" if gateway else "⚪ Not loaded"
    await update.message.reply_text(
        "🟢 *Bill Noter is running.*\n"
        "I auto-parse prices from messages and store them locally.\n\n"
        f"🔧 *Swarm Engine:* {swarm_status}\n"
        "📸 *Photo bills:* Supported\n"
        "🎯 *Goal engine:* ruflo active",
        parse_mode="Markdown",
    )
    log.info("ACTION /status chat=%s", chat.id)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*Bill Noter*\n"
        "Just write a message with a price, e.g. `Taxi 8.50`. I'll note it and reply.\n"
        "📸 Send a photo of a bill and I'll capture it too!\n\n"
        "*Commands:*\n"
        "/recent — last 10 notes\n"
        "/total — sum of all notes\n"
        "/swarm — agent stats\n"
        "/optimize — run self-optimization\n"
        "/status — is the bot alive?\n"
        "/help — this message",
        parse_mode="Markdown",
    )


async def cmd_swarm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show swarm agent statistics."""
    gateway = context.bot_data.get("gateway")
    if gateway:
        await gateway.handle_swarm_status(update, context)
    else:
        await update.message.reply_text("⚪ Swarm skill not loaded.")


async def cmd_optimize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger self-optimization."""
    gateway = context.bot_data.get("gateway")
    if gateway:
        await gateway.handle_optimize(update, context)
    else:
        await update.message.reply_text("⚪ Swarm skill not loaded.")


def build_application() -> Application:
    store = NotesStore(STORE_PATH)
    app = Application.builder().token(TOKEN).build()
    app.bot_data["store"] = store

    # ── Initialize swarm gateway skill ────────────────────────────────
    try:
        from skills.bill_gateway_skill import BillGatewaySkill
        gateway = BillGatewaySkill()
        app.bot_data["gateway"] = gateway
        log.info("SKILL loaded: flow-nexus-swarm + ruflo (BillGatewaySkill)")
    except Exception as exc:
        log.warning("SKILL load failed (falling back to basic mode): %s", exc)
        app.bot_data["gateway"] = None

    # ── Command handlers ──────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("recent", cmd_recent))
    app.add_handler(CommandHandler("total", cmd_total))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("swarm", cmd_swarm))
    app.add_handler(CommandHandler("optimize", cmd_optimize))

    # ── Message handlers ──────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


def main() -> None:
    _load_env_file()
    token = os.environ.get("BILL_NOTER_TOKEN", "")
    store_path = os.environ.get("BILL_NOTER_STORE", "notes.json")
    if not token:
        raise SystemExit("BILL_NOTER_TOKEN is not set. Add it to .env or the environment.")
    log.info("START Bill Noter bot (store=%s)", store_path)
    global TOKEN, STORE_PATH
    TOKEN = token
    STORE_PATH = store_path

    # Auto-heal heartbeat — lets `heal.py` detect hangs. Harmless if
    # the supervisor is not running.
    try:
        from heal import start_heartbeat
        start_heartbeat("bot", interval=10)
    except Exception as exc:
        log.warning("heartbeat unavailable: %s", exc)

    app = build_application()
    app.run_polling()
    log.info("STOP Bill Noter bot")


if __name__ == "__main__":
    main()


