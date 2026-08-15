# AgentDB Memory Patterns — Reference

## Contents
- Tables and schema
- HNSW tuning
- Embedding choice
- Recall quality guidance

## Tables and schema
Created automatically by `VectorMemory`:

| Table             | Purpose                          | Key/columns                              |
|-------------------|----------------------------------|------------------------------------------|
| `memory_sessions` | persistent session state         | `session_id` PK, `state` (JSON), `updated_at` |
| `memory_vectors`  | content + embedding for recall   | `id` PK, `content`, `vector` (JSON), `created_at` |

Both live in the same `data/swarm_memory.db` file as the swarm tables
(`bills`, `agent_state`, `agent_log`), so one backup covers everything.

## HNSW tuning
`hnswlib.Index(space="cosine", dim=D)` with:
- `M = 16` — links per node; higher = better recall, more memory.
- `ef_construction = 200` — build-time quality.
- `set_ef(50)` — query-time recall/space trade-off.

If the index cannot be built (no `hnswlib`), `recall()` transparently
falls back to a full cosine scan — behavior is identical, just slower at
scale.

## Embedding choice
- **Offline / no deps:** `bag_of_tokens(text, dim=256)` — hashed
  bag-of-tokens, L2-normalized. Fine for small corpora; no internet or
  model needed.
- **Production:** pass embeddings from any model (OpenAI, sentence
  transformers, etc.). The API is just `List[float]` — swap freely.

## Recall quality guidance
1. Store the *same* text shape you will query with (labels ↔ labels).
2. k should be small (3–10) for bill recall; filter by similarity
   threshold if you need precision.
3. Normalize vectors yourself when using a custom model — cosine ignores
   magnitude, but consistency helps HNSW.
