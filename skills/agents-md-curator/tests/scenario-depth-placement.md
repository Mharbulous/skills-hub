# Test Scenario: Depth Placement (Phase 5)

## Purpose
Verify that `scripts/depth_placement.py` correctly routes each line to the deepest managed `CLAUDE.md` whose directory covers the longest common prefix of its observed `relevant_paths`. Cross-repo lines route to the home-global file.

## Input State

`managed_files` table populated by a prior run of `discover_managed_files.py`:

| path | repo | depth |
|------|------|-------|
| `C:/myapp/CLAUDE.md` | myapp | 0 |
| `C:/myapp/features/spellcheck/CLAUDE.md` | myapp | 2 |
| `C:/Users/Brahm/.claude/CLAUDE.md` | (null) | -1 |

Permanent lines:

| line_id | content |
|---------|---------|
| 1 | "Use ruff for linting" |
| 2 | "Spellcheck dictionaries live next to the engine module" |
| 3 | "Always check authStore.isInitialized before isAuthenticated" |
| 4 | "Never force-push to main" |
| 5 | "Imported but no relevance evidence yet" |

Observed `relevance_events`:

| line_id | repo | relevant_paths |
|---------|------|----------------|
| 1 | myapp | `src/main.py`, `docs/setup.md` |
| 2 | myapp | `features/spellcheck/engine.py`, `features/spellcheck/dictionaries.py` |
| 3 | myapp | `src/auth/store.ts` |
| 4 | myapp | `.github/workflows/ci.yml` |
| 4 | api-service | `.github/workflows/deploy.yml` |
| 5 | — | (none) |

## Expected Behavior

| line_id | longest common prefix | repo(s) | target |
|---------|----------------------|---------|--------|
| 1 | `""` (paths fork at root) | myapp | `C:/myapp/CLAUDE.md` (depth 0 — only candidate that covers `""`) |
| 2 | `features/spellcheck` | myapp | `C:/myapp/features/spellcheck/CLAUDE.md` (depth 2 wins over depth 0) |
| 3 | `src/auth` | myapp | `C:/myapp/CLAUDE.md` (no managed file under `src/auth` exists; deepest covering is the repo root) |
| 4 | `.github/workflows` (per repo) | myapp + api-service → ≥2 | `C:/Users/Brahm/.claude/CLAUDE.md` (cross-repo wins regardless of prefix) |
| 5 | n/a | (none) | unplaced (`reason: "no observed relevance events"`) |

## Verification Checks

- [ ] Line 1 (whole-repo evidence) → repo-root managed file
- [ ] Line 2 (sub-tree-only evidence) → deepest covering managed file
- [ ] Line 3 (single-subfolder evidence, no managed file at that depth) → repo-root managed file (deepest covering)
- [ ] Line 4 (≥2 repos) → home-global managed file
- [ ] Line 5 (no events) → appears in `unplaced` with the right reason
- [ ] `by_file` map keyed by managed-file path; values are lists of line_ids
- [ ] `promotions` only emitted when target differs from most-recent placement
- [ ] No line is assigned to a managed file whose directory is not an ancestor of its path prefix (tightest-fit honored — never overflows up to home unless cross-repo, never crosses sibling subtrees)
