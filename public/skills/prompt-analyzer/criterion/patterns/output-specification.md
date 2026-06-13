# Output Specification

**Category:** Clarity Pattern
**Priority:** High

## Pattern

Specify output format explicitly with schema when structured output is needed.

### Format Types

| Type | When to Use |
|------|-------------|
| JSON | Programmatic parsing, structured data |
| Markdown | Human-readable reports, documentation |
| Plain text | Simple responses, conversational |
| XML/Tags | Complex nested structures, clear delineation |

### Schema Definition

For structured output, provide:
- Field names and types
- Required vs optional fields
- Example of complete output

**Good Example:**
```
Return JSON:
{
  "summary": string (1-2 sentences),
  "issues": [{"severity": "high"|"medium"|"low", "description": string}],
  "recommendation": string
}
```

## Why This Works

- Explicit formats enable reliable parsing
- Schemas prevent missing fields
- Examples demonstrate expected structure

## Scoring Impact

| Issue | Point Deduction |
|-------|-----------------|
| No output format specified | -3 to -5 |
| Format without schema | -1 to -2 |
| Missing example output | -1 to -2 |
