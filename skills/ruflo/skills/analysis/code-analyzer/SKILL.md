---
name: code-analyzer
description: Performs deep architecture audits, security scans, performance bottleneck detection, and time-complexity evaluations on Python projects. Use when reviewing a codebase for secrets, syntax errors, dead weight, or structural hotspots.
---

# Code Analyzer

Part of the Ruflo **Development & Analysis** skill set.

## When to use
- Before a release or push: catch hardcoded secrets.
- After big refactors: find syntax errors, bare excepts, debug prints.
- Spotting largest files/functions and nesting depth hotspots.

## Activation
```bash
python -m skills.ruflo.code_analyzer --path .          # human report
python -m skills.ruflo.code_analyzer --path . --json   # machine report
```

## What it scans
1. **Security** — Telegram tokens, GitHub PATs, AWS keys, private keys.
2. **Health** — syntax errors, debug `print()`, bare `except:`,
   TODO/FIXME markers.
3. **Complexity** — max nesting depth, largest function, per-file stats.

## Details
See [REFERENCE.md](REFERENCE.md) for the report schema and
time-complexity evaluation guidance (loaded on demand).
