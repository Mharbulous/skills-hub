# Test Scenario: Run Output Formatting

## Purpose
Verify that the skill generates the correct run output summary after a cycle completes, with one row per managed file (N-tier) and accurate computed values.

## Input State

After processing 100 commits (abc1234..def5678) on repo "listbot":

- Cursor position: commit 347 of ~1,200
- Discovery returned 3 managed files:

| path | budget | manual_units |
|------|--------|--------------|
| `./CLAUDE.md` | 188 | 12 |
| `./features/spellcheck/CLAUDE.md` | 200 | 0 |
| `~/.claude/CLAUDE.md` | 200 | 0 |

- Per-file results from competitive placement:

| path | placed | cold | promotions in | demotions out |
|------|--------|------|---------------|---------------|
| `./CLAUDE.md` | 142 | 37 | 6 | 2 |
| `./features/spellcheck/CLAUDE.md` | 41 | 0 | 4 | 0 |
| `~/.claude/CLAUDE.md` | 8 | 0 | 1 | 0 |

- Proposed: 4 new lines generated
- Cold storage total (across all files): 283 units

## Expected Output

```
Claude Curator -- listbot

Discovered managed files:  3
Commits analyzed:          100 (abc1234..def5678)
Cursor position:           commit 347 of ~1,200

Per-file results:
  ./CLAUDE.md                                  budget 188  placed 142  cold  37  +6/-2
  ./features/spellcheck/CLAUDE.md              budget 200  placed  41  cold   0  +4/-0
  ~/.claude/CLAUDE.md                          budget 200  placed   8  cold   0  +1/-0

Proposed:           4 new lines generated
Cold storage total: 283 units across all files
```

## Verification Checks

- [ ] One row per managed file in the per-file table
- [ ] Each row shows: path, `budget` (= `200 - manual_units`), `placed`, `cold`, and `+promotions/-demotions`
- [ ] Header includes count of discovered managed files
- [ ] Commit range shown in parentheses
- [ ] Cursor position shows current/total commits
- [ ] No mention of `CLAUDE.local.md` (obsolete concept)
- [ ] No "User global" / "Project local" tier headings (now path-based)
