---
name: vision-progress-report
description: Translate recent git history into a non-technical progress report aimed at the person funding development (owner, investor, patron). Every change must be tied to specific principles in the project's vision document. Use this skill whenever the user asks for a progress update, status report, funder report, investor update, owner update, or "what got built" summary — even if they don't say "vision" explicitly. Also use when the user asks to explain technical work in plain language for a non-technical stakeholder.
---

# Vision Progress Report

Translate a window of git history into a funder progress report anchored to the project's vision document. Sell what the funder is buying — reliability, defensibility, audit trail — not what the developers wrote.

## When this skill applies

Trigger phrases: "progress report", "status update", "what got built", "explain this to my investor / owner / boss", "non-technical summary of recent work", "report for the funder", or `/vision-progress-report`.

Not a generic changelog or commit summary. If no vision document exists, say so and offer a plain-English summary — but clarify the funder-grade version requires a vision doc.

## Inputs

1. **Time window.** Always review the last 24 hours. Don't accept alternative windows on the initial run — complete the standard report first, then offer to extend. Compute the window as `git log --since="24 hours ago"` against the current clock. State the window at the top (e.g., "Window: 2026-04-17 14:00 → 2026-04-18 14:00 UTC").
2. **Vision document.** Check in order: `docs/product-vision/vision.md`, `docs/vision.md`, `VISION.md` at repo root, anything in project `CLAUDE.md` (often a "Critical Rules" or "Vision" section), `docs/**/vision*.md` as last resort. If none found, stop and ask.
3. **Git history.** Use `git log --since="..." --pretty=format:"%h %ai %s"` and `git diff --stat <base>..HEAD`. Read the vision doc fully before reading commits.

## Report structure

```
## What your developers built [over the window] (in plain English)

[One-sentence framing: total commits, span of time, headline change.]

---

### [Phase 1 name — thematic, not chronological]

**What changed:** [Plain-English, 2–4 sentences. No file paths, class names, or hashes.]

**Why it matters for the vision:**
- **[Vision principle name]** — [One concrete consequence the funder cares about.]
- [Repeat per principle this phase touches.]

### [Phase 2 name]
[...same shape...]

---

### Bottom line for you as the funder

[2–4 numbered points stating the strategic gain, each naming the vision dimension it strengthened — reliability, honesty, defensibility, scope discipline, etc.]

### One thing to flag

[What the work did NOT touch that the vision still calls for. This is the steering signal — without it the report is reporting, not steering. If genuinely nothing was skipped, say so explicitly.]
```

## Grouping commits into phases

- Look for cycle markers in commit messages (e.g., `chore: design-write-loop cycle`, merge commits, "baseline green") — these usually delimit phases.
- Group by what the funder would call "one initiative."
- Name phases by outcome, not technique. "Splitting the app into three independent pieces" beats "Module decoupling refactor."
- Aim for 2–5 phases. If you reach six, ask whether two should merge.

## Writing "Why it matters" lines

1. Name the vision element by its actual title.
2. State a concrete consequence in funder language — not "this enforces invariant X" but "if a client questions a bill six months later, you can reproduce exactly what the AI was choosing from."
3. Connect one change to one principle. If a change touches three, pick the strongest. The point is clarity, not exhaustiveness.

## Tone rules (non-negotiable)

These rules exist because the audience is paying for the work and cannot evaluate code.

- No jargon: no file paths, commit hashes, class names, method names, framework names, schema versions.
- Frame everything as what the funder is buying: reliability, honesty, defensibility, audit trail, scope discipline, future-proofing.
- Use concrete consequences, not abstract architecture. "If a client questions a bill six months later, you can reproduce the exact universe of options the AI had at the moment of decision" beats "this provides a reproducible audit trail."
- Be honest about gaps — the "One thing to flag" section makes this a steering tool, not a victory lap. Funders trust reports that admit what got skipped. If a vision element wasn't advanced, say so by name.
- No hype words: "robust," "powerful," "seamless," "leverages," "enables," "best-in-class."

## Worked excerpt

The full original example lives in `references/example-output.md` — read it if you need a longer model.

> ### Cycle 1 — Splitting the app into three independent pieces
>
> **What changed:** The app used to be one big program. It's now three separate programs that run side-by-side: one that **records**, one that **thinks** (the AI), and one that **shows** you results.
>
> **Why it matters for the vision:**
> - **The recorder is now bulletproof.** If the AI crashes or the review screen freezes, the recorder keeps going. Your vision says the *only* unforgivable failure is losing captured time — this architecture makes that failure nearly impossible.
> - **The lawyer only gets interrupted when recording actually stops.** A new alert fires *only* when capture has died — no "hey, want to review now?" popups. This is your Principle 1 made literal.

## Anti-patterns

- Listing commits — a bulleted list of commit subjects is what the funder can't read. That's what they hired you to translate.
- Generic vision references — "this advances the vision" is hollow; always name which principle and how.
- Burying the gaps — if you skip it because everything looks rosy, the funder loses the ability to redirect spend. The gap section is the most actionable part.
- Opining on developer choices — report outcomes against the vision; let the funder draw conclusions.
- Padding — a 12-hour window with 121 commits doesn't require 12 phases. Two pages is plenty for a multi-day window; one page for a single day.

## Workflow

1. Confirm the time window; state the assumption.
2. Locate the vision document; if missing, stop and ask.
3. Read the vision document fully before reading commits.
4. Pull `git log` and `git diff --stat` for the window.
5. Group commits into 2–5 thematic phases.
6. Draft the report, applying tone rules.
7. Always include the "One thing to flag" section.
8. Deliver inline. Don't save to a file unless asked.
9. End with: "Want me to review the previous 24 hours as well?" If yes, run the skill again with the window shifted back by 24 hours (`--since="48 hours ago" --until="24 hours ago"`), and repeat the offer shifted back another 24 hours each time.
