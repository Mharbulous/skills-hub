---
name: invoice-tracking
description: >
  Import invoice CSV exports from accounting systems (LEAP, PCLaw, Clio, UNITY, etc.) and store
  normalized invoice state in the practice database. Use when the user uploads or mentions an invoice
  export CSV, asks to import invoices, wants to update invoice records, or asks which matters have
  outstanding invoices. Also use when downstream skills (ar-follow-up, invoice-reviewing) need
  current invoice data and the database may be stale or empty.
---

# Invoice Tracking

Infrastructure skill — owns the invoice data layer. Ingests invoice CSV exports from the user's practice management system, normalizes invoice state, and stores it in the shared practice database. Downstream skills consume this data; none maintain their own copy.

## Scope

This skill tracks **current invoice state only**: invoice number, issue date, amount, amount paid, and status per matter. It does not generate invoices, flag overdue accounts, evaluate billing rates, or make any recommendations — those belong to other skills (invoice-reviewing, ar-follow-up, wip-tracker).

## Schema Extension (Prerequisite)

Invoice-tracking requires an `invoices` table that **must be added to `practice-data/SKILL.md`** before this skill can write data. Until that table exists, imports are unavailable — surface the error rather than working around it.

```sql
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id),
    invoice_number TEXT,
    issue_date TEXT,           -- ISO 8601
    amount REAL,               -- total invoice amount (always positive; see credit note handling below)
    amount_paid REAL,          -- NULL if source doesn't provide it; 0 means confirmed nothing paid
    status TEXT,               -- normalized to lowercase; raw value from accounting system
    last_import_at TEXT,       -- ISO 8601 datetime of the most recent import that touched this row
    created_at TEXT,
    UNIQUE(matter_id, invoice_number)  -- required for upsert; see NULL invoice_number note below
);

CREATE INDEX IF NOT EXISTS idx_invoices_matter_id ON invoices(matter_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
```

**NULL invoice_number:** When a source exports rows without invoice numbers, `UNIQUE(matter_id, NULL)` does not deduplicate — each NULL is treated as distinct. To prevent duplicate rows on re-import: before inserting rows with `invoice_number IS NULL`, delete all existing rows for that `matter_id` where `invoice_number IS NULL`, then insert fresh. Document this in the import report.

**Credit notes / negative amounts:** Some systems export credits as negative-amount invoices. Do not store a negative `amount` — it breaks the contract. Instead, skip the row and include it in the "rows skipped" count with a note: "N rows skipped — negative amounts (credit notes) are not supported."

If the `invoices` table is absent, tell the user: "Invoice-tracking requires a schema update to `practice-data/SKILL.md` before invoices can be imported. Please add the `invoices` table (including the `UNIQUE` constraint) listed in `invoice-tracking/SKILL.md`."

## Consumer Contract

Downstream skills depend on these column names and semantics. Renaming a column or changing its meaning is a breaking change.

| Field | Table | Guarantee |
|-------|-------|-----------|
| `matter_id` | invoices | Foreign key into `matters.id` |
| `invoice_number` | invoices | Raw value from accounting system; may be NULL if export doesn't include it |
| `issue_date` | invoices | ISO 8601 date string, or NULL if not in export |
| `amount` | invoices | Total invoice amount as a positive number; never NULL, never negative |
| `amount_paid` | invoices | Amount received against this invoice; NULL = source didn't provide this column; 0 = confirmed nothing paid |
| `status` | invoices | Normalized to lowercase; raw value from source — not interpreted by this skill |
| `last_import_at` | invoices | ISO 8601 datetime when this row was last written |

**Absence semantics:** No `invoices` row for a matter ≠ no outstanding invoices. It means invoice data has not been imported for that matter. Downstream skills must not treat absence as "paid in full."

**Stale data:** Before acting on invoice data, downstream skills should check `last_import_at`. If the most recent `last_import_at` across all invoices is more than 7 days old, surface: "Invoice data last imported [date]. Results may not reflect recent payments."

**Known status vocabulary:** Accounting systems use varied status labels. Values observed in the wild include: `outstanding`, `paid`, `partial`, `void`, `voided`, `written_off`, `write-off`, `credited`. This list is informational — the skill stores whatever string the source provides (normalized to lowercase). Downstream skills are responsible for deciding which statuses represent AR exposure.

## Database Access

All path resolution and initialization owned by `practice-data/SKILL.md`.

```python
import os, json, sqlite3

config_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Coclerk', 'coclerk.json')
with open(config_path) as f:
    config = json.load(f)
db_path = os.path.join(config['database']['folder'], config['database']['filename'])

# Read-write connection for imports
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Read-only connection for queries
conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
```

## Import Workflow

When the user provides an invoice CSV:

