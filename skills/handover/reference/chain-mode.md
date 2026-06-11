# Chain Mode: Sequential Subagent Processing

## Overview

Chain mode processes multiple handover files using **sequential subagents with fresh context windows**. This enables processing arbitrarily long handover queues without context accumulation.

## When to Use

Trigger chain mode with:
- "process all handovers"
- "run handover chain"
- "batch process handovers"
- "process queued handovers sequentially"

## Architecture

```
+-------------------------------------------------------------+
|                    ORCHESTRATOR AGENT                        |
|  (minimal context: only cumulative stats between rounds)     |
+-------------------------------------------------------------+
|                                                              |
|   +-------------+    +-------------+    +-------------+      |
|   | Subagent 1  |    | Subagent 2  |    | Subagent N  |      |
|   | (005A)      | -> | (005B)      | -> | (005C)      |      |
|   | Fresh ctx   |    | Fresh ctx   |    | Fresh ctx   |      |
|   +-------------+    +-------------+    +-------------+      |
|         |                  |                  |              |
|      Record             Record             Record            |
|      Result             Result             Result            |
|         |                  |                  |              |
|      CLEAR              CLEAR              CLEAR             |
|      CONTEXT            CONTEXT            CONTEXT           |
|                                                              |
+-------------------------------------------------------------+
```

## Orchestrator Workflow

### Step 1: Scan and Sort

```python
from handover_utils import sort_handovers, detect_chains

queued_dir = Path(".handovers/queued")
sorted_files = sort_handovers(queued_dir)
chains = detect_chains(queued_dir)
```

Report to user:
- Number of files in queue
- Chains detected (if any)
- Processing order

### Step 2: Initialize State

```python
from handover_utils import OrchestratorState

state = OrchestratorState()
```

The orchestrator retains ONLY:
- `processed`: count
- `succeeded`: count
- `failed`: list of filenames (NOT contents)
- `new_handovers`: count

### Step 3: Process Each Handover

For each file in sorted order:

```python
from handover_utils import generate_subagent_prompt

prompt = generate_subagent_prompt(handover_file, repo_root)

# Spawn work subagent with Task tool
Task(
    subagent_type="general-purpose",
    model="sonnet",  # or user preference
    description=f"Process {handover_file.name}",
    prompt=prompt
)
```

**CRITICAL:** Wait for subagent to complete before spawning next.

### Step 4: Record Result and Clear Context

After each subagent completes:

1. Parse JSON response from subagent
2. Record result: `state.record_result(filename, result)`
3. **CLEAR CONTEXT**: Forget all details of the handover just processed
   - Do NOT remember file contents
   - Do NOT remember what changes were made
   - Do NOT remember error details (only filename if failed)

### Step 5: Handle Dependencies

If a handover fails and has dependents (letter suffixes):
- Skip dependent handovers (005B, 005C if 005A failed)
- Record them as "skipped due to dependency failure"
- Continue with next independent chain

### Step 6: Report Summary

```python
print(state.get_summary())
```

## Subagent Protocol

Each work subagent receives a prompt instructing it to:

1. Move handover from `queued/` to `WIP/`
2. Invoke `required_skill` if present in frontmatter
3. Execute the handover instructions
4. Move handover from `WIP/` to `completed/`
5. Commit changes with git-agent
6. Return JSON summary

The subagent has a **completely fresh context window** - no knowledge of previous handovers.

## Example Session

```
User: process all handovers

Claude: Scanning queued handovers...

Found 5 handovers:
- 006_prep-work.md
- 005A_schema-changes.md
- 005B_migrate-data.md
- 005C_verify-migration.md
- 004_cleanup.md

Detected 1 chain: 005A -> 005B -> 005C

Processing order: 006 -> 005A -> 005B -> 005C -> 004

Starting chain processing...

[Spawns subagent for 006_prep-work.md]
Completed 006_prep-work.md

[Spawns subagent for 005A_schema-changes.md]
Completed 005A_schema-changes.md

[Spawns subagent for 005B_migrate-data.md]
Completed 005B_migrate-data.md

[Spawns subagent for 005C_verify-migration.md]
Completed 005C_verify-migration.md

[Spawns subagent for 004_cleanup.md]
Completed 004_cleanup.md

## Chain Processing Complete

**Processed:** 5
**Succeeded:** 5
**Failed:** 0
```

## Error Handling

### Subagent Timeout
If subagent doesn't respond within reasonable time:
- Record as failed
- Log filename only
- Continue to next eligible handover

### Subagent Returns Error
Parse error from JSON response:
- Record as failed with filename
- Skip any dependent handovers
- Continue processing

### Write Target Conflicts
Before spawning subagent, check for WIP overlaps:
- If current handover's write_targets overlap with WIP files
- Skip and record as "blocked by WIP"
- Continue to next eligible handover

## Token Efficiency

This design is token-efficient because:

1. **Fresh subagents**: Each handover processed in isolated context
2. **Minimal state**: Orchestrator only keeps counts and failed filenames
3. **Explicit forgetting**: Details cleared after each handover
4. **No accumulation**: Context doesn't grow with queue size

Can process **unlimited handovers** with constant orchestrator context size.

## Context Pressure Reality

The orchestrator's context DOES accumulate even when subagents run in isolation — the orchestrator retains tool call results, status tracking, and conversation flow. This degradation affects quality on **complex tasks at any chain length**, not just long chains. Simple/mechanical tasks mask the problem because they don't demand much intelligence. The "explicit forgetting" principle above is aspirational — in practice the orchestrator cannot truly forget prior context within a single conversation.
