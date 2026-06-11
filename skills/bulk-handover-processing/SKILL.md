---
name: bulk-handover-processing
description: Use when multiple handovers are queued and you want to process them in parallel - spawns coordinated agents with conflict-free assignments to avoid race conditions
disable-model-invocation: true
---

# Bulk Handover Processing

Process multiple handovers in parallel by selecting conflict-free batches and spawning dedicated agents.

## When to Use

- Multiple handovers in `.claude/handovers/queued/`
- Want faster throughput than sequential `/handover` calls
- Dependencies and key file overlaps need coordination

## Algorithm

### Phase 0: Pre-checks

Before starting, verify:

```bash
ls .claude/handovers/WIP/*.md 2>/dev/null
```

**If WIP contains .md files: STOP.** Investigate or clear stuck handovers before proceeding. Do not add more work to WIP while previous work is incomplete.

### Phase 1: Collect Data

```
1. List all .md files in queued/ (sorted alphabetically)
2. For each file, parse YAML frontmatter:
   - key_files: list of paths this handover modifies
   - blocked_by: list of handover filenames that must complete first
3. List all .md files in completed/
```

### Phase 2: Filter to Unblocked

A handover is unblocked if:
- `blocked_by` is empty, OR
- Every entry in `blocked_by` exists in `completed/`

### Phase 3: Resolve Key File Overlaps

Iterate unblocked handovers in filename order. Track claimed files.

```
claimed_files = {}
batch = []

for handover in unblocked (sorted by filename):
    if any(handover.key_files in claimed_files):
        skip  # defer to next iteration
    else:
        batch.append(handover)
        claimed_files.add(handover.key_files)
```

First-by-filename wins. This respects A→B→C ordering from handover creation.

**If batch is empty:** Report "No unblocked handovers available" and stop. All remaining handovers have unsatisfied dependencies.

### Phase 4: Move to WIP

Before spawning, move entire batch to `WIP/`:

```bash
for file in batch:
    mv .claude/handovers/queued/$file .claude/handovers/WIP/
```

### Phase 5: Spawn Agents

**Critical**: Use Bash tool's `run_in_background: true` parameter. Do NOT use shell `&` backgrounding - it creates empty log files because the Bash tool intercepts background jobs.

```
mkdir -p .claude/handovers/logs

task_ids = []
for file in batch:
    # Use run_in_background: true, NOT shell &
    result = Bash(
        command="claude -p \"/handover $file\" --allowedTools \"Read,Write,Edit,Bash,Glob,Grep,Skill\"",
        run_in_background=true
    )
    task_ids.append({file: result.task_id})
```

**Collecting Results**: After spawning all agents, retrieve output via TaskOutput:

```
for {file, task_id} in task_ids:
    output = TaskOutput(task_id=task_id, block=true, timeout=600000)  # 10 min timeout
    Write(
        file_path=".claude/handovers/logs/${file%.md}.log",
        content=output.content
    )
```

Each agent gets fresh context and specific assignment. No limit on batch size.

### Phase 6: Report

After all agents complete:

```
=== Bulk Handover Processing Complete ===

Batch size: N handovers

Completed (in completed/):
  - file1.md
  - file2.md

Still in WIP (likely failed):
  - file3.md

Remaining in queued: M handovers
```

## Error Handling

Fire-and-forget. Failed handovers stay in `WIP/` for manual inspection.

Logs preserved at `.claude/handovers/logs/` for debugging.

## Iterative Usage

Run repeatedly. Each iteration:
1. Picks newly-unblocked handovers (previous completions clear blockers)
2. Continues until `queued/` empty or only blocked handovers remain

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running when WIP has files | Clear WIP first or investigate stuck handovers |
| Expecting automatic retry | Failures need manual intervention |
| Parallel agents editing same file | Algorithm prevents this via key_files check |
