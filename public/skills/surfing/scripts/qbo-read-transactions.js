/**
 * QBO: Read the pending (For Review) transaction table.
 *
 * Returns structured data for each visible transaction row.
 * Read-only — does NOT click or modify anything.
 *
 * Usage: Pass this file's content to browser_evaluate.
 * Returns: { success: bool, count: number, transactions: Array }
 */
(() => {
  const rows = Array.from(document.querySelectorAll('tr'))
    .filter(row => {
      const cells = row.querySelectorAll('td');
      // Transaction rows have multiple cells with data
      return cells.length >= 3 && row.offsetHeight > 0;
    });

  if (rows.length === 0) {
    return {
      success: true,
      count: 0,
      transactions: [],
      detail: 'No transaction rows found. Check if For Review tab is active.'
    };
  }

  const transactions = rows.map((row, idx) => {
    const cells = row.querySelectorAll('td');
    const texts = Array.from(cells).map(c => c.textContent?.trim() || '');

    // QBO transaction table typically has:
    // checkbox | date | description | spent | received | action/status
    return {
      index: idx,
      date: texts[1] || '',
      description: texts[2] || '',
      spent: texts[3] || '',
      received: texts[4] || '',
      raw: texts.join(' | ')
    };
  });

  return {
    success: true,
    count: transactions.length,
    transactions
  };
})()
