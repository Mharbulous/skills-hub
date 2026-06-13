# QuickBooks Online (QBO)

Site-specific knowledge for interacting with QuickBooks Online via browser automation.

## Table of Contents

1. [Authentication](#authentication)
2. [Navigation](#navigation)
3. [Known quirks](#known-quirks)

---

## Authentication {#authentication}

**URL:** `https://app.qbo.intuit.com`

Claude logs in autonomously using `QBO_EMAIL` and `QBO_PASSWORD` environment
variables (set at OS user level via `setx`, not in settings.json).

**Login flow:**
1. Navigate to `https://app.qbo.intuit.com`
2. Intuit account selector appears — click the `***REMOVED***` account button
3. Password page loads with the password auto-filled by Edge — click **Continue**
4. QBO dashboard loads

No 2FA required. Edge pre-fills the password field; no manual entry needed.
No need to wait for Brahm to authenticate.

---

## Navigation {#navigation}

**Left sidebar gear icon:** Settings are accessed via the gear icon (⚙) in the
top-right area, not the left sidebar.

**Settings > Manage Users:** This is where accountant access is managed. There are
two tabs: "Users" (for team members) and "Accounting Firms" (for connected
accountants). Stale accountant connections show on the Accounting Firms tab.

**Reports:** Accessible from the left sidebar. Key reports for tax work:
- Profit & Loss (P&L) — filterable by date range
- Balance Sheet
- Trial Balance
- General Ledger

---

## Known quirks {#known-quirks}

**Banking page — new AI-powered UI (as of Mar 2026):** When you first navigate to
`/app/banking`, QBO shows a redesigned "Welcome to accounting with AI" view with a
flat transaction list. This view does NOT show the connected bank account cards,
error banners, or "Fix now" links. To access the legacy view with account management:
1. Click the **"Go to your transactions"** green button at the top of the page
2. Wait for the page to reload — it will show connected account cards with warning
   triangles (⚠) for broken feeds, an error banner listing affected accounts, and
   "Fix now" / "disconnect" links
3. Do NOT click the gear icon (⚙) next to the transaction table — it can clear the
   view unexpectedly and you'll need to re-click "Go to your transactions"

**Bank feed reconnection:** For Error 103 (username/password not working), click
"Fix now" next to the affected account in the error banner. QBO opens a "Connect
an account" overlay with an "Update your connection" form. For RBC, this asks for
Username/Card Number and Password (direct credential entry, not OAuth). Brahm
enters RBC credentials → clicks "Save and connect". A single credential update
fixes ALL accounts sharing the same bank login (e.g., both RBC General and RBC
Visa Avion were fixed with one credential entry in Mar 2026). After success, both
account cards lose their ⚠ triangles, the error banner disappears, and pending
transaction counts update immediately.

**Plan limitations:** BDLC is on QBO Simple Start (1 user). Some features available
in Plus or Advanced (like class tracking, budgets) are not available.

**Fiscal year:** QBO is configured with fiscal year Nov–Oct (not calendar year).
Reports default to the current fiscal year — always check the date range filter.

**Accrual basis:** QBO is set to accrual basis accounting. Reports can be switched
to cash basis via a toggle, but the default view is accrual.

**Reports — direct URL navigation returns 404:** Navigating directly to
`/app/reports/profitandloss` (or similar report URLs) returns a 404 page.
Instead, click the **Reports** button in the left sidebar (use `find` to locate
it, then click or use JavaScript `querySelector` on the nav item). From the
Reports landing page (`/app/standardreports`), find the specific report link
(e.g., "Profit and Loss by Month") and click it.

**Reports — date range form_input quirks:** When changing the date range on a
report, the "Report period" combobox may not accept `form_input` with value
"Custom" — it can silently fail and keep the previous value (e.g., "This fiscal
year to date"). The From/To text fields accept `form_input` with date strings,
but the report may not refresh with the new range automatically. After setting
From and To, you must click the "refresh-report" button (find it via `find` or
`querySelector` with `[aria-label="refresh-report"]`). Even then, verify the
rendered report header shows the expected date range — if it still shows the old
range, the date inputs didn't take effect. In that case, try clicking into the
From field, clearing it via JavaScript (`el.value = '';
el.dispatchEvent(new Event('input', {bubbles: true}))`), then re-entering the
date.

**Balance Sheet — both dates must be set together:** The Balance Sheet report
requires both the From (start) date AND the To (end) date to be set before the
refresh takes effect. Setting only the To date fails silently — the report
re-renders with the old date range without any error. Always set From first,
then To, then click refresh. Example: to get Aug 2017 Balance Sheet, set
From = 2017-08-01 and To = 2017-08-31, then refresh.

**Reconciliation History — account dropdown cannot be switched programmatically:**
The Reconciliation History page (`Accounting > Reconcile > History by Account`)
uses a React Select component for the account dropdown. This component resists
all standard Playwright automation approaches:
- `dispatchEvent(new MouseEvent('mousedown'))` — opens the dropdown visually
  but selecting an option does NOT actually change the account
- `.click()` on options — returns "Selected" state but the page stays on the
  previous account
- Direct URL navigation with different `accountId` parameter values (e.g.,
  `accountId=1` vs `accountId=10`) — loads the wrong page or shows no history

This is a genuine platform limitation, not a technique gap. **Workaround:**
Ask Brahm to manually switch the account dropdown, or navigate via a different
path if available.

**Cheque/expense entry — form prefill from previous entry:** When entering
multiple cheques or expenses in sequence, QBO prefills the new form with values
from the previous entry (date, ref#, payee). You MUST explicitly clear and
re-enter the Date, Ref no., and Payee fields for each new transaction. If you
don't, the entry will save with the previous transaction's date/ref, which is
wrong and requires manual correction later. Verify every field before saving.

---

## Intuit SSO tab isolation {#tab-isolation}

**Problem:** Intuit's SSO system uses cross-domain navigation that can hijack the
active tab. When automating flows that span multiple Intuit properties (e.g., QBO
at `app.qbo.intuit.com` and the Intuit Developer portal at `developer.intuit.com`),
navigating between them in the same tab causes Intuit SSO to redirect the tab to the
Intuit login/account-selector flow, interrupting your automation.

**Discovery:** This was observed during QBO MCP OAuth setup when navigating between
QBO and the Intuit Developer portal. Opening the second destination in a new tab
prevented SSO from hijacking the QBO session tab.

**Technique:** Create a new browser tab via `mcp__playwright__browser_tabs` before
navigating to a second Intuit domain:

```
browser_tabs(action="new")          # opens a new tab, switches focus to it
browser_navigate(url="https://developer.intuit.com/...")
```

The original QBO tab retains its session state. You can switch back to it with
`browser_tabs(action="select", index=<tab_index>)`.

**Scope:** This is an Intuit SSO behavior, not a general Playwright limitation. It
applies to any automation that crosses Intuit sub-domains within the same session.

---

## DOM interaction — why native Playwright clicks fail {#dom-interaction}

QBO is a React SPA that frequently detaches and re-renders DOM elements.
Playwright's native `click()` command consistently fails with:

> element was detached from the DOM, retrying... Timeout 5000ms exceeded

**Root cause:** Between Playwright resolving the element ref and executing the
click, QBO's React reconciler replaces the DOM node. The ref points to a
detached (stale) node.

**The fix:** All clicks on QBO elements must use JavaScript `dispatchEvent`
via `browser_evaluate`, not native Playwright `click()`:

```javascript
element.dispatchEvent(new MouseEvent('click', {
  bubbles: true, cancelable: true, view: window
}));
```

This also applies to `browser_fill_form` — QBO comboboxes are
`input[role="combobox"]`, NOT `<select>` elements. Playwright's form fill
fails with "Element is not a <select> element."

---

## Automation scripts {#automation-scripts}

Reusable JavaScript files for common QBO browser interactions. Each script is
an IIFE that runs inside `browser_evaluate`. Read the file, pass its content
as the JS string.

**Location:** `scripts/` directory (relative to this skill's root)

### How to use

```
1. Read the script file content
2. For parameterized scripts, prepend: const TARGET = "value";
3. Pass the combined string to browser_evaluate
4. Parse the returned JSON object for success/failure
5. Wait ~3 seconds between actions for QBO's React DOM to re-render
```

### Available scripts

| Script | Purpose | Parameters |
|--------|---------|------------|
| `qbo-post-transaction.js` | Post the first visible pending transaction | None |
| `qbo-set-category.js` | Set category on expanded transaction | `TARGET` = account name |
| `qbo-set-tax-code.js` | Set tax code on expanded transaction | `TARGET` = tax code |
| `qbo-match-transaction.js` | Confirm a Match on selected transaction | None |
| `qbo-read-transactions.js` | Read pending transaction table (read-only) | None |

### Posting workflow (per transaction)

```
1. Run qbo-post-transaction.js
   → If method="primary": transaction posted, done
   → If method="post-action": expanded form opened, continue to step 2
   → If method="text-fallback": expanded form opened, continue to step 2
   → If success=false: no Post button found, check page state

2. (If category needs changing) Run qbo-set-category.js with TARGET
   → MUST run qbo-set-tax-code.js afterward (QBO silently changes tax)

3. (If tax needs fixing) Run qbo-set-tax-code.js with TARGET

4. Run qbo-post-transaction.js again
   → Should find primary Post button now (expanded form is open)
   → Returns method="primary" on success
```

### Critical rules

- **Always wait ~3 seconds** between script executions — QBO needs time to
  re-render after each DOM interaction
- **Always verify tax after category change** — QBO silently changes the tax
  code when you change the category (e.g., "Travel" may flip tax from
  "Exempt (0%)" to "GST (5%)")
- **Category AND tax propagation** — changing category OR tax code on one
  vendor row changes ALL rows with the same vendor. This is QBO behavior,
  not a bug. Always verify both category and tax on subsequent rows after
  changing either field on any row.
- **post-action class disappears** when the filtered transaction list has
  fewer than ~5 rows. The script handles this via Tier 3 text-content
  fallback, but be aware of it when debugging.

### Parameterization example

To set category to "Travel":
```javascript
const TARGET = "Travel";
// ... then append the content of qbo-set-category.js ...
```

The combined string is passed to `browser_evaluate` as a single call.
