# Create Mode Workflow

Generate handover from conversation for the next session.

## Pre-Creation Analysis (MANDATORY)

### Step 1: Task Separation

Are there conceptually distinct tasks that should be separate handovers?

| Indicator     | Single Handover       | Multiple Handovers             |
| ------------- | --------------------- | ------------------------------ |
| Scope         | One cohesive goal     | Multiple independent goals     |
| Files touched | Overlapping file sets | Disjoint file sets*            |
| Completion    | All-or-nothing        | Can complete one without other |
| Context       | Shared discoveries    | Separate problem domains       |

*Disjoint files suggest separation but do NOT prove independence. Always run Step 2 dependency analysis — tasks with zero file overlap can still have functional dependencies.

### Step 2: Dependency Analysis

For each pair of handovers, check ALL dependency types — not just file overlap:

| Dependency Type | Test | Example |
|-----------------|------|---------|
| **File dependency** | Does B write to files that A also writes? | Schema migration → data backfill |
| **Output dependency** | Does B read/use files that A creates or modifies? | Generate config → deploy using config |
| **Functional dependency** | Does B *run, invoke, or test* something that A changes? | Fix a skill → re-run test using that skill |
| **Semantic dependency** | Does B's success criteria assume A is complete? | Refactor API → update docs referencing API |

**Common trap:** "Disjoint file sets" does NOT mean independent. Task A may modify a tool/skill/config that Task B *executes* without directly reading its source files.

**The dependency test is not "would the output differ?" — it is "does B exercise or follow A?"** If B invokes, runs, or tests an artifact that A modifies, B depends on A.

**When in doubt, chain.** The cost of an unnecessary chain (slightly slower sequential processing) is far lower than the cost of a missed dependency (broken execution order, wasted work). If you find yourself arguing that a functional dependency "doesn't really count," default to chaining.

### Step 3: Number and Letter Assignment

**Dual ordering system:**

| Level   | Order             | Direction   | Rationale              |
| ------- | ----------------- | ----------- | ---------------------- |
| Numbers | LIFO (descending) | 006 → 005   | Higher numbers first   |
| Letters | FIFO (ascending)  | A → B → C   | Chain execution order  |

**Full example:** `006 → 005A → 005B → 005C → 004`

**Assignment rules:**

| Relationship              | Assignment                                    |
| ------------------------- | --------------------------------------------- |
| Independent tasks         | Different numbers, no letters                 |
| Dependency chain          | Same number, letters A → B → C in exec order  |
| Must run before existing  | Use higher number than existing               |
| Must run after chain      | Add next letter to that chain                 |

**Example - creating a dependency chain:**

```
005A_update-schema.md      ← First to execute (no dependencies)
005B_migrate-data.md       ← Depends on 005A
005C_verify-migration.md   ← Depends on 005A AND 005B
```

Processing order: `005A → 005B → 005C`

**Example - inserting before existing work:**

Existing queue has `003_refactor-ui.md`. You realize prep work is needed:

1. Create `004_prep-ui-refactor.md` (higher number, runs first)
2. No need to rename `003_refactor-ui.md`
3. Processing order: `004 → 003`

### Step 4: Planning Superpower Routing

Only applies when the handover describes an **implementation task** (building/modifying code — not research, investigation, or refactoring-only).

| Condition | Action |
| --- | --- |
| Low complexity (1-2 files, trivial logic) | No routing needed. Proceed normally. |
| Medium+ complexity, **no pending plan** | Next Step MUST include: `REQUIRED SKILL: superpowers:writing-plans` |
| Medium+ complexity, **pending plan exists** | Next Step MUST include: `REQUIRED SKILL: superpowers:executing-plans` |

**Complexity threshold:** 3+ files modified, multiple components involved, or non-trivial logic changes.

**Plan detection:**
1. Search `docs/plans/` in the target repo for a plan matching this task
2. A matching plan must have BOTH:
   - The writing-plans signature: `> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans`
   - YAML frontmatter with `status: pending` (plans with `status: executed` or no frontmatter are ignored)

**Next Step format when routing applies:**

```markdown
## Next Step

REQUIRED SKILL: superpowers:{writing-plans|executing-plans}

{Specific immediate action}
```

## Handover File Format

**YAML frontmatter is required:**

```markdown
---
write_targets:
  - src/AutoTimer/ui/__init__.py
  - src/AutoTimer/ui/dialogs.py
read_only_targets:
  - src/AutoTimer/config/settings.py
  - docs/ui-architecture.md
blocked_by:
  - 004_other-wip-task.md
---

# Handover: Task Summary

## Task

{1-2 sentence description}

## Current State

{Done vs remaining}

## Red Herrings

- path/to/file.py - {why irrelevant}

## Failed Approaches

1. {approach} - {why failed}

## Key Discoveries

- {non-obvious insight}

## Useful URLs

- [description](url)

## Next Step

{Specific immediate action}
```

### Frontmatter Rules

| Field              | Required | Format                    | Notes                                              |
| ------------------ | -------- | ------------------------- | -------------------------------------------------- |
| `write_targets`    | No*      | YAML list or `[]`         | Files to modify or create (exclusive lock)         |
| `read_only_targets`| No*      | YAML list or `[]`         | Files needed for context only (shared lock)        |
| `blocked_by`       | No       | YAML list of filenames    | Omit entirely if no blockers                       |

*At least one of `write_targets` or `read_only_targets` should be present.

