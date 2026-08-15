"""The Telegram gateway (AUTOBOT).

Core scan logic runs against *any* client that mimics the slice of the Pyrogram
async API it uses (get_dialogs / get_chat_history). That lets us run it:
  * live   -> real Pyrogram Client (user session or bot)
  * sandbox-> the offline SandboxClient (no external connection, all in-repo)

Behavior:
  * AUTOMATIC: scan runs on a loop (autobot) at a fixed interval.
  * TARGETED : scans only the configured chat (pencatatbill2) when chat_id is set.
  * BILLS    : text prices (bill format) AND photos passed through OCR.
  * FRESH    : per-chat checkpoint so only unseen bills are reported.
Bill detection reuses bill_noter.price_parser so behavior is consistent.
"""

import asyncio
import logging
from typing import List, Optional

from .bill_detector import AnalyzedMessage, analyze
from .checkpoint import Checkpoint

log = logging.getLogger("gateway")


class TelegramGateway:
    def __init__(
        self,
        api_id: str = "",
        api_hash: str = "",
        session_name: str = "session/gateway_client",
        state_path: str = "gateway_state.json",
        history_limit: int = 20,
    ) -> None:
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.checkpoint = Checkpoint(state_path)
        self.history_limit = history_limit

    # ------------------------------------------------------------------ #
    # OCR helper
    # ------------------------------------------------------------------ #
    async def _ocr_text(self, client, msg) -> str:
        sim = getattr(msg, "ocr", "")
        if sim:
            return sim
        try:
            from .ocr import ocr_text
            path = await client.download_media(msg)
            if path:
                return ocr_text(path)
        except Exception as exc:
            log.warning("OCR download failed: %s", exc)
        return ""

    # ------------------------------------------------------------------ #
    # Per-chat scan
    # ------------------------------------------------------------------ #
    async def _scan_one(self, client, chat_id: int, title: Optional[str] = None):
        chat_title = title or str(chat_id)
        log.info("GATEWAY chat=%s title=%r", chat_id, chat_title)

        fresh: List[AnalyzedMessage] = []
        max_id = 0
        max_date = ""
        try:
            async for msg in client.get_chat_history(chat_id, limit=self.history_limit):
                a = analyze(msg)
                if a.message_id > max_id:
                    max_id, max_date = a.message_id, a.date
                cp = self.checkpoint.get(chat_id)
                if a.message_id <= cp["last_id"]:
                    continue

                # Photo -> OCR, then check if the image is actually a bill.
                if a.is_photo and not a.is_bill:
                    ocr_text = await self._ocr_text(client, msg)
                    if ocr_text:
                        oa = analyze({"text": ocr_text})
                        if oa.is_bill:
                            a.is_bill = True
                            a.is_bill_candidate = False
                            a.prices = oa.prices
                            a.label = oa.label
                            a.text = oa.text
                            log.info("  🖼️  OCR found bill in photo: %s — %s",
                                     a.label, ", ".join(a.prices))
                        else:
                            log.info("  🖼️  photo scanned, not a bill (msg %s)", a.message_id)
                            continue
                    else:
                        log.info("  🖼️  candidate bill (photo, OCR unavailable) msg %s",
                                 a.message_id)
                        continue

                if a.is_bill:
                    fresh.append(a)
                    log.info("  💰 FRESH BILL: %s — %s (msg %s)",
                             a.label, ", ".join(a.prices), a.message_id)
        except Exception as exc:  # restricted / no history access
            log.warning("  cannot read history for %r: %s", chat_title, exc)
            return (chat_title, fresh)

        if not fresh:
            log.info("  no fresh bill in %r", chat_title)
        self.checkpoint.update(chat_id, max_id, max_date)
        return (chat_title, fresh)

    # ------------------------------------------------------------------ #
    # Shared scan loop — works with any client
    # ------------------------------------------------------------------ #
    async def scan_with_client(self, client, chat_id: Optional[int] = None) -> List[tuple]:
        if chat_id is not None:
            return [await self._scan_one(client, int(chat_id))]
        results: List[tuple] = []
        log.info("GATEWAY scanning all dialogs")
        async for dialog in client.get_dialogs():
            chat = dialog.chat
            cid = chat.id
            title = getattr(chat, "title", None) or getattr(chat, "first_name", None)
            results.append(await self._scan_one(client, cid, title))
        return results

    # ------------------------------------------------------------------ #
    # Live: real Pyrogram Client (user session -> every chat)
    # ------------------------------------------------------------------ #
    async def scan_once(self, chat_id: Optional[int] = None):
        from pyrogram import Client
        async with Client(self.session_name, api_id=self.api_id,
                          api_hash=self.api_hash) as client:
            return await self.scan_with_client(client, chat_id=chat_id)

    def run_scan(self, chat_id: Optional[int] = None) -> None:
        asyncio.run(self.scan_once(chat_id))

    # ------------------------------------------------------------------ #
    # Sandbox: offline client, everything in-repo
    # ------------------------------------------------------------------ #
    def run_sandbox(self, sandbox_client, chat_id: Optional[int] = None) -> None:
        asyncio.run(self.scan_with_client(sandbox_client, chat_id=chat_id))

    # ------------------------------------------------------------------ #
    # AUTOBOT: automatic loop
    # ------------------------------------------------------------------ #
    async def autobot(self, client_factory, interval: int = 15,
                      chat_id: Optional[int] = None) -> None:
        log.info("AUTOBOT started (interval=%ss, chat=%s)", interval, chat_id)
        while True:
            try:
                async with client_factory() as client:
                    await self.scan_with_client(client, chat_id=chat_id)
            except Exception as exc:
                log.error("AUTOBOT scan error: %s", exc)
            log.info("AUTOBOT sleeping %ss", interval)
            await asyncio.sleep(interval)

    def run_autobot(self, client_factory, interval: int = 15,
                    chat_id: Optional[int] = None) -> None:
        asyncio.run(self.autobot(client_factory, interval, chat_id))

    # ------------------------------------------------------------------ #
    # Live: bot listener (chats the bot is in)
    # ------------------------------------------------------------------ #
    async def _bot_on_message(self, client, message) -> None:
        """Always-standby consumer: store fresh bills into AgentDB (dedup
        guarded) and reply, so the gateway consumes — not just watches."""
        a = analyze(message)
        chat_id = a.chat_id
        cp = self.checkpoint.get(chat_id)
        if a.is_bill and a.message_id > cp["last_id"]:
            log.info("FRESH BILL in %s: %s %s",
                     getattr(message.chat, "title", chat_id), a.label, a.prices)
            try:
                await self._store_bill(a, message)
                await message.reply_text(
                    f"💰 Noted: {a.label} — {', '.join(a.prices)}"
                )
            except Exception as exc:
                log.warning("gateway consume failed: %s", exc)
        elif a.is_bill_candidate:
            log.info("candidate bill photo in %s (OCR needed)", chat_id)
        self.checkpoint.update(chat_id, a.message_id, a.date)

    async def _store_bill(self, a, message) -> None:
        """Persist a consumed bill into the shared AgentDB with dedup."""
        from skills.flow_nexus_swarm.shared_memory import (
            AgentDB, DuplicateBillError,
        )

        db = AgentDB()
        author = getattr(getattr(message, "from_user", None), "first_name", "") or ""
        # Reuse the same price parser the swarm uses so currency/thousands
        # separators are handled identically everywhere.
        from bill_noter.price_parser import parse_prices
        prices = parse_prices(a.raw)
        max_p = max(prices, key=lambda p: p.value) if prices else None
        try:
            db.save_bill(
                chat_id=a.chat_id,
                message_id=a.message_id,
                author_id=getattr(getattr(message, "from_user", None), "id", 0) or 0,
                author_name=author or "Member",
                bill_type="local_bill",
                source="gateway",
                label=a.label or "Bill",
                amount=max_p.value if max_p else 0.0,
                currency=max_p.currency if max_p else "",
                raw_text=a.raw,
            )
        except DuplicateBillError as exc:
            log.info("GATEWAY duplicate rejected: %s", exc)
            try:
                await message.reply_text(
                    f"⚠️ *Duplicate Rejected:* already recorded as `#{exc.existing_id}`."
                )
            except Exception:
                pass

    def run_bot(self, bot_token: str) -> None:
        from pyrogram import Client

        bot = Client("gateway_bot", bot_token=bot_token)

        @bot.on_message()
        async def _handler(client, message):
            await self._bot_on_message(client, message)

        log.info("GATEWAY bot listener started")
        bot.run_polling()
