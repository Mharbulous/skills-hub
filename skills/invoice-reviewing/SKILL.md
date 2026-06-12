---
name: invoice-reviewing
description: >
  Review a draft invoice against time entries and invoice data in the practice database before
  sending. Use when the practitioner says "check this invoice", "review invoice before sending",
  "sanity-check billing for [matter]", "look over my draft invoice", or any variant of wanting
  a pre-send accuracy check. Also trigger when the practitioner asks whether entries are missing
  from a draft, whether amounts look unusual, or whether an invoice matches the underlying time
  entries. Triggers on: "before I send", "draft invoice", "billing review", "check my invoice".
---

# Invoice Reviewer

QA skill — read-only. Reads time entries and invoice state from the shared practice database and
produces an itemized checklist of potential issues before the draft invoice reaches the client.
Never writes, updates, or deletes any record.

## Design Principles

The five principles from `vision.md` that govern every output:

1. **Read-only** — never modify DB state. Any code path that writes a row or updates a field violates the skill boundary.
2. **Surface every issue** — report all detected anomalies, even if the list is long. Never filter by severity; the practitioner decides what is intentional.
3. **Cite the data** — every flag must state the record ID, the observed value, and why it is anomalous. "Unusual amount on matter 1042" is not actionable. "Time entry #447 (2.5 hrs, 2026-04-18, matter 1042) is 3× the median entry duration for this matter" is.
4. **Warn on stale data** — if invoice data or time entry data was last updated beyond the staleness threshold, flag it before presenting any checklist.
5. **Always report what was checked** — when no issues are found, state that explicitly and list which checks were performed and against which data range.

## Schema Prerequisites

Several checks require tables not yet in the authoritative schema (`practice-data/SKILL.md`).
Until those tables are added, gate the dependent checks as described below.

### `invoices` table (required for Checks E, I, J and stale-data check)

The current schema has no `invoices` table. Required addition:

```sql
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id),
    billing_period_start TEXT,   -- ISO 8601 date; NULL if not tracked
    billing_period_end TEXT,     -- ISO 8601 date; NULL if not tracked
    amount REAL,
    hourly_rate REAL,            -- rate used for this invoice; NULL if not stored
    last_import_at TEXT,         -- ISO 8601 datetime of last import via invoice-tracking
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_invoices_matter ON invoices(matter_id);
```

**Until this table exists:** Checks E (invoice total vs entry hours), I (billing period overlap),
and J (rate mismatch) are unavailable, and the stale-data check is limited to time entries only.
Surface this to the practitioner:

> "Invoice data is not yet imported. Running checks on time entry data only: statistical outliers,
> entry gaps, near-duplicates, NULL hours, and description completeness. Run invoice-tracking first
> to enable invoice-amount and billing-period checks."

### `invoice_line_items` table (required for Checks F, G, H)

```sql
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    time_entry_id INTEGER REFERENCES time_entries(id),  -- NULL if line item has no linked entry
    hours REAL,
    amount REAL,
    description TEXT,
    entry_date TEXT,    -- ISO 8601; matches time_entries.entry_date or standalone date
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_entry ON invoice_line_items(time_entry_id);
```

**Until this table exists:** line-item cross-checks (F, G, H) are unavailable. Surface this as:

> "Line-item cross-checking requires a schema update (`invoice_line_items` table). Running checks
> available on current data."

Then proceed with the **Available Now** checks.

## Data Sources (Read-Only)

| Source | What it provides | Table/Field |
|--------|-----------------|-------------|
| time_entries | Individual time records for cross-checking | `time_entries` (all columns) |
| invoices | Invoice state per matter | `invoices` (all columns) — when table exists |
| invoice_line_items | Per-line linking of entries to draft | `invoice_line_items` — when table exists |
| matters | Matter metadata for attribution checks | `matters.matt_num`, `matters.description`, `matters.status` |
| clients | Client identity for display | `clients.name`, `clients.client_num` |

Invoice-reviewing never reads accounting CSVs directly. If data is missing from the DB, state what
is absent and tell the practitioner which upstream skill to run first.

### Draft Invoice Entry Point

