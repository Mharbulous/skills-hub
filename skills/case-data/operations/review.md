# Review -- Walk the Lawyer Through Rows Needing Human Judgment

## Scope

The lawyer's review queue is query 05b (`verified = 2` only): rows the AI verifier flagged as genuinely ambiguous. The full `verified = 0` backlog belongs to the verifier, not the lawyer.

## Verified Flag Reference

| Value | Meaning | Set by |
|---|---|---|
| `0` | Unverified - freshly inserted | Ingesting agent |
| `1` | AI-verified - source clearly supports the row | AI verifier agent or lawyer confirmation |
| `-1` | AI-rejected - source contradicts or does not support the row | AI verifier agent or lawyer rejection |
| `2` | Needs human judgment - source validity is ambiguous | AI verifier agent |

The ingesting agent always sets `verified = 0`. The AI verifier handles query 05a in a separate session. The lawyer reviews only query 05b.

## Steps

### 1. Run Query 05b

Execute query 05b from `references/queries.sql` using the connection setup from `operations/query.md`.

### 2. Group Results by Current Table

Group rows by actual v6.2 tables:

- `sources`
- `facts`
- `positions`
- `evidence_links`
- `issues`

For `positions`, include the `position` value in the display so the lawyer sees whether the row is a claim, admission, denial, or silent response.

### 3. Present Each Group

For each row, display:

- table name
- row id
- summary
- current `verified` value
- computed citation if available

Computed citations are built from `sources.file_path` plus the row's `source_locator`. For `evidence_links`, use `evidence_links.source_locator`; for `positions`, use `positions.source_locator`; for `facts`, use `facts.source_locator`.

### 4. Collect Judgment

For each item, ask the lawyer to choose one action:

- Confirm - row is accurate as-is.
- Correct - row has the right idea but wrong content.
- Reject - row is wrong and should remain excluded from current views.
- Delete - row was inserted in error and should be removed.

Prefer Reject over Delete when preserving audit history matters.

### 5. Process Decisions

Confirm:

```sql
UPDATE main.<table> SET verified = 1 WHERE <id_column> = ?;
```

Correct:

```sql
UPDATE main.<table>
SET <content_column> = ?, verified = 1
WHERE <id_column> = ?;
```

Reject:

```sql
UPDATE main.<table> SET verified = -1 WHERE <id_column> = ?;
```

Delete:

```sql
DELETE FROM main.<table> WHERE <id_column> = ?;
```

For `privileged.fact_provenance` rows surfaced by ad hoc review, write through the attached `privileged` schema and preserve the privilege firewall.

### 6. Dump

After processing decisions, run the dump procedure from `operations/maintain.md`.

## Batch Confirmation

If the lawyer says "confirm all" or "looks good," report the count by table before writing. Proceed only after acknowledgment, then update all selected `verified = 2` rows to `verified = 1` and dump.

## Tracking

A growing `verified = 2` backlog means ingestion is outpacing review. Surface the count by table when it grows across sessions.
