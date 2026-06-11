/**
 * QBO: Set the tax code on the currently expanded transaction.
 *
 * MUST be called after every category change — QBO silently changes the
 * tax code when the category changes.
 *
 * Usage: Prepend `const TARGET = "Exempt (0%)";` then pass to browser_evaluate.
 * Returns: { success: bool, detail: string, currentValue: string }
 *
 * Known BDLC tax codes:
 *   "GST (5%)", "Exempt (0%)", "Out of Scope (0%)",
 *   "PST BC (7%)", "GST/PST BC (12%)"
 *
 * @param {string} TARGET — the tax code to select
 */
(() => {
  // Find the tax dropdown — usually a combobox or select near the category field
  // QBO renders tax as a dropdown/combobox with tax-related aria labels
  const taxInputs = Array.from(
    document.querySelectorAll(
      'input[role="combobox"], select, [class*="tax"] input, [class*="Tax"] input'
    )
  ).filter(el => el.offsetHeight > 0);

  // Heuristic: the tax field is usually the second combobox (first is category)
  // or has "tax" in a parent's class/aria-label
  let taxField = null;
  for (const el of taxInputs) {
    const parent = el.closest('[class*="tax"], [class*="Tax"], [aria-label*="tax"], [aria-label*="Tax"]');
    if (parent) {
      taxField = el;
      break;
    }
  }
  // Fallback: if category is first combobox, tax is second
  if (!taxField) {
    const comboboxes = Array.from(
      document.querySelectorAll('input[role="combobox"]')
    ).filter(el => el.offsetHeight > 0);
    if (comboboxes.length >= 2) {
      taxField = comboboxes[1];
    }
  }

  if (!taxField) {
    return {
      success: false,
      detail: 'Tax field not found. Is a transaction expanded?',
      currentValue: null
    };
  }

  const currentValue = taxField.value || '(empty)';

  // Check if already correct
  if (currentValue.toLowerCase().includes(TARGET.toLowerCase())) {
    return {
      success: true,
      detail: `Tax already set to: ${currentValue}`,
      currentValue
    };
  }

  // Open dropdown and type target
  taxField.focus();
  taxField.dispatchEvent(new MouseEvent('click', {
    bubbles: true, cancelable: true, view: window
  }));
  taxField.value = '';
  taxField.dispatchEvent(new Event('input', { bubbles: true }));
  taxField.value = TARGET;
  taxField.dispatchEvent(new Event('input', { bubbles: true }));

  // Find matching option
  const options = Array.from(
    document.querySelectorAll('[role="option"]')
  ).filter(opt => opt.offsetHeight > 0);

  const match = options.find(opt =>
    opt.textContent.trim().toLowerCase().includes(TARGET.toLowerCase())
  );

  if (match) {
    match.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));
    return {
      success: true,
      detail: `Tax changed from "${currentValue}" to: ${match.textContent.trim()}`,
      currentValue
    };
  }

  return {
    success: false,
    detail: `Typed "${TARGET}" but no matching option. `
          + `Available: ${options.map(o => o.textContent.trim()).slice(0, 10).join(', ')}`,
    currentValue
  };
})()
