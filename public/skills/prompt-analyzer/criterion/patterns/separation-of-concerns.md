# Separation of Concerns

**Category:** Structure Pattern
**Priority:** High

## Pattern

Keep distinct prompt elements in clearly delineated sections:

- Instructions separate from examples
- Sections marked with headers or XML tags
- Related constraints grouped together

## Good Example

```
You are a code reviewer.

## Task
Review the provided code for bugs and security issues.

## Constraints
- Focus only on critical issues
- Do not suggest style changes

## Output Format
List issues as: [SEVERITY] file:line - description
```

## Poor Example

```
Review code for bugs like this example: function foo() { eval(input) } is bad because eval is dangerous. Also check security. Output as a list.
```

## Why This Works

- Clear sections reduce ambiguity
- Model can reference specific sections
- Easier to maintain and iterate on prompts

## Scoring Impact

| Issue | Point Deduction |
|-------|-----------------|
| Mixed instructions/examples | -3 to -5 |
| No section delineation | -2 to -3 |
| Scattered constraints | -1 to -2 |
