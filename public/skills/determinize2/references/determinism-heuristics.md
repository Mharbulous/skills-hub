# Determinism Heuristics

## Purpose

This reference gives the scoring system used in Stage 2 (`classify-and-score.md`)
to decide which sections of a skill are worth extracting into deterministic
scripts, and to rank the candidates against each other.

## Core question

For every section of a skill under review, ask exactly one question:

> **Given identical input, would the output always be identical?**

This is **not** the same question as "is this a code block?" A code block can
contain judgment ("review the diff and decide whether it's safe to merge").
A plain-prose checklist can be fully deterministic ("if status code is 4xx,
retry; if 5xx, fail"). Classification runs on determinism, never on format.

## Per-section workflow

1. Read the section.
2. Ask the core determinism question.
   - **NO** — mark the section Declarative/Reference. It is not extractable.
     Move to the next section.
   - **YES** — continue to step 3.
3. Score the section 0–3 on all 11 heuristics below.
4. Compute the section's Determinism Value (formula below).
5. Record the score and value.
6. After all sections are scored, rank them highest-value first.

## The 11 heuristics

### 1. Computational Intensity
Many calculations, comparisons, or modifications where a conventional
algorithm outperforms an LLM doing the same arithmetic by hand.
**Key question:** How bad are humans (and LLMs) at this computation?
- 0: No iteration, a single comparison.
- 1: Small iteration (fewer than 10 operations).
- 2: Medium iteration (10–100 operations).
- 3: Large iteration (100+ operations) or nested loops.

### 2. Data Volume with Low Signal Density
Reading a large amount of data where most of it is irrelevant to the task.
**Key question:** How much of this data is actually needed?
- 0: All data is relevant.
- 1: 50–70% signal.
- 2: 20–50% signal.
- 3: Less than 20% signal.

### 3. Iteration Over Collections
"For each of N items, apply deterministic rule X."
**Key question:** Does collection size directly affect reasoning cost?
- 0: No iteration.
- 1: Fixed, small collection (fewer than 10 items).
- 2: Variable collection (10–100 items).
- 3: Large or unbounded collection (100+ items, or user-provided size).

### 4. Precision-Critical Operations
Character-level matching, exact arithmetic, hashing, date parsing.
**Key question:** Does this require exact character-by-character correctness?
- 0: Fuzzy matching is acceptable.
- 1: Approximate correctness (roughly 90%) is acceptable.
- 2: High precision (roughly 99%) is required.
- 3: Perfect precision is required (100% — hashing, exact string equality).

### 5. State Accumulation Across Items
Building a running result across a sequence of items.
**Key question:** Does this build intermediate data that is only used later?
- 0: No accumulation.
- 1: Fewer than 10 items.
- 2: 10–100 items.
- 3: 100+ items, or complex nested accumulation.

### 6. File I/O as Filtering
Reading files or directories to extract a small piece of the content.
**Key question:** What percentage of the file's content is actually needed?
- 0: No file I/O.
- 1: Small file (under 1KB) or all of it is needed.
- 2: Medium file (1–10KB) that requires filtering.
- 3: Large file (over 10KB), or a directory with many entries.

### 7. Cross-Referencing Between Datasets
Comparing every item of dataset A against dataset B.
**Key question:** Does this compare items from two lists against each other?
- 0: No cross-referencing.
- 1: N × M is fewer than 100 comparisons.
- 2: N × M is 100–1,000 comparisons.
- 3: N × M is more than 1,000 comparisons.

### 8. Format Transformation
Parsing CSV, constructing JSON, building markdown tables.
**Key question:** Is this just moving data between formats with no interpretation?
- 0: No transformation.
- 1: Simple transformation (split/join).
- 2: Structured transformation (CSV → objects, objects → table).
- 3: Complex transformation (nested structures, multiple formats).

### 9. Multi-Step Deterministic Pipelines
Step A feeds step B, and both steps are themselves deterministic.
**Key question:** Are there intermediate results only used to compute the
final result?
- 0: Single step.
- 1: Two steps.
- 2: Three to four steps.
- 3: Five or more steps, or branching/merging pipelines.

### 10. Redundant Computation Across Phases
The same operation is repeated with the same inputs.
**Key question:** Is this calculation repeated with the same inputs?
- 0: No repetition.
- 1: Repeated 2–3 times.
- 2: Repeated 4–10 times.
- 3: Repeated 10+ times, or repeated across separate phases.

### 11. Enumerable Branching
All cases are fully specified — no judgment calls at the branch points.
**Key question:** Are all branches explicitly defined, with no judgment
required?
- 0: No branching, or the branching requires judgment.
- 1: 2–3 simple branches.
- 2: 4–6 branches, or nested branching.
- 3: 7+ branches, or a complex, fully-specified decision tree.

## Priority bands

Sum the 11 heuristic scores (max 33) and bucket the section:

- **High (18–33):** extract first.
- **Medium (9–17):** extract if time permits.
- **Low (0–8):** skip.

## Determinism Value formula

This is the unified ranking formula. The identical formula also appears in
`modes/harden-stages/classify-and-score.md` — the two must match byte-for-byte.

```
Determinism Value = (Heuristic Score / 33) × (Section line count) × (Execution frequency per invocation)
```

"Execution frequency per invocation" is a qualitative estimate, not a
precise count — see the note in `classify-and-score.md` for how to estimate it.

### Optional implementation-effort divisor

When two candidates are close in Determinism Value, divide each by an
estimated implementation-effort factor:

- Simple script (single function, fewer than 50 lines): divide by 1.0.
- Medium script (multiple functions, 50–150 lines): divide by 1.5.
- Complex script (external dependencies, more than 150 lines): divide by 2.5.

Rank candidates highest-value-first. Extract only the #1 candidate — one
extraction per hardening run.

## Misclassification red flags

Watch for these four mistakes:

1. **Scripting non-deterministic content.** Don't script "review and decide."
   Do script "run pytest, parse the output, count PASS/FAIL, return JSON."
2. **Classifying by format instead of determinism.** "It's a table, not code,
   so it's not extractable" is WRONG — a table of transformation rules is
   exactly the kind of thing that IS extractable.
3. **Ignoring low-scoring heuristics.** Heuristic scores are cumulative;
   moderate scores spread across many heuristics can still add up to a
   high-value candidate.
4. **Not estimating implementation effort.** Don't extract a 6/33 section just
   because "might as well" — weigh the effort against the value.
