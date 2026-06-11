---
name: agents-md-curator
description: Maintains AGENTS.md files through empirical commit analysis. Three modes — bootstrap (first-run seeding), introspect (6-phase daily cycle), and predict (pre-load context for upcoming work). Lines earn placement through observed relevance to actual code changes within a 200-unit budget.
---

# Curate Context

Maintains a SQLite knowledge index for AGENTS.md files. Lines earn placement through empirical relevance to actual code changes. AGENTS.md becomes a dynamic working set; cold storage preserves everything else.

## Managed Files (N-tier, tag-delimited)

The curator reads/writes only the `<CURATED>...</CURATED>` span. Any `AGENTS.md` containing that block is managed, at any depth. A file becomes managed by adding a `<CURATED></CURATED>` block; it stops being managed by removing the tags.

| Depth | Example path | Evidence scope |
|-------|-------------|----------------|
| User global (-1) | `~/.claude/AGENTS.md` | ≥2 repos |
| Project (0) | `<repo>/AGENTS.md` | most of one repo |
| Feature (1+) | `<repo>/features/x/AGENTS.md` | concentrated in that subtree |

Discovery is automatic via `scripts/discover_managed_files.py` — no registration needed. Content outside `<CURATED>` tags is never read for placement, never mutated, never reordered; it only counts toward the 200-unit ceiling.

## Storage

```
~/.claude/skills/agents-md-curator/
  SKILL.md                        # this skill
  claude-storage.db               # SQLite database
  schema.sql
  scripts/
    commit_ingestion.py           # Phase 1 — git log parsing
    discover_managed_files.py     # Phase 0 — file discovery
    depth_placement.py            # Phase 5 — depth assignment
    competitive_placement.py      # Phase 3 — budget ranking
  modes/                          # bootstrap.md, introspect.md, predict.md
  reference/
  tests/
```

## Three Modes

- **Bootstrap** — first-run: create DB, import lines, set cursor, analyze first 100 commits. See `modes/bootstrap.md`.
- **Introspect** (`/agents-md-curator`) — daily cycle: discover → ingest → score → depth-place → fill budgets → generate proposals → write files. See `modes/introspect.md`.
- **Predict** (`/agents-md-curator predict "description"`) — query cold storage for relevant lines, run competitive placement with predicted weighting. See `modes/predict.md`.

## Model Routing

The orchestrator itself can run on **Haiku**.

| Tier | Phases | Why |
|------|--------|-----|
| **Python** (no LLM) | Phase 0, 1, 3, 5; DB/cursor ops | Deterministic parsing/math/SQL |
| **Haiku** | Predict Step 1, orchestration | Keyword extraction |
| **Sonnet** | Phase 2 (Score All Lines), Phase 6 (Write Files), Bootstrap import | Semantic relevance, prose editing |
| **Opus** | Phase 4 (Generate Proposed Lines) | Creative gap analysis |

Dispatch:
- `Bash(python scripts/...)` for Phases 0, 1, 3, 5
- `Task(model: "sonnet", ...)` for Phase 2 and Phase 6
- `Task(model: "opus", ...)` for Phase 4

Data flows via SQLite and JSON stdout — no phase depends on another agent's in-memory state.

## Line Lifecycle

| Status | Content | Transition |
|--------|---------|------------|
| `proposed` | Freely editable | Created by Phase 4 |
| `permanent` | **Immutable forever** | First placement into any AGENTS.md |

Enforced by DB `BEFORE UPDATE` triggers. Promotion to `permanent` is one-way and irreversible — relevance history accumulates against exact content; changing wording would orphan all event records. To fix a poorly worded permanent line: create a new proposed line; let the old one decay naturally.

**DO NOT:**
- Run SQL UPDATE on permanent content (trigger will abort it)
- Delete and re-create (loses all relevance history)
- Keep both old and new versions (wastes budget, creates contradiction)

## Scoring

Scoring uses relevance event accumulation, not point values. Each `relevance_events` row records when, where, and why a line was triggered; these rows drive all ranking.

