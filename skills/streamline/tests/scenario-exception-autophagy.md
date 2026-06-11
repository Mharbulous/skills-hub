# Scenario: Exception List File — Autophagy Continuation

## Purpose
Tests the CONTRADICTION between the flowchart (which shows exception list files continue to autophagy gate) and the tendency to STOP after informing the user of the exemption.

## Setup
- Target file: `src/features/documents/components/table/DocumentTable.vue` (on exception list)
- The file has unused exports (dead code planted)

## Prompt
```
Review the file at path: src/features/documents/components/table/DocumentTable.vue
```

## Pressure Points
- Agent sees "exempt" → may rationalize stopping early
- Flowchart explicitly shows: ExCheck →|yes| ExSkip → AG1 (autophagy gate)
- The text "(autophagy gate still runs)" is in the exception list header

## Expected Behavior (per flowchart)
1. Parse arguments → file path provided
2. Exception list check → MATCH
3. Inform user file is exempt from 300-line limit
4. **Continue to Autophagy Gate** (NOT stop)
5. Analyze exports and search for references
6. Report autophagy result (clean/trimmed/deleted)
7. Update ledger with autophagy fields
8. Churn check → if 0 commits, skip streamline; otherwise would go to size check but EXEMPT from 300-line limit

## Key Assertions
- [ ] Agent does NOT stop after exception list match
- [ ] Autophagy gate runs on the exception list file
- [ ] Dead code analysis is performed
- [ ] Ledger is updated with autophagy result
- [ ] 300-line decomposition is NOT triggered (file is exempt)

## What Baseline Found
Previous baseline result showed "STOP — no further processing" after exception match, contradicting the flowchart. This scenario tests whether the skill's text is clear enough to override that tendency.
