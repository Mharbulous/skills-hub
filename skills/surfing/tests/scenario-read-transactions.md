---
scenario: read-transactions
candidate: QBO Browser Automation Patterns
tests_section: Read pending transaction table via browser_evaluate
---

# Scenario: Read Transactions

## Context

QBO Banking page showing pending (For Review) transactions. Claude needs to
read the transaction table to know what's pending before processing.

## Input Conditions

### Condition A: Multiple pending transactions visible
- The Banking page "For Review" tab is active
- Transaction table has rows with: date, description, amount columns

### Condition B: Filtered to a specific account
- User has filtered to e.g., "RBC Avion Visa"
- Only transactions for that account are shown

## Expected Behavior

1. Script queries all visible transaction rows from the table
2. For each row, extracts: date, description/payee, amount (spent/received)
3. Returns structured data (array of objects or formatted string)
4. Does NOT modify any transactions — read-only operation

## Critical Invariants

- Read-only — must not click, modify, or interact with any transaction
- Must handle both "Spent" and "Received" amount columns
- Table cell indices may vary — use column headers or semantic selectors rather than hardcoded indices
- Returns data in a format Claude can parse and use for the categorization workflow

## Edge Cases

- Empty transaction list → return empty array/message
- Table not yet loaded → return appropriate error
- Very long list (100+ rows) → should still work (DOM query, not pagination)
