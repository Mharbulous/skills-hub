# Claude Curator — Vision & Design Philosophy

**Date:** 2026-04-17

> Claude Curator automates the maintenance of a project's `AGENTS.md` hierarchy based on empirical analysis of git history, placing each curated line at the tightest folder scope where observed commit evidence supports it — so any Claude session loads exactly the guidance relevant to the code being touched. Human-authored content lives outside `<CURATED>` tags and is never touched; the automation must demonstrably maintain `AGENTS.md` better than a human would, with human-maintained content preserved as the benchmark.

## 1. Theme & Design Philosophy

The skill automates `AGENTS.md` maintenance without ever interfering with human-authored additions. Every design decision reinforces two structurally separate concerns: (a) the curator owns only what lives inside `<CURATED>` tags, and (b) within those tags, each line earns its folder-depth placement from observed commit evidence. The surrounding machinery — SQLite, immutability triggers, competitive placement, model-tier routing — exists to make that automation trustworthy enough to hand it those managed zones unsupervised.

### Design Principles

1. **Authorship boundary is inviolable.** Anything outside `<CURATED>` tags in any `AGENTS.md` file is human territory. The curator never reads it for placement decisions, never mutates it, never re-orders it. *Violation:* tidying whitespace, normalizing heading levels, or "fixing" a typo outside the tags. *Why:* the human-authored content is deliberately preserved as the benchmark the curator must outperform — touching it corrupts the comparison.

2. **Tightest-fit folder placement.** Each curated line lives at the narrowest folder scope where git evidence still supports it. Lines with path breadth concentrated in `features/spellcheck/**` sink into `features/spellcheck/AGENTS.md`; lines with path breadth spanning the whole repo rise to `./AGENTS.md`; lines observed relevant across multiple repos promote to `~/.claude/AGENTS.md`. Placement is bidirectional and continuously rebalanced as evidence shifts.

3. **Earned placement, never authored placement.** Lines enter the managed zone only after accumulating `observed` relevance events against real commits. No manual priority overrides, no pinning, no category bonuses, no thresholds — the budget is the only gate. *Why:* any human-tuning knob would smuggle the human-authorship benchmark back into the curator's territory and break the A/B frame.

4. **Immutability preserves honest history.** Once a line is placed, its wording is permanent — enforced at the database engine level by `BEFORE UPDATE` triggers. *Why:* relevance data is attached to specific wording; if wording changed, accumulated history would become misleading. Corrections happen by proposing a new line and letting the old one decay.

5. **Deterministic work stays deterministic.** Parsing git log, ranking by composite score, tier classification — these are Python stdlib + SQLite, not LLM calls. LLMs are reserved for tasks that genuinely require semantic judgment (scoring relevance) or creative synthesis (gap analysis for proposed lines). *Why:* LLM variance in mechanical work produces fabricated output; hardening phases to scripts eliminates it.

6. **Cheapest capable model per phase.** Each phase dispatches to the tier that can handle it: Python for deterministic, Haiku for template assembly, Sonnet for semantic matching, Opus only for genuine creative gap analysis. Running all phases on the ambient model wastes Opus on mechanical tasks.

7. **Zero-dependency portability.** No third-party Python packages, no build step, no package manifest. Drop the folder into `~/.claude/skills/` and it works. *Why:* frictionless install is a precondition for the skill being trusted with automated maintenance across many repos.

### Litmus Test

**Does this help place each `<CURATED>` line at the tightest folder scope where git evidence supports it?**

- *Yes:* adding a third hierarchical tier (feature-folder `AGENTS.md` files) so narrow-scope lines can sink below the project-local tier.
- *Yes:* recording `relevant_paths` per event so path-breadth can inform depth placement.
- *No:* a "pin" flag to force a line to stay in the global tier regardless of evidence.
- *No:* editing content outside `<CURATED>` tags — orthogonal to placement, breaks the boundary.
- *No:* a global-only mode that flattens the hierarchy — abandons tightest-fit placement.

## 2. Purpose

### Audience

Solo developer, primary user: the author, on a personal Windows Claude Code setup. Not currently published for other users; not currently shared with a team. Future trajectory — if the N-tier folder-placement design proves itself against the human-maintained benchmark, the skill could generalize to other Claude Code power users. A multi-user "popularity dimension" for shared `./AGENTS.md` management remains deferred (see `reference/shared-claude-md.md`).

### Pain Points

Three linked symptoms of a single underlying problem — hand-curated `AGENTS.md` content decays:

- **`AGENTS.md` goes stale.** Lines that were once useful no longer match how the code evolved. The human who wrote them has moved on; the line lingers.
- **`AGENTS.md` gets bloated.** Accretion past ~200 lines causes Claude to ignore instructions (documented in `reference/2026-02-15-Writing-Excellent-AGENTS-md.md`). Humans add without subtracting.
- **Curation is guesswork.** No empirical basis for which lines actually inform Claude's decisions on real commits. Author intent is the only signal.

Folder placement is a fourth, deeper problem: even correct guidance, placed in the wrong `AGENTS.md` file, either loads irrelevant context into every session or fails to surface when the relevant code is being touched.

### Value Proposition

Automated `AGENTS.md` maintenance that is demonstrably better than the human-maintained benchmark — because lines earn placement from commit evidence rather than author intent, and sink or rise through the folder hierarchy to surface only when working in the code they apply to. The human authorship boundary is structurally preserved by `<CURATED>` tags, so the human-maintained sections remain the control group the automation must outperform.

### Killer Use Case

A developer returns to a feature they haven't touched in 3 months and asks Claude to extend it. Because the curator has spent those months routing commit-derived guidance to the tightest folder scope, Claude loads the feature-folder `AGENTS.md` and gets exactly the gotchas, conventions, and design principles that historically mattered for *that* feature — without wading through global context that doesn't apply. The developer gets the benefit of "past-self documented this for me" *without having ever written the documentation*, because the curator inferred it from commit evidence and placed it where it surfaces at the right moment.

## North Star Metric

Compared against the human-maintained portion of `AGENTS.md` files as the benchmark (control), the curator's managed zone should measurably do better at loading exactly the right context during Claude sessions.

Formally — let `S` be a Claude session, `L(S)` the set of lines loaded into context from all `AGENTS.md` files, and `R(S) ⊆ L(S)` the subset empirically relevant to the code touched in `S`:

```
relevance_precision(S) = |R(S)| / |L(S)|
```

The curator wins when `relevance_precision` averaged over many sessions is higher for curated lines than for human-authored lines across the same `AGENTS.md` hierarchy.

Equivalently, for any individual `<CURATED>` line, optimal placement means the folder depth matches the breadth of paths where the line has been observed relevant — a line relevant only in `features/spellcheck/**` belongs in `features/spellcheck/AGENTS.md`, not `./AGENTS.md`.

## 3. Non-Goals

- **Managing the shared `./AGENTS.md`'s unmanaged zones.** Content outside `<CURATED>` tags is human territory in every file at every depth — including the root.
- **Real-time / per-commit operation.** The cycle is cursor-based and batched (100 commits per run). No on-commit hooks, no watchers.
- **Team collaboration / multi-user popularity scoring.** Deferred — requires 2+ users daily, not a current constraint.

## 4. Anti-Patterns

*No anti-patterns documented yet — add entries here as they are discovered empirically.*
