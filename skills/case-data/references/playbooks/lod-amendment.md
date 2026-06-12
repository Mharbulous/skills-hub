# LOD Amendment Workflow

**When to use:** A document's list position changes — a source needs to be added to or removed from the List of Documents. In v6, LOD status is tracked via the `listed` boolean on `main.sources` and LOD amendment history is tracked via bitemporal supersession on `evidence_links`.

## Updating listed status

When a source is added to or removed from the List of Documents, update its `listed` flag:

```sql
UPDATE main.sources
SET listed = 1   -- or 0 to remove from LOD
WHERE source_id = :source_id;
```

## Superseding an evidence_links row

When an evidence link's assessment changes (e.g., strength re-evaluated after LOD amendment):

> **Rationale:** `evidence_links` uses bitemporal supersession. The old row gets `valid_to` set; a new row is inserted with `prior_id` pointing back. Views filter on `valid_to IS NULL` to show only current links.

```sql
BEGIN;

-- 1. Find the current row for this evidence link
SELECT link_id
FROM main.evidence_links
WHERE source_id = :source_id AND fact_id = :fact_id AND valid_to IS NULL;

-- 2. Supersede the current row
UPDATE main.evidence_links
SET valid_to = date('now')
WHERE link_id = :current_link_id;

-- 3. Insert successor with prior_id pointing at superseded row
INSERT INTO main.evidence_links (
    source_id, fact_id, strength, notes,
    prior_id, valid_from, verified
) VALUES (
    :source_id, :fact_id, :new_strength, :notes,
    :current_link_id,   -- prior_id — points at the row we just superseded
    date('now'), 0
);

COMMIT;
```

Dump the database after the transaction.
