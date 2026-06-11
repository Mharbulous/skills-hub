---
description: "Use $handover to create repo-local handover files or resume queued handovers in Codex. Handles handovers/queued, WIP, completed, dependency chains, selector claim, repair mode, and completion commits when possible."
---

## Codex-Specific Notes

In Codex, invoke this skill with `$handover` (not `/handover`).

### Selector Script Path

Run the deterministic selector with the Codex skill path:

```bash
python C:\Users\Brahm\.codex\skills\handover\scripts\handover_selector.py --claim [repo_path]
```

### Status Codes

The Codex selector returns `conflict` (not `all_overlapped`) when all queued handovers have file overlap with the current WIP.

### Chain Mode

- Trigger with `$handover chain` (not `/handover chain`).
- After a work subagent drafts a commit message, the main agent passes it to the normal Codex git workflow (not a separate git-agent).
