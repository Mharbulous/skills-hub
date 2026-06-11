---
name: Firebase-Prompting
description: TDD workflow for Firebase AI (Google Gemini) prompts. Use when (1) writing or fixing Gemini prompts in Cloud Functions, (2) adding AI extraction fields, (3) debugging LLM response parsing issues, (4) any work touching `functions/matter-extraction/` or similar prompt-based extraction code. Teaches RED-GREEN-REFACTOR adapted for prompt engineering with mock-based unit tests and optional live integration tests.
disable-model-invocation: true
---

# Firebase-Prompting: TDD for Gemini Prompts

## TDD Cycle for Prompts

1. **RED** - Write unit tests with mock AI responses covering known failure modes. Tests MUST fail before any fix.
2. **GREEN** - Fix in priority order: structured output schema > prompt constraints > response sanitization code. Run tests until green.
3. **REFACTOR** - Run integration tests (if API key available) to validate against real Gemini. Add quality assertions.

**Bug-fix variant:** When fixing a bug (not adding a field), you still follow RED-GREEN-REFACTOR. First diagnose the root cause by reading code. Then write failing tests for ALL 8 failure modes on the affected field — not just the mode that triggered the bug. The bug proves the field's defenses are weak; test them all.

## Gemini Response Failure Modes (Mandatory Test Checklist)

When Gemini is asked for a scalar value without structured output, expect these failure modes. **You MUST write a test for EVERY row** when adding or modifying a scalar field — no exceptions, no "the sanitizer already covers this."

**Label each test** with its failure mode number (e.g., `// Failure Mode #3: JSON object wrapper`). This ensures you can visually confirm all 8 are covered.

| # | Failure Mode | Example Response | Expected Parse |
|---|---|---|---|
| 1 | Verbose null | `"The description is not explicitly stated in the document. null"` | `null` |
| 2 | Markdown-wrapped | `` "`4077`" `` or `` "```json\n\"4077\"\n```" `` | `"4077"` |
| 3 | JSON object wrapper | `'{"description": "Strata dispute"}'` | `"Strata dispute"` |
| 4 | Prefixed value | `"The client number is 4077"` | `"4077"` — or reject via length limit |
| 5 | Thinking + answer | `"Let me check... The matter number is L145"` | `"L145"` — or reject via length limit |
| 6 | Extremely long | 500+ char explanation | `null` (reject) |
| 7 | Whitespace-only | `"   \n  "` | `null` |
| 8 | Case-variant null | `"NULL"`, `"Null"`, `"None"` | `null` |

**If a test reveals sanitization can't handle a failure mode:** Escalate to a higher defense layer (prompt constraints or structured output). Do NOT accept a passing test with a bad value — that means the defense is insufficient.

## Defense Priority

1. **Structured output** (`responseMimeType: 'application/json'` + `responseSchema`) — best defense, forces JSON conformance
2. **Prompt constraints** — explicit "respond with ONLY the value or null" instructions
3. **Code sanitization** — `sanitizeScalarResponse()` as last-resort cleanup

Use structured output for complex objects (Wave 1, Wave 3). Use prompt constraints + sanitization for simple scalar fields (Wave 2).

## Codebase Map

| File | Role |
|---|---|
| `functions/matter-extraction/extractFields.js` | Extraction pipeline (Wave 1/2/3), parsing logic |
| `functions/matter-extraction/prompts.js` | All prompt templates and field descriptions |
| `tests/functions/matter-extraction/extractFields.test.js` | Unit tests with mock AI (DI pattern) |
| `tests/functions/matter-extraction/extractFields.integration.test.js` | Live Gemini tests (requires API key) |

## DI Testing Pattern

The `extractFields()` function accepts `options.ai` for dependency injection. Create mock AI:

```js
const mockAi = { models: { generateContent: vi.fn() } }
// Mock sequential calls: Wave 1, then Wave 2 per field, then Wave 3 per person
mockAi.models.generateContent
  .mockResolvedValueOnce({ text: JSON.stringify(wave1Response) })
  .mockResolvedValueOnce({ text: 'verbose garbage here' }) // Wave 2 field
```

## Common Mistakes

| Mistake | Why It Fails |
|---|---|
| Checking only `text === 'null'` | Gemini returns `"NULL"`, `"null."`, verbose explanations |
| No length limit on scalar responses | LLM returns full paragraphs instead of values |
| Trusting markdown-free responses | Gemini wraps in backticks or code blocks unpredictably |
| Testing only happy path | Failure modes are the whole point of prompt TDD |
| Accepting a bad value as "good enough" | If a test passes with `"The jurisdiction is BC"` instead of `"BC"`, the defense is broken — escalate to a higher defense layer |
| Skipping failure mode rows | "The sanitizer already handles this" is not a reason to skip the test — tests document expected behavior for THIS field |
| Only testing the failure mode that caused the bug | A bug in one mode means the field's defenses are weak — test ALL 8 modes, not just the broken one |
| Unlabeled failure mode tests | Without `// Failure Mode #N` comments, you can't verify coverage at a glance — always label |
