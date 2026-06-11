# Process Mode Workflow

Resume from latest incomplete handover. **Process ONE handover per session.**

**⚡ FAST PATH: If you were directed here from SKILL.md without running the deterministic selector first, you're doing it wrong. Go back and run the selector script immediately.**

## Quick Start (No Arguments)

When `/handover` is invoked without arguments in an empty/minimal conversation:

1. **Run deterministic selector immediately** (don't read this entire file first):
   ```bash
   cd ~/.claude/skills/handover && python scripts/handover_selector.py --claim [repo_path]
   ```

2. **Handle JSON response** based on `status` field (see Deterministic Selection section below)

3. **Consult this file** only for edge cases, manual fallback, or understanding specific statuses

## Folder Structure

All paths are relative to the repository root at `.handovers/`:

| Folder                        | Contains                           |
| ----------------------------- | ---------------------------------- |
| `.handovers/queued/`    | Handovers waiting to be processed  |
| `.handovers/WIP/`       | Handover currently being worked on |
| `.handovers/completed/` | Finished handovers                 |

Create these folders if they don't exist.

## The Iron Rule

```
STOP after finding unblocked work. Do NOT continue checking other files.
```

Process mode finds the first unblocked handover and begins work. You do not check additional handovers after finding work to do.

## The WIP Rule

```
NEVER touch files in .handovers/WIP/ when .handovers/queued/ has work.
```

Files in `.handovers/WIP/` are being actively worked on by another session. **Assume they are in progress.** Do not read them, do not "check their status," do not rationalize that they might be abandoned.

**The ONLY exception**: When `.handovers/queued/` is completely empty before you moved any files to WIP/ (see Edge Cases).

## Sort Order

**Dual ordering system:**

| Level   | Order             | Direction   | Rationale              |
| ------- | ----------------- | ----------- | ---------------------- |
| Numbers | LIFO (descending) | 006 → 005   | Higher numbers first   |
| Letters | FIFO (ascending)  | A → B → C   | Chain execution order  |

**Full example:** `006 → 005A → 005B → 005C → 004`

**Implementation:** Sort files by numeric prefix descending, then by letter suffix ascending.

## Workflow

### Deterministic Selection

Before manually checking files, invoke the deterministic selector with `--claim`:

```bash
cd ~/.claude/skills/handover && python scripts/handover_selector.py --claim [repo_path]
```

The `--claim` flag atomically moves the selected file to WIP/ during selection, eliminating the LLM round-trip between selection and claim.

The script outputs JSON with one of these statuses:

| Status | Action |
| --- | --- |
| `ready` | File already moved to WIP (when `--claim` used). Begin work immediately. |
| `repair` | Read `reference/repair-mode.md` for `file` |
| `conflict` | Top-priority file conflicts with WIP. **Ask user** (see Handling Conflicts below). |
| `all_blocked` | Inform user: "All queued handovers blocked by dependencies" |
| `wip_only` | Ask user about WIP files (see Edge Cases) |
| `empty` | Inform user: "No handovers in queue" |

**Example output (with `--claim`):**

```json
{
  "status": "ready",
  "file": ".handovers/queued/005_task.md",
  "claimed": true,
  "claimed_path": ".handovers/WIP/005_task.md",
  "skip_reasons": {
    "006B_chain.md": "waiting for 006A"
  }
}
```

**Example conflict output:**

```json
{
  "status": "conflict",
  "file": ".handovers/queued/170F_user-invitation.md",
  "conflict_with": "170E_court-form-auto-population.md",
  "skip_reasons": {}
}
```

Without `--claim`, behavior is unchanged (file is not moved, LLM must move it manually).

The `skip_reasons` field shows why higher-priority handovers were skipped (letter dependency, blocked_by).

### Handling Conflicts

When status is `conflict`, the top-priority handover cannot run because `conflict_with` (a WIP file) touches the same source files. **Do not silently skip to a lower-priority handover.** Present the situation to the user:

```
170F_user-invitation.md cannot run — it conflicts with 170E_court-form-auto-population.md (currently in WIP).

What would you like to do?
1. Wait — 170E is actively being worked on in another session. End this session.
2. Investigate — Check whether 170E was completed but accidentally left in WIP (not archived to completed/).
3. Skip 170F — Process the next handover in priority order instead.
```

**After user chooses:**

| Choice | Action |
| --- | --- |
| Wait | Inform user, end session. |
| Investigate | Read the WIP file. If it looks complete (all tasks done), move it to `completed/` and re-run selector. |
| Skip | Re-run selector with `--exclude=170F_user-invitation.md` to get the next eligible handover. |

**Re-running with exclude:**

```bash
cd ~/.claude/skills/handover && python scripts/handover_selector.py --claim --exclude=170F_user-invitation.md [repo_path]
```

### Manual Workflow (Fallback)

If the script is unavailable, follow this manual process:

1. **Scan `.handovers/queued/`** for files, sorted by dual order

   **Chain Detection (optional suggestion):**
   - Group files by numeric prefix
   - If any group has 2+ files with letter suffixes (e.g., 005D, 005E, 005F):
     - Announce: "Found chain {NNN}{A}→{NNN}{B}→{NNN}{C}. Run `/handover chain` to process all in series, or continue with single handover."
   - Continue with normal single-handover processing

2. **If `.handovers/queued/` is empty**: See "Empty Queue with WIP Files" in Edge Cases
3. **For each file (in sorted order):**

   a. **Parse YAML frontmatter**
      - If missing or malformed → Trigger Repair mode, stop session
      - If both `write_targets` and `read_only_targets` missing → Trigger Repair mode, stop session
      - If legacy `key_files` found → Trigger Repair mode for migration

   b. **Check letter-suffix dependency**
      - If file is `NNNB`, check if `NNNA` exists in `.handovers/completed/`
      - If file is `NNNC`, check if both `NNNA` and `NNNB` exist in `.handovers/completed/`
      - If not satisfied → "Skipping 005B - waiting for 005A to complete", continue to next

   c. **Check `blocked_by` field**
      - For each blocker, check if it exists in `.handovers/completed/`
      - If any not in completed → "Skipping 004 - blocked by 005B_task.md", continue to next

   d. **Check write target overlap with WIP**
      - Extract `write_targets` and `read_only_targets` from candidate
      - Compare against WIP files (see "Write Target Overlap Detection" section)
      - If conflict → **STOP and ask user** (see "Handling Conflicts" in Deterministic Selection section)

   e. **Move to `.handovers/WIP/`**, announce "Resuming handover: .handovers/WIP/{filename}", **STOP** and begin work

## Letter-Suffix Dependencies & Overlap Detection

The selector script handles both letter-suffix dependency checking and write-target overlap detection automatically. For manual fallback only:

- **Letter suffixes**: `005B` depends on `005A` being in `completed/`. Use glob `completed/005A_*.md`.
- **Overlap rule**: Conflict if any file appears in EITHER handover's `write_targets`. Read-only vs read-only is OK.
- **Repair triggers**: Missing frontmatter, missing both target fields, legacy `key_files`, malformed YAML → read `reference/repair-mode.md`.

## Parallel Session Safety

**Critical**: Move file to `.handovers/WIP/` BEFORE reading handover details or starting work.

This prevents a second parallel session from picking up the same handover:

- Session A sees file in `.handovers/queued/`, moves to WIP, starts work
- Session B sees queued is empty (or file is gone), checks next file or reports nothing to do

```bash
# Atomic move command
mv .handovers/queued/079_task-name.md .handovers/WIP/079_task-name.md
```

## Edge Cases

| Condition (at session start)                              | Action                                                          |
| --------------------------------------------------------- | --------------------------------------------------------------- |
| `.handovers/queued/` empty, `WIP/` empty            | Inform: "No handovers in queue"                                 |
| `.handovers/queued/` empty, `WIP/` has files        | **ASK USER** (see below)                                        |
| `.handovers/queued/` has files, `WIP/` has files    | Process queued normally. WIP conflict → surface to user (see Handling Conflicts). |
| All queued handovers blocked                              | Inform: "All queued handovers are blocked by dependencies."     |
| Top-priority file conflicts with WIP                      | **Ask user** (see Handling Conflicts in Deterministic Selection section). |

### Empty Queue with WIP Files

When `.handovers/queued/` is empty but `.handovers/WIP/` has files, **you must ask the user**:

```
The queue is empty, but .handovers/WIP/ contains: {list files}

These may be:
- Actively worked on by another session (do not touch)
- Abandoned from a crashed/ended session (safe to resume)

Should I pick up one of these WIP files, or is another session working on them?
```

**Only proceed with a WIP file if the user explicitly confirms it's abandoned.**

## Human Decision Points

When a handover requires human decisions with subagent recommendations:

**MANDATORY**: Read and follow `reference/human-decision-workflow.md`

Key requirements:

- **Never relay** - Counter-recommend or explicitly agree with YOUR reasoning
- **Always summarize** - Assume human has not read handover or key files
- **Both justify** - Subagent AND main agent must persuade

## Completing a Handover

Completion workflow is documented in SKILL.md. This file covers only edge cases and manual fallback.
