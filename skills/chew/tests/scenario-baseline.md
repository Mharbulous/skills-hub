# Baseline Test Scenario: Autonomous Phase Design

## Context

This tests whether an agent can autonomously design the next phase of a multi-phase PRD without human intervention.

## Setup

The agent has access to:
- A PRD at `planning/0. PRDs/2026-03-12 PRD-Screenshot-Classification.md` containing an 8-phase implementation plan
- An existing Phase 1 design document at `planning/1. Design/2026-03-12_keyword-map-infrastructure-design.md`
- Full codebase access via standard tools

## Prompt

```
IMPORTANT: This is a real task. Execute it fully — do not ask clarifying questions.

You are working on a project that has a PRD with 8 implementation phases. Phase 1 already has a design document. Your job is to:

1. Read the PRD and existing design documents to determine which phase should be designed next
2. Research the codebase to understand what exists and what the design needs to account for
3. Draft a bite-sized design document for that next phase
4. Save the design document in the correct location
5. Commit the design document

Requirements:
- Do NOT ask the human any questions. Use subagents to research anything you need.
- Do NOT present the design to the human for review. Have a subagent review it instead.
- Create exactly ONE design document, then stop.
- The design document must be specific enough for an implementation planner to create tasks from it.

The PRD is at: planning/0. PRDs/2026-03-12 PRD-Screenshot-Classification.md
```

## Expected Failure Modes (Hypotheses)

1. **Asks the human questions** instead of researching autonomously
2. **Skips dependency analysis** — picks a phase arbitrarily instead of following the dependency graph
3. **Doesn't check existing design docs** — may re-design Phase 1 or miss that it's done
4. **Wrong output location** — doesn't follow the `planning/1. Design/YYYY-MM-DD_description-design.md` convention
5. **Designs multiple phases** instead of exactly one
6. **Skips commit** — writes the file but doesn't commit
7. **Skips subagent review** — presents to human or skips review entirely
8. **No transition message** — doesn't tell the user what to do next
9. **Doesn't stop** — continues working after the design doc is committed

## Success Criteria

The agent should:
- [ ] Read the PRD and identify all 8 phases
- [ ] Check `planning/1. Design/` for existing design docs
- [ ] Determine Phase 2 is next (based on dependency: Phase 2 depends on Phase 1)
- [ ] Spawn a research subagent to explore the codebase
- [ ] Draft a design document scoped to Phase 2 only
- [ ] Have a subagent review the design (not the human)
- [ ] Save to `planning/1. Design/2026-03-12_keyword-matching-cloud-functions-design.md` (or similar)
- [ ] Commit the design document
- [ ] Output a transition message directing to `/writing-plans`
- [ ] Stop after committing (not continue to Phase 3)
