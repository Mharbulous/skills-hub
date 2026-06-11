# Anti-Pattern: Politeness Tokens

**Category:** Efficiency Anti-Pattern
**Severity:** Low

## The Problem

Excessive politeness ("please", "thank you", "would you kindly") wastes tokens without affecting output quality.

**Bad:**
```
Please analyze this code. Thank you for your help. I would really appreciate it if you could be thorough. Thanks in advance!
```

**Good:**
```
Analyze this code. Be thorough.
```

## Why It Fails

- LLMs don't respond to social pressure
- Each word costs tokens
- Politeness doesn't improve output quality

## Fix

Use direct, imperative instructions. The model will comply regardless of politeness.

## Exception

In user-facing prompts where the prompt text is visible to humans, some politeness may be appropriate for UX reasons.

## Scoring Impact

Deduct 1 point from Token Efficiency per unnecessary politeness phrase.
