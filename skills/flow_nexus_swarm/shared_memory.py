"""Shared memory layer — SQLite-backed persistence for the swarm.

Stores bills, agent state, and action logs.  Thread-safe via per-thread
connections.  The database is created automatically at first use.

Deduplication: every bill gets a content fingerprint (chat, author,
label, amount, currency, raw text). If identical data is fed again — a
re-sent message, a re-run of hunger_catchup on the same export, or the
gateway and bot both consuming the same bill — `save_bill` raises
`DuplicateBillError` and nothing is stored twice.
"""

import hashlib
import json
import logging
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("swarm.memory")


class DuplicateBillError(Exception):
    """Raised when identical bill data is fed in again.

    Attributes
    ----------
    existing_id : int
        The id of the bill already stored with the same fingerprint.
    """

    def __init__(self, existing_id: int, fingerprint: str) -> None:
        self.existing_id = existing_id
        self.fingerprint = fingerprint
        super().__init__(
            f"duplicate bill rejected — already stored as #{existing_id}"
        )


def bill_fingerprint(
    chat_id: int,
    author_id: int,
    label: str,
    amount: float,
    currency: str,
    raw_text: str,
) -> str:
    """Stable content hash — identical data always yields the same key.

    Normalization: lower-case, whitespace collapsed, amount rounded to
    two decimals, currency uppercased. Two feeds of the same bill (same
    chat, author, label, amount, currency, raw text) collide on purpose.
    """
    def norm(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    key = "|".join([
        str(chat_id),
        str(author_id),
        norm(label),
        f"{float(amount or 0):.2f}",
        norm(currency),
        norm(raw_text),
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class AgentDB:
    """SQLite shared memory backend for the flow-nexus-swarm agents.

    Tables
    ------
    bills        — every captured bill (text or photo).
    agent_state  — per-agent key/value store for hints & config.
    agent_log    — audit trail of every agent action.
    """

    def __init__(self, db_path: str = "data/swarm_memory.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        log.info("AgentDB ready — %s", self.db_path)

    # ── connection (one per thread) ───────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    # ── schema ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bills (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER,
                message_id  INTEGER,
                author_id   INTEGER,
                author_name TEXT,
                bill_type   TEXT,
                source      TEXT,
                label       TEXT,
                amount      REAL,
                currency    TEXT,
                raw_text    TEXT,
                image_path  TEXT,
                fingerprint TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now')),
                confirmed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS agent_state (
                agent_id   TEXT,
                key        TEXT,
                value      TEXT,
                updated_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (agent_id, key)
            );

            CREATE TABLE IF NOT EXISTS agent_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id    TEXT,
                action      TEXT,
                input_data  TEXT,
                output_data TEXT,
                success     INTEGER,
                error       TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        self._migrate_bills(conn)
        conn.commit()

    def _migrate_bills(self, conn: sqlite3.Connection) -> None:
        """Add the fingerprint column + unique index to pre-existing DBs."""
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(bills)")}
        if "fingerprint" not in cols:
            conn.execute("ALTER TABLE bills ADD COLUMN fingerprint TEXT")
            log.info("AgentDB migration: added bills.fingerprint")

        # Backfill fingerprints for rows stored before dedup existed, so
        # re-feeding old data is rejected too.
        rows = conn.execute(
            "SELECT id, chat_id, author_id, label, amount, currency, raw_text "
            "FROM bills WHERE fingerprint IS NULL"
        ).fetchall()
        for r in rows:
            fp = bill_fingerprint(
                chat_id=r["chat_id"] or 0,
                author_id=r["author_id"] or 0,
                label=r["label"] or "",
                amount=r["amount"] or 0,
                currency=r["currency"] or "",
                raw_text=r["raw_text"] or "",
            )
            conn.execute("UPDATE bills SET fingerprint = ? WHERE id = ?", (fp, r["id"]))
        if rows:
            log.info("AgentDB migration: backfilled %d fingerprints", len(rows))

        # Unique index enforces dedup at the database level too. If a
        # pre-existing DB already contains true duplicates the index
        # creation fails — the Python check still protects new inserts.
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_bills_fingerprint "
                "ON bills(fingerprint)"
            )
        except sqlite3.IntegrityError as exc:
            log.warning("could not create unique index (pre-existing duplicates?): %s", exc)

    # ── bills ─────────────────────────────────────────────────────────────

    def save_bill(
        self,
        chat_id: int,
        message_id: int,
        author_id: int,
        author_name: str,
        bill_type: str,
        source: str,
        label: str,
        amount: float,
        currency: str,
        raw_text: str,
        image_path: Optional[str] = None,
    ) -> int:
        """Store a bill, rejecting identical data that was already consumed.

        Raises DuplicateBillError when a bill with the same content
        fingerprint already exists — the caller should report this as a
        rejection instead of storing it.
        """
        fp = bill_fingerprint(chat_id, author_id, label, amount, currency, raw_text)
        existing = self._conn().execute(
            "SELECT id FROM bills WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if existing is not None:
            log.info("REJECT duplicate bill (fp=%s...) existing_id=%s",
                     fp[:12], existing["id"])
            raise DuplicateBillError(existing["id"], fp)

        conn = self._conn()
        cur = conn.execute(
            """INSERT INTO bills
               (chat_id, message_id, author_id, author_name, bill_type,
                source, label, amount, currency, raw_text, image_path, fingerprint)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (chat_id, message_id, author_id, author_name, bill_type,
             source, label, amount, currency, raw_text, image_path, fp),
        )
        conn.commit()
        log.info("save_bill id=%s label=%r amount=%.2f", cur.lastrowid, label, amount)
        return cur.lastrowid  # type: ignore[return-value]

    def get_bill(self, bill_id: int) -> Optional[Dict[str, Any]]:
        row = self._conn().execute(
            "SELECT * FROM bills WHERE id = ?", (bill_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_bills(self, chat_id: Optional[int] = None,
                   limit: int = 50) -> List[Dict[str, Any]]:
        if chat_id is not None:
            rows = self._conn().execute(
                "SELECT * FROM bills WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
                (chat_id, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM bills ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def update_bill_status(self, bill_id: int, status: str) -> None:
        conn = self._conn()
        if status == "confirmed":
            conn.execute(
                "UPDATE bills SET status = ?, confirmed_at = datetime('now') WHERE id = ?",
                (status, bill_id),
            )
        else:
            conn.execute(
                "UPDATE bills SET status = ? WHERE id = ?", (status, bill_id)
            )
        conn.commit()

    def total_bills(self, chat_id: int) -> Dict[str, Any]:
        row = self._conn().execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount), 0) as total FROM bills WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return {"count": row["cnt"], "total": row["total"]} if row else {"count": 0, "total": 0}

    # ── agent state ───────────────────────────────────────────────────────

    def set_agent_state(self, agent_id: str, key: str, value: Any) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO agent_state (agent_id, key, value, updated_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (agent_id, key, json.dumps(value, default=str)),
        )
        conn.commit()

    def get_agent_state(self, agent_id: str, key: str) -> Any:
        row = self._conn().execute(
            "SELECT value FROM agent_state WHERE agent_id = ? AND key = ?",
            (agent_id, key),
        ).fetchone()
        return json.loads(row["value"]) if row else None

    # ── agent log ─────────────────────────────────────────────────────────

    def log_action(
        self,
        agent_id: str,
        action: str,
        input_data: str,
        output_data: str,
        success: bool,
        error: str = "",
    ) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT INTO agent_log
               (agent_id, action, input_data, output_data, success, error)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (agent_id, action, input_data, output_data, int(success), error),
        )
        conn.commit()

    def get_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        """Return success/failure stats per agent from the log."""
        rows = self._conn().execute(
            """SELECT agent_id,
                      COUNT(*) as runs,
                      SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
               FROM agent_log
               GROUP BY agent_id"""
        ).fetchall()
        stats: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            runs = r["runs"]
            succ = r["successes"]
            stats[r["agent_id"]] = {
                "runs": runs,
                "successes": succ,
                "success_rate": round(succ / runs, 4) if runs else 1.0,
            }
        return stats
