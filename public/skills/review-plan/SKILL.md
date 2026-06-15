---
name: review-plan
description: "Review an implementation plan for flaws and opportunities for improvement, then produce an improved version incorporating all corrections."
---

# Review Plan

Delegate plan review to the most capable available model via a subagent.

## Input

The plan to review is provided as arguments: `$ARGUMENTS`

## Execution

Spawn a single Agent with `model: "claude-opus-4-8"` and pass it the prompt below. Relay its response verbatim to the user — do not summarize or reformat.

### Agent Prompt

```
You are reviewing an implementation plan for flaws and opportunities for improvement. Your job is to produce an improved version that incorporates everything good about the original while correcting flaws and adding improvements.

## Plan to Review

$ARGUMENTS

## Instructions

1. Read the plan carefully. Identify:
   - Logical flaws or contradictions
   - Missing steps or gaps in coverage
   - Ordering issues (dependencies out of sequence)
   - Overcomplexity or unnecessary steps
   - Opportunities for simplification
   - Missing edge cases or error scenarios
   - Unclear or ambiguous instructions

2. Produce your output in this exact format:

### Analysis

Briefly list each flaw found and each improvement identified. Be specific — name the step or section affected.

### Improved Plan

The complete rewritten plan. Keep everything good from the original. Correct every flaw. Incorporate every improvement. Do not omit sections — this must be a complete replacement, not a patch.
```
