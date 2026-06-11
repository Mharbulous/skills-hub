---
name: e2e-test
description: Collaborative visual E2E testing for desktop or web apps. Claude directs verification, captures screenshots with /glimpse, and interprets UI state while the user acts as hands (clicking, hovering, navigating). Use when verifying UI changes visually, walking through manual test plans, testing Approve/Unapprove or other round-trip flows, or confirming a feature works end-to-end before committing. Also use when a handover or plan includes a manual verification task.
---

# E2E Visual Verification

Systematic UI testing where Claude sees the app via `/glimpse`, interprets screenshots against a verification spec, and directs the user to perform interactions Claude can't do (clicking, hovering, navigating menus). Fix issues inline before advancing.

## Roles

- **Claude:** Reads spec, captures screenshots, interprets UI state, fixes code, seeds data, tracks progress
- **User:** Clicks buttons, hovers for tooltips, navigates menus, confirms behaviors Claude can't observe from screenshots (animations, transitions, tooltip text)

## Invocation

```
/e2e-test                    -- detect from context (handover, plan, conversation)
/e2e-test <spec-path>        -- path to verification plan or handover
```

## Workflow

### Phase 1: Understand

Read the verification spec to identify every checkpoint. Sources (check in order):
1. Explicit path argument
2. Current handover being processed
3. Implementation plan with a verification/testing task
4. User's verbal description

Extract a flat list of **verification checkpoints** — each is a concrete, observable thing to confirm (e.g., "tooltip appears on hover over disabled button", "double checkmark on approved entries", "block disappears from list after clicking Approve").

### Phase 2: Checklist

Create a `TaskCreate` todo for each checkpoint. Group by view/screen when the app has multiple views.

### Phase 3: Unblock

Check for known defects that would prevent verification from passing. The spec often calls these out (e.g., "missing tooltip is a defect discovered this session; must be fixed before Task 11 can pass").

For each blocking defect:
1. Read the relevant source file
2. Apply the fix (surgical — minimal change)
3. Build to verify it compiles

### Phase 4: Prepare

**Build and launch:**
1. Build the project
2. If a running instance is locking files, ask user before killing it
3. Launch the app in background

**Seed test data when needed.** The spec may note that certain views require data that doesn't exist yet. Signs you need to seed:
- Empty state shown where the spec expects populated data
- The spec explicitly mentions "seed with manual SQL" or similar
- View modes that require specific data states (classified, approved, etc.)

Seeding approach:
1. Understand the data model (read schema/migrations)
2. Query existing data to find what's available
3. Insert synthetic records that exercise all required states
4. Handle encrypted databases by using the app's own infrastructure (connection factories, etc.)
5. Restart the app to pick up new data

**Diagnose blank screens.** If the app loads but shows no data and no empty-state message, the data load is likely throwing silently. Add temporary diagnostic logging (try/catch with file output), rebuild, check the log, fix the root cause, then remove the diagnostics.

### Phase 5: Verify

For each checkpoint, use this loop:

1. **Capture** — Use `/glimpse` to screenshot the app window
   ```bash
   python "$HOME/.claude/skills/glimpse/src/glimpse.py" capture "window title"
   ```
   If the title doesn't match, run `windows` to list available windows.

2. **Interpret** — Read the screenshot and compare against the spec. Note what's visible, what's correct, what's missing.

3. **Interact** — For things Claude can't verify from a screenshot (tooltips, hover states, click behaviors), use `AskUserQuestion` to direct the user:
   - Navigation: "Can you switch to [View] mode? (View menu → [option])"
   - Hover: "Can you hover over [element] to check if a tooltip appears?"
   - Click: "Can you click [button] and tell me what happens?"
   - Observe: "Does the block disappear from the list?"

4. **Verify negatives** — When the user reports something missing, wrong, or not working, capture a screenshot immediately before treating it as a failure. The user may have missed the element, looked in the wrong spot, or misidentified it. Compare the screenshot against the spec yourself — if the element is actually present and correct, tell the user what you see and where, then re-ask.

5. **Record** — Mark the task completed or note the failure.

**Question design:** Keep AskUserQuestion options concrete and observable. Describe UI elements by position and appearance, not code names.

See `references/verification-patterns.md` for question templates.

### Phase 6: Exercise Round-Trips

For workflows that involve action → state change → reverse action:

1. Direct user to perform action (e.g., "Click Approve on the first block")
2. Verify state change (e.g., "Block disappeared from Pending Review? ✓")
3. Navigate to the target view and capture screenshot (e.g., "Switch to Approved")
4. Verify arrival (e.g., "Block appears with double checkmark and Unapprove button? ✓")
5. Direct reverse action (e.g., "Click Unapprove")
6. Navigate back and verify return (e.g., "Block reappears in Pending Review? ✓")

Capture a screenshot at each state transition for evidence.

### Phase 7: Clean Up

1. Remove any temporary diagnostic code (try/catch logging, breadcrumb traces)
2. Delete temporary tools (seed scripts, test projects)
3. Build to confirm clean compilation
4. Run tests to confirm nothing broke
5. Commit the actual fixes with a summary of verification findings

## Completion Report

After all checkpoints pass, output a summary table:

```markdown
| Checkpoint | Result |
|-----------|--------|
| Raw Captures: context chips visible | Pass |
| Raw Captures: tooltip on hover | Pass |
| Pending Review: Approve button | Pass |
| ... | ... |
```

## Tips

- **Glimpse captures VS Code too.** If the wrong window is captured, use `python .../glimpse.py windows` to list titles, then capture with the exact title.
- **WPF tooltips on disabled controls** need `ToolTipService.ShowOnDisabled="True"`.
- **SQLCipher databases** can't be accessed from command-line sqlite3. Use the app's own connection factory infrastructure.
- **Fire-and-forget async (`_ = LoadAsync()`)** silently swallows exceptions. If the UI shows a blank screen with no empty state, add temporary try/catch logging to surface the error.
