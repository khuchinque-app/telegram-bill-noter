---
name: agentdb-memory-patterns
description: Implements persistent session states, HNSW-indexed vector storage, and long-term context recall over the SQLite AgentDB. Use when storing or retrieving agent memory across sessions, or when adding semantic recall of past bills.
---

# AgentDB Memory Patterns

Part of the Ruflo **Memory & Self-Learning** skill set.

## When to use
- Persisting session state that must survive restarts.
- Storing/recalling memories by similarity (bills, labels, notes).
- Choosing between HNSW acceleration and brute-force fallback.

## Activation
```python
from skills.ruflo.memory import VectorMemory, bag_of_tokens

mem = VectorMemory("data/swarm_memory.db")
bid = mem.remember("GrabFood dinner 35.50 USD", bag_of_tokens("GrabFood dinner 35.50 USD"))
hits = mem.recall(bag_of_tokens("grab dinner"), k=5)
mem.save_session("chat-42", {"unconfirmed": 3})
state = mem.load_session("chat-42")
```

## Patterns
1. **Session state** — `memory_sessions` table (session_id → JSON state).
2. **Vector recall** — `memory_vectors` table (content + embedding);
   cosine similarity, HNSW graph index when `hnswlib` is installed,
   brute-force scan otherwise.
3. **Offline embeddings** — `bag_of_tokens()` hash embedding needs no
   model; swap for a real embedding model by passing your own vector.

## Details
See [REFERENCE.md](REFERENCE.md) for schema, HNSW tuning, and
recall-quality guidance (loaded on demand).
