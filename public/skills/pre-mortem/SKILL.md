---
name: pre-mortem
description: Imagine future bug post-mortems for the codebase. Identifies fragile code, implicit assumptions, and likely failure modes by writing realistic incident reports for bugs that haven't happened yet.
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

# Pre-Mortem: Future Bug Post-Mortems

**Scope:** $ARGUMENTS

This is not a bug hunt. The code may be perfectly correct today. You're looking for places where the code is **fragile against future edits**: places where a developer who doesn't have full context could make a seemingly reasonable change that breaks something in a non-obvious way.

## Scope

- Named files/directories → analyse those.
- No argument → inspect source layout, then use `AskUserQuestion` to agree on a starting scope; pick one module or package with meaningful logic, don't try to cover everything at once.
- Focus on production code. Config files, migrations, and boilerplate are out of scope unless they contain logic other code depends on.

## Workflow

1. **Read deeply.** Don't skim — understand data flow, state management, implicit invariants, and the relationships between components. Read callers and callees, not just the file in isolation. Use `TaskCreate` when scope spans many files.

2. **Identify fragility.** For each pattern in the catalogue, ask: "What change would a reasonable developer make here that would break this?" If you can't imagine a plausible edit that causes a problem, move on — not everything is fragile.

3. **Write post-mortems.** Write as if the bug has already happened — in past tense, from the perspective of the team investigating the incident after the fact. Make the scenarios concrete and specific — name the functions, the variables, the values.

4. **Produce the report.** Write all post-mortems to a single file. Use `AskUserQuestion` to confirm the output path with the user, defaulting to `PRE-MORTEM.md` in the project root. Flag actual current bugs via text output; don't bury them in fictional post-mortems. Ask via `AskUserQuestion` before including uncertain patterns.

## Fragility Catalogue

Not exhaustive — use judgement to spot anything that would surprise a future editor.

**1. Implicit ordering** — Code that must run in a specific order without enforcement: setup before use, sorted-list assumptions, init sequences where step N silently depends on step 1. *Trigger:* Reorder calls; insert a step between dependent ones; call a method before the object is fully initialized.

**2. Semantic coupling through shared mutable state** — Two components sharing state through a shared object (dict, list, module var, object attribute) rather than explicit args/returns. The reader of component A might not realise that component B is reading or writing the same state. *Trigger:* Modify one component without realising the other depends on it; add caching/memoization that blocks updates.

**3. Stringly-typed contracts** — Logic depending on exact string values (dict keys, status fields, column names, error messages), creating invisible contracts between producers and consumers that no type checker enforces. *Trigger:* Rename a string in one place but not another; add an enum variant that existing if-elif chains don't handle.

**4. Baked-in data assumptions** — A function assuming input shape, range, or non-null values that upstream currently guarantees but nothing enforces. *Trigger:* Change the upstream source; add a code path feeding different data; relax boundary validation.

**5. Coincidental correctness** — Code correct for the wrong reason: a condition that happens to work because two variables are always equal today, a loop never called with empty input, a broad exception handler that currently sees only one type. *Trigger:* Widen input space; introduce a new exception type; let the previously-equal variables diverge.

**6. Non-atomic compound ops** — Check-then-act or multi-step state updates with no rollback, including file operations that assume no concurrent access. Includes anything where a failure or interruption between steps leaves the system in an inconsistent state. *Trigger:* Add concurrency; add an early return between steps; move to an interruptible context.

**7. Invisible invariants** — Relationships between data maintained only by convention ("this counter equals len(that list)"), never asserted or typed. *Trigger:* Update one side of the invariant — especially when the two sides are in different functions or files.

**8. Load-bearing defaults** — Defaults (function params, config, class attrs, env vars) where the default doesn't just provide convenience — the code would behave incorrectly or dangerously with a different value, and nothing documents this constraint. *Trigger:* Change the default to something equally reasonable; a caller starts passing an explicit value no one anticipated.

**9. Implicit resource lifecycle** — Resources (connections, handles, locks, threads) whose cleanup depends on a specific control flow path with no context manager or finalizer. *Trigger:* Add an early return or exception; refactor into smaller functions that skip the cleanup.

**10. Version-coupled assumptions** — Relies on undocumented dependency/runtime behaviour (dict ordering pre-3.7, library side effects, error message format). *Trigger:* Upgrade the dependency; change runtime version; the API's undocumented behaviour shifts.

## Post-Mortem Format

```markdown
### <Title>

**Severity:** Critical | High | Medium | Low
**Component:** <file(s) and function(s)>
**Fragility type:** <catalogue category>

#### What happened
<2–4 sentences, past tense, specific symptoms — name the functions, variables, values>

#### The change that caused it
<Reasonable edit a well-intentioned developer would make that would pass code review. Include plausible motivation (new feature, refactor, perf improvement, dependency upgrade).>

#### Why it broke
<Hidden assumption violated; cite specific functions, variable names, and file paths>

#### How it was caught
<Tests? Silent failure? Data corruption? Conditions required? Be honest — if no test would catch it, say so.>

#### Hardening suggestions
<1–3 concrete actions specific enough that someone could implement them directly>
```

## Output File Structure

```markdown
# Pre-Mortem Report
**Scope:** ...
**Date:** ...

## Summary
<Overall fragility posture: how many post-mortems, dominant themes, whether fragilities are systemic patterns or mostly independent>

## Post-Mortems
### 1. ...

## Themes and Recommendations
<Cross-cutting patterns; structural fixes that address multiple fragilities at once, not just point fixes>
```

## Calibration

**Aim for:** 3–7 post-mortems per module. Cause and effect non-obvious (change in one place, breakage elsewhere or under specific conditions). Fragilities that are endemic to the design, not surface-level issues. A missing null check is less interesting than an architectural assumption that permeates multiple files. Reader should think "I wouldn't have thought of that."

**Severity:** Silent data corruption = Critical. Clear error in an uncommon path = Low. Not everything is Critical — use severity honestly.

**Avoid:**
- Current bugs (flag separately via text; don't write a fictional post-mortem about a real bug)
- Adversarial edits (imagined changes must be well-intentioned)
- Unlikely changes — the imagined edit should be small and local: a refactoring, a feature addition, a performance tweak. "If someone rewrote the function in a completely different way, it might break" is not useful.
- Generic advice ("this function has no tests") — every post-mortem must describe a specific future change and specific resulting failure

## Critical Rules

- Read before writing. Never write post-mortems for code you haven't read thoroughly.
- Be specific. Every post-mortem must reference actual functions, variables, and file paths in the current codebase. No hand-waving.
- Be plausible. The imagined changes must be things a reasonable developer might do. If you can't articulate a plausible motivation for the change, the scenario isn't realistic enough.
- Don't implement hardening suggestions unless the user asks.
- Separate actual current bugs: surface them immediately via text output, not in a fictional post-mortem.
- Ask when uncertain. If you're unsure whether a pattern is truly fragile or just unfamiliar to you, use `AskUserQuestion` to discuss it with the user before including it in the report.
