---
name: regression-test-repair
description: Use when test suite has failures caused by intentional production code changes where tests were not updated - diagnoses root cause, applies mechanical fixes autonomously when provably safe (parameter shifts, import relocations), routes to human review when judgment is required (UI text changes, feature removal, behavioral changes), enforces zero-assertion-change rule and vacuous pass detection
---

# Regression Test Repair

## Overview

Diagnose and repair test failures caused by intentional production code changes where tests were not updated.

**Two modes:** Autonomous (provably safe mechanical fixes) or Assisted (human judgment required), determined per-test-file by a mechanical safety gate — not by intuition.

**Core principle:** A test that "just passes" is worse than a deleted test — every repair must prove the test still verifies real behavior.

**Asymmetric risk:** Silencing a real-bug-catching test is catastrophic; leaving a valid regression unfixed is trivial. **When in doubt, route to Assisted Mode.**

## Scope Boundaries

**Does:** Repair or delete existing tests broken by intentional production changes.
**Does NOT:** Write new tests, modify production code, handle flaky tests or dependency upgrades. If production code appears buggy, STOP and report.

## The Safety Gate (MANDATORY Before Any Fix)

All four must pass for Autonomous Mode. Any failure = Assisted Mode.

### Gate 1: Single Causing Commit
```
Method: git log on tested source file(s)
Pass:   Exactly one commit changed the tested interface
Fail:   Multiple commits, unclear causation, indirect dependency
```

### Gate 2: Mechanical Root Cause
Only two categories qualify:

**Parameter Shift** — new parameter inserted with default; existing params unchanged (same names, types, semantics); behavior unchanged when new param takes its default.

**Import Relocation** — function moved to different module; signature byte-identical (same params, same order, same defaults, same return shape) and body byte-identical. **Body must be identical.** Any body change (even "harmless" changes like Unicode normalization) fails Gate 2.

### Gate 3: Zero Assertion Changes
```
Pass: Every assertion byte-identical after fix
Fail: Any assertion modified, added, or removed
```

### Gate 4: Identical Code Path
```
Pass: New param defaults to no-op AND guarded by check; or relocated function with identical signature AND body
Fail: Default triggers new behavior; body changed at all
```

**All four pass = Autonomous Mode. Any failure = Assisted Mode. No "semi-autonomous", no "partial" — binary decision.**

## Autonomous Mode Workflow

1. Run `npm run test:run`. Collect all failing test files.
2. Per file, four sub-steps: (1) identify source files under test from imports; (2) `git log` on source files — find the causing commit; (3) read the causing commit's diff; (4) run the Safety Gate.
3. All gates pass → apply mechanical fix. Any gate fails → Assisted Mode.
4. **Parameter Shift:** insert default at new parameter position in all call sites. Touch nothing else.
   **Import Relocation:** update import paths and call sites; update describe block names referencing old module. Touch nothing else.
5. Run file in isolation, then full suite. Any new failure → revert all changes to this file → Assisted Mode.
6. Generate repair document, commit: `fix(tests): <description>`.

## Assisted Mode Workflow

1. **Diagnose:**
   1. State test intent — one sentence per failing test
   2. grep `src/` for tested behavior
   3. Check redundancy
   4. Classify root cause
   5. Assess vacuous pass risk
2. **Propose:** present root cause with evidence, diff (mechanical repair only — no comments, TODOs, or annotations), confidence level (High/Medium/Low), risks, alternative interpretations, and coverage gaps (in the proposal narrative, NOT as code comments or TODOs in the test file).
3. **Wait for human decision.** Do NOT proceed without explicit approval. Do NOT offer "provisional fixes." Do NOT apply changes "to unblock CI."
4. Apply if approved → verify → document → commit.

## Assisted Mode Root Cause Categories

