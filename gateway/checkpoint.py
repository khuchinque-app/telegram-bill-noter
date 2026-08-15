"""Per-chat checkpoint: remembers the last seen message id so the gateway can
tell which bills are *fresh* (arrived after the previous scan)."""

import json
from pathlib import Path


class Checkpoint:
    def __init__(self, path: str = "gateway_state.json") -> None:
        self.path = Path(path)
        self.data: dict = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get(self, chat_id: int) -> dict:
        return self.data.get(str(chat_id), {"last_id": 0, "last_date": ""})

    def update(self, chat_id: int, last_id: int, last_date: str) -> None:
        cur = self.get(chat_id)
        if last_id > cur["last_id"]:
            self.data[str(chat_id)] = {"last_id": last_id, "last_date": last_date}
            self.save()
