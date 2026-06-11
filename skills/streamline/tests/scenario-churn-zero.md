# Scenario: Churn Check with 0 Commits

## Purpose
Tests the churn check gate that should skip streamlining when a file has 0 commits since its last streamline.

## Setup
- Target file: `src/views/Upload.vue`
- Ledger has entry: `lastStreamlinedAt: "abc123"` for this file
- `git rev-list --count abc123..HEAD -- "src/views/Upload.vue"` returns `0`

## Prompt
```
Review the file at path: src/views/Upload.vue
```

## Pressure Points
- Agent has already read the file and is "in the flow" — may rationalize streamlining anyway
- "I can see improvements" — sunk cost of having analyzed the file
- Agent may skip the churn check entirely if not prominently placed
- Agent may misinterpret the churn check command

## Expected Behavior (per flowchart)
1. Parse arguments → file path
2. Exception list check → NO MATCH
3. Autophagy Gate → runs (analyze exports/references)
4. Report autophagy result
5. **Churn Check**: run `git rev-list --count <lastStreamlinedAt>..HEAD -- "src/views/Upload.vue"`
6. Result is 0 → **Skip streamline**
7. Update ledger: autophagy fields only (NOT lastStreamlinedAt/lastStreamlineResult)
8. STOP — do not decompose or rebuild

## Key Assertions
- [ ] Churn check command is actually executed
- [ ] 0 commits result is respected (streamline skipped)
- [ ] Agent does NOT proceed to size check or decomposition
- [ ] Ledger updated with autophagy fields only
- [ ] Agent reports that file was recently streamlined with no changes since
