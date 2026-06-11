---
description: "Use this skill whenever Codex encounters a bug, failing test, build failure, flaky behavior, performance issue, or any unexpected technical behavior, before proposing or applying fixes. Enforces root-cause-first debugging in four phases: evidence gathering, pattern comparison, single-hypothesis testing, and one verified implementation change."
---

# Systematic Debugging (Codex)

Use this skill before Codex proposes or applies fixes for bugs, test failures, build failures, flaky behavior, performance problems, integration failures, or unexpected technical behavior.

The point is simple: random fixes waste time and create new bugs. Find the root cause first, then fix the smallest thing that actually caused the failure.

## Core Rule

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If Phase 1 has not been completed, Codex must not propose a fix. A symptom explanation is not a root cause.

## Working Style In Codex

- State assumptions before acting when the evidence is incomplete.
- Prefer repository facts over guesses: read errors, inspect code, search for working examples, and run focused commands.
- Keep a short visible debugging plan for multi-step investigations.
- When a test fails, show the failing assertion and the smallest reproducing input before attempting a fix.
- Do not hide failures behind fallbacks. A hard failure with useful evidence is better than a silent workaround.
- Touch only files required by the root cause. Mention unrelated issues without fixing them.

## When To Use

Use for any technical issue:

- Failing unit, integration, or e2e tests
- Production or local bugs
- Build, lint, typecheck, or deploy failures
- Unexpected UI, API, data, or state behavior
- Flaky tests or timing-dependent failures
- Performance regressions
- Multi-component integration issues

Use especially when:

- A quick fix seems obvious
- The same issue has already resisted one or more fixes
- The user is under time pressure
- The failure crosses component boundaries
- Codex does not fully understand why the behavior happens

## The Four Phases

Complete each phase before moving to the next.

### Phase 1: Root Cause Investigation

Before attempting any fix:

1. Read the error carefully.
   - Read stack traces, failing assertions, line numbers, paths, and error codes.
   - Do not skip warnings that appear near the failure.
   - If the user supplied output, preserve the important lines in the analysis.

2. Reproduce consistently.
   - Identify the exact command, input, route, action, or state that triggers the problem.
   - If it is not reproducible, gather more evidence before guessing.
   - For failing tests, isolate the smallest test, assertion, and input that reproduces the failure.

3. Check recent changes and local state.
   - Inspect diffs, recent commits, changed config, dependency updates, environment differences, and generated artifacts.
   - Respect dirty worktrees. Do not revert user changes unless explicitly asked.

4. Gather boundary evidence in multi-component systems.
   - At each boundary, verify what enters and exits the component.
   - Check config and environment propagation explicitly.
   - Add temporary diagnostics only when they will reveal where the break occurs; remove or keep them deliberately according to the final fix.

   Example evidence plan:

   ```text
   Boundary A: log/request input and output
   Boundary B: verify normalized data and config
   Boundary C: inspect persisted state or external response
   Boundary D: verify final consumer receives expected shape
   ```

5. Trace bad values backward.
   - If the error appears deep in the call stack, read `references/root-cause-tracing.md`.
   - Ask where the bad value originated, what called this code with it, and which earlier assumption allowed it.
   - Fix at the source, not only where the exception surfaced.

Phase 1 success criteria: Codex can state what fails, where it fails, how to reproduce it, and the most likely source of the bad state with supporting evidence.

### Phase 2: Pattern Analysis

Find the pattern before fixing:

1. Locate working examples in the same codebase.
   - Search for similar components, tests, APIs, config, or error handling.
   - Prefer local patterns over invented abstractions.

2. Compare against the reference completely.
   - If an existing implementation is the pattern, read the relevant file or function end-to-end.
   - Do not skim only the similar lines.

3. List meaningful differences.
   - Include small differences in ordering, lifecycle, state shape, imports, dependency injection, and error handling.
   - Avoid dismissing a difference until it has evidence.

4. Understand dependencies and invariants.
   - Identify required config, data shape, timing, permissions, initialization order, and cleanup.

