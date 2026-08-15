"""Entry point for the Telegram bill gateway.

Usage:
  python gateway/gateway_run.py --self-test            # offline proof (no Telegram)
  python gateway/gateway_run.py                        # live user-session scan
  python gateway/gateway_run.py --mode bot --token TOKEN   # live bot listener
  python gateway/gateway_run.py --standby              # ALWAYS-ON bot listener
                                                       # (token from --token, BILL_NOTER_TOKEN, or .env)

Standby mode is the production way to run the gateway: it listens
continuously, stores every fresh bill into the shared AgentDB
(dedup-guarded), and replies in-chat. Pair it with `heal.py` so it
never stays down.

Credentials (user mode) come from app/conf/config.ini [pyrogram] or the
environment: TG_API_ID, TG_API_HASH, TG_SESSION.
"""

import argparse
import configparser
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.bill_detector import analyze
from gateway.checkpoint import Checkpoint
from gateway.gateway import TelegramGateway
from gateway.sandbox import SandboxClient

# Offline sample messages spanning two chats.
SAMPLE = [
    {"id": 1, "chat_id": -1001, "date": "2026-08-15T10:00:00", "text": "Lunch 12.50"},
    {"id": 2, "chat_id": -1001, "date": "2026-08-15T10:05:00", "text": "halo guys"},
    {"id": 3, "chat_id": -1001, "date": "2026-08-15T10:10:00", "photo": True},
    {"id": 4, "chat_id": -1002, "date": "2026-08-15T11:00:00", "text": "Taxi €23,40"},
    {"id": 5, "chat_id": -1002, "date": "2026-08-15T11:30:00", "text": "meeting at noon"},
]


def self_test(state_path: str) -> int:
    print("=== gateway self-test (offline) ===")
    cp = Checkpoint(state_path)
    max_id: dict = {}

    def sweep():
        fresh = []
        for m in SAMPLE:
            a = analyze(m)
            max_id[a.chat_id] = max(max_id.get(a.chat_id, 0), a.message_id)
            if a.is_bill and a.message_id > cp.get(a.chat_id)["last_id"]:
                fresh.append(a)
        return fresh

    fresh1 = sweep()
    for cid, mid in max_id.items():
        cp.update(cid, mid, "")
    print("PASS 1 fresh bills:", [(b.label, b.prices) for b in fresh1])
    print("PASS 1 candidate photos:",
          [a.message_id for a in (analyze(m) for m in SAMPLE)
           if a.is_bill_candidate and a.message_id > cp.get(a.chat_id)["last_id"]])

    fresh2 = sweep()  # checkpoint already advanced -> nothing new
    print("PASS 2 fresh bills (should be empty):", [(b.label) for b in fresh2])
    print("checkpoint:", cp.data)
    print("=== done ===")
    return 0


def load_user_config():
    api_id = os_env("TG_API_ID")
    api_hash = os_env("TG_API_HASH")
    session = os_env("TG_SESSION") or "session/gateway_client"
    cfg = Path("app/conf/config.ini")
    if cfg.exists():
        p = configparser.ConfigParser()
        p.read(cfg)
        if "pyrogram" in p:
            sec = p["pyrogram"]
            api_id = api_id or sec.get("api_id", "")
            api_hash = api_hash or sec.get("api_hash", "")
            session = session or sec.get("session_name", session)
    return api_id, api_hash, session


def os_env(name: str) -> str:
    return os.environ.get(name, "")


def _load_env_file(path: str = ".env") -> None:
    """Minimal .env loader (no extra dependency), matching bill_noter/bot.py."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


# Default practice chat the AUTOBOT targets in sandbox mode.
SANDBOX_PENCATATBILL2 = -1006006006006


def main() -> int:
    ap = argparse.ArgumentParser(description="Telegram bill gateway (AUTOBOT)")
    ap.add_argument("--self-test", action="store_true", help="offline proof")
    ap.add_argument("--sandbox", action="store_true",
                    help="run against the in-repo sandbox (no Telegram)")
    ap.add_argument("--mode", choices=["user", "bot"], default="user")
    ap.add_argument("--token", default="", help="bot token (bot mode)")
    ap.add_argument("--standby", action="store_true",
                    help="ALWAYS-ON bot listener: consume+store incoming bills")
    ap.add_argument("--chat", type=int, default=None,
                    help="scan ONLY this chat id (e.g. pencatatbill2)")
    ap.add_argument("--autobot", action="store_true",
                    help="run the automatic loop (scan on interval)")
    ap.add_argument("--interval", type=int, default=15,
                    help="AUTOBOT scan interval in seconds")
    ap.add_argument("--state", default="gateway/gateway_state.json")
    ap.add_argument("--history", type=int, default=20)
    args = ap.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
    )

    _load_env_file()

    if args.self_test:
        return self_test(args.state)

    # Auto-heal heartbeat — lets `heal.py` detect hangs.
    try:
        from heal import start_heartbeat
        start_heartbeat("gateway", interval=10)
    except Exception as exc:
        logging.getLogger("gateway").warning("heartbeat unavailable: %s", exc)

    # Sandbox: default to pencatatbill2 if no chat given.
    chat = args.chat
    if args.sandbox and chat is None:
        chat = SANDBOX_PENCATATBILL2

    if args.sandbox:
        gw = TelegramGateway(state_path=args.state)
        client_factory = lambda: SandboxClient("gateway/sandbox_data.json")
        if args.autobot:
            gw.run_autobot(client_factory, interval=args.interval, chat_id=chat)
        else:
            gw.run_sandbox(client_factory(), chat_id=chat)
        return 0

    if args.standby:
        token = args.token or os_env("BILL_NOTER_TOKEN") or os_env("GATEWAY_TOKEN")
        if not token:
            raise SystemExit(
                "standby mode needs a bot token — set BILL_NOTER_TOKEN in .env "
                "or pass --token"
            )
        log = logging.getLogger("gateway")
        log.info("GATEWAY STANDBY engaged — always listening & consuming bills")
        TelegramGateway(state_path=args.state).run_bot(token)
        return 0

    if args.mode == "bot":
        token = args.token or os_env("BILL_NOTER_TOKEN") or os_env("GATEWAY_TOKEN")
        if not token:
            raise SystemExit("--token (or BILL_NOTER_TOKEN) required for bot mode")
        TelegramGateway(state_path=args.state).run_bot(token)
        return 0

    api_id, api_hash, session = load_user_config()
    if not (api_id and api_hash):
        raise SystemExit(
            "TG_API_ID/TG_API_HASH (or app/conf/config.ini [pyrogram]) required "
            "for user-mode scan"
        )
    gw = TelegramGateway(api_id, api_hash, session, args.state, args.history)
    client_factory = lambda: __import__("pyrogram").Client(
        session, api_id=api_id, api_hash=api_hash
    )
    if args.autobot:
        gw.run_autobot(client_factory, interval=args.interval, chat_id=chat)
    else:
        gw.run_scan(chat_id=chat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