Invoice-reviewing does not parse raw invoice files. The practitioner exports a draft invoice
listing from their practice management system (LEAP or similar) and imports it via invoice-tracking
before running a review. If the invoice data in the DB is absent or stale, tell the practitioner to
run invoice-tracking first.

## Database Access

All path resolution per `practice-data/SKILL.md`. Always open read-only:

```python
import os, json, sqlite3, statistics
from datetime import date

config_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Coclerk', 'coclerk.json')
with open(config_path) as f:
    config = json.load(f)
db_path = os.path.join(config['database']['folder'], config['database']['filename'])

conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
```

## Review Workflow

When the practitioner invokes invoice-reviewing for a matter (or a set of matters):

1. Resolve the matter from the practitioner's description (name, file number, or matter number)
2. Check whether `invoices` and `invoice_line_items` tables exist (schema-gate check)
3. Run the **Stale Data Check** (limited to time entries if `invoices` absent)
4. Check for entries at all — if none exist, stop early and report
5. Run all applicable checks from **Available Now**
6. If `invoices` exists, run **Invoice-Level Checks**
7. If `invoice_line_items` exists, run **Full Cross-Draft Checks**
8. Present the checklist

### Schema-Gate Check

Before running any checks, detect which tables are present:

```python
tables = {
    row[0]
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
}
has_invoices = 'invoices' in tables
has_line_items = 'invoice_line_items' in tables
```

Announce any missing tables (see Schema Prerequisites section).

### Early Exit: No Entries

If `time_entries` has no rows for this matter, stop immediately:

```python
count = conn.execute(
    'SELECT COUNT(*) FROM time_entries WHERE matter_id = ?', (matter_id,)
).fetchone()[0]
```

If `count == 0`, report:
> "No time entries found for [matter]. Nothing to review. If entries exist in your practice
> management system, run time-entry-drafting or import them before reviewing."

Do not run any other checks.

### Stale Data Check

Before any other checks, query data currency.

**When `invoices` table exists:**

```sql
SELECT
    MAX(i.last_import_at) AS latest_invoice_import,
    MAX(te.created_at)    AS latest_time_entry
FROM matters m
LEFT JOIN invoices i ON i.matter_id = m.id
LEFT JOIN time_entries te ON te.matter_id = m.id
WHERE m.matt_num = ?
```

**When `invoices` table absent:** query only `time_entries.created_at` and omit invoice staleness.

**Thresholds (configurable — defaults):**
- Invoice data: flag if `latest_invoice_import` is NULL or more than **7 days** before today
- Time entries: flag if `latest_time_entry` is NULL or more than **14 days** before today

If stale, open the checklist with:

> **Data currency warning:** Invoice data last imported [date] ([N] days ago). Time entries last
> recorded [date] ([N] days ago). Review results reflect data as of those dates — entries or
> payments recorded since then are not included.

Do not suppress this warning even if the practitioner has already acknowledged it.

### Billing Period

The billing period is used by several checks to scope which entries to examine. Resolve it in this order:

1. **From `invoices` row:** use `billing_period_start` / `billing_period_end` if not NULL
2. **Practitioner-supplied:** if the practitioner specified a date range when invoking the review, use that
3. **Derived from entries:** if neither of the above is available, use `MIN(entry_date)` and `MAX(entry_date)` from `time_entries` for this matter and note: "Billing period derived from entry dates ([start] to [end]) — no invoice period on file."

Never silently assume the billing period. Always state which source was used in the output header.

---

## Available Now: Time Entry Checks

Run these against `time_entries` for the identified matter. First, fetch all entries for the
matter, excluding NULL hours:

```python
rows = conn.execute(
    '''SELECT id, entry_date, hours, description
       FROM time_entries
       WHERE matter_id = ?
         AND entry_date BETWEEN ? AND ?
       ORDER BY entry_date''',
    (matter_id, period_start, period_end)
).fetchall()
```

#### Check A: NULL or Zero Hours

Before statistical analysis, flag entries with NULL or zero hours — these are likely recording
errors and will corrupt any downstream calculation.

```python
null_hour_rows = conn.execute(
    'SELECT id, entry_date, description FROM time_entries WHERE matter_id = ? AND (hours IS NULL OR hours = 0)',
    (matter_id,)
).fetchall()
```