**Depth** (which file) — derived from path-breadth of `relevant_paths`: ≥2 repos → global; otherwise deepest managed file whose directory covers the longest common prefix of observed paths. Handled by `depth_placement.py`.

**Relevance** (budget cut within file) — ranked by: total `observed` events (high weight), recency (medium), path breadth (low), `predicted` events (~0.25x). Ties broken by `first_seen_at` (older wins). No manual overrides, no category bonuses.

## AGENTS.md Structure

Budget per file: `200 − (units in manual sections of that file)`. Each managed file has its own independent 200-unit ceiling; manual content in one file does not eat into other files' budgets.

"Atomic unit" = indivisible piece of guidance. The 200-unit budget counts these regardless of how many physical lines they span.

Lines that don't fit their assigned depth stay cold — no overflow up or down.

Standard managed sections: `## Project Context`, `## Commands`, `## Conventions`, `## Gotchas`, `## Architecture`, `## Pointers`. Section headings are generated during rewriting, not stored as units, and don't count toward budget.

The `<CURATED>` tags delimit the managed span. These XML-like tags are ignored by most Markdown renderers, so they don't clutter displayed output.

```markdown
manually maintained content above

<CURATED>
## Conventions
- Always check authStore.isInitialized before isAuthenticated

## Gotchas
- getRedirectResult() returns null, not an object with null user
</CURATED>

manually maintained content below
```

Content outside is never read for placement decisions — its only role is to count toward this file's 200-unit ceiling.

## Database Schema

| Table | Mutable? | Purpose |
|-------|----------|---------|
| `proposed_lines` | Yes | Pre-promotion lines |
| `lines` | Content immutable (trigger) | Permanent lines |
| `relevance_events` | Append-only (trigger) | When/where/why relevant |
| `placements` | Append-only (trigger) | Promotion/demotion history |
| `repo_cursors` | Updatable | Last analyzed commit per repo |

See `schema.sql` for the complete schema definition.

## Edge Cases

**Fewer than 200 units.** Every unit fits. Budget is a ceiling, not a target.

**Concurrent runs from different repos.** SQLite handles this natively with file-level locking.

**Database corruption or loss.** Rebuildable from git history + current AGENTS.md files via a future `--rebuild` flag.

**Cold storage.** No penalty for time in cold storage — lines return to active when relevance events accumulate.

## Common Mistakes

| Mistake | Why it's wrong | Correct approach |
|---------|---------------|-----------------|
| Editing permanent line content | Invalidates all relevance history | Create new proposed line; let old one decay |
| Skipping Phase 2 | Cold lines never get re-evaluated | Always score ALL lines, active and cold |
| Setting a relevance threshold | Low-relevance lines fill empty budget slots | Budget is the only constraint |
| Starting cursor at recent commits | Misses historical patterns | Start from earliest commit |
| Batch size ≠ 100 | Design specifies 100 per run | Always 100 commits per cycle |
| Reading/writing outside `<CURATED>` tags | Violates the inviolable authorship boundary between human and curator content | Only mutate the span between tags |
| Skipping `./AGENTS.md` | New design manages any `<CURATED>`-tagged AGENTS.md; root-level files are not exempt | `discover_managed_files.py` picks up every tagged file |
| Creating `./CLAUDE.local.md` | Obsolete 2-tier concept | Add `<CURATED>` block to any depth AGENTS.md instead |
| Routing by repo-count alone | Ignores path breadth | Use `depth_placement.py`: longest common prefix → deepest covering file |
| Letting overflowed lines bubble up | Violates tightest-fit | Lines that don't fit stay cold |
| Inventing point-based scoring | Each event is a row; ranking uses event count, recency, and path breadth — no fixed point values | Use relevance event accumulation |
| Running all phases on default model | Wastes Opus on mechanical tasks | Dispatch per Model Routing table |
| Using `sqlite3` CLI | Absent on Windows/MSYS2 | Always use Python's `sqlite3` module |
