---
name: plan-declutter
description: "Organize, track, and review planning files. Standardizes folder structure to canonical categories, generates declutter inventory tables, and reviews individual files against the codebase. Use on any project with a planning/ folder."
---

# /plan-declutter

Organize, track, and review planning files across any project.

**Target file**: `$ARGUMENTS`

---

## Canonical Planning Folder Structure

| # | Name | Description |
|---|------|-------------|
| 0 | Ideas | Rudimentary plans lacking sufficient detail |
| 1 | Design | Design documents with detailed specifications |
| 2 | ADR | Architecture Decision Records |
| 3 | Plan | Implementation plans ready for execution |
| 4 | Staging | Prototypes, test scripts, experimental files |
| 5 | Executed | Plans executed (with as-built notes) |
| 6 | Abandoned | Abandoned plans no longer relevant |
| 7 | Consumed | Designs/plans consumed by downstream processes |

**Date format**: `YYYY-MM-DD` (ISO). Recognize both `YY-MM-DD-` and `YYYY-MM-DD-` when parsing existing files.

---

## Tasks

One task per invocation. **CRITICAL**: Never perform more than one task in a single chat.

- **Task S**: Standardize folder structure to canonical categories
- **Task A**: Create or update `plan-declutter-table.md`
- **Task B**: Review a single planning file

## Auto-Detection (empty `$ARGUMENTS`)

Stop at first match:

1. No `planning/` folder → "No planning/ folder found in this project."
2. Subfolders don't match canonical structure → Task S
3. No table dated today (`planning/YYYY-MM-DD-plan-declutter-table.md`) → Task A
4. Table has files needing review → Task B on the first one
5. Otherwise → "All clear. Planning files are organized and reviewed."

**Explicit overrides:**
- `"standardize"` → Task S
- `"table"` → Task A
- file path → Task B on that file

---

## Task S: Standardize

Scan `planning/` and map each subfolder to canonical structure.

### Matching Heuristics (priority order)

For each subfolder, extract number prefix and name (e.g., `2. ADRs` → number=2, name="ADRs"). Then:

1. Exact name match (case-insensitive)
2. Plural strip: remove trailing 's' and recheck (ADRs → ADR)
3. Synonym lookup: `references/synonyms.md` in the materialized skill directory
4. Name-over-number: name matches canonical but number differs → use canonical number
5. No match → ask user

### Steps

1. List all `planning/` subfolders
2. For each, apply heuristics to determine target canonical folder
3. Present the full mapping table:

   ```
   | Current Folder | Target Folder | Match Type | Files |
   |---------------|---------------|------------|-------|
   | 0. PRDs | 0. Ideas | synonym | 3 |
   | 2. ADRs | 2. ADR | plural strip | 5 |
   | 3. Executed | 5. Executed | name-over-number | 2 |
   ```

4. Wait for user confirmation (skip in YOLO mode)
5. If multiple sources map to same target, list all files that will merge and note any filename collisions
6. Execute with `git mv` (quoted paths, preserves git history)
7. Create missing canonical folders
8. Work backwards from highest target number to avoid collisions

**Collision handling**: append disambiguating suffix before extension (`plan.md` → `plan-from-folder-name.md`), present to user before executing.

---

## Task A: Create or Update Plan-Declutter Table

**Model**: Haiku subagent (mechanical task).

**Execute if ANY of the following are true:**
- No `planning/YYYY-MM-DD-plan-declutter-table.md` exists (either date format)
- Existing table is dated in the past
- `$ARGUMENTS` equals "table" (case-insensitive)

**How**: Read `references/table-format.md` from the materialized skill directory, spawn Haiku subagent:
- `model`: "haiku"
- `prompt`: content from `references/table-format.md` (inside the code fence)

**After subagent returns**:
1. Verify `TABLE_CREATED: YES` and file path
2. Read file to confirm correctness
3. `git add -A && git commit -m "planning: Update plan-declutter-table for YYYY-MM-DD" && git push`
4. Report outcome; if `TABLE_CREATED: NO`, report failure without committing

**STOP** after Task A.

---

## Task B: Review a Single Planning File

**Model**: Inline (primary model — requires judgment).

**Execute when**: current table exists (dated today) AND `$ARGUMENTS` is empty or a file path.

### Steps

1. **Select file**: from `$ARGUMENTS` or first file in "Files Needing Review" table section

2. **Analyze thoroughly**:
   - Read the entire file content
   - Identify all action items, steps, or tasks mentioned
   - Check git history for modification dates and related commits
   - Look for implementation evidence:
     - PR references (check if merged)
     - Code file references (check if they exist)
     - Status markers ("done", "implemented", "cancelled", etc.)
     - Feature descriptions (verify against codebase)

3. **Update file contents**:
   - Add checkmarks to completed items
   - ~~Strikethrough~~ cancelled or superseded items
   - Add status notes where helpful

4. **Determine category**:

   | Category | Criteria |
   |----------|----------|
   | Ideas | Lacks detail, needs discussion |
   | Design | Detailed design specifications |
   | ADR | Architecture decision with context, decision, and consequences |
   | Plan | Clear implementation steps, ready to build |
   | Staging | Experimental code, prototypes, test scripts |
   | Executed | Plan has been implemented (with as-built notes) |
   | Abandoned | Superseded, cancelled, or no longer relevant |
   | Consumed | Design/plan consumed by a downstream process |

5. **Rename**: `YYYY-MM-DD-original-name.md` (replace existing date prefix if present); move folder if category changed; use `git mv`
6. **Update table**: remove from "Files Needing Review", update summary counts
7. `git add -A && git commit -m "planning: Review [filename] - [brief status summary]" && git push`
8. **STOP** — Do NOT review another file in this session

---

## YOLO Mode (Autonomous Workflow)

- Skip confirmations; make judgment calls; complete exactly one task per run

| File state | Action |
|------------|--------|
| Unchecked items exist in codebase | Add checkmarks |
| Items clearly cancelled/superseded | Add ~~strikethrough~~ |
| Shows significant progress since last review | Add status notes |
| Appears fully complete | Move to "5. Executed", flag in commit |
| Clearly abandoned (60+ days, no activity) | Move to "6. Abandoned" |
| Needs human judgment | Leave in current folder, add note to table |

**Constraints:**
- **ONE task per run**: S, A, or B — pick one
- **Never move to Consumed**: only deliberate downstream consumption triggers this
- **20-minute timeout**: stop if exceeded
- **When uncertain**: leave file in current category, add note to table
- **Preserve meaning**: updates should clarify status, not change the plan's intent

---

## Git Operations (Orchestrator Responsibility)

Orchestrator handles ALL git. Subagents must NOT run git commands.

`git add -A && git commit -m "planning: [description]" && git push`

**CRITICAL**: Do NOT exit without pushing changes. Any local commits that are not pushed will be lost.

---

## Error Handling

| Condition | Response |
|-----------|----------|
| No `planning/` folder | "No planning/ folder found in this project." Exit without changes. |
| No files need review | "All planning files have current review dates. Nothing to review." Exit without commits. |
| `$ARGUMENTS` file not found | "File not found: `$ARGUMENTS`" Exit without changes. |
| Table exists, no files need review | "Plan-declutter table is current and all files have been reviewed recently." Exit without commits. |
| Review is ambiguous | YOLO: add note to table; Interactive: ask user |

---

## Usage Examples

```
/plan-declutter              # Auto-detect
/plan-declutter standardize  # Force Task S
/plan-declutter table        # Force Task A
/plan-declutter planning/3. Plan/feature-plan.md  # Task B on specific file
```
