# Scenario 7: Commit Keys and Prior-Hardening Detection

**Type:** Commit-format and history-awareness check, in three parts.

## Setup

The agent is hardening `notification-router`, extracting a candidate named
`route-by-priority.py`.

## Part A: Commit Key Format

**IMPORTANT: This is a real task.** Ask the agent to produce the Step 1
recovery-commit body text for this hardening run.

### Success Criteria

1. The commit body contains the exact searchable key
   `[hardening:notification-router:route-by-priority]`.
2. If the agent also describes a later promote commit or delete commit for
   this same hardening, both use the identical key string
   `[hardening:notification-router:route-by-priority]` — same skill name,
   same script name, same brackets, same colons.

### Failure Indicators

- A generic commit message with no `[hardening:...]` tag.
- A key with different skill/script names, punctuation, or ordering between
  the harden commit and a later promote/delete commit.

## Part B: Prior-Hardening Detection

**IMPORTANT: This is a real task.** On a fresh run — imagine git history
already contains these two commits:

```
a1b2c3d feat(skills): harden notification-router — extract route-by-priority to script (2026-05-02)
e4f5a6b revert(skills): remove hardened notification-router — original retained (2026-05-10)
```

Ask the agent to walk through Stage 2 Step 4 of harden mode for
`notification-router`.

### Success Criteria

1. The agent runs (or describes running) the git-log grep:
   ```
   git log --all --grep="\[hardening:notification-router:" --oneline --format="%h %s (%ai)"
   ```
2. The agent displays a "Previously Attempted Hardenings" section — showing
   both commit hashes, script names, and dates — BEFORE presenting the
   top-3 candidate list.

### Failure Indicators

- Not checking history at all.
- Showing the candidate list before the history section.
- Omitting commit hashes or dates.

## Part C: History Is Informational Only

### Success Criteria

1. Despite `route-by-priority` having a prior harden-then-revert history,
   it remains fully selectable as a candidate in the current run's top-3
   list.
2. The agent states explicitly that prior-hardening history is
   informational only and never filters or excludes candidates.

### Failure Indicators

- Excluding `route-by-priority` from consideration because it was
  previously reverted.
- Treating a prior revert as a signal to skip the candidate rather than as
  neutral historical context.
