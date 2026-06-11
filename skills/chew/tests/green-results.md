# GREEN Results: /chew Skill Test

## Test Date: 2026-03-12
## Agent: Sonnet (with /chew skill loaded)

## Iteration 1 (before refactor)

**Failure:** Agent re-derived phases from the PRD instead of using the established roadmap in the Phase 1 design doc. Selected "Deterministic Rule Engine" instead of Phase 2.

**Root cause:** Step 1 said "Read source document → Extract phase list" without instructing the agent to check existing design docs for an established roadmap first.

## Iteration 2 (after refactor)

**All checks passed:**

| Check | Result |
|-------|--------|
| Used established roadmap from Phase 1 design doc | YES — explicitly cited the instruction to use existing roadmap |
| Selected correct next phase | YES — Phase 2: Keyword Matching in Cloud Functions |
| Would spawn research subagent (not inline) | YES — Opus subagent with structured question |
| Would spawn review subagent (not human) | YES — Opus subagent with PRD cross-reference |
| Correct file path convention | YES — `planning/1. Design/2026-03-12_keyword-matching-cloud-functions-design.md` |
| Exact transition message | YES — matched required format |
| Stops after one phase | YES — explicitly stated "no second phase, no summary" |

## Refactoring Applied

1. Reordered Steps 1 and 2: scan existing design docs FIRST, read source doc second
2. Added explicit instruction: "If an existing design doc contains a phase roadmap table, use that as authoritative. Do NOT re-derive phases from the PRD."
3. Added red flag: "Re-deriving phases from the PRD when a phase roadmap already exists in a design doc"
