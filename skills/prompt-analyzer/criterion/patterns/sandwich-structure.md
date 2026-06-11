# Sandwich Structure

**Category:** Structure Pattern
**Priority:** Critical

## Pattern

Place user input last, sandwiched after all priming content:

| Layer | Content | Purpose |
|-------|---------|---------|
| 1. System/Task | Role definition, high-level instructions | Prime model behavior |
| 2. Context/Rules | Constraints, tone, background data, output format | Set boundaries |
| 3. Examples | 3-5 input/output pairs demonstrating desired behavior | Show the pattern |
| 4. Final Input | The actual question or data to process | **Must be last** |

## Why This Works

- LLMs weight recent context more heavily (recency bias)
- Examples immediately before input create strong pattern-matching
- Instructions at top establish persistent behavioral constraints

## Violations to Flag

- User input buried in the middle of instructions
- Examples appearing after the input placeholder
- Instructions split before and after user input

## Scoring Impact

| Violation | Point Deduction |
|-----------|-----------------|
| Input not last | -5 to -10 |
| Examples after input | -3 to -5 |
| Split instructions | -2 to -4 |
