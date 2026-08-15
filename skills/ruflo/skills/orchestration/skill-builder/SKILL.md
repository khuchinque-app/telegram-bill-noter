---
name: skill-builder
description: Autonomously creates and scaffolds new modular Claude Code Skills with SKILL.md frontmatter, a REFERENCE.md for progressive disclosure, and a runtime skill_info registry entry. Use when adding a new capability to the skills tree.
---

# Skill Builder

Part of the Ruflo **Orchestration & Planning** skill set.

## When to use
- Adding a new skill unit to `skills/`.
- Standardizing the SKILL.md + REFERENCE.md structure.

## Activation
```bash
python -m skills.ruflo.skill_builder \
    --name my-skill \
    --description "Does X. Use when Y." \
    --dir skills/ruflo/skills/orchestration
```

Generates:
```
my-skill/
├── SKILL.md            # frontmatter + overview (loaded first)
├── REFERENCE.md        # deep detail (loaded on demand)
├── __init__.py         # skill_info for the runtime registry
└── tests/test_scaffold.py
```

## Naming rules (Claude Code)
- lowercase letters, digits, hyphens only; ≤ 64 chars
- gerund form preferred: `parsing-prices`, `recalling-memory`
- description: third person, *what* it does + *when* to use it

## Details
See [REFERENCE.md](REFERENCE.md) for templates and progressive-disclosure
guidance (loaded on demand).
