# Stage 2: Classify and Score

## Goal

Classify every SKILL.md section from Stage 1's inventory as deterministic
or not, score the deterministic ones, and select exactly one extraction
candidate for this run (or exit cleanly if none qualify).

## Prerequisites

- Stage 1's inventory and section list.
- Load `references/determinism-heuristics.md` now — its rubrics and
  formula are used throughout this stage and are not repeated here.

## Steps

### Step 1: The determinism question

For each section from Stage 1's list, ask:

> **Given identical input, would this section always produce identical
> output?**

Classification runs on determinism, not on format:

- Tables of transformation rules (normalization, scoring thresholds) **ARE**
  script-extractable.
- Code blocks containing judgment calls ("review and decide") are **NOT**
  script-extractable.
- Checklists needing context-dependent interpretation are **NOT**
  script-extractable.
- Step-by-step procedures with enumerable branches **ARE**
  script-extractable.

Sections that answer NO are marked Declarative/Reference and set aside.

### Step 2: Score

For each section that answers YES, score it 0–3 on all 11 heuristics
defined in `references/determinism-heuristics.md`. Do not duplicate the
full rubric text here — read it from that reference.

### Step 3: Rank

Compute each scored section's Determinism Value:

```
Determinism Value = (Heuristic Score / 33) × (Section line count) × (Execution frequency per invocation)
```

"Execution frequency per invocation" is an estimate, not a precise count —
judge qualitatively how many times per hardening run this section's logic
would execute (once per run, once per item in a loop, etc.) and use that
as the multiplier.

Priority bands: **High** (≥18) extract first; **Medium** (9–17) extract if
time permits; **Low** (≤8) skip.

### Step 4: Git-history check

Run:

```
git log --all --grep="\[hardening:<skill-name>:" --oneline --format="%h %s (%ai)"
```

substituting the actual skill name. If this returns any matches, display a
"Previously Attempted Hardenings" section — listing commit hash, script
name, and date for each match — **before** the candidate list in Step 5.
This is informational only: it never filters or excludes candidates. If no
matches are found, skip this section silently (don't mention its absence).

### Step 5: Present top 3

Present the top 3 scored candidates:

```
Top Script Extraction Candidates:

1. [Section Name]
   - Heuristic Score: X/33
   - Determinism Value: X,XXX
   - Key heuristics: [which scored highest]
   - Why extract: [what LLM variance this eliminates]
2. ...
3. ...
```

**HITL mode:** ask "Which candidate should I extract first? (Enter 1, 2, or
3, or 'skip' if no extraction is warranted)" and wait for the response.

**Autonomous mode:** auto-select #1 and announce: "Auto-selecting
highest-ranked candidate: [Section Name] (Determinism Value: X,XXX)".

### One-at-a-time principle

Exactly ONE extraction happens per hardening run, even if multiple
candidates score High.

### Clean-exit branch

If no section scores as an extraction candidate (every section is
Declarative/Reference, or every deterministic section falls below the
extraction threshold), show the classification breakdown, then state
exactly:

> "No script extraction candidates found. This skill's content requires LLM judgment and cannot be replaced with deterministic scripts. Hardening does not apply to this skill."

End the session. Do not create a `-hardened` copy. Do not offer a
progressive-disclosure or restructuring fallback of any kind.

## Gate

Before proceeding: confirm all sections are classified, all deterministic
sections are fully scored, and a candidate is selected (or the clean-exit
branch was taken, in which case the session has already ended).

**Read `baseline-tests.md` next.**
