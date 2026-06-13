# Test Scenario: Competitive Placement (Phase 3, per-file)

## Purpose
Verify that `scripts/competitive_placement.py` ranks the lines assigned to each managed file independently and fills each file's budget top-down. No cross-file overflow — lines that don't fit at their assigned depth stay cold for that file.

## Input State

`claude-storage.db` contains 8 permanent lines (all observed in repo `myapp` only — no cross-repo lines for this scenario):

| line_id | content | section |
|---------|---------|---------|
| 1 | "Always run pytest before committing" | Commands |
| 2 | "Use snake_case for Python functions" | Conventions |
| 3 | "The auth module uses JWT tokens" | Architecture |
| 4 | "Never modify migration files after merge" | Gotchas |
| 5 | "Config lives in app/core/config.py" | Architecture |
| 6 | "Use ruff for linting" | Commands |
| 7 | "Database seeds are in tests/fixtures/" | Pointers |
| 8 | "getRedirectResult returns null not object" | Gotchas |

Relevance events (all `observed`, all repo `myapp`):

| line_id | count | most_recent | typical relevant_paths |
|---------|-------|-------------|------------------------|
| 1 | 12 | 2026-02-10 | tests/, scripts/run.sh |
| 2 | 8 | 2026-02-12 | src/utils/, src/api/ |
| 3 | 6 | 2026-02-01 | src/auth/jwt.py |
| 4 | 6 | 2026-02-14 | migrations/, src/db/ |
| 5 | 3 | 2026-01-15 | app/core/config.py |
| 6 | 2 | 2026-02-13 | pyproject.toml |
| 7 | 1 | 2025-12-01 | tests/fixtures/ |
| 8 | 0 | — | — |

Phase 5 has already run and produced the assignment map. Two managed files in scope:

```json
{
  "managed_files": [
    {"path": "C:/myapp/CLAUDE.md",                    "repo": "myapp", "depth": 0, "managed_budget": 5},
    {"path": "C:/myapp/src/auth/CLAUDE.md",           "repo": "myapp", "depth": 2, "managed_budget": 3}
  ],
  "by_file": {
    "C:/myapp/CLAUDE.md":          [1, 2, 4, 5, 6, 7, 8],
    "C:/myapp/src/auth/CLAUDE.md": [3]
  }
}
```

(Line 8 is assigned to the root file because its history puts it there — but with 0 events its score is 0, so it places last.)

## Expected Behavior

For `C:/myapp/CLAUDE.md` (budget = 5):
1. Rank by composite score (observed events HIGH 3x, recency MEDIUM 2x, breadth LOW 1x; older `promoted_at` breaks ties).
2. Top 5 placed: 1, 2, 4, 3, 5 (event count dominates; recency breaks the 6-vs-6 tie between 4 and 3).
3. Cold (within this file): 6, 7, 8.
4. Lines 6/7/8 do **not** appear in any other file's placed list — no overflow.

For `C:/myapp/src/auth/CLAUDE.md` (budget = 3):
1. Only line 3 was assigned. It gets placed at rank 1.
2. `cold` for this file is empty.

## Verification Checks

- [ ] Output is keyed `files: { "<path>": { placed, cold, promotions, demotions, stats } }`
- [ ] Each file ranks only lines from its `by_file` entry
- [ ] Each file fills only its own `managed_budget`
- [ ] Lines that are cold for one file do **not** appear in another file's `placed`
- [ ] `promotions` for a file only when target ≠ most-recent placement for that line
- [ ] `demotions` for a file when a previously placed line is now cold for that same file
- [ ] No minimum relevance threshold — line 8 (0 events) makes the cut only if budget has remaining room and it ranked into it
- [ ] `stats.budget_used` = `len(placed)`; `stats.budget_available` = `managed_budget`
