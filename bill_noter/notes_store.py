"""JSON-backed store for bill/price notes."""

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class Note:
    chat_id: int
    chat_title: str
    message_id: int
    author_id: int
    author_name: str
    label: str
    value: float
    currency: str
    raw: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NotesStore:
    """Append-only JSON store of notes, keyed by chat id."""

    def __init__(self, path: str = "notes.json") -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._data: Dict[str, List[dict]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add(self, note: Note) -> None:
        with self._lock:
            self._data.setdefault(str(note.chat_id), []).append(asdict(note))
            self._save()

    def recent(self, chat_id: int, limit: int = 10) -> List[Note]:
        rows = self._data.get(str(chat_id), [])[-limit:]
        return [Note(**r) for r in rows]

    def total(self, chat_id: int, currency: str = "") -> float:
        rows = self._data.get(str(chat_id), [])
        if currency:
            return sum(r["value"] for r in rows if r["currency"] == currency)
        return sum(r["value"] for r in rows)

    def count(self, chat_id: int) -> int:
        return len(self._data.get(str(chat_id), []))
