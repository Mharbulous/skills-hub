# Promoting a Privileged Source to Main

**When to use:** A `privileged_sources` row that was originally privileged becomes disclosable. Common triggers:
- A draft affidavit is sworn and filed (privilege ends on the unfiled draft; the filed version is now a court document).
- A privileged letter is ordered produced following a successful privilege challenge.
- Counsel decides to waive privilege and rely on the document at trial.

## The two-row pattern (v6)

The `privileged_sources` row is **never deleted**. Instead, INSERT a new row in `main.sources` with the same `file_hash`. The relationship is discoverable via matching `file_hash` values across databases — no cross-database FK is needed.

> **Rationale:** The privileged_sources row is never deleted — the two-row pattern preserves the lineage that proves how the document came to be produced.

```python
con.execute("BEGIN")

# Step 1 — INSERT the main.sources row (same file_hash as privileged row)
con.execute("""
    INSERT INTO main.sources (
        proceeding_id, category, title, date, author,
        description, file_path, file_hash, listed, verified
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
""", (proceeding_id, category, title, date, author,
      desc, file_path, file_hash, listed, ))

con.execute("COMMIT")
```

Dump the database after the transaction (Section 5 of SKILL.md). Report the new `main.sources.source_id` and confirm the `privileged_sources` row remains intact with matching `file_hash`.

## Worked example: draft affidavit sworn and filed

Smith v. Jones — a draft affidavit (`privileged_sources.source_id = 42`, category `'privileged_work_product'`) is sworn by the client and filed as Affidavit #1 on 2026-03-10.

```sql
-- Inside one BEGIN..COMMIT on the ATTACHed connection
BEGIN;

-- Step 1: insert the producible source into main.sources
INSERT INTO main.sources (
    proceeding_id,
    category,
    title,
    date,
    author,
    description,
    file_path,
    file_hash,
    listed,
    verified
) VALUES (
    1,
    'court',
    'Affidavit #1 (Smith)',
    '2026-03-10',
    'Jane Smith',
    'Affidavit of Jane Smith sworn March 10 2026',
    '4. AFFIDAVITS/Smith Aff1 2026-03-10.pdf',
    (SELECT file_hash FROM privileged.privileged_sources WHERE source_id = 42),
    1,                                   -- listed = 1 (on List of Documents)
    0
);

COMMIT;
```

Dump the database after all mutations. Report the new `main.sources.source_id` and confirm `privileged_sources.source_id = 42` remains intact with matching `file_hash`.
