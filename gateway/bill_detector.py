"""Bill detection for the gateway.

Decides whether a message is a bill by looking for a price. Photos without
parseable text are flagged as *candidates* (they need OCR, which the gateway
does not perform on its own).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from bill_noter.price_parser import extract_label, parse_prices


@dataclass
class AnalyzedMessage:
    message_id: int
    date: str
    chat_id: int
    text: str
    is_photo: bool
    is_bill: bool
    is_bill_candidate: bool  # photo with no parseable text -> needs OCR
    prices: List[str] = field(default_factory=list)
    label: str = ""
    raw: str = ""


def _text_of(msg) -> str:
    if isinstance(msg, dict):
        return msg.get("text") or msg.get("caption") or ""
    return getattr(msg, "text", None) or getattr(msg, "caption", None) or ""


def _id_of(msg):
    if isinstance(msg, dict):
        return int(msg.get("id", 0))
    return int(getattr(msg, "id", 0))


def _date_of(msg) -> str:
    if isinstance(msg, dict):
        return msg.get("date", "")
    d = getattr(msg, "date", None)
    return d.isoformat() if d else ""


def _chat_of(msg):
    if isinstance(msg, dict):
        return int(msg.get("chat_id", 0))
    chat = getattr(msg, "chat", None)
    return int(chat.id) if chat else 0


def _is_photo(msg) -> bool:
    if isinstance(msg, dict):
        return bool(msg.get("photo"))
    return bool(getattr(msg, "photo", None))


def _is_bill_price(price) -> bool:
    """A number is a bill price only if it carries a currency hint or a
    price-like shape (decimal/thousands separator). Bare integers like '7'
    (e.g. 'jam 7 malam') are rejected to avoid false positives."""
    if price.currency:
        return True
    return bool(re.search(r"[.,]", price.raw))


def analyze(msg) -> AnalyzedMessage:
    """Analyze a message (dict or pyrogram Message) for bill content."""
    text = _text_of(msg).strip()
    prices = [p for p in parse_prices(text) if _is_bill_price(p)]
    is_photo = _is_photo(msg)
    is_bill = bool(prices)
    candidate = is_photo and not is_bill
    label = extract_label(text, prices) if is_bill else ""
    return AnalyzedMessage(
        message_id=_id_of(msg),
        date=_date_of(msg),
        chat_id=_chat_of(msg),
        text=text,
        is_photo=is_photo,
        is_bill=is_bill,
        is_bill_candidate=candidate,
        prices=[p.raw for p in prices],
        label=label,
        raw=text,
    )
