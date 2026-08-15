---
name: sparc-methodology
description: Structured framework for spec-driven design, architecture, and feature building via Specification, Pseudocode, Architecture, Refinement, Completion. Use when building complex features that need planning before code.
---

# SPARC Methodology

Part of the Ruflo **Development & Analysis** skill set.

## When to use
- New features with ambiguous requirements.
- Multi-agent builds that need a shared plan before implementation.
- Any work where "think before code" pays off.

## The five phases
1. **Specification** — define WHAT: requirements, constraints, acceptance.
2. **Pseudocode** — sketch the solution at a high level, no syntax.
3. **Architecture** — map modules, agents, data flow, interfaces.
4. **Refinement** — tighten edge cases, error paths, performance.
5. **Completion** — implement, test, verify against the spec.

## Activation
Run the phases in order; each phase must produce an artifact before the
next starts (SPEC → PSEUDOCODE → ARCH → REFINED SPEC → CODE).

## Details
See [REFERENCE.md](REFERENCE.md) for phase templates and how SPARC maps
onto this repo's agent pipeline (loaded on demand).
