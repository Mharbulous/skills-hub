# Ingest -- Add Sources, Facts, Positions, and Legal Authorities

## Ingestion Rules

These rules apply to every ingestion operation.

1. Resolve the matter pointer first with the shared snippet from `SKILL.md`. This migrates legacy pointers into native `0. CASE DATA` storage when needed.

2. Do not read `evidence.sql` during ingest. It is a dump/rebuild artifact, not the live inspection surface. To check existing records, copy `.sqlite` files from native `case_data_dir` to a fresh temp directory and query SQLite.

3. Set `verified = 0` on every inserted row that has a `verified` column. The verifier runs in a separate session.

4. Store provenance as `source_id` plus `source_locator`. Display citations are computed as `<sources.file_path>#<source_locator>`.

5. Compute `file_hash` from raw file bytes before registering a source. Check duplicates by hash:

```python
import hashlib

def compute_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
```

```sql
SELECT source_id, title, file_path FROM main.sources WHERE file_hash = ?;
```

If a match is found, report the existing source and skip registration unless the user explicitly confirms a duplicate row.

6. Facts are idempotent by exact document location. Before inserting a fact from a source, check whether that same `(source_id, source_locator)` already exists:

```sql
SELECT fact_id FROM main.facts WHERE source_id = ? AND source_locator = ?;
```

Do not auto-merge similar facts across different sources. Similarity can be reported for review, but the ingestion step should not collapse litigation facts by fuzzy text matching.

7. Claims, admissions, denials, and no-knowledge responses are all `main.positions` rows with `position IN ('claim','admit','deny','silent')`.

8. When inserting a new current position for the same `(party_id, fact_id)`, close any current row by setting `valid_to = date('now')`, then insert the new row with `prior_id` pointing to the closed row. Never delete or overwrite position history.

9. Writes touching more than one attached database must run inside one `BEGIN..COMMIT` on a connection with all three databases attached and `PRAGMA journal_mode = DELETE` confirmed.

10. Report every INSERT and UPDATE to the user in the chat turn that performs it.

11. After every mutation, run the dump procedure from `operations/maintain.md`.

---

## Document Type Routing

Determine the document type, then use the matching section below.

| Document type | Section |
|---|---|
| Pleading, amended pleading, petition, response, counterclaim, reply | Ingest a Pleading |
| Discovery transcript | Ingest a Discovery Transcript |
| Client email, lawyer note, internal strategy, privileged correspondence | Ingest an Internal or Privileged Source |
| Notice to Admit response or Rule 7-7 non-response admission | Ingest a Notice to Admit Admission |
| Case law, statute, rule, regulation, treatise, legal test | Ingest a Legal Authority |

---

## Ingest a Pleading

Use for court pleadings and other court-filed documents that assert or respond to facts.

1. Register the document in `main.sources`:

```sql
INSERT INTO main.sources (
    proceeding_id, category, title, description,
    filed_by_party_id, date, file_path, file_hash,
    listed, admissible, last_ingested_at, verified, notes
) VALUES (
    :proceeding_id, 'court', :title, :description,
    :filed_by_party_id, :date, :file_path, :file_hash,
    :listed, :admissible, datetime('now'), 0, :notes
);
```

2. Extract factual assertions from each numbered paragraph. Insert new facts with the source row and paragraph locator:

```sql
INSERT INTO main.facts (
    description, category, date_of_fact,
    source_id, source_locator, verified, notes
) VALUES (
    :description, :category, :date_of_fact,
    :source_id, :source_locator, 0, :notes
);
```

3. Insert positions:

- Originating allegations: `position = 'claim'`.
- Admissions: `position = 'admit'`.
- Denials: `position = 'deny'`.
- No-knowledge or no-position responses: `position = 'silent'`.
- Qualified admissions stay one row with `position = 'admit'` and verbatim qualification text in `qualification`.

```sql
INSERT INTO main.positions (
    fact_id, party_id, position, qualification,
    source_id, source_locator, valid_from,
    prior_id, verified, notes
) VALUES (
    :fact_id, :party_id, :position, :qualification,
    :source_id, :source_locator, :valid_from,
    :prior_id, 0, :notes
);
```

4. If the pleading attaches or identifies proof for a fact, insert an evidence link. Do not create evidence links merely because the pleading is the origin source for a fact.

```sql
INSERT INTO main.evidence_links (
    source_id, fact_id, source_locator,
    strength, verified, notes
) VALUES (
    :source_id, :fact_id, :source_locator,
    :strength, 0, :notes
);
```

5. Dump and report counts for new sources, facts, positions, evidence links, skipped duplicate locators, and all rows left at `verified = 0`.

---

## Ingest a Discovery Transcript

Use for examination for discovery transcripts or other transcript sources.

1. Register the transcript in `main.sources` with `category = 'court'`, `title`, `description`, `date`, `file_path`, `file_hash`, and `verified = 0`.

2. Extract admissions or denials under oath. Insert or reuse facts by `(source_id, source_locator)`.

3. Insert transcript positions with `position = 'admit'`, `position = 'deny'`, or `position = 'silent'` as appropriate. Use line locators such as `p42-L3-L18`.

