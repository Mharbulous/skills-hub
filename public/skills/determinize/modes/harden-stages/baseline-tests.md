# Stage 3: Baseline Tests

## The Iron Law

```
NO HARDENING WITHOUT BASELINE TESTS FIRST
```

If you find yourself about to write or run an extraction script before
this stage is fully complete: stop, delete any work done out of order, and
restart from here. There are no exceptions. In particular, none of the
following justify skipping this stage:

- "the extraction is obvious"
- "just moving code blocks"
- "I'll backfill tests"

## Goal

Establish, in writing, exactly how the ORIGINAL skill behaves for the
candidate section selected in Stage 2 — before any extraction exists to
bias the comparison.

## Prerequisites

- The candidate section selected (or auto-selected) in Stage 2.

## Steps

1. Create `<skill-name>-hardened/tests/`. Note: this is the first thing
   created in the hardened tree — SKILL.md and scripts/ do not exist yet
   and are not created until Stage 4. The hardened directory exists at
   this point solely to hold tests.
2. Write scenario files into that directory, one per meaningful input
   condition for the candidate section. Each scenario file must specify a
   specific input condition and an expected behavior. Cover normal cases,
   edge cases, and boundary cases for the candidate section — not just the
   happy path.
3. For each scenario, run it using a `general-purpose` subagent (model
   `sonnet` by default, `run_in_background: true`) driving the ORIGINAL
   skill (not the hardened copy, which doesn't have SKILL.md yet). Wait for
   each subagent to complete before launching the next.
4. Record the ORIGINAL skill's verbatim behavior for every scenario in
   `<skill-name>-hardened/tests/baseline-results.md`.

## Output artifacts

- `<skill-name>-hardened/tests/scenario-*.md`
- `<skill-name>-hardened/tests/baseline-results.md`

## Red flags

Watch for these rationalizations — all of them mean "go back, baseline
first":

1. "The extraction is obvious, I don't need to test the original first."
2. "Testing wastes time we don't have."
3. "I'll backfill the baseline after I extract."
4. "I'm just moving code blocks, nothing can change."

## Gate

Before proceeding: confirm the scenario files are saved, the baseline
behavior is documented from the ORIGINAL skill (not from any draft
extraction), and `baseline-results.md` is saved to disk.

**Read `extract.md` next.**
