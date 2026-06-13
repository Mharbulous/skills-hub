# Scenario: YOLO Mode

## Setup
- Argument is "yolo" (case-insensitive)

## Prompt
```
Review the file at path: yolo
```

## Expected Behavior
1. Detects YOLO mode from argument
2. Runs Folder-Structure date check (treats "no target file" as default)
3. If date is outdated: updates line counts, renames, stops
4. If date is current: auto-selects the best candidate file
5. Skips all user approval steps
6. Auto-proceeds with decomposition or rebuild
7. Creates commits directly
8. No interactive prompts at any point

## Key Assertions
- [ ] YOLO mode is activated
- [ ] No user prompts or approval requests
- [ ] Auto-selection of candidate file
- [ ] Autonomous execution of decomposition/rebuild
- [ ] Commits are created without asking
