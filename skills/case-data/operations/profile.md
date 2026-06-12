# Profile -- Audit and Fill Matter-Level Profile

Ensures the case database has complete matter-level metadata, then delegates proceedings completeness to `operations/proceedings-profile.md`. Downstream consumers expect both matter-level and proceedings gaps to be resolved before drafting forms.

## Step 0: Resolve Matter Pointer

Use the shared pointer-resolution snippet from `SKILL.md`.

Do not read `evidence.sql` for profile or status checks. Query staged SQLite binaries copied from native `case_data_dir`.

## Step 1: Audit Matter Metadata

Use the connection setup from `operations/query.md`, then run:

```python
conn.row_factory = sqlite3.Row
matter_metadata = {
    row["key"]: row["value"]
    for row in conn.execute("SELECT key, value FROM main.matter_metadata").fetchall()
}
```

Matter-level keys expected by downstream workflows:

| Key | Purpose |
|---|---|
| `matter_id` | Stable matter identifier |
| `client_no` | Accounting client number |
| `matter_no` | Accounting matter number |
| `short_name` | Human-readable matter folder label |
| `client_name` | Client display name |
| `filing_lawyer_name` | Lawyer name for court-form signature blocks |
| `filing_lawyer_firm` | Firm name for court-form signature blocks |
| `created` | Date the case-data store was initialized |

Build a gap report for missing or obviously placeholder values.

Example:

```text
Matter-level:
  client_name: "John Duckworth"
  filing_lawyer_name: [MISSING]
  filing_lawyer_firm: [MISSING]
```

## Step 2: Fill Matter-Level Gaps

If gaps exist, inspect matter documents likely to contain the answer, such as pleadings, retainer correspondence, or signature blocks. Present extracted values with citations computed from source file path plus locator. Wait for user confirmation before writing.

Write confirmed values with:

```sql
INSERT OR REPLACE INTO main.matter_metadata (key, value) VALUES (?, ?);
```

Dump after mutation per `operations/maintain.md`.

## Step 3: Delegate Proceedings Completeness

Run `operations/proceedings-profile.md` whenever proceedings are absent or incomplete, or when a downstream skill needs guaranteed complete proceedings metadata.

`profile` does not insert or update proceedings, parties, or proceeding-party rows directly. `proceedings-profile` owns that contract.

## Step 4: Verify

Re-run the matter-metadata query. Then call `operations/proceedings-profile.md` for proceedings verification. Report either:

- `Profile complete`, if both matter-level and proceedings gaps are empty.
- A concise list of remaining gaps and why they could not be filled.
