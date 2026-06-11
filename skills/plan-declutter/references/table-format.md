# Task A: Haiku Subagent Prompt

Copy the prompt below verbatim when spawning the Haiku subagent for Task A.

---

```
Create or update the plan-declutter-table.md file - a comprehensive inventory of ALL planning files.

## Canonical Planning Folder Structure

| # | Folder | Description |
|---|--------|-------------|
| 0 | 0. Ideas | Rudimentary plans lacking sufficient detail |
| 1 | 1. Design | Design documents with detailed specifications |
| 2 | 2. ADR | Architecture Decision Records |
| 3 | 3. Plan | Implementation plans ready for execution |
| 4 | 4. Staging | Prototypes, test scripts, and experimental files |
| 5 | 5. Executed | Plans that have been executed |
| 6 | 6. Abandoned | Abandoned plans that are no longer relevant |
| 7 | 7. Consumed | Designs/plans consumed by downstream processes |

## Date Format

Use YYYY-MM-DD throughout (ISO 8601). Recognize both YY-MM-DD- and YYYY-MM-DD- prefixes when parsing existing filenames.

## Your Task

1. **Archive old table (if exists)**
   - If an old planning/YYYY-MM-DD-plan-declutter-table.md or planning/YY-MM-DD-plan-declutter-table.md exists with a past date:
     - Create folder deprecated/plans/ if it doesn't exist
     - Copy the old file to deprecated/plans/ (preserve original filename)
     - Delete the old file from planning/

2. **Scan ALL planning folders**
   - Scan all .md files in ALL category folders: 0. Ideas, 1. Design, 2. ADR, 3. Plan, 4. Staging, 5. Executed, 6. Abandoned, 7. Consumed
   - Also scan: planning/archived/, planning/deprecated/, planning/research/
   - **EXCLUDE**: The plan-declutter-table.md file itself

3. **Analyze each file for review status**
   Determine if each file needs review based on these rules:

   **NEEDS REVIEW** (Priority Order):
   - NO date prefix (e.g., `feature-plan.md`) -> "No date prefix - needs initial review"
   - In "3. Plan" folder AND date is NOT today -> "Plan file with stale date"
   - Date prefix is 30+ days old -> "Review date over 30 days old"

   **OK** (no review needed):
   - Has date prefix from today
   - Has date prefix within last 30 days AND not in "3. Plan"
   - In "7. Consumed" folder (archived)

4. **Create new table file**
   - Create planning/YYYY-MM-DD-plan-declutter-table.md with today's date
   - Calculate workflow status counts:
     - REMAINING_WORK = total files in "Files Needing Review" section
     - HUMAN_REVIEW_ONLY = count of files with "Human Review" as reason (legacy files, ambiguous cases)
     - AUTO_PROCESSABLE = REMAINING_WORK - HUMAN_REVIEW_ONLY
     - STATUS = "COMPLETE" if REMAINING_WORK=0, "BLOCKED" if AUTO_PROCESSABLE=0, else "ACTIVE"
   - Include the machine-readable header (see format below)
   - Use "Human Review" as Review Reason for files requiring human judgment

5. **Final Report (DO NOT commit or push - the orchestrator handles git)**
   Your final message MUST include:
   - TABLE_CREATED: YES or NO
   - Table file path (if created)
   - Total files inventoried
   - Files needing review count
   - Any errors encountered

IMPORTANT: Your job ends after creating the table file. Do NOT run any git commands.

## Table File Format

Use this exact structure:

# Plan Declutter Table
Generated: YYYY-MM-DD

<!-- WORKFLOW STATUS (machine-readable - do not modify format) -->
<!-- REMAINING_WORK: X -->
<!-- HUMAN_REVIEW_ONLY: Y -->
<!-- AUTO_PROCESSABLE: Z -->
<!-- STATUS: [ACTIVE|BLOCKED|COMPLETE] - [description] -->

Where:
- REMAINING_WORK = total files needing review
- HUMAN_REVIEW_ONLY = files that require human judgment (cannot be auto-processed)
- AUTO_PROCESSABLE = REMAINING_WORK - HUMAN_REVIEW_ONLY (files workflow can process)
- STATUS: ACTIVE (work available), BLOCKED (only human review files remain), COMPLETE (all done)

## Files Needing Review

| File | Current Location | Review Reason | Last Reviewed |
|------|------------------|---------------|---------------|
| feature-plan.md | planning/3. Plan/ | No date prefix | Never |
| 2025-11-01-old-task.md | planning/3. Plan/ | Plan file with stale date | 2025-11-01 |
| 2025-10-15-idea.md | planning/0. Ideas/ | Review date over 30 days old | 2025-10-15 |

NOTE: Use "Human Review" as Review Reason for files that require human judgment.

## All Planning Files Inventory

### 0. Ideas
| File | Last Reviewed | Status |
|------|---------------|--------|
| 2025-12-05-brainstorm.md | 2025-12-05 | OK |

### 1. Design
| File | Last Reviewed | Status |
|------|---------------|--------|
| 2025-12-08-feature-design.md | 2025-12-08 | OK |

[...repeat for each category folder...]

## Summary
- Total files: X
- Files needing review: X
- Files OK: X
- By category:
  - 0. Ideas: X files (Y need review)
  - 1. Design: X files (Y need review)
  - 2. ADR: X files (Y need review)
  - 3. Plan: X files (Y need review)
  - 4. Staging: X files (Y need review)
  - 5. Executed: X files (Y need review)
  - 6. Abandoned: X files (Y need review)
  - 7. Consumed: X files (Y need review)
  - Other folders: X files (Y need review)
```
