---
name: verify-bc-lawyer
description: Use when asked to verify someone is a licensed practicing lawyer in British Columbia, or to look up a BC lawyer's status, firm, or contact info - queries the Law Society of BC Lawyer Directory programmatically via Node.js with session cookie handling
disable-model-invocation: true
---

# Verify BC Lawyer

## Overview

Programmatic lookup against the Law Society of BC (LSBC) Lawyer Directory. Requires a two-step HTTP flow with cookie persistence — the detail page returns 302 without valid session cookies.

## When to Use

- User asks to verify someone is a practicing lawyer in BC
- User asks for a BC lawyer's firm, status, or contact info
- User needs to confirm a lawyer's standing with the Law Society of BC

## Critical: What Does NOT Work

| Approach | Why it fails |
|----------|-------------|
| WebFetch | Summarizes HTML, strips form field names. Cookie-less = 302 on detail page |
| curl | Shell escaping breaks the encrypted URLs with special chars |
| Guessed params (`lastname`, `firstName`) | ColdFusion uses `txt_last_nm`, `txt_given_nm` |
| POST method | Form uses GET only |
| Detail page without cookies | Returns 302 — requires CFID/CFTOKEN/JSESSIONID from search |
| Inline `node -e` | Regex patterns with backslashes break in shell. Always write to `.cjs` file |

## The Working Flow

**MUST use Node.js `https` module. MUST save script as `.cjs` file (not `.js` — ESM projects break `require()`).**

### Step 1: Search (GET, captures cookies)

```
GET /lsbc/apps/lkup/directory/mbr-search.cfm
  ?txt_search_type=1          # 1=starts with, 2=contains, 3=exact match
  &txt_last_nm={LAST_NAME}
  &txt_given_nm={FIRST_NAME}  # optional
  &txt_city=                  # optional
  &is_submitted=1
  &member_search=Search
  &results_no=10
```

### Step 2: Parse search results

Regex: `href="mbr-details\.cfm\?encrypted=([^"]+)">\s*([^<]+)`

**CRITICAL:** Strip `#_toph1` anchor fragment from encrypted value before using it. The href contains `#_toph1` which causes 400 errors if included in the HTTP request.

### Step 3: Detail page (GET, with cookies from Step 1)

```
GET /lsbc/apps/lkup/directory/mbr-details.cfm?encrypted={ENCRYPTED_WITHOUT_FRAGMENT}
Cookie: CFID=...; CFTOKEN=...; JSESSIONID=...
```

### Step 4: Parse detail HTML

The HTML uses multiline label/value pairs (NOT on same line):
```html
<div class="col-sm-3 form-label">Current status</div>
<div class="col-sm-9">
  <p>Practising</p>
</div>
```

Use **multiline regex** with `[\s\S]*?` to span across lines. See the script below.

## Ready-to-Use Script

**Save this as a `.cjs` file, then run with `node script.cjs`. Replace {LAST} and {FIRST}.**

```javascript
const https = require('https');

function lsbcFetch(path, cookies) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: 'www.lawsociety.bc.ca', path,
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
    };
    if (cookies) opts.headers['Cookie'] = cookies;
    https.get(opts, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        const sc = (res.headers['set-cookie'] || []).map(c => c.split(';')[0]).join('; ');
        resolve({ status: res.statusCode, data: d, cookies: sc });
      });
    }).on('error', reject);
  });
}

async function verifyBCLawyer(lastName, firstName) {
  // Step 1: Search (try "starts with" first, fall back to "contains")
  for (const searchType of [1, 2]) {
    const path = `/lsbc/apps/lkup/directory/mbr-search.cfm?txt_search_type=${searchType}&txt_last_nm=${encodeURIComponent(lastName)}&txt_given_nm=${encodeURIComponent(firstName || '')}&txt_city=&is_submitted=1&member_search=Search&results_no=10`;
    const search = await lsbcFetch(path);

    // Step 2: Parse results — strip #fragment from encrypted links
    const linkRx = /href="mbr-details\.cfm\?encrypted=([^"]+)">\s*([^<]+)/g;
    const results = [];
    let m;
    while ((m = linkRx.exec(search.data)) !== null) {
      results.push({ encrypted: m[1].replace(/#.*$/, ''), name: m[2].trim() });
    }

    if (results.length === 0) {
      if (searchType === 1) continue; // try "contains" next
      console.log('Not found in LSBC directory.');
      return null;
    }

    console.log(`Found ${results.length} result(s) [search type: ${searchType === 1 ? 'starts with' : 'contains'}]`);

    // Step 3: Detail page with session cookies
    const detail = await lsbcFetch(
      `/lsbc/apps/lkup/directory/mbr-details.cfm?encrypted=${results[0].encrypted}`,
      search.cookies
    );

    if (detail.status !== 200) {
      console.error('Detail page failed:', detail.status);
      return null;
    }

    // Step 4: Parse — multiline regex to extract label/value pairs
    const extract = (label) => {
      const rx = new RegExp(
        label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') +
        '</div>[\\s\\S]*?<div class="col-sm-9">[\\s\\S]*?([\\s\\S]*?)</div>',
        'i'
      );
      const match = detail.data.match(rx);
      if (!match) return 'Not found';
      return match[1]
        .replace(/<[^>]+>/g, ' ')
        .replace(/&nbsp;/g, ' ')
        .replace(/\[\s*Show Map\s*\]/g, '')
        .replace(/QRCode/g, '')
        .replace(/\[\s*Add to Outlook Contacts\s*\]/g, '')
        .replace(/\[\s*Show QRCode\s*\]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
    };

    return {
      name: results[0].name,
      status: extract('Current status'),
      firm: extract('Primary location'),
      address: extract('Contact address'),
      phone: extract('Phone number'),
      restrictions: extract('Current practice restrictions'),
      discipline: extract('Discipline history since 1983'),
      allResults: results.map(r => r.name)
    };
  }
}

verifyBCLawyer('{LAST}', '{FIRST}').then(r => {
  if (r) console.log(JSON.stringify(r, null, 2));
});
```

## Output Format

```
**Verification Result: {Name}**
- Status: {Practising / Non-practising / etc.}
- Firm: {Firm name}
- Location: {City, Province}
- Phone: {Number}
- Restrictions: {None / details}
- Discipline history: {None / details}
- Email: Not available (CAPTCHA-protected)
```

## Edge Cases

- **Multiple results:** Show all names in `allResults`, ask user which to look up in detail
- **No results:** Report "Not found in LSBC directory" — may be unlicensed, retired, or name spelling differs. Script auto-falls back from "starts with" to "contains" before reporting not found.
- **Non-practising status:** Lawyer exists but is not currently licensed to practice

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Saving as `.js` | Save as `.cjs` — ESM projects (`"type": "module"` in package.json) break `require()` |
| Running inline with `node -e` | Regex backslashes break in shell escaping. Write to file. |
| Including `#_toph1` in detail URL | Strip fragment: `.replace(/#.*$/, '')` or get 400 error |
| Single-line regex for field extraction | HTML is multiline. Use `[\s\S]*?` to span lines. |
| Not sending cookies to detail page | Detail page returns 302 without CFID/CFTOKEN/JSESSIONID |