Phase 2 success criteria: Codex can explain how the broken path differs from a working path and which difference best explains the failure.

### Phase 3: Hypothesis And Testing

Use one hypothesis at a time:

1. State a single hypothesis.
   - Format: "Codex thinks X is the root cause because Y evidence shows Z."
   - Be specific enough that a small test can disprove it.

2. Test minimally.
   - Change one variable or run one focused diagnostic.
   - Do not bundle multiple possible fixes into a single trial.

3. Interpret the result.
   - If confirmed, proceed to Phase 4.
   - If disproven, form a new hypothesis from the new evidence.
   - If unclear, gather better evidence instead of stacking changes.

4. Admit uncertainty.
   - If Codex does not understand something, say so and inspect further.
   - Ask the user only when the missing information is not discoverable locally or the product intent is ambiguous.

Phase 3 success criteria: the root cause hypothesis has been confirmed by focused evidence, not just plausibility.

### Phase 4: Implementation

Fix the root cause, not the symptom:

1. Create a failing test or focused reproduction first when practical.
   - Prefer the existing test framework.
   - Use a small one-off script only when no appropriate test harness exists.
   - If an automated test is impractical, document the exact manual verification before changing code.

2. Implement one fix.
   - Address the confirmed root cause.
   - Keep edits surgical.
   - Do not add speculative configurability, broad refactors, or unrelated cleanup.

3. Verify the fix.
   - Re-run the failing test or reproduction.
   - Run the narrowest relevant regression checks.
   - Inspect the result; do not rely only on command exit if the output suggests a hidden failure.

4. If the fix does not work, stop.
   - Count the failed fix attempt.
   - If fewer than 3 fixes have failed, return to Phase 1 with the new evidence.
   - If 3 or more fixes have failed, question the architecture before attempting another fix.

5. If repeated fixes fail, question fundamentals.
   - Repeated failures across shared state, lifecycle, or component boundaries often indicate a wrong pattern, not a stubborn bug.
   - Discuss the architecture and tradeoffs with the user before continuing.

Phase 4 success criteria: the original failure is gone, the reproduction now passes, relevant regression checks pass, and Codex can explain why the fix targets the root cause.

## Red Flags

Stop and return to Phase 1 if Codex is about to:

- Propose a fix before reading the error and relevant code.
- Say "probably" without evidence.
- Change multiple things before testing one hypothesis.
- Add a fallback that hides a developer-visible failure.
- Fix only the line where the exception appears without tracing the source.
- Skip the failing test or reproduction when one is practical.
- Keep trying "one more fix" after two failed attempts.
- Adapt a local pattern without reading the working reference.

## User Redirection Signals

If the user says any of the following, treat it as a process failure and reset to evidence gathering:

- "Stop guessing"
- "Is that not happening?"
- "Will it show us...?"
- "Ultrathink this"
- "We're stuck?"
- "Why are we changing that?"

## Supporting Techniques

Load these files only when relevant:

- `references/root-cause-tracing.md`: use when the symptom appears deep in the stack or the bad value's origin is unclear.
- `references/defense-in-depth.md`: use after root cause is found and the bug came from invalid data crossing multiple layers.
- `references/condition-based-waiting.md`: use when a test or workflow relies on sleeps, timeouts, polling, async readiness, or flaky timing.

## Quick Reference

| Phase | Activity | Success criteria |
| --- | --- | --- |
| 1. Root cause | Read errors, reproduce, inspect changes, gather evidence | Know what fails, where, how, and why |
| 2. Pattern | Compare broken path to working examples | Identify the meaningful difference |
| 3. Hypothesis | State and test one theory | Confirm or disprove with focused evidence |
| 4. Implementation | Add reproduction, fix root cause, verify | Failure resolved and regressions checked |

## Completion Report

Before declaring the debugging task complete, report:

- Root cause found.
- Fix applied.
- Files changed.
- Verification run and result.
- Assumptions not verified.
- Any unrelated issues noticed but not changed.
