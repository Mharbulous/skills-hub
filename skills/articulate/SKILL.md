---
name: articulate
description: >
  TDD for prompts — aggressively compresses an LLM-targeted document while preserving
  behavior, then refines until the shortened version answers a blind test suite
  identically to the original. Use when a SKILL.md, CLAUDE.md, ADR, prompt, or
  similar instruction document is bloated or context-hungry and needs to be made
  shorter without changing what downstream agents do. Optionally finishes with a
  human-driven intent pass. Do not use for general copyediting.
---

# Articulate — TDD for Prose

Compress an LLM-interpreted document while preserving behavior. The original is the behavioral reference; an oracle on the original and a candidate on the revision answer the same questions, and any divergence is a regression to fix.

**Core principle:** The reference document defines correct behavior. Never judge your own revision — test it blind against the oracle.

## Invocation

```
/articulate <file_path> "<natural language description of target section>"
```

## Input Validation

1. Read the file. Locate the target text.
2. Confirm with user: "I found this section (lines N-M). Is this what you want to compress?"
3. The confirmed text becomes the **reference version** — the immutable behavioral baseline. The oracle always answers from this version.

**Context envelope:** Full document retained as test context. Only the target paragraph gets revised.

## Versions

- **Reference version** (immutable): user-confirmed original. Oracle always answers from this. Never modified during the run.
- **Working version** (mutable): current best compressed candidate. Updated as revisions are auto-promoted.

## State Files

All iteration state lives in `C:/Users/Brahm/.claude/skills/articulate/work/`:

```
work/
├── reference.md      # Immutable original (written once at Input Validation)
├── candidate.md      # Current working version (updated each iteration)
├── suite.json        # Accumulated test suite [{id, question, oracle, status}]
└── scorecard.md      # Latest iteration results (human-readable)
```

The orchestrator writes `reference.md` and `candidate.md` at the start. Agents read from these paths — document content is never embedded inline in agent prompts.

### suite.json Format

```json
[
  {"id": "RQ1", "question": "Does the document...", "oracle": "YES", "status": "divergent"},
  {"id": "RQ2", "question": "Does the document...", "oracle": "YES", "status": "convergent"}
]
```

- `oracle`: The oracle's answer (ground truth for behavior)
- `status`: `"divergent"` (oracle ≠ candidate) or `"convergent"` (match)

### Iteration Protocol

1. WRITE reference.md and candidate.md to work/
2. DISPATCH review agent (file paths only, not inline content)
3. PARSE review output → new questions
4. DISPATCH oracle + candidate IN PARALLEL (questions + file paths)
5. SCORE: compare oracle vs candidate answers
6. UPDATE suite.json (append new questions with oracle answers + status)
7. WRITE scorecard.md (human-readable summary)
8. CHECK termination:
   - Phase 1: ≥10 divergent + ≥20 total → exit to Phase 2
   - Phase 2: all pass → auto-promote; else revise candidate.md → goto 2
9. If revising: apply fix to work/candidate.md, goto step 2

## Phase 1 — Compress (Oracle-Verified Test Discovery)

**Goal:** Maximally compressed working version + accumulated test suite of **≥10 divergent and ≥20 total** questions.

### Compression Loop

1. **Draft a shorter revision.** ('agents/distiller.md'): Dispatch with filepath or target text.
2. **Review agent** (`agents/review.md`): Dispatch with (revised, reference) → emits edge questions probing potential meaning loss.
3. **Oracle + Candidate in parallel:**
   - **Oracle** (`agents/oracle.md`): on reference, with the edge questions.
   - **Candidate** (`agents/candidate.md`): on revised, with the edge questions.
4. **Score each question:**
   - Oracle = Candidate → **Convergent.** Add to suite.
   - Oracle ≠ Candidate → **Divergent.** Add to suite, oracle's answer as expected.
5. **Update working version** to the latest revision even if it has divergent answers — Phase 2 will fix them.
6. **Loop until** ≥10 divergent questions accumulated.

### Stopping Early

If 5 iterations produce no new divergent questions, the document may already be near-minimal. Show the suite and ask whether to proceed to Phase 2 with fewer divergent questions, or to terminate (the working version is already a passing compression).

## Phase 2 — Articulate (Pass the Suite)

**Goal:** Revise the working version until candidate matches oracle on every accumulated question.

### Correctness Loop (max 5 iterations)

