# Skill Builder — Reference

## Contents
- Directory layout
- SKILL.md frontmatter
- Progressive disclosure rules
- Registry wiring

## Directory layout
```
skills/<namespace>/
└── <skill-name>/
    ├── SKILL.md          # required: frontmatter + overview
    ├── REFERENCE.md      # optional: deep detail, one level deep
    ├── __init__.py       # optional: runtime skill_info
    └── scripts/          # optional: executable utilities
```

## SKILL.md frontmatter
```yaml
---
name: my-skill            # lowercase, digits, hyphens, ≤64 chars
description: Does X. Use when Y.   # third person, what + when
---
```
The description is what the runtime registry and any skill loader reads
to decide when to load this skill — make it specific.

## Progressive disclosure rules
1. Keep SKILL.md under 500 lines; it is loaded eagerly once relevant.
2. Reference detail files **one level deep** only — nested references
   cause partial reads.
3. Reference files over ~100 lines should start with a `## Contents` TOC.
4. Put exact commands/scripts in the skill dir; don't inline fragile
   shell in SKILL.md.

## Registry wiring
The runtime `SkillRegistry` discovers Python packages under `skills/`
that export `skill_info`. A generated `__init__.py`:

```python
skill_info = {
    "name": "my-skill",
    "version": "1.0.0",
    "description": "Does X. Use when Y.",
}
```
