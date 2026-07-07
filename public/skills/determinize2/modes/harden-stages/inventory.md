# Stage 1: File Inventory

## Goal

Build a complete inventory of the skill being hardened, so that Stage 2 has
a full picture of what exists before classifying any of it.

## Prerequisites

- The path to the skill directory being hardened (the skill's actual
  location — do not assume a fixed root; resolve relative to wherever the
  skill actually lives).

## Steps

1. List every file in the skill directory (recursively) using Glob.
2. Read each file and count its lines.
3. Emit an inventory table:

   ```
   Inventory: <skill-name>
   | File | Lines | Purpose |
   |------|-------|---------|
   | SKILL.md | 216 | Main skill document |
   | scripts/foo.py | 45 | Helper script |
   | ... | ... | ... |
   | **Total** | **XXX** | |
   ```

4. List every heading in SKILL.md along with its line range, e.g.:

   ```
   ## Step 1: Schema Discovery and Scoring   (lines 10-28)
   ## Step 2: Type Validation                (lines 30-55)
   ...
   ```

## Output artifacts

- The inventory table (in-conversation; not written to disk).
- The SKILL.md section/line-range list (in-conversation; not written to
  disk).

## Gate

Before proceeding: confirm every file in the skill directory is counted,
the inventory table is complete, and the SKILL.md sections are listed with
line ranges.

**Read `classify-and-score.md` next.**
