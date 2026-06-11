---
scenario: post-transaction
candidate: QBO Browser Automation Patterns
tests_section: Post transaction via browser_evaluate
---

# Scenario: Post Transaction

## Context

QBO Banking page with pending (For Review) transactions. Claude needs to post
a transaction that has already been categorized and tax-coded correctly.

## Input Conditions

### Condition A: Expanded form visible (green primary Post button present)
- A transaction row has been expanded (clicked)
- The expanded form shows a green button with text "Post" and class containing "primary"
- The button is visible (`offsetHeight > 0`)

### Condition B: Inline post-action button visible (5+ rows in filtered list)
- Transaction table has 5+ rows
- Each row has a `button.post-action` element
- No expanded form is open

### Condition C: Post-action class missing (fewer than ~5 rows)
- Transaction table has fewer than ~5 rows
- `button.post-action` selector returns null
- Buttons with text "Post" exist but without the `.post-action` class

## Expected Behavior

### For Condition A:
1. Script finds the green primary Post button
2. Dispatches `MouseEvent('click', {bubbles: true, cancelable: true, view: window})`
3. Transaction posts (disappears from For Review, appears in In QuickBooks)
4. Returns confirmation message indicating what was posted

### For Condition B:
1. Script finds `button.post-action` (or similar selector)
2. Clicks the row first (to expand), then clicks the post-action button
3. This opens the expanded form (transitions to Condition A behavior on next call)
4. Returns description of the transaction being posted

### For Condition C:
1. Script falls back to finding buttons by `textContent === 'Post'` and `offsetHeight > 0`
2. Clicks the first visible Post button
3. Dispatches via `dispatchEvent`, NOT native Playwright click
4. Returns result

## Critical Invariants

- **MUST use `dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}))`** — native Playwright `click()` fails with "element was detached from the DOM"
- **MUST NOT use Playwright's `browser_click` tool** for QBO post actions
- The fallback chain must be: primary Post → post-action → text-content search
- Must return a human-readable result describing what happened (for session logging)

## Edge Cases

- No Post button found at all → return clear "not found" message, do not throw
- Multiple visible Post buttons → click the first one (most recent/topmost transaction)
- Button exists but `offsetHeight === 0` (hidden) → skip it, try next fallback
