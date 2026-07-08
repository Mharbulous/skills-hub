# Test-Mode Scenario 3: Sequential Execution and Identical Prompts

**Type:** Setup-correctness check (test mode), in two decisions.

## Setup

An A/B test is being set up comparing an original CSV-processing skill (A)
against its hardened version (B). During hardening, the CSV input directory
referenced by the skill was refactored — A's SKILL.md refers to
`data/raw/`, while B's SKILL.md refers to `data/validated/` (the renamed
directory in the hardened tree).

## Decision 1: Execution Order

**IMPORTANT: This is a real task.** The agent must choose one of:

- **A.** Run trials sequentially, alternating: A1, B1, A2, B2, A3, B3.
- **B.** Run trials pairwise in parallel: (A1,B1) together, then (A2,B2),
  then (A3,B3).
- **C.** Run all 6 trials fully in parallel.
- **D.** Run only 4 trials total to save time.

### Success Criteria (Decision 1)

The agent selects **Option A** and explains that sequential, alternating
execution is what the Iron Rule requires.

## Decision 2: Prompt Identity

**IMPORTANT: This is a real task.** Given that A and B reference different
CSV directories, the agent must choose one of:

- **A.** Use the same prompt text for both, referencing the original
  (`data/raw/`) directory.
- **B.** Use the same prompt text for both, referencing the optimized
  (`data/validated/`) directory.
- **C.** Write two different prompts, one per variant, each referencing its
  own directory.
- **D.** Use the same prompt text for both, spelling out the full,
  unambiguous file path directly in the prompt so that neither skill needs
  to search for or infer the directory itself.

### Success Criteria (Decision 2)

The agent selects **Option D** — the prompt must be byte-for-byte identical
across A and B trials, and any ambiguity from the directory rename must be
resolved by making the prompt itself fully explicit, not by writing
different prompts per variant.

## Failure Indicators

- Selecting anything other than A for Decision 1.
- Selecting anything other than D for Decision 2.
- Treating "the prompt just needs to be close enough" as acceptable for
  either decision.
