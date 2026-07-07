> **Provenance note:** this file is a historical artifact documenting
> `determinize`'s own construction (RED phase of the TDD cycle under which
> this skill was built). It is not a live regression suite for end users to
> run — it records how the predecessor skill behaved, for reference only.

# Baseline Results: `optimizing-skills` (predecessor) — RED phase

**Date:** 2026-02-14
**Commit under test:** `9f3a2c1` (last commit of `optimizing-skills` before
the determinize rewrite began)

## Summary

The predecessor skill, `optimizing-skills`, was run against the framing and
discipline scenarios that later became Scenarios 3 and 4 of this suite.
It failed both, for related reasons: its internal value proposition was
built around token consumption, not determinism.

## Scenario 3 equivalent (clean-exit behavior)

**Result: FAIL**

Given a 100%-judgment skill, `optimizing-skills` did not exit cleanly. It
proposed a "restructure for progressive disclosure" fallback — splitting
the single judgment-heavy file into a router plus reference files — and
described this as valuable even though no script extraction was possible.
This is exactly the anti-pattern this suite's Scenario 3 now checks for.

## Scenario 4 equivalent (framing check)

**Result: FAIL**

Asked why optimization mattered, `optimizing-skills` answered primarily in
token-savings terms: "reduces token consumption on repeat invocations,"
"more efficient use of the context window." Determinism was mentioned only
as a secondary, incidental benefit.

## What the Hardened Skill Must Fix

1. Remove token-savings language from the core value proposition entirely.
2. Remove the progressive-disclosure fallback for 100%-judgment skills —
   replace it with a clean exit.
3. Reframe the ranking formula (then an "ROI" formula) around determinism
   value rather than estimated token reduction.
4. Rename the skill from `optimizing-skills` to `determinize` to make the
   determinism framing unmistakable from the name alone.
5. Add an explicit Iron Law forcing baseline tests before any extraction,
   which `optimizing-skills` did not have.
