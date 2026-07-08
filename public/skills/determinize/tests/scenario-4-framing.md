# Scenario 4: Determinism Framing vs Token-Savings Language

**Type:** Framing/vocabulary check.

## Setup

The agent is given `determinize` and asked to explain, in its own words,
why hardening a skill is valuable — no specific skill is provided, this is
a framing-only conversation.

## Task

**IMPORTANT: This is a real task.** Ask the agent directly: "Why would I
want to harden a skill?" and evaluate its answer.

## Success Criteria

The answer should use language consistent with these passing phrases (or
close paraphrases of them):

- "identical output for identical input"
- "eliminates LLM variance"
- "more predictable and robust"
- "more predictable but more brittle" (the trade-off is acknowledged, not
  hidden)
- "scripts get it right the first time"

## Failure Indicators

The answer must NOT contain any of these failing phrases or their
paraphrases:

- "reduce token consumption"
- "save tokens"
- "more efficient"
- "smaller context window"
- "token optimization"
- "progressive disclosure"

## What to Watch For

An answer that is otherwise correct but slips in a token-savings
justification as a secondary benefit still fails this scenario — the
framing must be determinism-only, with the brittleness trade-off named
honestly.
