# Harden Mode

## Core insight

Extracting a deterministic procedure out of prose and into a script
eliminates LLM variance for that procedure — the same input will always
produce the same output, because a script has no judgment to vary. This is
**not** about consuming fewer resources. A 200-line step-by-step procedure
that an LLM currently re-reads and re-executes on every invocation becomes
a single line: `Run: scripts/do_thing.<ext> <args>`. The win is that the
script gets it right the same way every time; the trade-off is that the
result is more brittle than prose an LLM can flex around when
circumstances differ slightly.

## Required background skills

Load these before proceeding:

- `superpowers:test-driven-development`
- `superpowers:writing-skills`

## The Iron Law

```
NO HARDENING WITHOUT BASELINE TESTS FIRST
```

If baseline tests are skipped or written after the fact, delete the
extraction work and restart from Stage 3. There are no exceptions,
including these three that come up often:

- "the extraction is obvious"
- "just moving code blocks"
- "I'll backfill tests"

## Language selection

Determine the extraction language before Stage 4 at the latest:

- If the user specified a language, use it.
- Otherwise, ask the user before proceeding.

Then load `references/<language>.md`. Only languages with a reference file
are available: `python`, `javascript`.

## Stage pipeline

| Stage | File | Title |
|---|---|---|
| 1 | `harden-stages/inventory.md` | File Inventory |
| 2 | `harden-stages/classify-and-score.md` | Classify and Score |
| 3 | `harden-stages/baseline-tests.md` | Baseline Tests |
| 4 | `harden-stages/extract.md` | Extract |
| 5 | `harden-stages/verify.md` | Verify |
| 6 | `harden-stages/commit-and-finalize.md` | Commit and Finalize |

## No-read-ahead rule

Read exactly one stage file at a time. Each stage file ends with a Gate
that names the next file to read. Reading ahead — even "just to understand
the full process" — is a violation of this rule, because it leads to
stage-skipping. The rationalization "I'll read ahead to understand the
full process first" is explicitly forbidden.

## Promised output structure

```
<skill-name>-hardened/
  SKILL.md
  scripts/           # extracted helper scripts
  references/        # inherited from original (if any)
  tests/             # regression tests (ALWAYS present, never deleted)
    baseline-results.md
    scenario-*.md
```

## Red flags

| Rationalization | Reality |
|---|---|
| "Extraction is obvious" | Obvious extractions still break subtle behavior. Test first. |
| "Backfill tests after" | Tests written after hardening verify what you built, not what you should preserve. Worthless. |
| "Just extracting code blocks" | Code blocks carry context (thresholds, error formats, edge cases). Easy to lose. |
| "I'll script this checklist" | Checklists require judgment → non-deterministic → scripting them wastes effort. |
| "No scripts found, but I can still restructure" | If no deterministic procedures exist, hardening doesn't apply. Exit cleanly. |
| "I'll read ahead to understand the full process" | Each stage gives you exactly what you need. Reading ahead causes stage-skipping. |

## Quick reference

| Skill content type | Hardening strategy |
|---|---|
| Deterministic procedures | Extract to helper scripts |
| Non-deterministic content (judgment, guidelines) | Leave in SKILL.md — LLM flexibility is the value |
| Reference material (schemas, examples) | Leave in SKILL.md — no hardening benefit |

## Common mistakes

| Mistake | Correction |
|---|---|
| Skipping baseline tests | Always do Stage 3 first — no exceptions. |
| Reading ahead | Read only the current stage file. |
| Forcing scripts onto non-deterministic content | Leave judgment-based content in prose. |
| Modifying the original skill directly | Always create a `-hardened/` copy instead. |
| Forgetting to save tests | Tests are mandatory and live in `<name>-hardened/tests/`. |
| Not testing extracted scripts | Actually run each script against sample input. |
| Framing the value as resource savings | The value is determinism, not speed or cost. |
| Creating a deprecated/archived folder | Git history is the recovery mechanism — no archive folders. |
| Committing original and hardened together | Commit ONLY the hardened files in Stage 6. |
| Combining classification with test writing | Finish all of Stage 2 before starting Stage 3. |

## Start

Read `harden-stages/inventory.md` next.
