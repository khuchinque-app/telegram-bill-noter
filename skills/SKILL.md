---
name: skills
description: Skill registry and discovery system for the Telegram Bill Noter bot
---

# Skills System

Runtime skill discovery and loading for the Telegram Bill Noter bot.

## Installed Skills

| Skill              | Version | Description                                    |
|--------------------|---------|------------------------------------------------|
| flow-nexus-swarm   | 1.0.0   | Multi-agent swarm orchestrator for bill capture|
| ruflo              | 1.0.0   | Goal-oriented execution and self-optimization  |

## How It Works

1. `SkillRegistry.discover()` scans subdirectories of `skills/`
2. Each skill has a `__init__.py` with a `skill_info` dict
3. `SkillRegistry.load(name)` instantiates the skill's entry point class
4. The main bot (`bill_noter/bot.py`) loads the `BillGatewaySkill` at startup

## Adding New Skills

Create a directory under `skills/` with:
- `__init__.py` containing a `skill_info` dict
- `SKILL.md` with documentation
- Your Python modules
