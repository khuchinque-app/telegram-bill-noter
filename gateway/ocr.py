"""Optional OCR bill detection for photos.

If pytesseract + Pillow are available, a photo is read and its text is checked
for bill content. Otherwise the bot degrades gracefully (flags the photo as a
candidate). The sandbox passes pre-set OCR text via a message `ocr` field.
"""

import logging

log = logging.getLogger("gateway.ocr")

try:
    import pytesseract
    from PIL import Image
    _HAVE_OCR = True
except Exception:  # pragma: no cover - optional deps
    _HAVE_OCR = False


def ocr_text(image_path: str) -> str:
    if not _HAVE_OCR:
        return ""
    try:
        return pytesseract.image_to_string(Image.open(image_path)) or ""
    except Exception as exc:
        log.warning("OCR failed: %s", exc)
        return ""
