"""Flow-Nexus-Swarm specialized agents for HUNGER BILL processing.

Pipeline: BillCollectorAgent → BillParserAgent → BillStorageAgent → BillResponderAgent
Every agent executes aggressively in hunger-mode, extracting all bills, receipts, OCR texts,
and logging to SharedMemory (AgentDB).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .shared_memory import AgentDB
from gateway.ocr import ocr_text

log = logging.getLogger("swarm.agents")

_BILL_KEYWORDS: Dict[str, List[str]] = {
    "grab": ["grab", "grabfood", "grabpay", "grabcar", "grab express", "grabmart"],
    "foodpanda": ["foodpanda", "food panda", "pandamart", "panda"],
    "shopee": ["shopee", "shopeepay", "shopee pay", "spay"],
    "lazada": ["lazada", "lazpay"],
    "gojek": ["gojek", "goride", "gofood", "gopay"],
    "lineman": ["lineman", "line man"],
    "starbucks": ["starbucks"],
    "mcdonalds": ["mcdonalds", "mcd", "mcdonald's"],
    "kfc": ["kfc"],
    "indomaret": ["indomaret"],
    "alfamart": ["alfamart"],
    "seven_eleven": ["7-eleven", "7 eleven", "7-11"],
}


class BaseAgent:
    name: str = "base"
    role: str = ""

    def __init__(self, db: AgentDB) -> None:
        self.db = db

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def _log(self, action: str, inp: Any, out: Any,
             success: bool = True, error: str = "") -> None:
        try:
            self.db.log_action(
                agent_id=self.name,
                action=action,
                input_data=json.dumps(inp, default=str)[:2000],
                output_data=json.dumps(out, default=str)[:2000],
                success=success,
                error=error,
            )
        except Exception as exc:
            log.warning("agent log write failed: %s", exc)


class BillCollectorAgent(BaseAgent):
    """Hunger Collector: Ingests text, OCR from photos, and metadata."""

    name = "BillCollector"
    role = "Hungry collector of messages & receipt images"

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        update = data.get("update")
        msg = getattr(update, "effective_message", None) if update else None
        chat = getattr(update, "effective_chat", None) if update else None
        user = getattr(update, "effective_user", None) if update else None

        now = datetime.now(timezone.utc)

        text = ""
        if msg:
            text = msg.text or msg.caption or ""

        image_path = data.get("image_path", "")
        has_photo = bool(image_path or (msg and msg.photo))
        photo_file_id = ""
        if msg and msg.photo:
            photo_file_id = msg.photo[-1].file_id

        # HUNGER OCR: If image_path exists, run OCR extraction immediately
        ocr_extracted = ""
        if image_path:
            try:
                ocr_extracted = ocr_text(image_path)
                log.info("HUNGER OCR extracted %d chars from %s", len(ocr_extracted), image_path)
            except Exception as exc:
                log.warning("OCR failed on %s: %s", image_path, exc)

        combined_text = f"{text}\n{ocr_extracted}".strip()

        # Detect bill type aggressively from keywords
        text_lower = combined_text.lower()
        bill_type = "local_bill"
        for btype, keywords in _BILL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                bill_type = btype
                break

        result: Dict[str, Any] = {
            "text": text,
            "ocr_text": ocr_extracted,
            "combined_text": combined_text,
            "chat_id": chat.id if chat else 0,
            "chat_title": (chat.title if chat else "") or "",
            "message_id": msg.id if msg else 0,
            "author_id": user.id if user else 0,
            "author_name": (user.full_name if user else "") or "unknown",
            "bill_type": bill_type,
            "has_photo": has_photo,
            "photo_file_id": photo_file_id,
            "image_path": image_path,
            "source": "telegram",
            "collected_at": now.isoformat(),
            "date_display": now.strftime("%Y-%m-%d"),
            "time_display": now.strftime("%H:%M:%S UTC"),
        }

        log.info("HUNGER COLLECT chat=%s user=%s type=%s has_photo=%s ocr_len=%d",
                 result["chat_id"], result["author_name"],
                 result["bill_type"], result["has_photo"], len(ocr_extracted))
        self._log("collect", {"text": text[:200], "image": image_path}, result)
        return result


class BillParserAgent(BaseAgent):
    """Hunger Parser: Scans text + OCR thoroughly for all prices and subtotals."""

    name = "BillParser"
    role = "Hungry parser of bill amounts and receipts"

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from bill_noter.price_parser import extract_label, parse_prices

        combined = data.get("combined_text", "") or data.get("text", "")
        prices = parse_prices(combined) if combined else []

        amounts: list = []
        total = 0.0
        currency = ""
        label = data.get("bill_type", "bill").replace("_", " ").title()

        if prices:
            # If OCR has multiple prices, pick the largest one (usually total/grand total)
            # or sum them if distinct items
            max_price = max(prices, key=lambda p: p.value)
            for p in prices:
                amounts.append({"value": p.value, "currency": p.currency, "raw": p.raw})
                if p.currency and not currency:
                    currency = p.currency
            
            # If multiple prices found in an OCR receipt, take max as the bill total
            if len(prices) > 1 and data.get("has_photo"):
                total = max_price.value
                if max_price.currency:
                    currency = max_price.currency
            else:
                total = sum(p.value for p in prices)

            # NOTE: price spans were computed against `combined` (caption + OCR).
            # Only extract a label when there is no OCR text, otherwise the spans
            # would be applied to a different-length string and garble the label.
            if not data.get("ocr_text"):
                text_for_label = data.get("text") or ""
                extracted = extract_label(text_for_label, prices)
                if extracted and extracted != "untitled":
                    label = extracted
        elif data.get("has_photo"):
            label = f"{label} (Receipt Image)"

        result = {
            **data,
            "amounts": amounts,
            "total": round(total, 2),
            "currency": currency,
            "label": label,
            "parsed": bool(prices),
        }

        log.info("HUNGER PARSE label=%r total=%.2f currency=%s parsed=%s",
                 result["label"], result["total"], result["currency"], result["parsed"])
        self._log("parse", {"combined": combined[:200]}, result)
        return result


class BillStorageAgent(BaseAgent):
    """Hunger Storage: Persists every piece of parsed data into SQLite AgentDB."""

    name = "BillStorage"
    role = "Store bill into SQLite shared memory"

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        bill_id = self.db.save_bill(
            chat_id=data.get("chat_id", 0),
            message_id=data.get("message_id", 0),
            author_id=data.get("author_id", 0),
            author_name=data.get("author_name", ""),
            bill_type=data.get("bill_type", "generic"),
            source=data.get("source", "telegram"),
            label=data.get("label", ""),
            amount=data.get("total", 0.0),
            currency=data.get("currency", ""),
            raw_text=data.get("combined_text", "") or data.get("text", ""),
            image_path=data.get("image_path", None),
        )
        self.db.update_bill_status(bill_id, "confirmed")

        result = {
            **data,
            "bill_id": bill_id,
            "stored": True,
        }

        log.info("HUNGER STORE bill_id=%s label=%r amount=%.2f",
                 bill_id, data.get("label"), data.get("total", 0))
        self._log("store", {"bill_id": bill_id}, result)
        return result


class BillResponderAgent(BaseAgent):
    """Hunger Responder: Formats rich checkmark response with timestamp & details."""

    name = "BillResponder"
    role = "Format and output rich bill confirmation"

    def _fmt_amount(self, value: float, currency: str) -> str:
        if currency:
            return f"{value:,.2f} {currency}"
        return f"{value:,.2f}"

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        label = data.get("label", "Bill")
        total = data.get("total", 0.0)
        currency = data.get("currency", "")
        date_display = data.get("date_display", "")
        time_display = data.get("time_display", "")
        author = data.get("author_name", "unknown")
        has_photo = data.get("has_photo", False)
        bill_type = data.get("bill_type", "")
        ocr_text_data = data.get("ocr_text", "")

        lines = [
            "✅ *Bill Noted & Saved!*",
            f"📋 *Item:* {label}",
            f"💰 *Amount:* {self._fmt_amount(total, currency)}",
            f"📅 *Date:* {date_display}",
            f"🕐 *Time:* {time_display}",
            f"👤 *Payer:* {author}",
        ]
        if bill_type and bill_type != "local_bill":
            lines.append(f"🏷️ *Source:* {bill_type.replace('_', ' ').title()}")
        if has_photo:
            lines.append("🖼️ *Receipt:* Photo Captured & OCR Processed")
            if ocr_text_data:
                preview = ocr_text_data[:120].replace("\n", " ").strip()
                lines.append(f"🔍 *OCR Snippet:* `{preview}`")

        response = "\n".join(lines)

        result = {
            **data,
            "response": response,
        }

        log.info("HUNGER RESPOND bill_id=%s", data.get("bill_id"))
        self._log("respond", {"bill_id": data.get("bill_id")}, {"response": response[:200]})
        return result
