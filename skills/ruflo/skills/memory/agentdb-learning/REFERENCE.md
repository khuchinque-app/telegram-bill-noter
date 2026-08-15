# AgentDB Learning — Reference

## Contents
- Data sources
- Hint vocabulary
- Curriculum learning schedule
- SONA extension

## Data sources
| Source           | Columns used                              | Read by              |
|------------------|-------------------------------------------|----------------------|
| `agent_log`      | `agent_id`, `success`, `error`, `created_at` | stats + optimize  |
| `agent_state`    | `agent_id`, `key`, `value`                | hints written here   |
| `bills`          | `amount`, `currency`, `label`, `status`   | curriculum staging   |

## Hint vocabulary
`SelfOptimizer.optimize()` writes one of:

| Hint            | Condition                  | Meaning                    |
|-----------------|----------------------------|----------------------------|
| `needs_attention` | success_rate < 0.70      | review this agent          |
| `monitor`         | 0.70 ≤ rate < 0.90      | watch, may regress         |
| `optimal`         | rate ≥ 0.90              | healthy                    |

Thresholds are constants — tune them to your tolerance.

## Curriculum learning schedule
Progress through ingestion stages, oldest/simplest first:
1. Text bills (clean, one price)
2. Text bills with multiple prices
3. Simple receipts (single-line OCR)
4. Multi-item / subtotal receipts (max-price heuristic active)

Each stage's completion is measured by parse success rate in `agent_log`.

## SONA extension
SONA (Self-Organizing Neural Adaptation) is the planned neural layer:
- **Inputs:** per-agent `runs`, `successes`, error strings, bill features
  from `bills`.
- **Outputs:** predicted next success rate + suggested parameter deltas
  (e.g. OCR sensitivity, price heuristic).
- **Storage:** read from/write to `agent_state` — the schema is already
  compatible, so adding a trained model is a drop-in change.