1. Resolve DB path per `practice-data/SKILL.md`. Verify `invoices` table exists — abort with the prerequisite message if not.
2. Check `coclerk.json` for `accounting.invoice_mapping`.
3. **If `invoice_mapping` is missing:** run the **First Import Protocol** below, then continue from step 4.
4. Load column mapping from `accounting.invoice_mapping`.
5. Parse CSV with Python's `csv` module using the confirmed mapping.
6. For each row:
   - Match `matter_id` by looking up `matters.matt_num` or `matters.file_number` from the mapped matter column. If no match, count as skipped.
   - Skip rows with negative `amount` values (credit notes); count separately.
   - Normalize `status` to lowercase.
   - Set `last_import_at` = current ISO 8601 datetime.
   - **If `invoice_number` is NULL:** delete existing NULL-invoice rows for this `matter_id`, then insert fresh (prevents duplicates on re-import).
   - **If `invoice_number` is non-NULL:** upsert on `(matter_id, invoice_number)` — always overwrite with the latest CSV data (the CSV is the source of truth).
7. Report: rows imported, rows skipped (no matter match), rows skipped (credit notes/negative amount), and count of invoices with `status NOT IN ('paid', 'void', 'voided', 'written_off', 'write-off', 'credited')`.
8. If more than 20% of rows were skipped due to no matter match, warn the user: "N rows had no matching matter in the database — verify that matter numbers in the CSV match `matters.matt_num`."

### First Import Protocol

When `accounting.invoice_mapping` is absent:

1. Ask the user what accounting system they use (if not already in `accounting.system`). Write it back to `coclerk.json`.
2. Show the user a sample of the CSV headers (first row).
3. Ask the user to confirm which column maps to each required field:

   | Internal field | Meaning |
   |---|---|
   | `matterID` | Matter or file number matching `matters.matt_num` |
   | `invoiceNumber` | Invoice identifier (mark as `null` if absent) |
   | `issueDate` | Date invoice was sent |
   | `amount` | Total invoice amount |
   | `amountPaid` | Amount paid to date (mark as `null` if absent) |
   | `status` | Invoice status (e.g. outstanding, paid, partial) |

4. Confirm the date format (e.g. `YYYY-MM-DD`, `MM/DD/YYYY`).
5. Write the confirmed mapping to `coclerk.json` under `accounting.invoice_mapping`:

```json
"invoice_mapping": {
  "csv_report_name": "<name of the invoice listing report>",
  "date_format": "<date format>",
  "column_map": {
    "matterID": "<column name>",
    "invoiceNumber": "<column name or null>",
    "issueDate": "<column name>",
    "amount": "<column name>",
    "amountPaid": "<column name or null>",
    "status": "<column name>"
  }
}
```

6. Confirm with the user before proceeding to import.

## Queries

| Question | Action |
|---|---|
| Which matters have outstanding invoices? | Query `invoices` where status is not a closed status, joined to `matters` and `clients`. Surface `last_import_at` if stale. |
| What invoices are on file [matter]? | Query all `invoices` rows for that matter, ordered by `issue_date`. |
| What is the outstanding balance for [matter/client]? | See balance query below. |
| When were invoices last imported? | `SELECT MAX(last_import_at) FROM invoices` |
| Import this invoice CSV | Run import workflow above |

```sql
-- Outstanding invoices per matter
-- "Outstanding" = not paid, not void, not written off, not credited
-- Downstream skills (ar-follow-up) drive this status list; adjust as needed
SELECT
    m.matt_num,
    m.description,
    c.name AS client_name,
    c.client_num,
    COUNT(i.id) AS invoice_count,
    SUM(i.amount - COALESCE(i.amount_paid, 0)) AS outstanding_balance,
    MIN(i.issue_date) AS oldest_invoice_date,
    MAX(i.last_import_at) AS last_import_at
FROM invoices i
JOIN matters m ON m.id = i.matter_id
JOIN clients c ON c.id = m.client_id
WHERE LOWER(i.status) NOT IN ('paid', 'void', 'voided', 'written_off', 'write-off', 'credited')
  AND (m.status IS NULL OR m.status != 'closed')
GROUP BY m.id
ORDER BY MIN(i.issue_date);
```

**Note on `amount_paid`:** When the source doesn't include a payment column, `amount_paid` is NULL. `COALESCE(amount_paid, 0)` treats NULL as zero — meaning no payment recorded, not confirmed unpaid. Downstream skills should be aware that `outstanding_balance` may overstate exposure when `amount_paid` is not tracked.

## Integration with Other Skills

| Skill | Relationship |
|---|---|
| **practice-data** | Owns schema and path resolution. `invoices` table must be added there. |
| **ar-follow-up** | Reads `invoices` to include outstanding amounts in the AR list |
| **invoice-reviewing** | Reads `invoices` to cross-reference against draft billing |
| **retainer-tracking** | Parallel data layer — trust balances and invoice state are separate imports |

## Anti-Patterns

- **Flagging or prioritizing invoices** — this skill stores; ar-follow-up interprets
- **Generating or drafting invoices** — data enters only via user-exported CSV
- **Treating absence as paid** — no row for a matter = no data, not zero balance
- **Treating NULL `amount_paid` as zero** without noting the distinction to consumers
- **Defining CREATE TABLE** in this skill — schema belongs to `practice-data/SKILL.md`
- **Serving stale data silently** — always surface `last_import_at` to downstream skills when it exceeds 7 days
- **Bypassing the column mapping** — never hardcode column names; source format varies by accounting system
- **Filtering write-offs or voids in the storage layer** — status semantics belong to downstream consumers, not here
- **Storing negative amounts** — credit notes from accounting systems must be skipped, not inverted
