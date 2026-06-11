# Anti-Pattern: Nested Instructions in Examples

**Category:** Structure Anti-Pattern
**Severity:** High

## The Problem

Embedding instructions within examples causes confusion about what to follow.

**Bad:**
```
Here's an example of good output:
"The function calculates tax. Always explain edge cases like this. Make sure to mention performance."

Now analyze the code.
```

**Good:**
```
## Instructions
- Explain what the function does
- Cover edge cases
- Note performance considerations

## Example Output
"The calculateTax function computes sales tax by multiplying price by rate. Edge case: returns 0 for negative prices. Performance: O(1) constant time."

## Your Task
Analyze the following code:
```

## Why It Fails

- Model may follow embedded instructions inconsistently
- Unclear what's example vs. what's instruction
- Hard to maintain and iterate

## Fix

- Use clear section headers
- Keep examples as pure output samples
- Place all instructions in dedicated sections

## Scoring Impact

Deduct 3-5 points from Best Practices.