1. Pick the highest-priority failing divergent question. Analyze why the working version diverges from oracle's answer.
2. Draft a revision that addresses it without re-bloating questions that already pass.
3. **Dual-agent test** in parallel:
   - **Test agent** (`agents/candidate.md`): revised working version + full suite. Score answers against expected (oracle's answers).
   - **Review agent** (`agents/review.md`): (revised, working-version-before-this-revision) — probes regressions in already-passing questions.
4. **Results:**
   - Not all passing → scorecard → auto-iterate.
   - All pass (regardless of review questions) → **Equivalence Check.**
5. After 5 iterations, stop. Report failing questions, attempted revisions, and what the next attempt would try differently. Ask permission to exceed the max.

### Equivalence Check

Run whenever all suite questions pass, regardless of whether the in-loop review found regression questions.

1. **Score any in-loop regression questions first** (if the loop's review agent raised questions):
   - Oracle + Candidate in parallel on those questions.
   - Divergent → add to suite (oracle's answer as expected) → resume Correctness Loop.
   - Convergent → add to suite. Continue to step 2.

2. **Run review(working, original reference)** — probes behavioral gaps not yet covered by the suite.
   - **NO CONCERNS → auto-promote.** Apply, show diff, report iterations.
   - **Questions found:**
     - Oracle + Candidate in parallel.
     - Any divergent → add to suite (oracle's answer as expected) → resume Correctness Loop.
     - All convergent → add to suite → **auto-promote.** Review probed edges, found no behavioral difference.

3. **Outer loop guard:** After 3 Equivalence Check cycles without auto-promote, stop. Show remaining divergent questions, attempted fixes, and ask permission to continue.

## Phase 3 — Refine for Intent (Human-Driven, Opt-In)

After Phase 2 auto-promotes, ask:

> "The compressed version now matches the original's behavior. Want to also refine against your intent (in case the original itself under-articulated)?"

Only if yes, run the human-driven discovery flow on the working version:

1. **Discover:** Generate edge questions one at a time in violate/comply framing. In parallel, ask the user (ground truth) and dispatch a test agent. Compare: human ≠ agent = Divergent; human = agent = Convergent. Repeat until 5+ divergent and 5+ convergent.
2. **Curate:** Select 10-question test suite (5D + 5C). User approves, edits, or overrides.
3. **Refine:** Run the Correctness Loop with this curated suite, using the user's answers as expected.

This phase catches cases where the *original document* under-articulated intent — the oracle inherits any ambiguity in the reference.

## User-Directed Changes

When the user directs additions/modifications during any phase:

1. If ambiguous, confirm interpretation before applying.
2. Apply via `agents/apply-changes.md` to the working version.
3. Next test cycle uses the updated working version.
4. If a change contradicts an accumulated test's expected answer, surface the conflict and ask: "Update expected answer?"

## Critical Rules

- **Reference version is immutable.** Oracle always answers from it. User-directed changes update the working version, not the reference.
- **Human = ground truth for intent. Oracle = ground truth for behavior.** Phases 1–2 use oracle. Phase 3 is for when oracle's interpretation may itself be wrong.
- **Never judge your own revision.** Test blind — no exceptions.
- **Test before presenting.** Draft → test → scorecard. Never ask approval of untested work.
- **All pass + Equivalence Check clean = auto-promote.** Don't ask.
- **Silence = state assumption, then answer.** If instructions are silent on a question, the answering agent should state its default assumption and answer Yes or No as if that default were explicit.
- **File paths, not inline content.** Agent prompts reference files in work/. Never embed document content inline in dispatches.
- Structural rules constrain the orchestrator, not the user.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Stopping compression after one pass | Loop until ≥10 divergent + ≥20 total — bloat hides edge cases |
| Reverting a cut because it caused divergence | Keep the cut, log the divergent question, fix in Phase 2 |
| Oracle reading the working version | Oracle ALWAYS answers from reference, never from a candidate |
| Updating the reference mid-run | Reference is locked at Input Validation |
| Treating Phase 3 as default | Opt-in only — original was already trusted as reference |
| Compound double-binary questions | "Does X apply only to A, or also to B?" makes YES and NO both ambiguous. Split into two independent questions, each with a clear YES/NO meaning. |
| Same agent context for testing | Fresh agent, read-only, no conversation context |
| Review agent returns prose | Must return test questions only |
| Approving untested revisions | Test first, present scorecard |
| Embedding documents inline in agent prompts | Point agents to file paths in work/ — they have Read access |
