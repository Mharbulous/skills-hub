# Test Scenario: Discover Managed Files (Phase 0)

## Purpose
Verify that `scripts/discover_managed_files.py` walks a repo tree, returns exactly the `CLAUDE.md` files that contain a `<CURATED>` block, and computes correct `depth` and `manual_units` for each.

## Input State — Fixture Tree

```
fx/
  CLAUDE.md                                  # has <CURATED> block + 2 manual units
  features/
    spellcheck/
      CLAUDE.md                              # has <CURATED> block, no manual content
  docs/
    CLAUDE.md                                # NO <CURATED> block
```

File contents:

`fx/CLAUDE.md`
```markdown
# Root
Some human notes.

<CURATED>
## Conventions
- curated content
</CURATED>

More human notes.
```

`fx/features/spellcheck/CLAUDE.md`
```markdown
# Spellcheck
<CURATED>
- spellcheck-specific
</CURATED>
```

`fx/docs/CLAUDE.md`
```markdown
# Docs only, no curated block
Manual only.
```

## Run

```bash
python scripts/discover_managed_files.py fx --repo fx --db claude-storage.db
```

## Expected Output (JSON)

```json
{
  "managed_files": [
    {
      "path": "<absolute>/fx/CLAUDE.md",
      "repo": "fx",
      "depth": 0,
      "manual_units": 2,
      "managed_budget": 198
    },
    {
      "path": "<absolute>/fx/features/spellcheck/CLAUDE.md",
      "repo": "fx",
      "depth": 2,
      "manual_units": 0,
      "managed_budget": 200
    }
  ]
}
```

## Verification Checks

- [ ] Exactly 2 entries returned (the docs/ file is correctly excluded — no `<CURATED>` tag)
- [ ] `depth` = directory depth below repo root (0 = root, 2 = `features/spellcheck`)
- [ ] `manual_units` counts non-blank, non-heading lines outside the `<CURATED>` block
- [ ] `managed_budget` = `200 - manual_units`, clamped to ≥0
- [ ] After `--db` flag, `managed_files` table contains both rows (and re-running upserts without duplicating)
- [ ] `--include-home` adds `~/.claude/CLAUDE.md` only if it has a `<CURATED>` block; depth = -1
- [ ] Unreadable files emit a warning to stderr but do not abort the walk
