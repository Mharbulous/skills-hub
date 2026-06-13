# Anti-Pattern: Repeating Constraints

**Category:** Efficiency Anti-Pattern
**Severity:** Low

## The Problem

Stating the same constraint multiple times wastes tokens without improving compliance.

**Bad:**
```
Keep your response brief.
...
Remember to be concise.
...
Make sure your answer is short.
...
Don't write too much.
```

**Good:**
```
Respond in under 100 words.
```

## Why It Fails

- Repetition doesn't improve adherence
- Wastes valuable context window
- Can actually dilute the instruction's impact

## Fix

- State each constraint exactly once
- Use specific, measurable criteria
- Place constraints in a dedicated section

## Scoring Impact

Deduct 1-2 points from Token Efficiency.
