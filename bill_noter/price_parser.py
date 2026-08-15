"""Price parsing for the bill/price noter bot."""

import re
from dataclasses import dataclass
from typing import List, Optional

_CURRENCY_SYMBOLS = "€$£¥฿₫₱₹Rp"
_CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "RUB", "UAH", "KZT", "INR", "CNY", "IDR", "THB", "SGD", "MYR", "VND", "PHP"}
_CURRENCY_NAMES = {
    "EURO": "EUR", "EUROS": "EUR", "DOLLAR": "USD", "DOLLARS": "USD",
    "POUND": "GBP", "POUNDS": "GBP", "RUBLE": "RUB", "RUBLES": "RUB",
    "YEN": "JPY", "RUPEE": "INR", "RUPEES": "INR", "YUAN": "CNY",
    "RUPIAH": "IDR", "RP": "IDR", "BAHT": "THB", "RINGGIT": "MYR", "RM": "MYR",
    "PESO": "PHP", "PESOS": "PHP", "DONG": "VND", "SGD": "SGD",
}

# A number: optional leading currency symbol, then digits with , . and spaces.
_NUM_RE = re.compile(
    r"[€$£¥]?\s*\d[\d.,]*\d"   # symbol + multi-digit number
    r"|\d+(?:[.,]\d{1,2})?",     # or a simple number with optional 1-2 decimal digits
    re.VERBOSE,
)
_TRAILING_CODE_RE = re.compile(r"^\s*([A-Za-z]{3,})\b")


@dataclass
class PriceMatch:
    """A single parsed price found in a message."""

    value: float
    currency: str
    raw: str
    start: int
    end: int


def _normalize_number(token: str) -> Optional[float]:
    """Turn a messy numeric string into a float, handling , / . as decimal or thousands."""
    digits = re.sub(r"[^0-9.,]", "", token)
    if not digits:
        return None
    if "," in digits and "." in digits:
        # Last separator is the decimal separator; the other is thousands.
        if digits.rfind(",") > digits.rfind("."):
            dec, thou = ",", "."
        else:
            dec, thou = ".", ","
        digits = digits.replace(thou, "").replace(dec, ".")
    elif "," in digits:
        parts = digits.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            digits = f"{parts[0]}.{parts[1]}"
        else:
            digits = digits.replace(",", "")
    elif "." in digits:
        parts = digits.split(".")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            pass  # already decimal
        else:
            digits = digits.replace(".", "")
    try:
        return float(digits)
    except ValueError:
        return None


def _currency_from_token(token: str) -> str:
    """Detect a currency from a leading symbol or a trailing known code/name."""
    token = token.strip()
    if token and token[0] in _CURRENCY_SYMBOLS:
        return token[0]
    m = re.search(r"([A-Za-z]{3,})\s*$", token)
    if m:
        up = m.group(1).upper()
        if up in _CURRENCY_CODES:
            return up
        if up in _CURRENCY_NAMES:
            return _CURRENCY_NAMES[up]
    return ""


def parse_prices(text: str) -> List[PriceMatch]:
    """Return every price found in `text`, left to right."""
    found: List[PriceMatch] = []
    for m in _NUM_RE.finditer(text):
        token = m.group(0)
        start, end = m.start(), m.end()
        value = _normalize_number(token)
        if value is None:
            continue
        # Extend the span to consume a trailing currency code (so it leaves the label).
        cm = _TRAILING_CODE_RE.match(text[end:])
        if cm and cm.group(1).upper() in (_CURRENCY_CODES | _CURRENCY_NAMES.keys()):
            end = end + cm.end()
            token = text[m.start():end]
        currency = _currency_from_token(token)
        found.append(
            PriceMatch(value=value, currency=currency, raw=token.strip(),
                       start=m.start(), end=end)
        )
    return found


def extract_label(text: str, prices: List[PriceMatch]) -> str:
    """Build a human label by removing the price tokens from the message."""
    if not prices:
        return text.strip()
    # Remove matched spans (longest first to keep indices valid).
    spans = sorted(((p.start, p.end) for p in prices), reverse=True)
    label = text
    for start, end in spans:
        label = label[:start] + " " + label[end:]
    label = re.sub(r"\s+", " ", label).strip()
    # Strip common leading markers like "bill:" or "price:".
    label = re.sub(r"^(bill|price|cost|paid|expense|note|buy|bought)\s*[:\-]?\s*",
                   "", label, flags=re.IGNORECASE)
    return label or "untitled"