For each: `Entry #{id} ({entry_date}): hours is {NULL/0} — possible recording error.`

Filter these out of subsequent checks: `rows = [r for r in rows if r['hours']]`

#### Check B: Statistical Outliers (Duration)

Require at least 5 entries with valid hours. If fewer, note: "Statistical outlier check skipped —
fewer than 5 entries with recorded hours."

If all entries have identical duration (zero variance), note: "Statistical outlier check skipped
— all entries have the same duration ({hrs} hrs); no outliers possible."

Otherwise:

```python
if len(rows) >= 5:
    durations = [r['hours'] for r in rows]
    med = statistics.median(durations)
    if max(durations) != min(durations):  # skip if zero variance
        for r in rows:
            if r['hours'] > 3 * med:
                flag(f"Entry #{r['id']} ({r['hours']} hrs, {r['entry_date']}): {r['hours'] / med:.1f}× the median entry duration ({med:.1f} hrs) for this matter.")
            elif r['hours'] < 0.1:
                flag(f"Entry #{r['id']} ({r['hours']} hrs, {r['entry_date']}): duration below 6 minutes — possible recording error.")
```

#### Check C: Entry Gaps

Flag any gap of **5 or more calendar days** between consecutive entries during the billing period.

```python
for i in range(1, len(rows)):
    prev, curr = rows[i - 1], rows[i]
    gap_days = (date.fromisoformat(curr['entry_date']) - date.fromisoformat(prev['entry_date'])).days
    if gap_days >= 5:
        flag(f"Gap of {gap_days} days between entry #{prev['id']} ({prev['entry_date']}) and #{curr['id']} ({curr['entry_date']}).")
```

A gap is not necessarily an error (weekends, vacations, hearing-only days). Surface it; the practitioner decides.

#### Check D: Near-Duplicate Entries

Find pairs on the same date with identical or near-identical descriptions, and pairs with
identical hours on the same date. Use a self-join to avoid double-reporting:

```sql
SELECT te1.id AS id1, te2.id AS id2,
       te1.entry_date, te1.hours AS h1, te2.hours AS h2,
       te1.description AS d1, te2.description AS d2
FROM time_entries te1
JOIN time_entries te2
  ON te1.matter_id = te2.matter_id
 AND te1.entry_date = te2.entry_date
 AND te1.id < te2.id
WHERE te1.matter_id = ?
  AND (
    TRIM(LOWER(te1.description)) = TRIM(LOWER(te2.description))
    OR te1.hours = te2.hours
  )
```

For each match, flag: `Possible duplicate: entry #{id1} and #{id2} ({entry_date}) — same
{description/hours}. Cite both descriptions and hours.`

#### Check E: Entries with Missing or Minimal Descriptions

Flag any entry where `description` is NULL, empty, or fewer than 10 characters.

```python
for r in rows:
    desc = (r['description'] or '').strip()
    if len(desc) < 10:
        flag(f"Entry #{r['id']} ({r['hours']} hrs, {r['entry_date']}): description {'is blank' if not desc else f'is too short ({len(desc)} chars)'}.")
```

---

## Invoice-Level Checks (when `invoices` table exists)

Fetch the invoice for this matter and billing period:

```sql
SELECT id, amount, hourly_rate, billing_period_start, billing_period_end
FROM invoices
WHERE matter_id = ?
  AND billing_period_start = ?
  AND billing_period_end = ?
LIMIT 1
```

If no invoice row is found, note: "No invoice record found for this matter and period. Run
invoice-tracking to import the draft invoice, then re-run this review."

#### Check F: Invoice Total vs Entry Hours

If the invoice has a known `hourly_rate`:

```python
total_hours = sum(r['hours'] for r in rows)
expected = total_hours * invoice['hourly_rate']
discrepancy_pct = abs(invoice['amount'] - expected) / expected if expected else None
if discrepancy_pct and discrepancy_pct > 0.05:
    flag(f"Invoice total (${invoice['amount']:,.2f}) differs from entry hours × rate "
         f"({total_hours:.1f} hrs × ${invoice['hourly_rate']}/hr = ${expected:,.2f}) by "
         f"{discrepancy_pct:.1%}.")
```

