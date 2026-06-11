---
scenario: set-tax-code
candidate: QBO Browser Automation Patterns
tests_section: Set transaction tax code via browser_evaluate
---

# Scenario: Set Tax Code

## Context

QBO Banking page, a transaction row is expanded. Claude needs to set or correct
the tax code after a category change (which may have silently altered the tax).

## Input Conditions

### Condition A: Tax dropdown needs to be changed
- The expanded form shows a tax field/dropdown
- Current value may be wrong (e.g., QBO auto-changed it to "GST (5%)" when it should be "Exempt (0%)")

### Condition B: Tax code is already correct
- Tax field shows the expected value
- No change needed

## Expected Behavior

### For Condition A:
1. Script locates the tax dropdown/combobox in the expanded form
2. Opens the dropdown
3. Finds the target tax code option by text content
4. Clicks it via `dispatchEvent`
5. Tax field updates to show the selected code
6. Returns confirmation of what was set

### For Condition B:
1. Script reads current tax value
2. Returns current value without making changes

## Critical Invariants

- **MUST verify tax code after every category change** — QBO silently changes tax when category changes (e.g., changing to "Travel" may flip tax from "Exempt (0%)" to "GST BC (5%)")
- Must use `dispatchEvent` for all clicks
- Tax codes in BDLC's QBO: "GST (5%)", "Exempt (0%)", "Out of Scope (0%)", "PST BC (7%)", "GST/PST BC (12%)"

## Edge Cases

- Tax dropdown not found → return error
- Target tax code not in dropdown options → return "code not found" with available options
- Multiple tax-related fields visible → ensure selecting the correct one for the active transaction

## Parameters

The script needs to accept:
- `targetTaxCode` (string) — the tax code to select (e.g., "Exempt (0%)", "GST (5%)", "Out of Scope (0%)")
