# Code Analyzer — Reference

## Contents
- Report schema
- Secret patterns
- Time-complexity evaluation
- Performance bottleneck detection

## Report schema
The JSON report (`--json`) has:
- `python_files` — count scanned
- `secrets_found` — file, line, kind, snippet
- `syntax_errors` — file, error
- `todos` — file, line, snippet
- `files` — per-file: lines, functions, classes, max_nesting,
  debug_prints, bare_excepts, largest_function

## Secret patterns
| Pattern                                | Kind                     |
|----------------------------------------|--------------------------|
| `\d{8,10}:AA[A-Za-z0-9_-]{20,}`        | Telegram bot token       |
| `ghp_[A-Za-z0-9]{20,}`                 | GitHub PAT               |
| `AKIA[0-9A-Z]{16}`                     | AWS access key id        |
| `BEGIN (RSA|EC|OPENSSH) PRIVATE KEY`   | private key              |

Any hit should be rotated and removed from history — the analyzer is
read-only, so removal is a separate step.

## Time-complexity evaluation
For each function, evaluate worst-case Big-O by loop structure:
- single loop over input → O(n)
- nested loop → O(n²)
- dict/set lookups inside loops → amortized O(1) each
- recursive without memoization → exponential (flag for review)
- sort inside a loop → O(n log n) each iteration

Report anything beyond O(n²) on hot paths (e.g. `_bruteforce` recall is
O(n) per query — fine for small corpora, but flag it when the vector
table grows).

## Performance bottleneck detection
Signals the analyzer surfaces:
- `max_nesting > 4` — candidate for early-exit or helper extraction
- `largest_function` with hundreds of lines — refactor candidate
- `debug_prints` in hot loops — I/O in loops is a classic bottleneck
