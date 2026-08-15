"""Bill Noter bot package.

Note: `.bot` is imported lazily by the entry point so that the pure parsing and
storage modules can be used (e.g. in --self-test) without python-telegram-bot.
"""

from .notes_store import Note, NotesStore
from .price_parser import extract_label, parse_prices

__all__ = [
    "Note",
    "NotesStore",
    "extract_label",
    "parse_prices",
]
