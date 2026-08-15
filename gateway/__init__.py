"""Gateway: detect fresh bills in every Telegram chat.

This package monitors all the chats a Telegram account has access to and reports
whether each chat contains a *fresh* (unseen since the last scan) bill.

Two modes (the "Telegram keys" the gateway knows):
  * user session  -- full coverage: enumerates every dialog via get_dialogs()
                     and reads recent history. Requires api_id/api_hash + a
                     logged-in session (no bot_token).
  * bot listener -- live @on_message: works only in chats the bot is a member
                     of (admin / privacy disabled to see all messages).

Bill detection reuses bill_noter.price_parser so behavior stays consistent with
the rest of the workspace.
"""

from .bill_detector import AnalyzedMessage, analyze
from .checkpoint import Checkpoint
from .gateway import TelegramGateway

__all__ = ["analyze", "AnalyzedMessage", "Checkpoint", "TelegramGateway"]
