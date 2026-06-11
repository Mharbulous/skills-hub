# Role Definition

**Category:** Structure Pattern
**Priority:** High

## Pattern

Define the model's role with specificity and clear boundaries.

### Effective Role Statements

- Be specific about expertise level
- Include relevant domain context
- Specify perspective/approach

**Strong:** "You are a senior security engineer specializing in web application vulnerabilities, with expertise in OWASP Top 10."

**Weak:** "You are helpful."

### Capability Boundaries

- State what the role should NOT do
- Define scope explicitly
- Prevent role drift

## Why This Works

- Specific roles activate relevant knowledge
- Boundaries prevent scope creep
- Domain context improves accuracy

## Scoring Impact

| Issue | Point Deduction |
|-------|-----------------|
| Vague role ("helpful assistant") | -3 to -5 |
| No expertise level specified | -1 to -2 |
| Missing capability boundaries | -2 to -3 |
