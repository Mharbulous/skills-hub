---
scenario: set-category
candidate: QBO Browser Automation Patterns
tests_section: Set transaction category via browser_evaluate
---

# Scenario: Set Category

## Context

QBO Banking page, a transaction row is expanded showing the categorization form.
Claude needs to change the category (account) assignment.

## Input Conditions

### Condition A: Category combobox is visible in expanded form
- The expanded transaction form has an `input[role="combobox"]` for category
- A listbox with account options appears when the combobox is activated

### Condition B: Category needs to be changed from QBO's suggestion
- QBO has pre-filled a suggested category (e.g., "Bank charges and fees")
- The correct category is different (e.g., "Travel")

## Expected Behavior

### For Condition A:
1. Script locates the category combobox (`input[role="combobox"]`)
2. Clicks/focuses the combobox to open the dropdown
3. The listbox renders with account options
4. Script finds the target account option by text content
5. Clicks the target option via `dispatchEvent`
6. Category field updates to show the selected account

### For Condition B:
1. Same as Condition A, but the combobox already has a value
2. Clicking the combobox opens the dropdown showing all options
3. Script selects the correct option from the listbox

## Critical Invariants

- **QBO comboboxes are `input[role="combobox"]`, NOT `<select>` elements** — Playwright's `fill_form` with type "combobox" fails with "Element is not a <select> element"
- After category change, **QBO may silently change the tax code** — this script does NOT handle tax verification (that's a separate script's responsibility), but the calling workflow MUST verify tax after every category change
- The dropdown re-renders frequently — if a click on a suggestion fails, a fresh snapshot is needed for updated element refs
- Must use `dispatchEvent` for all clicks, not native Playwright click

## Edge Cases

- Combobox not found → return clear error message
- Target account not in listbox → return "account not found" with list of available options
- Listbox takes time to render → script should check for listbox presence before clicking option

## Parameters

The script needs to accept:
- `targetAccount` (string) — the QBO account name to select (e.g., "Travel", "Computer-related expenses", "Meals and entertainment")