- **Stale Selectors / Text Drift** — UI text or structure changed; requires product knowledge.
- **Obsolete Tests / Feature Removal** — tested behavior no longer exists; deciding removal was intentional requires product roadmap knowledge; deletion is irreversible (institutional knowledge lost).
- **Mock Staleness (Co-occurring)** — component expects new dependencies; MUST re-evaluate ALL assertions after mock fix — do not stop at "mock fixed, test passes."
- **Behavioral / Logic Changes** — function returns different values; might be a production bug the test is correctly catching.
- **Unidentifiable** — cannot attribute to a single commit. "I don't know" is valid output.

## Vacuous Pass Detection

After any proposed fix: "If I removed all assertions, would this test still pass?" If yes, the test is structurally vacuous. **A fix that creates a vacuous pass is not a fix.** Delete the test instead.

Known patterns:
- Asserting text is NOT present → passes trivially when nothing renders
- Asserting list is empty → passes trivially when data source is unmocked
- Asserting function was NOT called → passes trivially when mock is disconnected
- `.toContain()` negation → passes trivially when target string absent from all output

## Action Decision Matrix

| Condition | Action |
|-----------|--------|
| Behavior exists, not tested elsewhere | **FIX** |
| Behavior exists, tested elsewhere identically | **DELETE** (document redundancy) |
| Behavior no longer exists | **DELETE** (document with grep evidence) |
| Fix would create vacuous pass | **DELETE** |
| Production code appears buggy | **STOP** — report, do not touch test |

## Repair Documentation

One document per test file in `docs/RegressionTestRepair/`:

```
# Regression Repair: <TestFileName> (<N> Tests)
**Date:** YYYY-MM-DD  **Mode:** Autonomous | Assisted
**Commit (cause):** `<hash>` — <description>
**Commit (fix):** `<hash>` — <description>
```

Required sections:
1. **Root Cause** — Category, what changed, why test wasn't updated
2. **Safety Gate Results** (Autonomous only) — Pass/fail per gate with evidence
3. **Affected Tests** — Table: test name, intent (one sentence), failure mode
4. **Decision per Test** — Fix/delete/escalate with reasoning
5. **Fix Applied** — Before/after code
6. **Intent Preservation** — WHY the test still tests real behavior (not just "it passes")
7. **Assessment Summary** table
8. **Verification** — Isolated + full suite results, pre-existing failures noted separately

## Guardrails

1. Conservative by default — when uncertain → Assisted Mode. Over-escalation acceptable, under-escalation is not.
2. Never modify production code.
3. Never weaken assertions autonomously. Assertion changes in Assisted Mode require human approval.
4. Never delete tests autonomously.
5. New failures in full suite → revert → Assisted Mode.
6. Document pre-existing failures separately.
7. Every Assisted proposal requires confidence level + risk assessment.
8. **Refuse gracefully.** "I don't know why this test fails" is valid and useful output.

## Red Flags — Stop and Reconsider

- Modifying an assertion in Autonomous Mode
- Deleting a test without Assisted Mode
- Offering a "provisional" or "quick" fix
- Calling something "semi-autonomous" or "partially autonomous"
- Adding comments, TODOs, or new tests
- Skipping `git log` or the Safety Gate because the fix "seems obvious"
- Fixing an import without checking if the function body also changed
- Accepting a fix because "tests pass" without verifying intent preservation

| Rationalization | Reality |
|----------------|---------|
| "Skip the gates, it's obviously a parameter shift" | Obvious fixes hide subtle behavioral changes. Run all 4. |
| "Tests pass, ship it" | Passing tests prove nothing without intent verification. |
| "CI is blocking the team, just fix the imports" | A false green suite is worse than a known red one. |
| "I'll add a TODO for the edge case" | Out of scope. Repair only. |
| "Semi-autonomous is fine for this one" | Two modes. Binary gate. No exceptions. |
| "The body change is harmless, still autonomous" | Any body change fails Gate 2. Route to Assisted. |
| "I'll write a test for the new behavior while I'm here" | Out of scope. Repair or delete existing tests only. |
| "Let me skip the test for now with test.skip" | Not an option. Fix, delete, or escalate. No skipping. |
