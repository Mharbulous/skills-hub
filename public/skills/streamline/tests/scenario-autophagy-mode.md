# Scenario: --autophagy Mode

## Purpose
Tests the entirely separate `--autophagy` flow path which has never been tested.

## Setup
- Argument: `--autophagy`
- Ledger exists with some files reviewed, some not
- prioritize.mjs would return 3 files with varying churn

## Prompt
```
Review the file at path: --autophagy
```

## Pressure Points
- Agent may not recognize `--autophagy` as a special flag
- Agent may try to treat `--autophagy` as a file path
- Agent may skip the prioritize.mjs script and manually pick files
- Agent may forget to loop and only process one file

## Expected Behavior (per flowchart)
1. Parse arguments → `--autophagy` detected
2. Run `node .claude/skills/streamline/scripts/prioritize.mjs --limit 5`
3. If empty result → report "all files up to date" → STOP
4. If files found → enter loop
5. For each file: run Autophagy Gate (analyze exports, search references)
6. Update ledger (autophagy fields ONLY, NOT streamline fields)
7. In interactive mode: ask "Continue to next file?" after each
8. In yolo mode: auto-continue through all files

## Key Assertions
- [ ] `--autophagy` is recognized as a mode flag, not a file path
- [ ] prioritize.mjs script is actually executed
- [ ] Multiple files are processed (loop behavior)
- [ ] Only autophagy fields updated in ledger (NOT lastStreamlinedAt)
- [ ] Streamlining (decomposition/rebuild) is NOT performed
- [ ] Interactive mode pauses between files
