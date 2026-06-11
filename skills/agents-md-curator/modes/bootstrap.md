# Bootstrap Mode — First-Run Seeding

**Invoked automatically** on first run when `claude-storage.db` doesn't exist.

## Steps

1. **Create database** [Python] — Run `python -c "import sqlite3; ..."` to execute `schema.sql`. No LLM needed. **Important:** Always use Python's `sqlite3` module for all database operations — do NOT use the `sqlite3` CLI, which is unavailable on Windows/MSYS2.
2. **Discover managed files** [Python] — Run:
   ```bash
   python scripts/discover_managed_files.py <repo_root> --db <db_path> --repo <name> --include-home
   ```
   Walks the tree, finds every `AGENTS.md` containing a `<CURATED>...</CURATED>` block, and upserts each into `managed_files`. Use the JSON output for the next step.
3. **Import existing managed content** [Sonnet] — For each discovered file, spawn a **Sonnet** agent to decompose **only the content inside the `<CURATED>` block** into atomic units. Each unit enters the `lines` table as `origin = 'imported'`, permanent and immutable from day one. They start with zero relevance events.
   - **The authorship boundary is inviolable:** never read, parse, or score content outside the tags. The human-authored portions of every file are the benchmark the curator must outperform — touching them corrupts the comparison.
   - **Why Sonnet:** Decomposing prose into indivisible guidance units requires understanding what constitutes a single "piece of guidance" — semantic judgment, not pattern matching.
4. **Set commit cursor to 100 commits from HEAD** [Python] — Run:
   ```bash
   python scripts/commit_ingestion.py --init-cursor <db_path> <repo> --repo-path <path>
   ```
   This sets the cursor to HEAD~100 (falls back to earliest commit if repo has < 100 commits) and inserts into `repo_cursors`. No LLM needed.
5. **Analyze first 100 commits** — Follow the introspect mode phases. Phase 1 will run `git log --reverse ... <cursor>..HEAD` returning up to 100 commits after the cursor. Phase 6 advances the cursor to the last analyzed commit.

Imported lines with no relevance to the first 100 commits **will be evicted immediately** from each managed file's budget. They remain in cold storage and earn their way back when relevant work resumes.

## First-Run File Behavior

The curator never creates a managed file silently and never modifies content outside `<CURATED>` tags.

- If a `AGENTS.md` exists at a given path **with** a `<CURATED>` block — it is treated as managed; the block contents are imported.
- If a `AGENTS.md` exists **without** a `<CURATED>` block — it is left strictly alone, and the curator emits a one-line message:
  > *Found `<path>` with no `<CURATED>` block. Add `<CURATED></CURATED>` where you want managed content; the next run will discover it.*
- If `./AGENTS.md` does not exist — the curator creates it containing only an empty `<CURATED>\n</CURATED>` block. Nothing else.

`./CLAUDE.local.md` is no longer a concept. If a prior run produced one, remove it manually; place its content (if you still want it) inside a `<CURATED>` block in `./AGENTS.md` or any deeper `AGENTS.md`.

## Edge Case: Repo Has No Commits

Skip analysis. Perform discovery + seeding only.
