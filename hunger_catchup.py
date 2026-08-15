"""Hunger Gateway Catch-Up Scanner (MTProto / User-Session & Export Ingester).

Solves the Telegram Bot API limitation:
When a bot is added late to a group, the Telegram Bot API cannot read past messages.
This script provides two hunger solutions:
1. User-Session Catch-Up: Connects via Pyrogram MTProto user session, fetches chat history backwards,
   extracts old photos & OCR, and inserts every missing bill into data/swarm_memory.db.
2. JSON/Chat Export Ingester: Ingests exported Telegram chat history JSON files directly into the Swarm DB.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skills.flow_nexus_swarm.shared_memory import AgentDB
from gateway.ocr import ocr_text
from bill_noter.price_parser import parse_prices, extract_label

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("hunger.catchup")


class HungerHistoryScanner:
    """Retroactively scavenges Telegram chat history for all past receipts & bills."""

    def __init__(self, db_path: str = "data/swarm_memory.db") -> None:
        self.db = AgentDB(db_path)
        self.photo_dir = Path("data/photos")
        self.photo_dir.mkdir(parents=True, exist_ok=True)

    # ── Solution 1: Scrape History via User Session (Pyrogram MTProto) ──

    async def scan_telegram_history(
        self,
        api_id: str,
        api_hash: str,
        session_name: str = "session/gateway_client",
        chat_id: Optional[int] = None,
        limit: int = 500,
    ) -> int:
        """Connect as a User Client to read older messages that bots cannot see."""
        from pyrogram import Client

        found_count = 0
        log.info("HUNGER MTPROTO: Connecting user session to fetch %d past messages...", limit)

        async with Client(session_name, api_id=api_id, api_hash=api_hash) as client:
            target_chats = []
            if chat_id:
                target_chats.append(chat_id)
            else:
                async for dialog in client.get_dialogs():
                    target_chats.append(dialog.chat.id)

            for cid in target_chats:
                log.info("HUNGER SCANNING chat %s for historical bills...", cid)
                async for msg in client.get_chat_history(cid, limit=limit):
                    text = msg.text or msg.caption or ""
                    photo_path = None

                    # If message has photo, download and OCR scan
                    if msg.photo:
                        try:
                            downloaded = await client.download_media(msg, file_name=str(self.photo_dir) + "/")
                            if downloaded:
                                photo_path = downloaded
                                ocr_res = ocr_text(downloaded)
                                if ocr_res:
                                    text = f"{text}\n{ocr_res}".strip()
                        except Exception as exc:
                            log.warning("Could not download/OCR historical photo %s: %s", msg.id, exc)

                    prices = parse_prices(text)
                    if prices:
                        max_p = max(prices, key=lambda p: p.value)
                        label = extract_label(text, prices) or "Historical Bill"
                        author_name = getattr(msg.from_user, "first_name", "Member") if msg.from_user else "Member"

                        bill_id = self.db.save_bill(
                            chat_id=cid,
                            message_id=msg.id,
                            author_id=getattr(msg.from_user, "id", 0) if msg.from_user else 0,
                            author_name=author_name,
                            bill_type="historical_bill",
                            source="telegram_history",
                            label=label,
                            amount=max_p.value,
                            currency=max_p.currency or "USD",
                            raw_text=text,
                            image_path=photo_path,
                        )
                        self.db.update_bill_status(bill_id, "confirmed")
                        found_count += 1
                        log.info("🔥 RECOVERED PAST BILL #%d: %s -> %.2f %s",
                                 bill_id, label, max_p.value, max_p.currency)

        log.info("HUNGER MTPROTO FINISHED: Recovered %d past bills.", found_count)
        return found_count

    # ── Solution 2: Ingest Telegram Export JSON ─────────────────────────

    def ingest_telegram_export_json(self, json_file_path: str, chat_id: int = 0) -> int:
        """Ingests exported result.json from Telegram Desktop 'Export Chat History'."""
        path = Path(json_file_path)
        if not path.exists():
            log.error("Export file not found: %s", json_file_path)
            return 0

        data = json.loads(path.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        recovered = 0

        log.info("HUNGER INGEST: Processing %d exported messages from %s...", len(messages), path.name)
        for m in messages:
            if m.get("type") != "message":
                continue

            raw_text = ""
            text_field = m.get("text", "")
            if isinstance(text_field, list):
                raw_text = "".join(t if isinstance(t, str) else t.get("text", "") for t in text_field)
            else:
                raw_text = str(text_field)

            prices = parse_prices(raw_text)
            if prices:
                max_p = max(prices, key=lambda p: p.value)
                label = extract_label(raw_text, prices) or "Exported Bill"
                mid = m.get("id", 0)
                author = m.get("from", "Export User")

                bill_id = self.db.save_bill(
                    chat_id=chat_id or data.get("id", 0),
                    message_id=mid,
                    author_id=0,
                    author_name=author,
                    bill_type="exported_bill",
                    source="telegram_export",
                    label=label,
                    amount=max_p.value,
                    currency=max_p.currency or "USD",
                    raw_text=raw_text,
                    image_path=m.get("photo", None),
                )
                self.db.update_bill_status(bill_id, "confirmed")
                recovered += 1

        log.info("HUNGER INGEST COMPLETE: Saved %d historical bills into SQLite memory.", recovered)
        return recovered


if __name__ == "__main__":
    scanner = HungerHistoryScanner()
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        scanner.ingest_telegram_export_json(sys.argv[1])
    else:
        print("Hunger History Scanner ready.")
        print("Usage:")
        print("  1. Ingest JSON export: python hunger_catchup.py result.json")
        print("  2. Programmatic user-mode scrape via scan_telegram_history()")
