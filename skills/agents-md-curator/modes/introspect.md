# Introspect Mode — Daily Cycle

**Invoked via:** `/agents-md-curator` (default mode)

The cycle has 7 phases. Phases 0, 1, 2, 5, 3, 4, 6 are executed in **dependency order** (note: phase 5 — depth assignment — runs before phase 3 — per-file budget fill — because per-file competition needs to know which lines are assigned to which file). Phase numbers stay aligned with the Model Routing table in `SKILL.md`; only the prose order reflects the dependency.

## Phase 0 — Discover Managed Files [Python]

**Run:** `python scripts/discover_managed_files.py <repo_root> --db <db_path> --repo <name> --include-home`

Walks the tree, finds every `AGENTS.md` containing a `<CURATED>...</CURATED>` block, upserts into `managed_files`, and emits JSON listing each file's path, depth, manual_units, and managed_budget. Phases 5, 3, and 6 all consume this list.

A file becomes managed simply by containing a `<CURATED>` block. There is no other registration — the tags are the registration.

## Phase 1 — Commit Ingestion [Python]

**Run:** `python scripts/commit_ingestion.py <db_path> <repo> --repo-path <path> [--limit 100]`

Reads the repo cursor from the database, runs `git log` for commits after the cursor (up to limit), and parses output into structured JSON. Trivial commits (typos, formatting-only via `style:` prefix or message keywords) are included but marked `trivial: true`.

- `<db_path>`: Path to `claude-storage.db`
- `<repo>`: Repository name (for cursor lookup in `repo_cursors`)
- `--repo-path`: Path to the git repository (default: current directory)
- `--limit`: Max commits to ingest (default: 100)

Output JSON contains `commits` (array of `{hash, msg, files, areas_touched, trivial}`), `cursor` (`{previous, current}`), `skipped_to` (hash if staleness guard fired, else `null`), and `stats`. Use the `commits` array as input for Phase 2.

## Phase 2 — Score All Lines [Sonnet]

Spawn a **Sonnet** agent (`Task` tool, `model: "sonnet"`) with:
- The commit summary JSON from Phase 1
- All lines from the database (query: `SELECT id, content, section FROM lines`)

The agent evaluates EVERY line (both active and cold) for relevance to the analyzed commits. "Relevant" means: informed a decision, prevented a mistake, or described a pattern that was followed.

For each match, the agent inserts a `relevance_event` row, including the **specific paths from the commit that supported relevance** in `relevant_paths` (comma-separated). These paths drive the depth assignment in Phase 5 — without them, lines have no signal for tightest-fit placement.

```sql
INSERT INTO relevance_events (line_id, repo, relevant_paths, commit_range, event_type, notes)
VALUES (?, '<repo>', '<comma-separated paths>', '<first_hash>..<last_hash>', 'observed', ?);
```

This phase accumulates data only — no promote/demote decisions yet.

**Why Sonnet:** Matching abstract guidance lines to concrete code changes requires semantic comprehension. Haiku cannot reliably judge whether a commit touching `stores/auth.js` is relevant to the line "check authStore.isInitialized before isAuthenticated."

## Phase 5 — Depth Placement [Python]

**Run:** `python scripts/depth_placement.py <db_path>`

For every permanent line, collects observed relevance events, partitions paths by repo, and routes the line to the deepest managed file whose directory covers the longest common path prefix. Cross-repo lines (≥2 repos with observed events) route to the home-global managed file (depth = -1). Lines without any observed events go unplaced this cycle.

Output JSON contains `assignments`, `by_file` (`{managed_file_path: [line_id, ...]}`), `promotions`, `unplaced`, `stats`. The `by_file` map is the key handoff to Phase 3.

Runs **before** Phase 3 — per-file competition needs the assignment first.

## Phase 3 — Competitive Placement [Python]

**Run:** `python scripts/competitive_placement.py <db_path> --managed-files <json_path>`

Build the input JSON from Phase 0's discovery output augmented with Phase 5's `by_file` map. The script then, **for each managed file independently**, ranks the lines assigned to that file by composite score (observed events HIGH weight, recency MEDIUM, path breadth LOW, predicted events 0.25x) and fills that file's budget top-down.

Output JSON contains a `files` map keyed by managed-file path. Each entry has `placed`, `cold`, `promotions`, `demotions`, and per-file `stats`. Use this output to drive Phase 6 file writing.

