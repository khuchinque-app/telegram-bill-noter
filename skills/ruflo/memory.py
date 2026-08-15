"""AgentDB Memory Patterns — persistent session state + vector recall.

Implements the two memory patterns the agentdb-memory-patterns skill
unit describes:

1. Persistent session states — key/value session memory stored in the
   same SQLite AgentDB file, surviving restarts.
2. Long-term context recall — embeddings stored per row, retrieved by
   cosine similarity. When `hnswlib` is installed, recall uses an HNSW
   graph index (sub-ms at high recall); otherwise it falls back to a
   brute-force cosine scan over the stored vectors. Either way the
   public API is identical.

Embeddings are provided by the caller (e.g. an embedding model or a
simple bag-of-tokens hash for offline use — see `bag_of_tokens`).
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

log = logging.getLogger("ruflo.memory")

try:  # optional HNSW acceleration
    import hnswlib  # type: ignore

    _HAVE_HNSW = True
except Exception:  # pragma: no cover - optional dep
    _HAVE_HNSW = False


def bag_of_tokens(text: str, dim: int = 256) -> List[float]:
    """Deterministic offline embedding: hashed bag-of-tokens, L2-normalized.

    Good enough for recall on small corpora (bills, labels, notes)
    without any external embedding model. Swap for a real embedding
    model when available — the API takes a plain List[float].
    """
    vec = [0.0] * dim
    for token in text.lower().split():
        vec[hash(token) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class VectorMemory:
    """SQLite-backed vector store with optional HNSW index."""

    def __init__(self, db_path: str = "data/swarm_memory.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        self._hnsw: Any = None
        if _HAVE_HNSW:
            try:
                self._init_hnsw()
            except Exception as exc:
                log.warning("HNSW init failed, using brute-force recall: %s", exc)
                self._hnsw = None

    # ── sqlite connection (one per thread) ───────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_sessions (
                session_id  TEXT PRIMARY KEY,
                state       TEXT NOT NULL,
                updated_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS memory_vectors (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content     TEXT NOT NULL,
                vector      TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

    def _init_hnsw(self) -> None:
        rows = self._conn().execute(
            "SELECT vector FROM memory_vectors"
        ).fetchall()
        if not rows:
            return
        dim = len(json.loads(rows[0]["vector"]))
        index = hnswlib.Index(space="cosine", dim=dim)
        index.init_index(max_elements=max(16, len(rows) * 2), ef_construction=200, M=16)
        index.add_items([json.loads(r["vector"]) for r in rows], list(range(len(rows))))
        index.set_ef(50)
        self._hnsw = index
        log.info("HNSW index loaded with %d vectors (dim=%d)", len(rows), dim)

    # ── session state ────────────────────────────────────────────────────

    def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO memory_sessions (session_id, state, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (session_id, json.dumps(state, default=str)),
        )
        conn.commit()

    def load_session(self, session_id: str) -> Dict[str, Any]:
        row = self._conn().execute(
            "SELECT state FROM memory_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return json.loads(row["state"]) if row else {}

    # ── vector memory ────────────────────────────────────────────────────

    def remember(self, content: str, vector: Sequence[float]) -> int:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO memory_vectors (content, vector) VALUES (?, ?)",
            (content, json.dumps(list(vector))),
        )
        conn.commit()
        # Keep the HNSW index warm when it is in use.
        if self._hnsw is not None:
            try:
                self._hnsw.add_items([list(vector)], [cur.lastrowid])
            except Exception as exc:
                log.warning("HNSW add failed, falling back to brute-force: %s", exc)
                self._hnsw = None
        return cur.lastrowid  # type: ignore[return-value]

    def recall(self, query: Sequence[float], k: int = 5) -> List[Tuple[str, float]]:
        """Return (content, similarity) for the k closest memories."""
        q = list(query)
        ids: List[int]
        scores: List[float]

        if self._hnsw is not None:
            try:
                labels, distances = self._hnsw.knn_query([q], k=k)
                ids = [int(i) for i in labels[0] if int(i) >= 0]
                scores = [float(1.0 - d) for d in distances[0][: len(ids)]]
            except Exception as exc:
                log.warning("HNSW query failed, using brute-force: %s", exc)
                ids, scores = self._bruteforce(q, k)
        else:
            ids, scores = self._bruteforce(q, k)

        if not ids:
            return []

        rows = self._conn().execute(
            f"SELECT id, content FROM memory_vectors WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        ).fetchall()
        by_id = {r["id"]: r["content"] for r in rows}
        return [(by_id[i], s) for i, s in zip(ids, scores) if i in by_id]

    def _bruteforce(self, q: List[float], k: int) -> Tuple[List[int], List[float]]:
        rows = self._conn().execute(
            "SELECT id, vector FROM memory_vectors"
        ).fetchall()
        scored: List[Tuple[float, int]] = []
        for r in rows:
            v = json.loads(r["vector"])
            scored.append((self._cosine(q, v), r["id"]))
        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:k]
        return [i for _, i in top], [s for s, _ in top]

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def count(self) -> int:
        return self._conn().execute(
            "SELECT COUNT(*) FROM memory_vectors"
        ).fetchone()[0]

    @property
    def hnsw_enabled(self) -> bool:
        return self._hnsw is not None
