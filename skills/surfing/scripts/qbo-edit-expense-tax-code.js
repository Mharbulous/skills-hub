/**
 * QBO: Change the tax code on an OPEN expense form (full edit view).
 *
 * Unlike qbo-set-tax-code.js (Banking page expanded rows where the combobox
 * is already visible), expense forms show tax as a read-only cell that must
 * be clicked to activate inline editing.
 *
 * Usage: Prepend `const TARGET = "GST M&E (5%)";` then pass to browser_evaluate.
 * Returns: { success: bool, detail: string, previousTax: string, newTax: string, category: string }
 *
 * Happy path (validated manually on Cheque 276, Nov 2016):
 * 1. Click read-only "Out of Scope" text in Sales Tax cell → edit mode activates
 * 2. Click tax combobox (data-testid="account_tax_code_dropdown_1__textField")
 * 3. Click matching [role="option"] from dropdown
 * 4. Wait for React re-render
 * 5. Read back category from data-testid="account_line_1__textField" for silent-reset detection
 *
 * Known BDLC tax codes:
 *   "GST (5%)", "Exempt (0%)", "Out of Scope (0%)",
 *   "PST BC (7%)", "GST/PST BC (12%)", "GST M&E (5%)"
 *
 * @param {string} TARGET — the tax code to select (must be defined before eval)
 */
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  const COMBOBOX_TESTID = 'account_tax_code_dropdown_1__textField';
  const CATEGORY_TESTID = 'account_line_1__textField';

  // --- Step 1: Check if combobox already visible (edit mode already active) ---
  let combobox = document.querySelector(`[data-testid="${COMBOBOX_TESTID}"]`);

  if (!combobox) {
    // --- Step 2: Find and click the read-only tax cell to activate editing ---
    const taxPatterns = /Out of Scope|GST \(5%\)|Exempt \(0%\)|GST M&E|GST\/PST|PST BC/;

    // Look for leaf elements with known tax text inside the line item table area
    const candidates = Array.from(document.querySelectorAll('div, td, span'))
      .filter(el =>
        el.offsetHeight > 0 &&
        el.children.length === 0 &&
        taxPatterns.test(el.textContent.trim())
      );

    // Prefer one inside a table row (line item area, not the tax summary at bottom)
    let taxCell = null;
    for (const el of candidates) {
      const row = el.closest('tr, [class*="line-item"], [class*="LineItem"], [class*="row"], [class*="Row"]');
      if (row) {
        taxCell = el;
        break;
      }
    }
    // Fallback: first match
    if (!taxCell && candidates.length > 0) {
      taxCell = candidates[0];
    }

    if (!taxCell) {
      return {
        success: false,
        detail: 'Read-only tax cell not found. Is an expense form open in edit view?',
        previousTax: null,
        newTax: null,
        category: null
      };
    }

    const previousTaxFromCell = taxCell.textContent.trim();

    // Already correct?
    if (previousTaxFromCell.toLowerCase().includes(TARGET.toLowerCase())) {
      const catField = document.querySelector(`[data-testid="${CATEGORY_TESTID}"]`);
      return {
        success: true,
        detail: `Tax already set to: ${previousTaxFromCell}`,
        previousTax: previousTaxFromCell,
        newTax: previousTaxFromCell,
        category: catField ? (catField.value || null) : null
      };
    }

    // Click to activate edit mode
    taxCell.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));

    await sleep(1500);

    combobox = document.querySelector(`[data-testid="${COMBOBOX_TESTID}"]`);
    if (!combobox) {
      return {
        success: false,
        detail: `Clicked tax cell ("${previousTaxFromCell}") but combobox [data-testid="${COMBOBOX_TESTID}"] did not appear after 1.5s.`,
        previousTax: previousTaxFromCell,
        newTax: null,
        category: null
      };
    }
  }

  // --- Step 3: Read current value from combobox ---
  const previousTax = combobox.value || '(empty)';

  if (previousTax.toLowerCase().includes(TARGET.toLowerCase())) {
    const catField = document.querySelector(`[data-testid="${CATEGORY_TESTID}"]`);
    return {
      success: true,
      detail: `Tax already set to: ${previousTax}`,
      previousTax,
      newTax: previousTax,
      category: catField ? (catField.value || null) : null
    };
  }

  // --- Step 4: Click combobox to open dropdown ---
  combobox.focus();
  combobox.dispatchEvent(new MouseEvent('click', {
    bubbles: true, cancelable: true, view: window
  }));
  await sleep(500);

  // --- Step 5: Find and click the target option ---
  const options = Array.from(
    document.querySelectorAll('[role="option"]')
  ).filter(opt => opt.offsetHeight > 0);

  const match = options.find(opt =>
    opt.textContent.trim().toLowerCase().includes(TARGET.toLowerCase())
  );

  if (!match) {
    return {
      success: false,
      detail: `Opened dropdown but no option matches "${TARGET}". `
            + `Available: ${options.map(o => o.textContent.trim()).slice(0, 15).join(', ')}`,
      previousTax,
      newTax: null,
      category: null
    };
  }

  match.dispatchEvent(new MouseEvent('click', {
    bubbles: true, cancelable: true, view: window
  }));

  // --- Step 6: Wait for React re-render ---
  await sleep(1000);

  // --- Step 7: Read back values for verification ---
  const updatedCombobox = document.querySelector(`[data-testid="${COMBOBOX_TESTID}"]`);
  const newTax = updatedCombobox
    ? (updatedCombobox.value || '(empty after change)')
    : '(combobox gone — edit mode may have closed)';

  const catField = document.querySelector(`[data-testid="${CATEGORY_TESTID}"]`);
  const category = catField ? (catField.value || null) : null;

  return {
    success: true,
    detail: `Tax changed from "${previousTax}" to "${match.textContent.trim()}". Category: ${category}`,
    previousTax,
    newTax,
    category
  };
})()
