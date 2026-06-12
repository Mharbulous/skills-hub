# Bill of Costs (Form 62) — Workflow

## Sources of Authority (declared — overrides router default)

This workflow does **not** follow the router's Sources of Authority rules. The BOC's facts and law come from different sources than part-based forms:

- **Facts:** gathered through the MCQ interview (Step 2) and from the disbursement CSV (parsed by the disbursement-processor subagent). Not from case data.
- **Law:** Appendix B tariff items, validated by the tariff-checker subagent against live BC sources (`bccourts.ca`, `bclaws.gov.bc.ca`). Not from the matter's `6. LAW/` folder.
- **Prohibited sources:** training knowledge used as a substitute for interview answers or tariff references. The tariff-checker subagent exists precisely to prevent stale training data from being used.

---

Draft a Form 62 Bill of Costs by mapping litigation steps to Appendix B tariff items, assigning units, and calculating totals.

This workflow uses two background subagents:

- **tariff-checker** — verifies Appendix B references are current against live BC sources and confirms all 48 items are present
- **disbursement-processor** — parses a CSV export of disbursements, nets out reversals, flags questionable items, and returns structured results to the parent agent

Both subagents are spawned as early as possible so they run in the background while you gather facts.

## Workflow

### Step 1 — Set up

**A — Ask initial questions**

Use the AskUserQuestion tool to gather:
1. Style of cause (plaintiff v. defendant names)
2. Court file number
3. Costs scale — A ($60/unit), B ($110/unit), or C ($170/unit). If none specified by order, default to Scale B.
4. Costs order details — what the order says, date, and judge's name if known

While the user is answering the above questions, spawn a background subagent from `forms/boc/agents/tariff-checker.md` (relative to the skill root), with `{SKILL_DIR}` replaced by the absolute path to the BOC form directory (i.e. `.agents/skills/draft-bcsc-form/forms/boc/`).  Announce "Tariff rates being checked by subagent."

**B - Generate a Bill of Costs Form**

Once you have enough information to populate the style of cause, file number, costs scale, and unit value:

1. Create `{workspace}/0. DRAFT/YYYY-MM-DD AI/` if it doesn't exist.
2. Copy `forms/boc/templates/bill-of-costs-form.html` (relative to skill root) into that folder.
3. Write `bill-of-costs-data.js` into the same folder with the preamble fields populated (`styleOfProceeding`, `name`, `tariffScale`, `unitValue`, `date`), one empty tariff item row, one empty disbursement row, GST rate at 5%, and PST rate at 7% (computed tax amounts initially $0.00).
4. Tell the user the `file://` path to the HTML copy so they can open it in their browser.

**C - Disbursement CSV export guidance** Help the user export a list of disbursements in CSV format from their accounting system or other sources. A single-row-per-transaction CSV is ideal. The disbursement-processor will net out reversals automatically.  When the user has uploaded the CSV, confirm receipt and announce "Disbursement CSV received — processing by background agent."  Then spawn from `forms/boc/agents/disbursement-processor.md` (relative to the skill root), with `{CSV_PATH}` replaced by the absolute path to the uploaded CSV file and `{SKILL_DIR}` replaced by the absolute path to the BOC form directory (i.e. `.agents/skills/draft-bcsc-form/forms/boc/`).


### Step 2 — Systematic MCQ interview

Walk through tariff categories in order using AskUserQuestion, batching questions by item. Use closed MCQ or yes/no questions — not open-ended. For example, instead of "Tell me about the discovery process", ask "Did you prepare a List of Documents?" If yes, "How many documents were listed?" with options for ranges (under 100, 100–500, over 500) that map to specific tariff items.

#### Category A — Commencement (Items 1, 5, 6)

- Were pre-litigation investigations or correspondence conducted? (Items 1–5)
- Was a Notice of Civil Claim (or other originating pleading) filed? (Item 6)
- Were any amendments to pleadings filed after service?

#### Category B — Defence / Counterclaim (Items 7–9)

Item 7 is a single block covering all of the **defendant's** process: filing a Response to Civil Claim, defending the proceeding, and — if applicable — commencing and prosecuting a Counterclaim. Ask:

