---
scenario: match-transaction
candidate: QBO Browser Automation Patterns
tests_section: Match transaction via browser_evaluate
---

# Scenario: Match Transaction

## Context

QBO Banking page, a pending transaction that QBO suggests matching to an
existing ledger entry (e.g., a Visa payment that matches a recorded transfer).

## Input Conditions

### Condition A: QBO shows a Match suggestion
- Transaction row shows "Match" action instead of "Categorize"
- Clicking Match confirms the link to an existing ledger entry

### Condition B: Match button in expanded form
- Transaction has been expanded
- Match/Confirm button visible in the expanded view

## Expected Behavior

1. Script finds the Match button (by text content "Match" or appropriate selector)
2. Clicks via `dispatchEvent`
3. Transaction matches and moves from For Review to In QuickBooks
4. Returns confirmation message

## Critical Invariants

- Must use `dispatchEvent`, not native Playwright click
- Matching does NOT create a new transaction — it links to existing
- After matching, the transaction should disappear from For Review

## Edge Cases

- No Match button found → return error message
- Multiple Match buttons visible → click the one in the active/expanded row
