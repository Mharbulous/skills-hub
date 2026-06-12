---
name: handover
description: "Invoked via /handover only. Resumes previous work or creates a handover for the next session. Automatically detects mode based on conversation state. Handles dependency chains, key file overlap detection, self-healing via Repair mode, and auto-commits on completion."
---

# Handover Skill

Context-aware handover management: resume previous work or create a handover for the next session.

## Folder Structure

Handover files are stored **locally in each repository** at `handovers/`:

| Folder                      | Purpose                                                      |
| --------------------------- | ------------------------------------------------------------ |
| `handovers/queued/`   | New handover files awaiting processing                       |
| `handovers/WIP/`      | Handover currently being worked on (parallel session safety) |
| `handovers/completed/`| Finished handovers                                           |

Create these folders if they don't exist when processing or creating handovers.

## Mode Detection

Determine mode based on conversation state and arguments:

| Conversation State                  | Argument  | Mode        | Action                                      |
| ----------------------------------- | --------- | ----------- | ------------------------------------------- |
| Empty or minimal                    | (none)    | **Process** | Run deterministic selector immediately      |
| Empty or minimal                    | `chain`   | **Chain**   | Read `reference/chain-mode.md`              |
| Progress has been made              | (any)     | **Create**  | Read `reference/create-mode.md`             |

**Auto-detection:** If Process mode finds multiple queued handovers with the same numeric prefix and letter suffixes, it MAY suggest chain mode: "Found chain 005D→005E→005F. Run `/handover chain` to process all, or continue with single handover."

## Process Mode

Resume from latest incomplete handover using the **deterministic selector script**.

**CRITICAL: Fast Path (Default)**

🚨 **MANDATORY FIRST ACTION:** Run the selector script BEFORE reading, globbing, or grepping ANY files.

If you catch yourself thinking "I'll just quickly Glob to see what's there first" — **STOP**. That's the rationalization trap. Run the selector.

When `/handover` is invoked without arguments in an empty/minimal conversation:

1. **BLOCKING REQUIREMENT: Run the deterministic selector with `--claim` as your FIRST action**
   ```bash
   cd "$SKILL_DIR" && python scripts/handover_selector.py --claim [repo_path]
   ```
   Materialize this skill folder from the full install or Myskillium per-skill
   tarball, set `SKILL_DIR` to that extracted folder, and use the working
   directory from environment context as `[repo_path]`.

   **FORBIDDEN SEQUENCE:**
   - ❌ Glob to see what's available
   - ❌ Read a handover file to "understand the format"
   - ❌ Grep for handover metadata
   - ❌ Run selector to "verify" your manual selection

   **CORRECT SEQUENCE:**
   - ✅ Run selector immediately
   - ✅ Parse JSON output
   - ✅ Read the file path from JSON (if status is `ready`)

   **EFFICIENCY NOTE:** Running the selector takes 0.5 seconds. Debugging a wrong-file error takes 2+ minutes and creates user frustration. The selector is ALWAYS the faster path.

   **The selector OUTPUT is your understanding.** Not the other way around.

2. **Act on the result** based on JSON output status:
   - `ready` → File already moved to WIP, begin work immediately
   - `repair` → Read `reference/repair-mode.md` for the returned file
   - `all_blocked` / `all_overlapped` / `wip_only` / `empty` → Inform user
   - Script error (not JSON) → Report error to user

3. **Do NOT read process-mode.md preemptively** — the selector tells you what you need to know

4. **Only read process-mode.md** if you need clarification on handling a specific status returned by the selector

**When to read process-mode.md upfront:**
- User provided a specific handover filename argument
- You need to understand the manual fallback workflow
- Debugging selector script issues

**Core Principles:**

- Process mode handles ONE handover per session
- Files are moved to `WIP/` BEFORE processing begins (parallel session safety)
- **WIP Rule**: NEVER touch files in `WIP/` when `queued/` has work
- **Repair Trigger**: Malformed handover frontmatter enters Repair mode

**Completing a Handover:**

After all tasks in the handover are done:

1. Move file from `.handovers/WIP/` to `.handovers/completed/`
2. Stage all changes and commit:
   ```
   feat: completed handover implementation
   
   Reference: handovers/completed/{filename}
   ```
3. Announce completion with commit hash. Do NOT start the next handover.

File archival is primary; commit is secondary. Never revert the move if commit fails.

**See** (only for edge cases, conflicts, or manual fallback):

- `reference/process-mode.md` - Conflict handling, WIP edge cases, manual fallback workflow
- `reference/repair-mode.md` - Self-healing for malformed handover files
- `reference/human-decision-workflow.md` - **MANDATORY** when handover requires human decisions with subagent recommendations

## Create Mode

Generate handover from conversation for the next session.

**Arguments:**

- `file` - Write to file only, suppress chat output
- `chat` - Output to chat only, skip file creation
- (none) - Both file and chat (default)

**See**: `reference/create-mode.md` for full workflow including:

- Pre-creation analysis (task separation, dependencies)
- YAML frontmatter format with `write_targets`, `read_only_targets`, and `blocked_by`
- Letter suffix dependencies for chains (005A → 005B → 005C)
- Insertion strategy (higher numbers run first, letters add to chains)
- Output format template

## Chain Mode

Process multiple handovers using **sequential subagents with fresh context windows**. This enables processing arbitrarily long handover queues without context accumulation.

**Trigger phrases:**
- "process all handovers"
- "run handover chain"
- "batch process handovers"
- "process queued handovers sequentially"
- "chain mode"
- `/handover chain` - Explicit chain processing
- Automatic detection when queued/ has multiple files with same number and letter suffixes (005D, 005E, 005F)

**Key Principle:** Main agent orchestrates, work subagents implement. This keeps orchestrator context minimal while giving each handover full context capacity.

**Workflow:**
1. Detect chain (same numeric prefix with letter suffixes)
2. For each handover in letter order (D → E → F):
   - Spawn work subagent to implement
   - Work subagent drafts commit message (has full context)
   - Main agent passes commit message to git-agent
   - Archive handover to completed/
3. Report final status

**See**: `reference/chain-mode.md` for full workflow including:
- Chain detection algorithm
- Work subagent protocol with commit message extraction
- Git agent protocol
- Error handling and edge cases

## Selector Script Is Non-Negotiable

Run the selector script. No exceptions — it handles dependencies, overlap detection, and priority logic that you cannot replicate by reading files manually. The selector output is your source of truth, not your own assessment.
