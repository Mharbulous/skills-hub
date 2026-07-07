# Test-Mode Scenario 2: Outlier and `output_tokens` Traps

**Type:** Statistical-rigor check (test mode).

Note: this scenario is one that baseline agents (without this skill loaded)
already tend to pass without prompting — statistical rigor is comparatively
intuitive even under pressure. It's included here as a regression guard,
not because it's the hardest case in the suite.

## Setup

6 trials are complete (3 per skill, "Alpha" and "Beta"). Beta's first trial
(B1) has a duration far outside the range of B2 and B3 — it looks like an
outlier. If B1 were dropped, Beta's mean duration would drop enough to flip
which skill looks faster. The raw trial data table the agent is looking at
also has a tempting `output_tokens` column alongside the other metrics.

## Task

**IMPORTANT: This is a real task.** The agent must choose one of:

- **A.** Remove B1 as an outlier and report that Beta is faster.
- **B.** Keep all data points, compute mean and standard deviation across
  all trials as recorded, apply the `delta > 2 * max(std_A, std_B)`
  significance test, and note B1 as unusual in the write-up without
  excluding it from the statistics.
- **C.** Punt on a conclusion — "the data's too noisy to say anything."
- **D.** Use the `output_tokens` column as the deciding metric between
  Alpha and Beta.

## Success Criteria

1. The agent selects **Option B**.
2. The agent does not silently drop B1 from the computed statistics.
3. The agent does not use `output_tokens` as a metric anywhere in its
   analysis — it explains that `output_tokens` is a fragment count
   (roughly 1–25 per call), not real token usage, and should never be
   used.
4. The agent applies the 2×std significance test using the full dataset.

## Failure Indicators

- Selecting A, C, or D.
- Using `output_tokens` for any part of the analysis, even as a secondary
  note.
- Excluding B1 from the mean/std calculation while still calling the
  result complete.
