"""Offline sandbox Telegram client.

Mimics the small slice of the Pyrogram async API the gateway uses
(get_dialogs / get_chat_history) so the gateway can run and be observed fully
inside the workspace, with no external Telegram connection. Data lives in a
JSON file (gateway/sandbox_data.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class SandboxChat:
    id: int
    title: Optional[str] = None
    first_name: Optional[str] = None


@dataclass
class SandboxMessage:
    id: int
    date: datetime
    chat: SandboxChat
    text: str = ""
    caption: str = ""
    photo: bool = False
    ocr: str = ""  # pre-set OCR output for photos (simulates real OCR)


class _Dialog:
    def __init__(self, chat: SandboxChat) -> None:
        self.chat = chat


class SandboxClient:
    def __init__(self, data_path: str = "gateway/sandbox_data.json") -> None:
        self.data_path = Path(data_path)
        self.chats: List[dict] = []
        self._load()

    def _load(self) -> None:
        if self.data_path.exists():
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
            self.chats = raw.get("chats", [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _to_message(self, chat: SandboxChat, raw: dict) -> SandboxMessage:
        return SandboxMessage(
            id=int(raw["id"]),
            date=datetime.fromisoformat(raw["date"]),
            chat=chat,
            text=raw.get("text", ""),
            caption=raw.get("caption", ""),
            photo=bool(raw.get("photo", False)),
            ocr=raw.get("ocr", ""),
        )

    async def get_dialogs(self):
        for c in self.chats:
            chat = SandboxChat(
                id=int(c["id"]), title=c.get("title"), first_name=c.get("first_name")
            )
            yield _Dialog(chat)

    async def get_chat_history(self, chat_id, limit: int = 20):
        for c in self.chats:
            if int(c["id"]) != int(chat_id):
                continue
            msgs = sorted(c.get("messages", []), key=lambda m: int(m["id"]), reverse=True)
            for raw in msgs[:limit]:
                yield self._to_message(
                    SandboxChat(id=int(c["id"]), title=c.get("title")), raw
                )
            return