**Important:**
- Letter suffix dependencies are IMPLICIT - do NOT list them in `blocked_by`
  - `005B` automatically depends on `005A`
  - `005C` automatically depends on `005A` AND `005B`
- Only use `blocked_by` for cross-number dependencies:
  - `004` depends on `005` → `blocked_by: [005_task.md]`
  - `004` depends on `005B` → `blocked_by: [005B_task.md]`

### When to Use `blocked_by` vs Letter Suffixes

| Relationship              | Encoding                          |
| ------------------------- | --------------------------------- |
| 005B depends on 005A      | Letter suffix (implicit)          |
| 004 depends on 005        | `blocked_by: [005_task.md]`       |
| 004 depends on 005B       | `blocked_by: [005B_task.md]`      |

## Context Gathering

Extract from conversation:

- **Write Targets**: Files that will be modified or created (goes in `write_targets`)
- **Read-Only Targets**: Files needed for context but not changed (goes in `read_only_targets`)
- **Red Herrings**: Files examined but irrelevant (explain why)
- **Failed Approaches**: Errors encountered, approaches abandoned (with reasons)
- **Key Discoveries**: Non-obvious insights that cannot be derived by reading the target files (see Content Boundary below)
- **Useful URLs**: Web searches, documentation links
- **Current State**: What's done vs what remains
- **Next Step**: Immediate action to take

### Cumulative Failure Tracking

Check if first user message contains "Failed Approaches:". If found, copy that section verbatim and prepend to new Failed Approaches.

## Content Boundary: What vs How

Handovers describe **what** to do and **why**, never **how**. The executing agent can read the files and determine implementation details itself.

**Include:**
- What needs to change and why (task, current state, key discoveries)
- Non-obvious insights the next agent would waste time re-discovering (e.g., "the route is gated by `import.meta.env.DEV`" — not visible without reading multiple files)
- Failed approaches and why they failed (saves re-treading dead ends)

**Never include:**
- Code snippets to copy-paste
- Line numbers (files change between sessions)
- Step-by-step implementation instructions
- Object shapes, function signatures, or API patterns readable from the target files
- Multi-step numbered "how to" lists in Next Step

**Next Step** is a single sentence describing the immediate action, not an implementation guide.

| Temptation | Why it's wrong | Instead |
|---|---|---|
| "Include the code so they can paste it" | Executing agent can read files and write better code with full context | Describe what to add, not the code itself |
| "Add line numbers so they find it fast" | Lines shift between sessions; Grep is instant | Name the function/variable/section |
| "List all 4 implementation steps" | That's implementation planning, not handover | Single Next Step; agent plans its own work |
| "Include the object shape from the file" | Agent will read the file anyway | Name the property/function; don't reproduce its structure |
| "Be thorough for the fresh context window" | Thorough = complete context, not prescriptive instructions | Focus on why and what, never how |
| "Mention the meta/config pattern so they match it" | Patterns are visible in the file; describing them is implementation detail | Just say "follow existing pattern in the file" |

**Litmus test — apply to EACH Key Discovery before writing it:**

1. Would the executing agent discover this by reading the write_targets? → **Delete it.** It's file content.
2. Does the discovery contain an object shape, signature, or pattern from a target file? → **Strip the structure, keep only the insight.** Example: "availableDemos is hardcoded, not driven by route meta" is a discovery. Adding `{ title, description, route, tags, status }` is file content — delete it.
3. Does it describe a cross-file relationship or non-obvious gating condition? → **Keep it.** This is what Key Discoveries are for.

## Exclusions

- Branch information
- Verbose explanations
- Details obvious to Sonnet 4.5
- Implementation instructions (code, line numbers, step-by-step how-to)

## File Output

**Folder:** `handovers/queued/` (relative to the repository root)

Create the folder structure if it doesn't exist: `handovers/queued/`, `handovers/WIP/`, `handovers/completed/`

Before running helper scripts, set `SKILL_DIR` to the materialized handover
skill folder from the full install or Skills-hub per-skill tarball.

**Single handover:**

1. Run script to determine next handover number:
   ```bash
   python "$SKILL_DIR/scripts/get_next_handover_number.py" {main_repo_path}
   ```
   The script scans ALL handover folders (`queued/`, `WIP/`, `completed/`) for highest numeric prefix (ignoring letters) and returns next number as zero-padded string (e.g., "039").
2. Generate slug (lowercase, hyphens, max ~40 chars)
3. Write to `{main_repo_root}/handovers/queued/{NNN}_{slug}.md`

**Multiple with dependencies (same-number chain):**

1. Run script to get next number (same command as above)
2. Use that number for the entire chain
3. Assign letters A, B, C... in execution order (first to execute = A)
4. Write all files with same number, different letters
5. Report all paths with execution order

**Inserting relative to existing handovers:**

| Goal                        | Action                           | Example                              |
| --------------------------- | -------------------------------- | ------------------------------------ |
| Run BEFORE existing chain   | Create higher number             | Add `006_prep.md` before `005A`      |
| Run AFTER existing chain    | Add next letter                  | Add `005D_followup.md` after `005C`  |
| Run BETWEEN chain steps     | Not supported (requires rename)  | Rare case, avoid if possible         |

## Behavior by Argument

| Argument  | File  | Chat     |
| --------- | ----- | -------- |
| (default) | Write | Output   |
| `file`    | Write | Suppress |
| `chat`    | Skip  | Output   |
