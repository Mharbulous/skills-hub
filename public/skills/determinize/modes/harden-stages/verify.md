# Stage 5: Verify

## Goal

Confirm the hardened skill reproduces the original's baseline behavior
exactly, with no new failures introduced by the extraction.

## Prerequisites

- The hardened `SKILL.md` and extracted script from Stage 4.
- `baseline-results.md` from Stage 3.

## Steps

1. Re-run the same scenario files from Stage 3, this time against
   `<skill-name>-hardened/SKILL.md` (same subagent parameters as Stage 3:
   `general-purpose` subagent, model `sonnet` by default,
   `run_in_background: true`, waiting for completion before the next
   trial).
2. Compare each result to `baseline-results.md`: same outputs, same edge
   handling, no new failures.
3. On any divergence: identify exactly where the hardened behavior differs
   from baseline, fix the script or the hardened SKILL.md, and re-run the
   affected scenario. Repeat until it matches. Never proceed with a
   failing test.

## Output artifacts

Write `<skill-name>-hardened/tests/green-results.md`, in the same shape as
`baseline-results.md`, plus a "Comparison: Baseline vs GREEN" table showing
each scenario's baseline result next to its GREEN (hardened) result.

## Gate

Before proceeding: confirm all scenarios pass, results match baseline
exactly, and `green-results.md` is saved to disk.

**Read `commit-and-finalize.md` next.**