Lines that don't fit at their assigned depth stay cold for that file — they do **not** overflow into a shallower or deeper file. Tightest-fit is non-negotiable.

## Phase 4 — Generate Proposed Lines [Opus]

Spawn an **Opus** agent (`Task` tool, `model: "opus"`) with:
- The commit summary JSON from Phase 1
- The placed lines from Phase 3 output (what's currently in each managed file)
- The cold storage lines from Phase 3 output (what's available but not placed at any file)

The agent asks: "What 3-5 pieces of context would have helped but were missing from ALL of these lines?" and inserts new proposed lines:
```sql
INSERT INTO proposed_lines (content, origin_repo, origin_commits, gap_notes, section)
VALUES (?, '<repo>', '<commit_range>', ?, ?);
```

Proposed lines don't enter any AGENTS.md yet — they compete for promotion in future runs.

**Why Opus:** This is the only genuinely creative phase. It requires synthesizing patterns across 100 commits and reasoning about what guidance is *absent*.

## Phase 6 — Write Files and Advance Cursor [Sonnet]

Spawn a **Sonnet** agent (`Task` tool, `model: "sonnet"`) with the placement JSON from Phase 3 (placed lines per managed file).

For **each managed file** in the placement output, the agent:
1. Reads the file.
2. Locates the `<CURATED>...</CURATED>` block (single block per file; if missing, error and skip).
3. Groups that file's placed lines by `section` field, assembles markdown.
4. Replaces only the content **between** the tags. Everything before and after is preserved byte-for-byte.
5. Updates `managed_files.last_written_at` for that path.

After all files are written, update the repo cursor: `UPDATE repo_cursors SET last_commit_hash = '<last_hash>' WHERE repo = '<repo>'`.

**Authorship boundary:** the agent must not read, parse, or rewrite anything outside the `<CURATED>` tags. Even normalizing whitespace outside the tags is forbidden.

**Why Sonnet:** Replacing a precise span inside a file without disturbing surrounding content requires careful Edit tool use and instruction-following fidelity that Haiku does not reliably deliver — it merges existing content rather than replacing it cleanly.

## Commit Cursor

Analysis is cursor-based, sequential, and recent-first.

- **First run:** Start from ~100 commits before HEAD (see `modes/bootstrap.md`). Analyze first 100 commits. Record cursor.
- **Subsequent runs:** Resume from cursor. Analyze next 100 commits. Advance cursor.
- **Staleness guard:** If the cursor is > 200 commits behind HEAD, skip forward to HEAD~100. The `skipped_to` field in Phase 1 output records the new cursor hash (or `null` if no skip occurred). Ancient history is not worth the token cost.
- **Caught up:** Fewer than 100 new commits → analyze only those. Zero new commits → skip analysis entirely.

The first week of runs is a "training period" — ingesting historical relevance data before predictive mode becomes useful.

## Run Output

```
Claude Curator -- Listbot

Discovered managed files:  3
Commits analyzed:          100 (abc1234..def5678)
Cursor position:           commit 347 of ~1,200

Per-file results:
  ./AGENTS.md                                  budget 188  placed 142  cold  37  +6/-2
  ./features/spellcheck/AGENTS.md              budget 200  placed  41  cold   0  +4/-0
  ~/.claude/AGENTS.md                          budget 200  placed   8  cold   0  +1/-0

Proposed:           4 new lines generated
Cold storage total: 283 units across all files
```

When fully caught up:

```
Claude Curator -- Listbot: No new commits since last run.
Skipping analysis. Run /agents-md-curator predict to pre-load for upcoming work.
```

## Edge Cases

**User manually edits wording inside `<CURATED>`.** Old wording detected as missing → recorded as demotion, line returns to cold storage. New wording detected as unrecognized → imported as permanent. Old line retains its history. New line starts fresh. Immutability preserved.

**User adds new content inside `<CURATED>`.** Detected as unrecognized lines, imported as permanent. Compete normally on next cycle.

**User deletes content inside `<CURATED>`.** Recorded as demotion. Line returns to cold storage. Repeated manual deletion suppresses its competitive score.

**User edits anything outside `<CURATED>`.** Curator never reads it; no-op for the curator. The user's content stands.

**A managed file disappears from disk.** Phase 0 won't list it; Phase 3 won't write to it; placements that referenced it become stale but remain in history (placements table is append-only). Next run rebalances anything assigned to that path into cold storage.
