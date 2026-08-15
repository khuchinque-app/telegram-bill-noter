"""Skill Builder — autonomously scaffolds new modular Claude Code Skills.

Creates a progressive-disclosure skill unit: a directory with a
SKILL.md (frontmatter + overview), an `__init__.py` exposing a
`skill_info` dict for the runtime registry, and a tests/ stub.

Usage
-----
    python -m skills.ruflo.skill_builder \\
        --name my-skill \\
        --description "Does X. Use when..." \\
        --dir skills/ruflo/skills/custom
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from typing import Optional

_SKILL_MD_TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

{summary}

## When to use
{when_to_use}

## Activation
{activation}

## Quick start
{quick_start}

## Details
See [REFERENCE.md](REFERENCE.md) for the full reference (loaded on demand).
"""

_REFERENCE_TEMPLATE = """# {title} — Reference

## Contents
- Architecture
- Configuration
- Examples

## Architecture
(TODO)

## Configuration
(TODO)

## Examples
(TODO)
"""

_INIT_TEMPLATE = '''"""Skill builder scaffold for: {name}."""

skill_info = {{
    "name": "{name}",
    "version": "1.0.0",
    "description": "{description}",
}}

__all__ = ["skill_info"]
'''

_TEST_TEMPLATE = '''"""Smoke test for the {name} skill scaffold."""

from {import_path} import skill_info


def test_skill_info():
    assert skill_info["name"] == "{name}"
    assert skill_info["description"]
'''


def _valid_name(name: str) -> bool:
    """Claude Code skill names: lowercase letters, digits, hyphens."""
    return bool(re.fullmatch(r"[a-z0-9-]+", name)) and len(name) <= 64


def build_skill(
    name: str,
    description: str,
    dest_dir: str = "skills/ruflo/skills",
    summary: str = "Progressive-disclosure skill unit.",
    when_to_use: str = "When the agent needs this capability.",
    activation: str = "Load this SKILL.md; read REFERENCE.md only when deeper detail is needed.",
    quick_start: str = "See the examples in REFERENCE.md.",
    import_path: Optional[str] = None,
) -> Path:
    """Create a new skill directory and return its path."""
    if not _valid_name(name):
        raise ValueError(
            f"invalid skill name {name!r}: use lowercase letters, digits, hyphens"
        )
    if not description:
        raise ValueError("description is required")

    dest = Path(dest_dir)
    skill_dir = dest / name
    if skill_dir.exists():
        raise FileExistsError(f"{skill_dir} already exists")

    title = " ".join(word.capitalize() for word in name.split("-"))
    import_path = import_path or f"{name.replace('-', '_')}"
    files = {
        "SKILL.md": _SKILL_MD_TEMPLATE.format(
            name=name, description=description, title=title,
            summary=summary, when_to_use=when_to_use,
            activation=activation, quick_start=quick_start,
        ),
        "REFERENCE.md": _REFERENCE_TEMPLATE.format(title=title),
        "__init__.py": _INIT_TEMPLATE.format(name=name, description=description),
        "tests/__init__.py": "",
        "tests/test_scaffold.py": _TEST_TEMPLATE.format(
            name=name, import_path=import_path.replace("-", "_")
        ),
    }
    for rel, content in files.items():
        path = skill_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return skill_dir


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a new Claude Code skill")
    ap.add_argument("--name", required=True, help="lowercase-hyphen skill name")
    ap.add_argument("--description", required=True, help="what it does + when to use")
    ap.add_argument("--dir", default="skills/ruflo/skills", help="destination directory")
    args = ap.parse_args(argv)

    try:
        path = build_skill(args.name, args.description, dest_dir=args.dir)
    except (ValueError, FileExistsError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    print(f"✔ Scaffolded skill: {path}")
    print(f"  • {path / 'SKILL.md'}   (overview — loaded first)")
    print(f"  • {path / 'REFERENCE.md'}  (details — loaded on demand)")
    print(f"  • {path / '__init__.py'}   (runtime skill_info registry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