4. If the transcript introduces exhibits or identifies proof, insert `main.evidence_links` with the transcript source and the relevant locator.

5. Compare transcript positions against current pleading positions for the same fact and party. If the transcript contradicts a current pleading position, record the inconsistency in the new position's `notes`.

6. Dump and report.

---

## Ingest an Internal or Privileged Source

Use this section for client communications, lawyer notes, internal strategy, work product, and other non-public matter materials.

### Routing Decision

Ask: is the document categorically privileged with no current expectation that it will be produced?

| Answer | Destination |
|---|---|
| Yes | `privileged.privileged_sources` |
| No, it may be served or produced | `main.sources` with `category = 'work_product'` and `listed = 0` |
| Unclear | `main.sources` with `category = 'work_product'`, `listed = 0`, and a note explaining the uncertainty |

Routing matters. A producible document in `privileged.privileged_sources` will not appear in evidence-gap queries. A privileged document in `main.sources` risks disclosure.

### Categorically Privileged

Insert in `privileged.privileged_sources`:

```sql
INSERT INTO privileged.privileged_sources (
    proceeding_id, category, title, description,
    author, recipient, date, file_path, file_hash,
    verified, notes
) VALUES (
    :proceeding_id, :category, :title, :description,
    :author, :recipient, :date, :file_path, :file_hash,
    0, :notes
);
```

Valid `category` values are `solicitor_client`, `privileged_correspondence`, `privileged_work_product`, and `other`.

If the privileged source revealed a fact, record privileged provenance:

```sql
INSERT INTO privileged.fact_provenance (
    fact_id, source_id, source_locator, source_note, verified
) VALUES (
    :fact_id, :privileged_source_id, :source_locator, :source_note, 0
);
```

Never link `privileged.privileged_sources` to `main.evidence_links`.

### Potentially Producible Work Product

Register the document in `main.sources` with `category = 'work_product'`, `listed = 0`, `admissible` set if known, and `verified = 0`. If the document later becomes evidence for a fact, add `main.evidence_links` rows at that time.

If a privileged source later becomes producible, create a new `main.sources` row for the producible source and leave the privileged provenance row intact.

---

## Ingest a Notice to Admit Admission

Use this section for BC Supreme Court Civil Rules Rule 7-7 admissions, including admissions arising from failure to respond in time.

1. Register the Notice to Admit or response document in `main.sources` with `category = 'court'`, `title`, `description`, `date`, `file_path`, `file_hash`, and `verified = 0`.

2. For each admitted fact, insert a `main.positions` row:

```sql
INSERT INTO main.positions (
    fact_id, party_id, position, qualification,
    source_id, source_locator, valid_from,
    prior_id, verified, notes
) VALUES (
    :fact_id, :admitting_party_id, 'admit', :qualification,
    :source_id, :source_locator, :effective_date,
    :prior_id, 0, :notes
);
```

Use `notes` to distinguish express admissions from Rule 7-7 non-response admissions. Do not add schema columns for that distinction unless a future design explicitly changes the positions model.

3. Dump and report every inserted position.

---

## Ingest a Legal Authority

Use this section for legal materials in `6. LAW\`: cases, statutes, regulations, rules, treatises, and materials that define legal concepts or criteria.

1. Register the authority in `law.authorities` after hash duplicate detection:

```sql
SELECT authority_id, title, file_path FROM law.authorities WHERE file_hash = ?;
```

```sql
INSERT INTO law.authorities (
    title, citation, authority_type,
    jurisdiction, file_path, file_hash, notes
) VALUES (
    :title, :citation, :authority_type,
    :jurisdiction, :file_path, :file_hash, :notes
);
```

Valid `authority_type` values are `case_law`, `statute`, `regulation`, `treatise`, and `other`.

2. If the authority establishes or shapes a legal concept, insert or reuse `law.legal_concepts`:

```sql
INSERT INTO law.legal_concepts (
    name, concept_type, description, jurisdiction, notes
) VALUES (
    :name, :concept_type, :description, :jurisdiction, :notes
);
```

Valid `concept_type` values are `cause_of_action`, `doctrine`, `test`, `defence`, and `remedy`.

3. Link concept-level authority relationships:

```sql
INSERT INTO law.concept_authorities (
    concept_id, authority_id, relationship, proposition
) VALUES (
    :concept_id, :authority_id, :relationship, :proposition
);
```

Valid `relationship` values are `establishes`, `refines`, `applies`, and `distinguishes`.

4. Extract criteria when the authority states elements or factors:

```sql
INSERT INTO law.legal_criteria (
    concept_id, requirement_type, criterion_order,
    criterion_description, burden_of_proof,
    determined_by_concept_id, authority_id,
    authority_proposition, notes
) VALUES (
    :concept_id, :requirement_type, :criterion_order,
    :criterion_description, :burden_of_proof,
    :determined_by_concept_id, :authority_id,
    :authority_proposition, :notes
);
```

5. Dump and report the authority, concepts, concept-authority links, and criteria inserted.

### Batch Legal Authority Ingestion

When asked to scan `6. LAW\`, iterate files in that folder, compute each hash, skip duplicates already present in `law.authorities`, and report a summary table with file, status, and number of criteria extracted.
