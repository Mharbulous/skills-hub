---
baseline_source: Session 58 (2026-03-26) — QBO Visa Avion Feb 2026 categorization
baseline_method: Actual JS patterns executed via browser_evaluate against live QBO
transactions_processed: 20
success_rate: 20/20 (100%)
---

# Baseline Results

## Source

These baselines are drawn from session 58, where 20 Feb 2026 RBC Visa Avion
transactions were categorized and posted in QBO. The JavaScript patterns below
were written inline as `browser_evaluate` calls and executed against the live
QBO DOM. All 20 transactions posted successfully.

## Why not subagent-tested

These scripts run inside `browser_evaluate` against QBO's live React DOM. They
cannot be tested without a live QBO session. The baseline is therefore the
**proven working code from session 58**, not subagent output.

---

## Baseline 1: Post Transaction (Combined Pattern with Fallback)

**Source:** Final evolved pattern used for last ~15 transactions in session 58.

```javascript
() => {
  // Tier 1: Green primary Post button (expanded form)
  const primaryPost = Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent.trim() === 'Post'
            && b.className.includes('primary')
            && b.offsetHeight > 0);
  if (primaryPost) {
    primaryPost.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));
    return 'Clicked green Post in expanded form';
  }

  // Tier 2: Inline post-action button (5+ rows)
  const btn = document.querySelector(
    'button.post-action, button[aria-label*="post-action"]'
  );
  if (btn) {
    const row = btn.closest('tr');
    const cells = row?.querySelectorAll('td');
    const date = cells?.[1]?.textContent?.trim() || '?';
    const desc = cells?.[2]?.textContent?.trim() || '?';
    const spent = cells?.[3]?.textContent?.trim() || '';
    if (row) row.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    btn.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));
    return `Posted: ${date} ${desc} ${spent}`;
  }

  // Tier 3: Text-content fallback (fewer than ~5 rows, class disappears)
  const allBtns = Array.from(document.querySelectorAll('button'));
  const postBtns = allBtns.filter(
    b => b.textContent.trim() === 'Post' && b.offsetHeight > 0
  );
  if (postBtns.length > 0) {
    const fallbackBtn = postBtns[0];
    const row = fallbackBtn.closest('tr');
    if (row) row.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    fallbackBtn.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));
    return `Fallback: found ${postBtns.length} Post buttons, clicked first`;
  }

  return 'No post button found';
}
```

**Behavior observed:**
- Tier 1 succeeded for transactions where the expanded form was already open
- Tier 2 succeeded for transactions 1–17 (5+ rows in filtered list)
- Tier 3 succeeded for transactions 18–20 (fewer than 5 rows remaining)
- All 20 transactions posted successfully using this combined pattern

---

## Baseline 2: Set Category

**Source:** Pattern used when changing category from QBO's suggestion.

The category change was done via Playwright snapshot → identify combobox ref →
click combobox ref to open → identify target option ref from listbox → click
option ref. This was a multi-step Playwright interaction, not a single
`browser_evaluate` call.

**Key observations:**
- QBO category field is `input[role="combobox"]`, not `<select>`
- `fill_form` with type "combobox" fails: "Element is not a <select> element"
- Opening the combobox renders a listbox with `[role="option"]` elements
- After category change, tax code may silently change — MUST verify
- QBO propagates category to all rows with same vendor simultaneously

**Baseline behavior:** Category was changed successfully for Compass (Bank charges → Travel),
Hostinger (suggested → Computer-related expenses), Evo (suggested → Travel),
Claude AI (suggested → Computer-related expenses), Intuit (suggested → Computer-related expenses),
Starbucks (suggested → Meals and entertainment).

---

## Baseline 3: Set Tax Code

**Source:** Pattern used to correct tax after category changes.

Same multi-step Playwright interaction as category: snapshot → find tax
dropdown ref → click to open → find target option → click option.

**Key observations:**
- After changing Compass to "Travel", QBO silently changed tax from Exempt (0%) to GST (5%)
- Required opening tax dropdown and re-selecting Exempt (0%)
- Compass Vending also needed tax fix (GST → Exempt)
- Intuit needed tax change from PST (7%) to GST/PST (12%)

**Baseline behavior:** Tax was corrected successfully for 3 transactions that
needed it. Other transactions had correct tax after category assignment.

---

## Baseline 4: Read Transactions

**Source:** Used `browser_snapshot` (accessibility tree) rather than `browser_evaluate`
to read the transaction table.

**Key observations:**
- The snapshot/accessibility tree provided transaction data (date, description, amount)
- Each row showed: date, payee/description, spent amount, received amount
- The snapshot was read by Claude to determine what to process next

**Baseline behavior:** Transaction data was successfully read from snapshot.
A `browser_evaluate` version would extract the same data from DOM directly.

---

## Baseline 5: Match Transaction

**Source:** Used for "Thank You Pai Thai" which QBO matched to an existing entry.

**Key observations:**
- QBO showed "Match" action instead of "Categorize" / "Post"
- Match was confirmed via the expanded form
- Used same dispatchEvent pattern for clicking

**Baseline behavior:** Match confirmed successfully. Transaction linked to
existing ledger entry and moved to In QuickBooks.

---

## Invariants Across All Baselines

These invariants held for all 20 transactions and must be preserved in scripts:

1. **dispatchEvent is mandatory** — every click uses `new MouseEvent('click', {bubbles: true, cancelable: true, view: window})`
2. **Native Playwright click always fails** — "element was detached from the DOM, retrying" timeout
3. **3-second waits between actions** — QBO's React DOM needs time to re-render after each interaction
4. **Two-step posting dance** — first click opens expanded form, second click on green Post actually posts
5. **Verify tax after every category change** — QBO silently changes tax codes
6. **Category propagation** — changing category on one vendor row changes ALL rows with same vendor
