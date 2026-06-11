/**
 * QBO: Confirm a Match for the currently expanded/selected transaction.
 *
 * Matching links a bank-feed transaction to an existing ledger entry.
 * No new transaction is created — it prevents duplicates.
 *
 * Usage: Pass this file's content to browser_evaluate.
 * Returns: { success: bool, detail: string }
 */
(() => {
  const evt = (el) =>
    el.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));

  // Look for Match/Confirm button in expanded form first
  const buttons = Array.from(document.querySelectorAll('button'))
    .filter(b => b.offsetHeight > 0);

  // Try "Match" button with primary styling (in expanded form)
  const primaryMatch = buttons.find(b =>
    b.textContent.trim() === 'Match'
    && b.className.includes('primary')
  );
  if (primaryMatch) {
    evt(primaryMatch);
    return {
      success: true,
      detail: 'Clicked primary Match button in expanded form'
    };
  }

  // Try any visible "Match" button
  const matchBtn = buttons.find(b =>
    b.textContent.trim() === 'Match'
  );
  if (matchBtn) {
    const row = matchBtn.closest('tr');
    if (row) evt(row);
    evt(matchBtn);
    return {
      success: true,
      detail: 'Clicked Match button'
    };
  }

  // Try "Confirm" button (alternate wording in some QBO views)
  const confirmBtn = buttons.find(b =>
    b.textContent.trim() === 'Confirm'
    && b.className.includes('primary')
  );
  if (confirmBtn) {
    evt(confirmBtn);
    return {
      success: true,
      detail: 'Clicked Confirm button (match variant)'
    };
  }

  return {
    success: false,
    detail: 'No Match or Confirm button found. Is a matched transaction selected?'
  };
})()
