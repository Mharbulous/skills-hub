# Repair Mode Workflow

Fix malformed handover files so they can be processed.

## Triggers

Repair mode is entered from Process mode when encountering a handover with:

- Missing YAML frontmatter (file starts with `#` instead of `---`)
- Both `write_targets` and `read_only_targets` missing in frontmatter
- Legacy `key_files` field (needs migration to new format)
- Malformed YAML syntax

## Non-Repairable Errors

**Stop with error if:**

- Missing `## Task` section - fundamental content missing, cannot infer

Announce: "Handover {filename} is missing ## Task section. Cannot repair - manual fix required."

## Repair Workflow

### Step 1: Announce

```
Handover {filename} is malformed. Entering Repair mode.
```

### Step 2: Analyze Handover Content

Read the handover file and determine:

1. **What files will this task MODIFY or CREATE?** → `write_targets`
   - Look at `## Task` section for files being changed
   - Look at `## Next Step` for specific file actions (edit, create, update)
   - Files with verbs like "modify", "update", "create", "add", "fix"

2. **What files are needed for CONTEXT only?** → `read_only_targets`
   - Look at `## Task` section for reference files
   - Look at `## Current State` for files examined but not changed
   - Files with verbs like "reference", "check", "based on", "following pattern in"
   - Look at `## Key Files` section if present (old format - treat as `write_targets`)

3. **Compile both lists** from discovered files

### Step 3: Analyze Queue for Dependencies

Read other handovers in `.handovers/queued/` to identify blockers:

1. **Check for write target overlaps:**
   - If another queued handover has overlapping `write_targets`, this indicates serialization needed
   - The one with the higher number should run first (per LIFO ordering)

2. **Check for output/input relationships:**
   - If this handover uses outputs from another, add that as a blocker

3. **Compile `blocked_by` list** from identified dependencies

### Step 4: Add WIP Blockers

**Add ALL files in `.handovers/WIP/` as blockers:**

- Don't analyze WIP contents (transient, wasted effort)
- Simply add every filename in `.handovers/WIP/` to `blocked_by`

**Why:** WIP files represent unknown concurrent work. Blocking on them prevents conflicts.

### Step 5: Generate Frontmatter

Create YAML frontmatter with:

```yaml
---
write_targets:
  - path/to/file-to-modify.py
  - path/to/new-file.py
read_only_targets:
  - path/to/reference-config.py
  - docs/architecture.md
blocked_by:
  - 007_wip-task.md
  - 005_other-dependency.md
---
```

**Rules:**
- At least one of `write_targets` or `read_only_targets` should be present
- Use empty list `[]` if none identified for a category
- `blocked_by` is optional, omit entirely if no blockers identified

### Step 6: Write Repaired File

1. Prepend frontmatter to existing content
2. Remove old-format sections if present:
   - Remove `BLOCKED BY:` line from markdown body
   - Remove `## Key Files` section from body (data moved to frontmatter)
3. Write back to `.handovers/queued/` (same filename)

### Step 7: Stop Session

Announce:

```
Repair complete. Handover {filename} ready for next session.
```

**Do NOT continue processing.** The session ends after repair.

## Why Stop After Repair?

1. **Blockers may have changed:** Repair adds WIP files as blockers, so the repaired file is likely blocked now
2. **Clean session boundary:** Repair is a complete unit of work
3. **Avoids confusion:** User knows exactly what happened this session

## Migration from Old Formats

### Legacy `key_files` Format

When encountering a handover with `key_files` in YAML frontmatter:

**Detection:** YAML frontmatter contains `key_files:` but not `write_targets:` or `read_only_targets:`

**Migration rule:** Treat all `key_files` as `write_targets` (conservative default)

**Example:**

```yaml
# Before (legacy)
---
key_files:
  - src/ui/dialogs.py
  - src/config/settings.py
---
```

```yaml
# After (migrated)
---
write_targets:
  - src/ui/dialogs.py
  - src/config/settings.py
read_only_targets: []
---
```

**Announce:** "Migrated legacy key_files to write_targets"

### No YAML Frontmatter

When encountering an old-format file (no YAML frontmatter):

**Detection:** File starts with `# Handover:` instead of `---`

**Extract existing data:**

| Old Format                  | New Format                      |
| --------------------------- | ------------------------------- |
| `BLOCKED BY: filename.md`   | `blocked_by: [filename.md]`     |
| `## Key Files` section      | `write_targets: [...]`          |

**Example old format:**

```markdown
# Handover: Update UI Components

BLOCKED BY: 005_refactor-base.md

## Task

Update UI components to use new base classes.

## Key Files

- src/AutoTimer/ui/dialogs.py
- src/AutoTimer/ui/settings.py

## Next Step

...
```

**Converted to:**

```markdown
---
write_targets:
  - src/AutoTimer/ui/dialogs.py
  - src/AutoTimer/ui/settings.py
read_only_targets: []
blocked_by:
  - 005_refactor-base.md
---

# Handover: Update UI Components

## Task

Update UI components to use new base classes.

## Next Step

...
```

## Common Rationalizations (All Wrong)

| Excuse                                    | Reality                                          |
| ----------------------------------------- | ------------------------------------------------ |
| "I can infer the key files later"         | NO. Repair now, don't defer.                     |
| "The WIP files might not conflict"        | NO. Block on them anyway. Safety first.          |
| "I'll just process it without frontmatter"| NO. That breaks overlap detection for others.    |
| "I can continue after repair"             | NO. Session ends. Clean boundaries.              |
| "This file is almost valid"               | NO. Malformed is malformed. Full repair.         |
