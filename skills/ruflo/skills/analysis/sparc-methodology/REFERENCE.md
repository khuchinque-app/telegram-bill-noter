# SPARC Methodology — Reference

## Contents
- Phase artifacts
- Phase templates
- SPARC × Ruflo pipeline mapping

## Phase artifacts
| Phase          | Artifact         | Exit criteria                              |
|----------------|------------------|--------------------------------------------|
| Specification  | SPEC.md          | requirements + acceptance criteria agreed  |
| Pseudocode     | PSEUDOCODE.md    | solution sketch, algorithm chosen          |
| Architecture   | ARCH.md          | module/agent map, interfaces, data flow    |
| Refinement     | REFINED-SPEC.md  | edge cases, error paths, complexity budget |
| Completion     | code + tests     | all acceptance criteria pass               |

## Phase templates
**Specification:**
```
Goal: <one sentence>
Users: <who>
Inputs: <what arrives>
Outputs: <what is produced>
Acceptance: <testable criteria, one per line>
Non-goals: <explicitly out of scope>
```

**Pseudocode:**
```
def handle_bill(msg):
    collect metadata + OCR text
    parse prices -> candidates
    pick total (max for receipts, sum for text)
    store to AgentDB
    respond with formatted confirmation
```

**Architecture:** draw the agent chain
`Collector → Parser → Storage → Responder` and mark where new work slots in.

**Refinement:** walk the spec looking for failure modes — empty OCR,
multiple currencies, zero amounts, duplicate messages — and add guards.

## SPARC × Ruflo pipeline mapping
| SPARC phase        | Ruflo facility                              |
|--------------------|---------------------------------------------|
| Specification      | `GoalEngine` (goal name/description)        |
| Pseudocode         | `GoapPlanner` actions draft                 |
| Architecture       | `SwarmOrchestrator` + topology              |
| Refinement         | `CodeAnalyzer` + tests                      |
| Completion         | agent pipeline + `SelfOptimizer` feedback   |