If `hourly_rate` is NULL: flag "Invoice amount (${amount}) cannot be verified against time entries
— hourly rate not on file. Add the rate to the invoice record or provide it now to enable this check."

#### Check G: Billing Period Overlap

Check whether another invoice for the same matter has a billing period that overlaps this one:

```sql
SELECT id, billing_period_start, billing_period_end, amount
FROM invoices
WHERE matter_id = ?
  AND id != ?
  AND billing_period_start <= ?   -- other invoice starts before this one ends
  AND billing_period_end   >= ?   -- other invoice ends after this one starts
```

For each overlap: `Invoice #{id} (${amount}, {start}–{end}) overlaps this billing period. An
entry may appear on both invoices.`

#### Check H: Rate Mismatch Across Entries

If the invoice has a stored `hourly_rate`, flag any time entry where the per-entry implied rate
differs by more than 5% — this requires `invoice_line_items` (gated) but can be noted as
unavailable until that table exists. When `invoice_line_items` is present, compute:

```sql
SELECT ili.id, ili.time_entry_id, ili.hours, ili.amount,
       (ili.amount / ili.hours) AS implied_rate
FROM invoice_line_items ili
WHERE ili.invoice_id = ?
  AND ili.hours > 0
  AND ABS((ili.amount / ili.hours) - ?) / ? > 0.05
```

Flag: `Line item #{id} (entry #{te_id}, {hours} hrs): implied rate ${implied_rate:.2f}/hr differs
from invoice rate ${rate}/hr by {pct:.1%}.`

---

## Full Cross-Draft Checks (when `invoice_line_items` exists)

#### Check I: Entries Present in DB but Absent from Draft

```sql
SELECT te.id, te.entry_date, te.hours, te.description
FROM time_entries te
WHERE te.matter_id = ?
  AND te.entry_date BETWEEN ? AND ?
  AND NOT EXISTS (
    SELECT 1 FROM invoice_line_items ili
    WHERE ili.time_entry_id = te.id
      AND ili.invoice_id = ?
  )
```

Flag: `Entry #{id} ({hours} hrs, {entry_date}): recorded in database but not on the draft invoice.`

#### Check J: Line Items on Draft Attributed to Wrong Matter

```sql
SELECT ili.id, ili.time_entry_id, ili.entry_date, ili.hours,
       te.matter_id AS db_matter_id, i.matter_id AS invoice_matter_id
FROM invoice_line_items ili
JOIN invoices i ON i.id = ili.invoice_id
LEFT JOIN time_entries te ON te.id = ili.time_entry_id
WHERE i.matter_id = ?
  AND te.matter_id IS NOT NULL
  AND te.matter_id != i.matter_id
```

Flag: `Line item #{ili_id} ({hours} hrs, {entry_date}): linked time entry #{te_id} is attributed
to matter {db_matter_id} in the database — this invoice is for matter {invoice_matter_id}.`

#### Check K: Invoice Total vs Sum of Line Items

```sql
SELECT i.amount, SUM(ili.amount) AS line_total
FROM invoices i
JOIN invoice_line_items ili ON ili.invoice_id = i.id
WHERE i.id = ?
GROUP BY i.id
```

Flag if `abs(i.amount - line_total) > 0.01`:
`Invoice total (${amount}) does not match sum of line items (${line_total}). Discrepancy: ${diff:.2f}.`

#### Check L: Entries Outside Billing Period

```sql
SELECT id, entry_date, hours, description
FROM time_entries
WHERE matter_id = ?
  AND (entry_date < ? OR entry_date > ?)
  AND EXISTS (
    SELECT 1 FROM invoice_line_items ili
    JOIN invoices inv ON inv.id = ili.invoice_id
    WHERE ili.time_entry_id = time_entries.id
      AND inv.id = ?
  )
```

Flag: `Entry #{id} ({hours} hrs, {entry_date}): date falls outside billing period ({start}–{end})
but appears on this invoice.`

---

## Output Format

Always use this structure:

