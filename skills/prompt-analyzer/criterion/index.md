# Prompt Engineering Best Practices Index

Quick reference for all patterns and anti-patterns used in prompt analysis.

## Patterns (Follow These)

| Pattern | Category | Priority | File |
|---------|----------|----------|------|
| Sandwich Structure | Structure | Critical | [patterns/sandwich-structure.md](patterns/sandwich-structure.md) |
| Separation of Concerns | Structure | High | [patterns/separation-of-concerns.md](patterns/separation-of-concerns.md) |
| Role Definition | Structure | High | [patterns/role-definition.md](patterns/role-definition.md) |
| Instruction Clarity | Clarity | High | [patterns/instruction-clarity.md](patterns/instruction-clarity.md) |
| Output Specification | Clarity | High | [patterns/output-specification.md](patterns/output-specification.md) |
| Safety Patterns | Safety | Critical | [patterns/safety-patterns.md](patterns/safety-patterns.md) |
| Template Security | Safety | Critical | [patterns/template-security.md](patterns/template-security.md) |

## Anti-Patterns (Avoid These)

| Anti-Pattern | Category | Severity | File |
|--------------|----------|----------|------|
| "Do Your Best" | Clarity | Medium | [anti-patterns/do-your-best.md](anti-patterns/do-your-best.md) |
| "Be Creative" (Alone) | Clarity | Medium | [anti-patterns/be-creative.md](anti-patterns/be-creative.md) |
| Nested Instructions | Structure | High | [anti-patterns/nested-instructions.md](anti-patterns/nested-instructions.md) |
| "As an AI..." | Efficiency | Low | [anti-patterns/ai-language-model.md](anti-patterns/ai-language-model.md) |
| Repeating Constraints | Efficiency | Low | [anti-patterns/repeating-constraints.md](anti-patterns/repeating-constraints.md) |
| Politeness Tokens | Efficiency | Low | [anti-patterns/politeness-tokens.md](anti-patterns/politeness-tokens.md) |

## Scoring Dimension Mapping

| Dimension | Primary Patterns | Primary Anti-Patterns |
|-----------|------------------|----------------------|
| Clarity & Specificity | Instruction Clarity, Output Specification | Do Your Best, Be Creative |
| Safety & Guardrails | Safety Patterns, Template Security | - |
| Token Efficiency | - | AI Language Model, Repeating, Politeness |
| Best Practices | Sandwich, Separation, Role Definition | Nested Instructions |
