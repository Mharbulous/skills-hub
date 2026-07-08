# Test Mode

## Overview

Measure the difference between two skill variants (typically an original
and its hardened counterpart) with equal rigor whether the result shows an
improvement or shows no difference at all. A null result is a valid,
useful result — it is not a failure to be minimized or explained away.

## Inputs

- Skill A and Skill B (two skill variants to compare).
- A single, byte-identical test prompt used for every trial of both
  skills.
- 3 trials per skill (minimum).

## Auto-detection

If only one skill is named, look for its `-hardened` sibling resolved
relative to that skill's actual location (e.g. given `.claude/skills/foo`,
look for `.claude/skills/foo-hardened` in the same parent directory —
`.claude/skills/` here is only an example; use wherever the named skill
actually lives). If no sibling is found, ask the user to name the second
skill explicitly rather than guessing.

## The Iron Rule

```
IDENTICAL INPUTS. SEQUENTIAL EXECUTION. NO SHORTCUTS.
```

## Time-pressure rule

Before starting, inform the user that N trials per skill takes roughly
N × 2–3 minutes per skill. Under time pressure, never reduce the trial
count below 3 per skill, never skip trials, and never parallelize
execution to save time.

## Phase 1: Setup

1. Read both skills' SKILL.md files.
2. Verify the chosen test prompt actually exercises the core functionality
   being compared — not an incidental code path.
3. Plan the trial order as strictly alternating: A1, B1, A2, B2, ..., up
   to A_N, B_N.
4. Use model `sonnet` by default (most consistent variance per prior
   observation), unless the user specifies a different model.
5. Use `max_turns: 50` by default, unless the user specifies otherwise.

## Phase 2: Execute trials

For each trial, in strict alternating order:

1. Launch a `general-purpose` Task subagent with: the test prompt, which
   skill (A or B) to use, `max_turns`, `model`, and `run_in_background:
   true`.
2. Wait for that subagent to complete before launching the next trial —
   never run two trials concurrently.
3. Extract metrics for that trial from the subagent's own transcript /
   structured output (the Task tool's per-trial output — locate whatever
   message list, tool-use log, and usage summary the harness provides for
   that specific subagent run) using this table:

   | Metric | Source | Notes |
   |---|---|---|
   | Duration (ms) | first & last timestamps | wall-clock |
   | API calls | count of assistant messages | round trips |
   | Tool uses | count of `tool_use` blocks | individual invocations |
   | Input context | sum of `input_tokens` + `cache_creation_input_tokens` + `cache_read_input_tokens` | total context processed |
   | Cost ($) | task completion message | if available |

   **Never use `output_tokens`** as a metric — it is a fragment count
   (roughly 1–25 per call), not a real usage measure.

4. Also record the trial's functional output, for equivalence comparison
   in Phase 3.
5. Record all metrics for the trial in a running results table before
   launching the next trial.

## Phase 3: Analyze

**3a. Summary statistics.** For each metric, compute mean and standard
deviation per skill. `Delta = |mean_A − mean_B|`.
`Delta % = (Delta / mean_A) × 100`.

**3b. Significance.** `Significant = delta > 2 * max(std_A, std_B)`.

**3c. Variance comparison.** Lower standard deviation means more
consistent behavior. Count, across all metrics, which skill has the lower
std in a majority of them.

**3d. Functional equivalence.** Did A and B produce the same functional
results? If not, are the differences minor or major? Which output is more
correct, judged against each skill's own stated rules?

## Phase 4: Report

Produce a report with exactly this structure:

- Title: `# A/B Test Results: [A] vs [B]`
- Date
- Model
- Trials per skill
- **Raw Trial Data** table: Trial, Skill, Duration (ms), API Calls, Tool
  Uses, Input Context, Cost
- **Summary Statistics** table (one row per metric — Duration, API Calls,
  Tool Uses, Input Context): Metric, A mean±std, B mean±std, Delta %,
  Significant? (YES/NO)
- **Variance Comparison** table: Metric, A Std, B Std, Lower Variance —
  followed by a line: "[Skill X] has lower variance in M/N metrics."
- **Functional Equivalence** summary
- **Decision**

## Phase 5: Decision matrix

| Result | Action |
|---|---|
| B shows lower variance AND no degradation elsewhere | B is an improvement. Recommend keeping B. |
| B shows no variance reduction | B doesn't achieve its goal. Recommend reverting to A. |
| Means differ significantly (any metric) | Investigate cause. Report which is better and why. |
| Functional differences found | Investigate which is more correct. Report findings. |
| No significant difference on any metric | Skills equivalent. Recommend the simpler one (fewer files, less complexity). |

Never auto-delete or auto-modify either skill based on this decision. If B
is recommended, say: "To replace the original skill with the hardened
version, run `/determinize -promote` in a new session." Do not load
`modes/promote.md` from test mode under any circumstances — promotion is a
separate, deliberately-invoked mode.

## Common rationalizations (all wrong)

| Rationalization | Why it's wrong |
|---|---|
| "3 trials is enough, no need for more" | 3 is a minimum, not a target — run more if results are ambiguous. |
| "Run in parallel to save time" | NO — sequential execution is required by the Iron Rule. |
| "Pairwise parallel preserves alternation" | NO — trials must run one at a time, not in paired batches. |
| "User's in a hurry, skip some trials" | NO — inform the user of the time cost; never silently cut trials. |
| "3A + 2B, asymmetric but defensible" | NO — trial counts must be equal per skill. |
| "The prompts are close enough" | NO — prompts must be byte-for-byte identical. |
| "I'll eyeball it instead of computing stats" | NO — always compute mean, std, and the significance test. |
| "One outlier, just remove it" | NO — outliers are data. Note them, but keep them in the statistics. |
| "Obvious from trial 1" | NO — N=1 proves nothing. Complete the full trial count. |

## "Baseline" vs "green" vocabulary

In harden mode, "baseline" results describe the ORIGINAL skill's behavior
(recorded in Stage 3) and "green" results describe the HARDENED skill's
behavior (recorded in Stage 5), which must match baseline. Test mode has
no "green" concept — it computes head-to-head statistics between two
variants instead. This baseline/green vocabulary is a holdover from the
TDD RED → GREEN → REFACTOR framing under which `determinize` itself was
built (see the `tests/*-results.md` provenance files) — it does not carry
special meaning inside test mode itself.
