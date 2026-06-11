/**
 * QBO: Post the first visible pending transaction.
 *
 * Three-tier fallback:
 *   1. Green "primary" Post button (expanded form already open)
 *   2. Inline post-action button (5+ rows in filtered list)
 *   3. Text-content fallback (fewer than ~5 rows, class disappears)
 *
 * All clicks use dispatchEvent — native Playwright click() fails on QBO's
 * React DOM ("element was detached from the DOM").
 *
 * Usage: Read this file, pass its content to browser_evaluate.
 * Returns: { success: bool, method: string, detail: string }
 */
(() => {
  const evt = (el) =>
    el.dispatchEvent(new MouseEvent('click', {
      bubbles: true, cancelable: true, view: window
    }));

  // --- Tier 1: Green primary Post button in expanded form ---
  const primaryPost = Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent.trim() === 'Post'
            && b.className.includes('primary')
            && b.offsetHeight > 0);
  if (primaryPost) {
    evt(primaryPost);
    return {
      success: true,
      method: 'primary',
      detail: 'Clicked green Post button in expanded form'
    };
  }

  // --- Tier 2: Inline post-action button ---
  const postAction = document.querySelector(
    'button.post-action, button[aria-label*="post-action"]'
  );
  if (postAction) {
    const row = postAction.closest('tr');
    const cells = row?.querySelectorAll('td');
    const date  = cells?.[1]?.textContent?.trim() || '?';
    const desc  = cells?.[2]?.textContent?.trim() || '?';
    const spent = cells?.[3]?.textContent?.trim() || '';
    if (row) evt(row);
    evt(postAction);
    return {
      success: true,
      method: 'post-action',
      detail: `Opened: ${date} | ${desc} | ${spent}`
    };
  }

  // --- Tier 3: Text-content fallback ---
  const postBtns = Array.from(document.querySelectorAll('button'))
    .filter(b => b.textContent.trim() === 'Post' && b.offsetHeight > 0);
  if (postBtns.length > 0) {
    const btn = postBtns[0];
    const row = btn.closest('tr');
    if (row) evt(row);
    evt(btn);
    return {
      success: true,
      method: 'text-fallback',
      detail: `Found ${postBtns.length} Post button(s), clicked first`
    };
  }

  return {
    success: false,
    method: 'none',
    detail: 'No Post button found on page'
  };
})()