- Did your client file a Response to Civil Claim? (Item 7 — defendant's item)
- Did your client also file a Counterclaim? (still Item 7 — the same item covers both defending and counterclaiming)

If your client is the **plaintiff** and the defendant filed a Counterclaim, the plaintiff's work responding to it is a separate item:

- Did your client receive a Counterclaim from the defendant and have to respond to it? (Item 9 — "Response to counterclaim and, if necessary, reply")

Item 8 covers **third party proceedings** only — not counterclaims:

- Was a Third Party Notice filed in the proceeding? If so, was your client a party to the third party proceeding, either as the party bringing or defending it? (Item 8)

#### Category C — Discovery (Items 10–16)

- Was a List of Documents prepared and/or received? If yes, approximately how many documents were listed?
  - Under 100 → Item 10
  - 100–500 → Item 11
  - Over 500 → Item 12
- Were there document demands, inspection requests, or production disputes? (Items 13–15)
- Was there electronic discovery? (Item 16)

#### Category D — Expert Evidence and Witnesses (Items 17–18)

- Were expert reports obtained and served? (Item 17)
- Were lay witnesses required to attend? (Item 18)

#### Category E — Examinations for Discovery (Items 19–20)

- Were examinations for discovery conducted? If yes:
  - How many days total?
  - Was your client conducting (Item 19) or being examined (Item 20)? (Both? Note which days apply to each.)
  - Were there any adjournments, disputes, or further examinations?

#### Category F — Applications, Hearings, Conferences (Items 21–32)

- How many interlocutory applications did your client bring? For each: was it opposed or unopposed? How long was the hearing? (Under 2 hours = ½ day; 2+ hours = full day.) (Items 21–22)
- How many applications did the other side bring that your client had to respond to? (Items 23–24)
- Were any applications heard in writing only? (Item 25)
- Were there any appeals of a master's order? (Item 28)
- Was there a:
  A Case Planning Conference? (Item 29)
  A Trial Management Conference? (Item 30)
  A Settlement Conference? (Item 31)
  A Judicial Case Conference? (Item 32)

#### Category G — Trial (Items 34–38)

- Was a trial completed? If yes:
  - How many trial days? (Item 34: 5 units/day prep — flat; Item 35: 10 units/day attendance — flat)
  - Was written argument submitted after trial? (Item 37: preparing; Item 38: oral argument attendance)
- If no trial: how was the matter resolved?

#### Category H — Registry Steps (Items 39–42)

- Was a Notice of Trial filed? (Item 39: 1 unit flat)
- Was a jury notice filed? (Item 40: 1 unit flat)
- Were other registry attendances required?  What for? (Items 41–42)

#### Category I — Miscellaneous (Items 43–48)

- Was mediation conducted? If yes, how many days? (Item 43)
- Were there formal settlement negotiations or Rule 9-1 offers? (Item 44)
- Was travel required for any step? (Items 45–48)
- Any other significant steps not yet covered?

### Step 3 — Write tariff items to data file

After the interview is complete, wait for the tariff-checker subagent if it hasn't returned yet.

**Handle the tariff-checker report:**

- **"ALL CURRENT" / "READY TO PROCEED":** Confirm to the user and proceed.
- **"UPDATE NEEDED":** Ask for permission to update reference files. If approved, spawn a second tariff-checker in bootstrap mode (prepend the prompt with: *"You are in bootstrap mode. Rebuild all reference files from scratch using live sources."*). If declined, warn the user and proceed with existing references.
- **"UNABLE TO VERIFY":** Warn which source(s) failed, note last known verification date from `references/source-versions.md`, ask whether to proceed.

Then read `references/tariff-appendix-b.md` and map all confirmed litigation steps to tariff items.

**Build the tariff items array.** Key rule: fill in fixed unit counts for flat-rate items; for range items, leave `unitsClaimed` empty. Write the `tariffItems` array directly into `bill-of-costs-data.js` as a full rewrite of the `window.billData` object.

Show a summary in chat: "14 tariff items mapped, 6 with fixed units, 8 range items to assign. Refreshing the form will show the current state."

Tell the user to refresh the form.

### Step 4 — Two-pass unit assignment (range items only)

For each range item (those with an empty `unitsClaimed`) work through them one at a time:

1. Name the item and state its range (e.g., "Item 2 — Investigating and advising, 1–30 units").
2. Briefly explain what factors affect unit count for this item.
3. Offer 3–4 concrete options with reasoning using the AskUserQuestion tool. Example:
   - 5 units — straightforward matter, standard work, short timeline
   - 15 units — moderate complexity, some novel issues, reasonable correspondence
   - 25 units — significant complexity, voluminous materials, or lengthy timeline
   - Custom number
4. Record the choice and immediately rewrite `bill-of-costs-data.js` (full rewrite of `window.billData`) with the updated `unitsClaimed` value. Tell the user to refresh the form.

After all range items are assigned, compute taxes on tariff fees (GST 5% + PST 7%) and show final totals in chat:

```
Total units:            [sum]
Unit value (Scale [X]): $[amount]
Tariff fees subtotal:   $[subtotal]
GST (5%):               $[gst]
PST (7%):               $[pst]
Total Part 1 fees:      $[subtotal + gst + pst]
```

Tell the user to refresh the form to see the complete tariff section.

### Step 5 — Disbursement review

Check whether the disbursement-processor subagent has returned. If not, wait for it now.

**If a disbursement CSV was processed:**
1. Parse the subagent's structured JSON report — the `disbursements` array and `flagged` array.
2. For each flagged item (by index), explain why it was flagged and ask: include as-is, exclude, or modify the amount?
3. After all flags resolved, write the finalized `disbursements` array into `bill-of-costs-data.js` (full rewrite of `window.billData`). Tell the user to refresh the form.

**If no CSV was provided:**
Build the disbursement schedule through conversation. Ask the user for each disbursement (description and amount). Common items to prompt for: filing fees, process server fees, transcripts, expert report fees, photocopying, mediation fees, court search fees, sheriff fees. Write the `disbursements` array to `bill-of-costs-data.js` (full rewrite) when complete. Tell the user to refresh the form.

### Step 6 — Combined summary

Present a combined summary:

```
BILL OF COSTS SUMMARY
=====================
Style of Cause: [Plaintiff] v. [Defendant]
Court File No.: [number]
Scale: [A/B/C] at $[amount]/unit

PART 1 — TARIFF FEES
  Total units:      [n]
  Fees subtotal:    $[subtotal]
  GST (5%):         $[gst]
  PST (7%):         $[pst]
  Total Part 1:     $[subtotal + gst + pst]

PART 2 — DISBURSEMENTS
  Total disbursements:  $[amount]

GRAND TOTAL:  $[total]
```

Refresh the form to see the complete bill of costs.

Ask: "Does this look right? Would you like any adjustments before I convert to Word?"

### Step 7 — Convert to Word (on approval)

After the user approves, re-read `bill-of-costs-data.js` as the source of truth — the user may have edited data via the form and pasted back since the agent last wrote. Parse the `window.billData` object and produce the final Word document:

1. Write `billData` to `/tmp/boc_context.json` using the context JSON schema documented in the Reference section at the end of this file.
2. Run:
   ```
   python .agents/skills/draft-bcsc-form/scripts/fill_boc.py \
       --context /tmp/boc_context.json \
       --out "<matter>/0. DRAFT/YYYY-MM-DD AI/BOC <PlaintiffLastNameFirstInitial>.docx"
   ```
   The script fills `templates/062-boc.dotx` directly — no custom styling, no shading, no formatting embellishments. Empty disbursement categories are collapsed to a single **N/A** row.
3. Run `scripts/verify.py` on the output and report any residual unsubstituted placeholders to the user.

### Paste-back handler (can occur at any point)

When the agent receives pasted JSON from the form's clipboard button:

1. Parse the JSON.
2. Echo a summary: "Got it — N tariff items, M disbursements, total claimed $X."
3. Wrap as `window.billData = <JSON>;` and write to the matter's `bill-of-costs-data.js` (full overwrite — the form's state is authoritative).
4. Confirm: "Data saved. Refresh the form to see the update."

