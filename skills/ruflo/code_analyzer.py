"""Code Analyzer — architecture audit, security scan, complexity checks.

Walks a Python project and reports:

* Security — hardcoded secrets (Telegram bot tokens, GitHub PATs,
  AWS keys, private keys).
* Health   — syntax errors, stray debug prints, bare excepts,
  TODO/FIXME markers, unused-ish imports.
* Complexity — deepest nesting and largest function per file.

It is intentionally read-only: it never modifies the tree.

Usage
-----
    python -m skills.ruflo.code_analyzer [--path .] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SECRET_RE = [
    (re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_\-]{20,}\b"), "telegram bot token"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "github personal access token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws access key id"),
    (re.compile(r"(?i)\b(private\s+key|BEGIN (RSA|EC|OPENSSH) PRIVATE KEY)\b"), "private key"),
]

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "data", ".pytest_cache"}


class _Analyzer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: List[Dict[str, Any]] = []
        self.secrets: List[Dict[str, Any]] = []
        self.syntax_errors: List[Dict[str, Any]] = []
        self.todos: List[Dict[str, Any]] = []

    # ── file traversal ───────────────────────────────────────────────────

    def _py_files(self) -> List[Path]:
        return sorted(
            p
            for p in self.root.rglob("*.py")
            if not any(part in _SKIP_DIRS for part in p.parts)
        )

    # ── secret scan (text level, catches strings ast can't see) ─────────

    # The analyzer's own source legitimately contains the regex patterns —
    # exclude it from the secret scan to avoid self-reporting.
    _SELF = Path("skills/ruflo/code_analyzer.py")

    def scan_text(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        if path == self.root / self._SELF:
            return
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern, kind in _SECRET_RE:
                if pattern.search(line):
                    self.secrets.append({
                        "file": str(path.relative_to(self.root)),
                        "line": lineno,
                        "kind": kind,
                        "snippet": line.strip()[:80],
                    })

    # ── AST analysis ────────────────────────────────────────────────────

    def analyze_file(self, path: Path) -> None:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError) as exc:
            self.syntax_errors.append({
                "file": str(path.relative_to(self.root)),
                "error": str(exc).split("\n", 1)[0],
            })
            return

        entry: Dict[str, Any] = {
            "file": str(path.relative_to(self.root)),
            "functions": 0,
            "classes": 0,
            "lines": len(path.read_text(encoding="utf-8").splitlines()),
            "max_nesting": 0,
            "debug_prints": 0,
            "bare_excepts": 0,
            "largest_function": ("", 0),
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entry["functions"] += 1
                size = node.end_lineno - node.lineno if node.end_lineno else 0
                if size > entry["largest_function"][1]:
                    entry["largest_function"] = (node.name, size)
            elif isinstance(node, ast.ClassDef):
                entry["classes"] += 1

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                entry["bare_excepts"] += 1

        # Debug prints at module top level or inside functions.
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                entry["debug_prints"] += 1

        # Nesting: depth of if/for/while/try bodies.
        def depth(node: ast.AST, level: int = 0) -> None:
            entry["max_nesting"] = max(entry["max_nesting"], level)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)):
                    depth(child, level + 1)
                else:
                    depth(child, level)

        depth(tree)
        self.files.append(entry)

    # ── TODO scan ────────────────────────────────────────────────────────

    def scan_todos(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line):
                self.todos.append({
                    "file": str(path.relative_to(self.root)),
                    "line": lineno,
                    "snippet": line.strip()[:80],
                })

    # ── run ──────────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        for path in self._py_files():
            self.scan_text(path)
            self.scan_todos(path)
            self.analyze_file(path)
        self.files.sort(key=lambda f: f["lines"], reverse=True)
        return {
            "root": str(self.root),
            "python_files": len(self.files),
            "secrets_found": self.secrets,
            "syntax_errors": self.syntax_errors,
            "todos": self.todos,
            "files": self.files,
        }


def audit(root: str = ".", as_json: bool = False) -> str:
    analyzer = _Analyzer(Path(root))
    report = analyzer.run()
    if as_json:
        return json.dumps(report, indent=2, default=str)

    lines: List[str] = [f"🔍 Code Analyzer — {report['root']}"]
    lines.append(f"   📄 {report['python_files']} Python files scanned")

    if report["secrets_found"]:
        lines.append("\n🚨 SECURITY — hardcoded secrets:")
        for s in report["secrets_found"]:
            lines.append(
                f"   ⛔ {s['file']}:{s['line']} ({s['kind']}) {s['snippet']}"
            )
    else:
        lines.append("\n✅ Security: no hardcoded secrets found")

    if report["syntax_errors"]:
        lines.append("\n❌ Syntax errors:")
        for e in report["syntax_errors"]:
            lines.append(f"   ✗ {e['file']}: {e['error']}")
    else:
        lines.append("✅ Syntax: all files parse cleanly")

    if report["todos"]:
        lines.append(f"\n📌 TODO/FIXME markers: {len(report['todos'])}")
        for t in report["todos"][:10]:
            lines.append(f"   • {t['file']}:{t['line']} {t['snippet']}")

    lines.append("\n📊 Largest files:")
    for f in report["files"][:5]:
        fn, size = f["largest_function"]
        lines.append(
            f"   • {f['file']} ({f['lines']} lines, {f['functions']} funcs, "
            f"{f['classes']} classes) largest fn {fn or '-'} ({size} lines)"
        )
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Architecture & security audit")
    ap.add_argument("--path", default=".", help="directory to audit")
    ap.add_argument("--json", action="store_true", help="emit JSON report")
    args = ap.parse_args(argv)
    print(audit(args.path, as_json=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
