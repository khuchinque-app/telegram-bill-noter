---
name: skills
description: Skill registry and discovery system for the Telegram Bill Noter bot
---

# Skills System

Runtime skill discovery and loading for the Telegram Bill Noter bot,
with progressive-disclosure skill sets (SKILL.md units) that agents load
on demand.

## Installed Skills

| Skill              | Version | Description                                    | Skill sets |
|--------------------|---------|------------------------------------------------|------------|
| flow-nexus-swarm   | 1.0.0   | Multi-agent swarm orchestrator for bill capture | —          |
| ruflo              | 1.1.0   | Goal-oriented execution + self-optimization    | 7 units    |

## Ruflo Skill Sets (progressive disclosure)

Ruflo ships 7 SKILL.md units organized into 3 skill sets. Read a unit's
`SKILL.md` first; open its `REFERENCE.md` only when you need depth:

### 🧭 Orchestration & Planning
| Skill unit             | Capability                                        |
|------------------------|---------------------------------------------------|
| swarm-orchestration    | Multi-agent task allocation, topologies, loops    |
| goal-planner-goap      | GOAP planning with A* search                      |
| skill-builder          | Scaffolds new Claude Code skill units             |

### 🧠 Memory & Self-Learning
| Skill unit                | Capability                                      |
|---------------------------|-------------------------------------------------|
| agentdb-memory-patterns   | Sessions, HNSW vectors, long-term recall        |
| agentdb-learning          | Adaptive pattern learning, curriculum, SONA     |

### 🔬 Development & Analysis
| Skill unit           | Capability                                       |
|----------------------|--------------------------------------------------|
| code-analyzer        | Security / health / complexity audits            |
| sparc-methodology    | Spec-driven design & feature building            |

## How It Works

1. `SkillRegistry.discover()` scans subdirectories of `skills/`
2. Each skill has a `__init__.py` with a `skill_info` dict
3. `SkillRegistry.discover_skill_units()` walks `skills/<name>/skills/**`
   and indexes every SKILL.md frontmatter (`name`, `description`, path)
4. `SkillRegistry.load(name)` instantiates the skill's entry point class
5. The main bot (`bill_noter/bot.py`) loads the `BillGatewaySkill` at startup

## Adding New Skills

Create a directory under `skills/` with:
- `__init__.py` containing a `skill_info` dict
- `SKILL.md` with documentation
- Your Python modules

For a new **skill set unit** inside Ruflo, use the Skill Builder:
```bash
python -m skills.ruflo.skill_builder --name my-skill --description "Does X. Use when Y."
```
