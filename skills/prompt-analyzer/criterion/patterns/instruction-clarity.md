# Instruction Clarity

**Category:** Clarity Pattern
**Priority:** High

## Pattern

Write instructions that are direct, specific, and handle edge cases.

### Imperative Form

Use direct commands: "Analyze", "List", "Identify", "Return"

Avoid passive/vague: "It would be good to...", "You might want to..."

### Specificity Hierarchy

1. **Explicit values**: "Return exactly 3 examples"
2. **Bounded ranges**: "Between 2-5 paragraphs"
3. **Qualified flexibility**: "Provide examples as needed, typically 1-3"
4. **Avoid**: "Some examples", "A few items"

### Handling Edge Cases

Address ambiguous scenarios explicitly:
- "If no results found, return: 'No matches'"
- "For invalid input, explain why and request clarification"

## Why This Works

- Imperative form removes ambiguity
- Specific quantities prevent under/over-delivery
- Edge case handling prevents unexpected behavior

## Scoring Impact

| Issue | Point Deduction |
|-------|-----------------|
| Passive/vague instructions | -2 to -4 |
| Unquantified outputs | -1 to -2 |
| No edge case handling | -2 to -3 |
