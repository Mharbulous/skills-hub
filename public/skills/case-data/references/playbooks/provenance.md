# Recording Investigative Provenance from a Privileged Source

**When to use:** A privileged source (e.g., a client email, a lawyer's notes from a meeting) reveals or is the direct source of a fact in `facts`. Log the link so the file record shows *how* the fact was discovered, even though the source itself cannot be disclosed.

## Steps

**INSERT into `fact_provenance`.**

```sql
INSERT INTO privileged.fact_provenance (
    fact_id,
    source_id,
    source_note
) VALUES (
    <fact_id>,
    <source_id>,
    '<brief note on how the document supports or reveals the fact>'
);
```

Dump the database.

> **Rationale:** This row records investigative provenance only — NOT admissible proof. The fact still needs an admissible source linked via `evidence_links` before it can be used at trial. Until that admissible link exists, the fact will surface in gap queries as requiring follow-up.

## Worked example: client email reveals a key fact

Smith v. Jones — a client email (`privileged_sources.source_id = 8`) discloses that the defendant was aware of the defect before the accident. This is recorded as fact_id 31 ("Defendant had prior knowledge of defect"). Until a main.sources row confirming the same fact is linked via `evidence_links`, the fact is admissible-source-free.

```sql
-- Link the privileged source to the fact
INSERT INTO privileged.fact_provenance (
    fact_id,
    source_id,
    source_note
) VALUES (
    31,
    8,
    'Client email dated 2025-09-12 states defendant notified in writing of defect one week before accident'
);
-- Dump
```

Fact 31 will now appear in gap queries under "provenance only." It will remain there until an admissible substitute — for example, a witness statement from the client, or a business record of the defendant's notification — is inserted into `main.sources` and linked to fact 31 via `evidence_links`. At that point, the gap query will no longer flag it.
