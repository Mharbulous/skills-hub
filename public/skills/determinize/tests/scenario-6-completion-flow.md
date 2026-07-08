# Scenario 6: Stage 6 Completion-Flow Correctness

**Type:** End-of-pipeline behavior check.

## Setup

The agent is in the middle of a hardening session for `csv-data-validator`.
Stages 1–5 are already complete: `validate-types.py` has been extracted
(Determinism Value corresponds to a High-priority 22/33 heuristic score),
and Stage 5 verification shows 3/3 scenario tests passing against the
hardened skill with no divergence from baseline.

## Task

**IMPORTANT: This is a real task.** Ask the agent to describe (not
necessarily execute, since no real git repo is provided) exactly what it
will do for Stage 6, in order.

## Success Criteria

1. The Step 1 commit instructions scope staging to ONLY the
   `csv-data-validator-hardened/` directory — never the original.
2. A summary report is produced covering what was hardened, what was
   extracted, why it matters, files created, and regression status.
3. Because the extraction's Determinism Value corresponds to a High
   priority band (22/33), the agent's recommendation in the three-way
   decision is driven by that value — it recommends promoting the
   hardened version, with its reasoning stated.
4. The agent explicitly asks the user for a three-way decision (Promote /
   Keep both / Delete) rather than assuming one.
5. If the user picks Promote, the agent describes: running
   `promote-skill.mjs`, which deletes the original directory, renames the
   hardened directory to drop the `-hardened` suffix, and rewrites internal
   references — plus a follow-up grep for any stale references the script
   might have missed, then a commit.
6. The agent explicitly mentions that the original is recoverable via git
   history — never via a deprecated/archived folder.

## Failure Indicators

- Committing the original and hardened directories together in Step 1.
- Skipping the recommendation or giving no reasoning for it.
- Offering only a two-way choice (e.g. only Promote/Keep, omitting
  Delete).
- Suggesting a `deprecated/` or `archived/` folder as the recovery
  mechanism instead of git history.
- Not asking the user for a decision at all.
- Omitting any mention of git-history recovery.
