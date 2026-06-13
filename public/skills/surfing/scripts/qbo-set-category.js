/**
 * QBO: Set the category (account) on the currently expanded transaction.
 *
 * QBO's category field is input[role="combobox"], NOT <select>.
 * Playwright's fill_form with type "combobox" fails.
 *
 * IMPORTANT: After this script runs, the TAX CODE may have silently changed.
 * The calling workflow MUST verify and correct the tax code afterward.
 *
 * Usage: Prepend `const TARGET = "Travel";` then pass to browser_evaluate.
 * Returns: { success: bool, detail: string, previousValue: string }
 *
 * @param {string} TARGET — the QBO account name to select
 */
(() => {
  // Find the category combobox in the expanded form
  const comboboxes = Array.from(
    document.querySelectorAll('input[role="combobox"]')
  ).filter(el => el.offsetHeight > 0);

  if (comboboxes.length === 0) {
    return {
      success: false,
      detail: 'No visible combobox found. Is a transaction expanded?',
      previousValue: null
    };
  }

  // Use the first visible combobox (category field)
  const combo = comboboxes[0];
  const previousValue = combo.value || '(empty)';

  // Focus and click to open the dropdown
  combo.focus();
  combo.dispatchEvent(new MouseEvent('click', {
    bubbles: true, cancelable: true, view: window
  }));

  // Clear current value and type the target to filter
  combo.value = '';
  combo.dispatchEvent(new Event('input', { bubbles: true }));
  combo.value = TARGET;
  combo.dispatchEvent(new Event('input', { bubbles: true }));

  // Look for the target option in the listbox
  // (May need a short delay for the listbox to render — caller should
  //  wait ~500ms and run qbo-select-option.js if this doesn't auto-select)
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
      detail: `Category set to: ${match.textContent.trim()}`,
      previousValue
    };
  }

  return {
    success: false,
    detail: `Typed "${TARGET}" but no matching option found. `
          + `Available: ${options.map(o => o.textContent.trim()).slice(0, 10).join(', ')}`,
    previousValue
  };
})()