Remind the user to refresh the form before editing if the agent has written to `bill-of-costs-data.js` since the form was last opened.

## Output file naming

`{workspace root}/0. DRAFT/YYYY-MM-DD AI/` (today's date; create if absent)

| File | Path |
|------|------|
| HTML form (copy) | `0. DRAFT/YYYY-MM-DD AI/bill-of-costs-form.html` |
| Data file | `0. DRAFT/YYYY-MM-DD AI/bill-of-costs-data.js` |
| Final Word document | `0. DRAFT/YYYY-MM-DD AI/BOC PlaintiffLastNameFirstInitial.docx` |

`PlaintiffLastNameFirstInitial` = plaintiff's last name + first initial (e.g., `Smith J` for John Smith). For corporations, use the first meaningful word of the name (e.g., `Acme` for Acme Corp.).

## Important notes

- **Tariff reference:** `references/tariff-appendix-b.md` — all 48 items; tariff-checker validates on every run.
- **Flat rates vs. ranges.** Many tariff items are flat rates per day or per step — not discretionary ranges. Always check the reference; do not assume a range exists.
- **Unit assignment is professional judgment.** Suggest unit counts with reasoning; the lawyer makes the final call. Err conservative — registrars reduce inflated claims.
- **Sales tax on tariff fees.** GST (5%) and PST (7%) both apply to the tariff fee subtotal. Compute `fees_gst = fees_subtotal × 0.05`, `fees_pst = fees_subtotal × 0.07`, `fees_taxes = fees_gst + fees_pst`. The context JSON must include `fees_subtotal`, `fees_gst`, `fees_pst`, `fees_taxes`, and `fees_total` (= subtotal + taxes). `grand_total` = `fees_total` + `disb_total`.
- **GST on disbursements.** Disbursements are claimed at actual cost including GST/HST paid. Do not strip GST from disbursement amounts.

---

## Reference — `fill_boc.py` context JSON schema

Write a JSON file with the following structure and pass it via `--context`:

```json
{
  "court_file_number": "S-241171",
  "registry": "Vancouver",
  "originating_party": "FULL NAME IN CAPS",
  "originating_party_role": "PETITIONER",
  "responding_party": "FULL NAME IN CAPS",
  "responding_party_role": "RESPONDENTS",
  "party_claiming_costs": "Descriptive name of claiming party",
  "costs_scale": "Scale B",
  "unit_value": "$110.00",
  "costs_order": "Order reference or leave-blank text",
  "costs_terms": "Quoted costs terms or leave-blank text",
  "tariff_items": [
    { "no": "1", "description": "...", "units_claimed": "3" },
    { "no": "26(b)", "description": "...", "units_claimed": "2.5" }
  ],
  "total_units": "17.5",
  "fees_subtotal": "$1,925.00",
  "fees_gst": "$96.25",
  "fees_pst": "$134.75",
  "fees_taxes": "$231.00",
  "disbursements": {
    "filing_fees":   [{ "date": "26 February 2024", "description": "...", "amount": "7.00", "gst": "0.00", "claimed": "$7.00" }],
    "transcripts":   [],
    "expert_fees":   [],
    "photocopying":  [],
    "search_fees":   [],
    "travel":        [],
    "other":         []
  },
  "disb_subtotals": {
    "filing_fees": "$14.00",
    "transcripts": "", "expert_fees": "", "photocopying": "",
    "search_fees": "", "travel": "", "other": ""
  },
  "disb_total": "$14.00",
  "fees_total": "$2,156.00",
  "grand_total": "$2,170.00",
  "notes": "",
  "notes_footer": ""
}
```

### Key behaviours

- **Tariff rows expanded:** the template's single `[ITEM NO.] / [ITEM DESCRIPTION] / [UNITS CLAIMED]` row is duplicated for each item in `tariff_items`. The Allowed column is left blank throughout (registrar fills it).
- **Empty disbursement categories → N/A:** for any category whose list is empty, the script collapses the header, column-label, data, and subtotal rows into a single two-row table: the category title row + one row containing "N/A". This avoids blank table sections in the output.
- **No styling embellishments:** the script makes no changes to cell shading, borders, fonts, or colours beyond what is in `062-boc.dotx`. It only substitutes text.
- **Allowed columns:** all `[*_ALLOWED]` placeholders are cleared (set to empty string). The registrar fills them at the assessment hearing.

### Run command

```bash
python .agents/skills/draft-bcsc-form/scripts/fill_boc.py \
    --context /tmp/boc_context.json \
    --out "<matter>/0. DRAFT/YYYY-MM-DD AI/BOC <Plaintiff>.docx"
```

Then verify:

```bash
python .agents/skills/draft-bcsc-form/scripts/verify.py \
    "<matter>/0. DRAFT/YYYY-MM-DD AI/BOC <Plaintiff>.docx"
```

### Programmatic scalars (reference)

| Placeholder | Template context | Source |
|-------------|-----------------|--------|
| `[COURT FILE NUMBER]` | `No. [COURT FILE NUMBER]` | `/case-data` |
| `[REGISTRY]` | `[REGISTRY] Registry` | `/case-data` |
| `[ORIGINATING PARTY]` | Standalone paragraph | `/case-data` |
| `[ORIGINATING PARTY ROLE]` | Standalone paragraph (e.g. `PLAINTIFF`) | `/case-data` |
| `[RESPONDING PARTY]` | Standalone paragraph | `/case-data` |
| `[RESPONDING PARTY ROLE]` | Standalone paragraph (e.g. `DEFENDANT`) | `/case-data` |
| `[PARTY CLAIMING COSTS]` | `This is the bill of costs of: [PARTY CLAIMING COSTS]` | Lawyer input |
| `[COSTS SCALE]` | `Tariff scale: [COSTS SCALE]` | Lawyer input (e.g. `Scale B`) |
| `[UNIT VALUE]` | `Unit value: [UNIT VALUE]` | Lawyer input (e.g. `$110.00`) |
| `[COSTS ORDER]` | `Costs awarded by: [COSTS ORDER]` | Lawyer input (order reference) |
| `[COSTS TERMS]` | Standalone paragraph | Lawyer input |

**Leave-blank** (never substituted — registrar fills at hearing):
All `[*_ALLOWED]` columns, `[COSTS ORDER]` and `[COSTS TERMS]` when not yet decided, `[NOTES]`, `[NOTES FOOTER]`.
