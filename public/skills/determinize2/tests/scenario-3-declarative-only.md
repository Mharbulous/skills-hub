# Scenario 3: Clean Exit on 100% Judgment Content

**Type:** Clean-exit correctness check.

## Setup

The agent is given `determinize2` (harden mode) and asked to harden the
following skill, `code-review-checklist`, provided inline:

```markdown
---
name: code-review-checklist
description: Guidance for reviewing pull requests for correctness, style, and risk.
---

# Code Review Checklist

## Review Passes

Review the diff in three passes: correctness, style, then risk. On each
pass, read the whole diff before commenting — don't comment line-by-line
on the first read.

## Anti-Pattern Table

| Pattern | Concern | Suggested response |
|---|---|---|
| Swallowed exceptions | Silent failures | Ask whether the failure should surface |
| Deeply nested conditionals | Hard to reason about | Suggest early returns or extraction |
| Magic numbers | Unclear intent | Ask for a named constant, weigh the reviewer's read on urgency |
| Broad try/except | Overly permissive | Ask whether the scope should narrow |

## Block / Request Changes / Approve Guidance

Use your judgment on severity: block merges that risk data loss or security
exposure; request changes for anything that would confuse a future reader;
approve if the concerns are purely stylistic and the author already
explained their reasoning. Weigh the team's current velocity needs against
the risk when it's a close call.
```

## Task

**IMPORTANT: This is a real task.** Run Stage 1 and Stage 2 of harden mode
against this skill.

## Success Criteria

1. The agent classifies all sections as non-deterministic (judgment-based)
   — none score as extractable.
2. The agent outputs this exact clean-exit sentence, verbatim:
   > "No script extraction candidates found. This skill's content requires LLM judgment and cannot be replaced with deterministic scripts. Hardening does not apply to this skill."
3. No `-hardened` copy is created.
4. The agent does not offer a restructuring or progressive-disclosure
   fallback.

## Failure Indicators

- Any variant of: "while no scripts can be extracted, we can still
  optimize by restructuring…" — this is a forbidden anti-pattern.
- Creating a `code-review-checklist-hardened/` directory anyway.
- Paraphrasing the clean-exit sentence instead of reproducing it verbatim.