```
Invoice Review — [Matter Number]: [Matter Description]
Date: [today]
Billing period: [start] to [end] — source: [invoice record / practitioner-supplied / derived from entries]
Data as of: invoices imported [date or "not available"], time entries through [date]

[Data currency warning if applicable]
[Schema prerequisite notices if applicable]

CHECKLIST — [N issues found / No issues found]
──────────────────────────────────────────────

[If issues found:]
  1. [Check type]: [Specific citation with record ID, observed value, and why anomalous]
  2. ...

[If no issues found:]
  No issues detected.

CHECKS PERFORMED
──────────────────────────────────────────────
  ✓ NULL/zero hours ([N] entries; [M] flagged)
  ✓ Statistical outlier detection ([N] entries analyzed; median [X] hrs) [or: skipped — reason]
  ✓ Entry gap detection ([N] gaps checked)
  ✓ Near-duplicate detection
  ✓ Description completeness
  ✓ Invoice amount vs entry hours [or: skipped — hourly rate unknown / invoices table absent]
  ✓ Billing period overlap [or: skipped — invoices table absent]
  — Rate mismatch: not available (invoice_line_items not present)
  — Line-item cross-check: not available (invoice_line_items not present)
  [etc.]
```

**Zero-issues example:**

```
Invoice Review — L3948: Smith v Jones
Date: 2026-04-23
Billing period: 2026-03-01 to 2026-03-31 — source: invoice record
Data as of: invoices imported 2026-04-22, time entries through 2026-04-20

CHECKLIST — No issues found
──────────────────────────────────────────────
No issues detected.

CHECKS PERFORMED
──────────────────────────────────────────────
  ✓ NULL/zero hours (18 entries; 0 flagged)
  ✓ Statistical outlier detection (18 entries analyzed; median 1.2 hrs)
  ✓ Entry gap detection (no gap ≥ 5 days)
  ✓ Near-duplicate detection (no duplicates)
  ✓ Description completeness (all 18 entries have descriptions)
  ✓ Invoice amount ($8,640.00) vs entry hours (48.0 hrs @ $180/hr = $8,640.00) — match
  ✓ Billing period overlap — no overlap found
  — Rate mismatch: not available (invoice_line_items not present)
  — Line-item cross-check: not available (invoice_line_items not present)
```

**Issue example:**

```
CHECKLIST — 4 issues found
──────────────────────────────────────────────

1. [NULL hours] Entry #389 (2026-03-05): hours is NULL — possible recording error.

2. [Outlier — duration] Entry #447 (2.5 hrs, 2026-03-18): 3.1× the median entry duration
   (0.8 hrs) for this matter. Verify this was a multi-session drafting day.

3. [Entry gap] 8-day gap between entry #432 (2026-03-07) and entry #433 (2026-03-15).
   No recorded work during this period. If a CMC or correspondence occurred, add the entry.

4. [Missing description] Entry #441 (1.0 hrs, 2026-03-12): description is blank.
```

## Integration with Other Skills

| Skill | Relationship |
|-------|-------------|
| **practice-data** | Owns schema and path resolution. `invoices` and `invoice_line_items` tables must be added there before the dependent checks are available. |
| **invoice-tracking** | Populates `invoices` and (eventually) `invoice_line_items`. Run this before invoice-reviewing to ensure current data. |
| **retainer-tracking** | Not directly used, but both skills read `matters` — no conflict. |
| **ar-follow-up** | Downstream consumer of `invoices`; shares data source but different purpose. |

## Anti-Patterns

- **Writing to the DB** — this skill is read-only. Any write is a boundary violation.
- **Filtering anomalies by severity** — all flags go to the practitioner. Do not rank or suppress.
- **Omitting record IDs from flags** — "possible duration issue on April 18" is not actionable.
- **Proceeding without staleness check** — always surface data currency before presenting the checklist.
- **Treating absence of `invoices` row as "no invoice"** — it means no data was imported. Say so.
- **Coercing NULL hours to 0** — NULL and zero are different signals; report both, filter both from calculations.
- **Running statistical checks when all entries have identical duration** — median is defined but outlier detection is meaningless; skip and note it.
- **Assuming a billing period when none is specified** — always derive or request it and state the source.
- **Hardcoding column names** — all DB access via the pattern in the Database Access section.
- **Parsing accounting CSVs directly** — data enters only through invoice-tracking.
- **Reporting "no issues" without listing what was checked** — the practitioner cannot assess whether the review was meaningful without knowing what was and wasn't verified.
