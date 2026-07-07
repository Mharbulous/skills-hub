# Scenario 5: Determinism-Based (Not Format-Based) Classification

**Type:** Classification correctness check.

## Setup

The agent is given `determinize2` (harden mode) and asked to run Stage 1
and Stage 2 against the fixture in `tests/sample-find-matches-skill.md`
(the `find-matches` skill).

## Task

**IMPORTANT: This is a real task.** Classify and score every phase of the
fixture skill.

## Success Criteria

1. Phase 1 (Normalization) is classified as extractable — it is a fixed
   table of transformation rules.
2. Phase 3 (Partial Containment / Word-Boundary Matching) is classified as
   extractable — it is a fixed table of comparison rules.
3. Phase 5 (Keyword Extraction) is classified as extractable — it is a
   fixed, enumerable pipeline.
4. Phase 4 (Relevance Review) is classified as NOT extractable — it
   explicitly requires contextual judgment.
5. Phase 5 scores highest among the extractable phases, at approximately
   26/33 against the 11 heuristics — driven by high scores on Iteration
   Over Collections, Multi-Step Deterministic Pipelines, Format
   Transformation, and Enumerable Branching.
6. The top-3 candidates are presented ranked by Determinism Value, not by
   which phase "looks most like code."
7. The agent's reasoning is framed in determinism terms ("would this
   always produce the same output"), not format terms ("this is a table so
   it's extractable").

## Failure Indicators

- Classifying Phase 4 as extractable because it's written as prose
  instructions rather than a code block.
- Classifying Phase 1 or Phase 3 as non-extractable because they're
  written as markdown tables rather than code.
- Ranking candidates by anything other than the Determinism Value formula.
- Token-savings framing anywhere in the classification reasoning.
