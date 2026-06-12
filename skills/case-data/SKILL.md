---
name: case-data
description: Sole access to CRUD operations for case data - parties, proceedings, sources, facts, issues, evidence, and legal authorities
---

## Operation Routing

Determine which operation the user needs and read the corresponding file.

| User intent | Operation | File |
|---|---|---|
| "Set up an evidence database" / new matter with no `coclerk.json` | Initialize | `operations/initialize.md` |
| "Ingest this pleading/transcript/document" | Ingest | `operations/ingest.md` |
| "Log this client email / lawyer note / internal document" | Ingest (internal) | `operations/ingest.md` |
| "Opposing counsel disputes privilege / challenges admissibility" | Deferred design review | `references/deferred/` memo listed below |
| "What proceedings are in this matter?" / another skill needs proceedings metadata | Proceedings Profile | `operations/proceedings-profile.md` |
| "Check proceedings profile" / "what's missing?" / downstream form-drafting needs profile | Profile | `operations/profile.md` |
| "Show me denied facts without evidence" / analytical question | Query | `operations/query.md` |
| "Review unverified rows" / "what needs my review" | Review | `operations/review.md` |
| "Dump the database" / "rebuild from dump" | Maintain | `operations/maintain.md` |
| "Extract facts from new documents" / "scan for new docs" | Extract Facts | `operations/extract-facts.md` |
| "Ingest this case law / statute / legal authority" / scan 6. LAW/ folder | Ingest (legal authority) | `operations/ingest.md` |

Read **only** the file for the identified operation. In Codex Cowork, use the inline code in that operation file; do not run, import, copy, or stage files from `references/scripts/`.

---

## Shared Conventions

These apply to all operations.

For terminology, domain-definition, documentation, or ambiguity questions, read `CONTEXT.md` in this directory before answering or editing docs. Do not read it for routine CRUD operations unless terminology affects the operation.

If you do not have access to a folder you need, request access from the user.  

Active operation files are v6.2-only. Historical v5/v6 compatibility notes live in ADRs and planning documents, not in executable operation instructions. Do not create retired tables or use retired schema names such as `core`, `ev`, `documents`, `evidence_items`, `legal_authorities`, or `authority_propositions`.

### Matter pointer resolution

Every operation starts by resolving the matter pointer with inline code. `coclerk.json` points from the matter folder to the native case-data store.

```python
import json, os, re, shutil, sqlite3
from datetime import date

CASE_DATA_FOLDER = '0. CASE DATA'
MATTER_ARTIFACTS_REL = '9. AI'
DUMP_DIR_REL = os.path.join('4. LAWYER BRIEF', 'CoWork')
POINTER_FILENAME = 'coclerk.json'
DBS = ('main', 'law', 'privileged')

def pointer_candidates(matter_root):
    return [
        os.path.join(matter_root, POINTER_FILENAME),
        os.path.join(matter_root, MATTER_ARTIFACTS_REL, POINTER_FILENAME),
    ]

def is_abs(path):
    return bool(os.path.isabs(path) or re.match(r'^[A-Za-z]:[\\/]', path) or path.startswith('\\\\'))

def join_rel(root, rel):
    return os.path.normpath(os.path.join(root, *[p for p in re.split(r'[\\/]+', rel) if p]))

def case_data_root(matter_root):
    return os.environ.get('COCLERK_CASE_DATA_ROOT') or os.path.join(
        os.path.dirname(os.path.normpath(matter_root)), CASE_DATA_FOLDER
    )

def sanitize(name):
    return re.sub(r'[:<>"/\\|?*]', '', name).rstrip('. ')[:60]

def make_case_data_dir(matter_root, matter_id, short_name):
    folder_name = f'{matter_id} {sanitize(short_name)}' if matter_id else sanitize(short_name)
    return os.path.join(case_data_root(matter_root), folder_name)

def read_matter_metadata(db_path):
    if not os.path.exists(db_path):
        return {}
    con = sqlite3.connect(db_path)
    try:
        exists = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='matter_metadata'"
        ).fetchone()
        if not exists:
            return {}
        return {key: value for key, value in con.execute("SELECT key, value FROM matter_metadata")}
    finally:
        con.close()

def migrate_legacy_dbs(matter_root, provisional_dir):
    old_dir = join_rel(matter_root, MATTER_ARTIFACTS_REL)
    os.makedirs(provisional_dir, exist_ok=True)
    for db in DBS:
        src = os.path.join(old_dir, f'{db}.sqlite')
        dst = os.path.join(provisional_dir, f'{db}.sqlite')
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.move(src, dst)
    metadata = read_matter_metadata(os.path.join(provisional_dir, 'main.sqlite'))
    final_dir = make_case_data_dir(
        matter_root,
        metadata.get('matter_id'),
        metadata.get('short_name') or os.path.basename(os.path.normpath(matter_root)),
    )
    if final_dir != provisional_dir and os.path.exists(os.path.join(provisional_dir, 'main.sqlite')):
        os.makedirs(os.path.dirname(final_dir), exist_ok=True)
        if not os.path.exists(final_dir):
            os.rename(provisional_dir, final_dir)
        else:
            for db in DBS:
                src = os.path.join(provisional_dir, f'{db}.sqlite')
                dst = os.path.join(final_dir, f'{db}.sqlite')
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.move(src, dst)
    return final_dir

def target_case_data_dir(matter_root, pointer):
    stored = pointer.get('case_data_dir')
    if stored and stored not in (MATTER_ARTIFACTS_REL, f'{MATTER_ARTIFACTS_REL}\\'):
        if is_abs(stored):
            return stored
        return join_rel(matter_root, stored)
    metadata = pointer.get('matter_metadata') or {}
    folder_name = os.path.basename(os.path.normpath(matter_root))
    match = re.match(r'^(\d+\.[A-Za-z0-9][A-Za-z0-9-]*|\.?[A-Za-z]\d+[A-Za-z0-9-]*)\b', folder_name)
    matter_id = metadata.get('matter_id') or (match.group(1).lstrip('.') if match else None)
    short_name = metadata.get('short_name') or os.path.basename(os.path.normpath(matter_root))
    return make_case_data_dir(matter_root, matter_id, short_name)

def resolve_pointer(matter_root):
    pointer_path = next((p for p in pointer_candidates(matter_root) if os.path.exists(p)), None)
    if not pointer_path:
        raise RuntimeError('coclerk.json not found; initialize the matter first')
    with open(pointer_path, encoding='utf-8') as f:
        pointer = json.load(f)
    case_data_dir = target_case_data_dir(matter_root, pointer)
    stored = pointer.get('case_data_dir')
    if stored in (MATTER_ARTIFACTS_REL, f'{MATTER_ARTIFACTS_REL}\\'):
        case_data_dir = migrate_legacy_dbs(matter_root, case_data_dir)
    else:
        os.makedirs(case_data_dir, exist_ok=True)
    pointer = {
        'schema_version': 3,
        'case_data_dir': case_data_dir,
        'evidence_sql_path': pointer.get('evidence_sql_path', os.path.join(DUMP_DIR_REL, 'evidence.sql')),
    }
    with open(pointer_path, 'w', encoding='utf-8') as f:
        json.dump(pointer, f, indent=2)
    return pointer

matter_root = '<matter_root>'  # workspace folder
pointer = resolve_pointer(matter_root)
case_data_dir = pointer['case_data_dir']
```

If pointer resolution fails, report the error to the user and halt.

**`coclerk.json` example:**
```json
{
  "schema_version": 3,
  "case_data_dir": "C:\\Users\\Brahm\\Logica Law\\Litigation - Documents\\0. CASE DATA\\4165.L153 Example Matter",
  "evidence_sql_path": "4. LAWYER BRIEF\\CoWork\\evidence.sql"
}
```

**Resolution order:**
1. Read `coclerk.json` from the matter root.
2. Otherwise read `9. AI\coclerk.json` for current matters.
3. If `case_data_dir` points to `9. AI`, move the closed `.sqlite` binaries to `0. CASE DATA\<matter>` and update the pointer. Folder names may start with the accounting matter number (`L153`) rather than the client number; if `main.matter_metadata` is present, use it after the move to name the native folder.
4. If no pointer exists, initialize the matter.

**Where the files live:**

| File | Location |
|------|----------|
| `coclerk.json` (pointer) | matter root or `9. AI\coclerk.json` |
| `main.sqlite`, `law.sqlite`, `privileged.sqlite` | native `0. CASE DATA\<matter>\` |
| `evidence.sql` (text dump) | `4. LAWYER BRIEF\CoWork\evidence.sql` |

Matter identity lives in `main.sqlite.matter_metadata`, not in `coclerk.json`.
During first initialization only, inline initialization code derives transient `matter_metadata` so `main.sqlite` can be seeded. Existing matters whose pointer references `9. AI` are migrated on first use.

### Database connection pattern

Every read or write opens the copied `main.sqlite` as the primary connection and attaches the other databases:
```sql
ATTACH DATABASE 'law.sqlite'        AS law;
ATTACH DATABASE 'privileged.sqlite' AS privileged;
```

Every connection runs `PRAGMA journal_mode = DELETE` — WAL breaks cross-database atomicity.

### FUSE mount note

SQLite binaries never live in the matter folder. All build and mutation operations stage `.sqlite` files in a fresh temp directory, close every connection, then copy or move the closed binaries into native `case_data_dir`. Plain-text writes for `coclerk.json` and `evidence.sql` are safe.

Do not read `evidence.sql` to inspect current database state during ingest, profile, query, review, or status checks. It is a text dump artifact: write it after mutations, and read it only for the Maintain/Rebuild operation or when the user explicitly asks to inspect or repair the dump. To check what is in the matter database, copy the `.sqlite` files from native `case_data_dir` to a fresh temp directory and query SQLite.

Do not execute, import, copy, or stage Python source from `references/scripts/` in Codex Cowork. Python's source loader and ordinary file reads can hit the same stale FUSE size bug and produce truncated code. Use inline code from the operation file instead.

Critical text reads of `schema.sql`, `triggers.sql`, `queries.sql`, and `evidence.sql` should use Codex's host-side Read tool before the text is used in inline code. For `evidence.sql`, this applies only to Maintain/Rebuild or explicit dump inspection. Do not copy text files to a temp directory as a truncation workaround; the copy can inherit stale FUSE size metadata. Temp staging remains required for SQLite binaries, and every staged database connection must assert `PRAGMA journal_mode = DELETE` because WAL breaks cross-database atomicity.

### Paragraph reference format

`para. <N>`, `para. <N>(a)`, `p<page>-L<start>-L<end>`.

### Source locator and citation format

Store source provenance as a `source_id` foreign key plus a `source_locator` pinpoint. Do not store a combined `source_ref` column in v6.2 tables.

When displaying a citation to the user, compute it from the source row:

```text
<sources.file_path>#<source_locator>
```

Examples:

| Stored fields | Display citation |
|---|---|
| `source_id -> sources.file_path = "5. COURT FILE/NOCC.pdf"`, `source_locator = "para. 14"` | `5. COURT FILE/NOCC.pdf#para. 14` |
| `source_id -> sources.file_path = "7. DISCOVERY/EFD-Smith.pdf"`, `source_locator = "p42-L3-L18"` | `7. DISCOVERY/EFD-Smith.pdf#p42-L3-L18` |

### Schema phases

Not all tables need data immediately — the system is useful from the moment Phase 1 tables are populated:

| Phase | Scope | Tables |
|-------|-------|--------|
| **Phase 1** (minimum viable) | `main` — proceedings, parties, sources, facts, positions, evidence_links | |
| **Phase 2** (law taxonomy + case application) | `law` — authorities, legal_concepts, concept_authorities, legal_criteria; `main` — causes_of_action, coa_criteria, criteria_facts | |
| **Phase 3** (strategic) | `main` — issues, issue_facts, issue_criteria | |

### Database files (v6.2 schema)

| Database | Tables | Contents |
|----------|--------|----------|
| **main.sqlite** | 14 | matter_metadata, proceedings, parties, proceeding_parties, sources, facts, positions, evidence_links, causes_of_action, coa_criteria, criteria_facts, issues, issue_facts, issue_criteria |
| **law.sqlite** | 4 | authorities, legal_concepts, concept_authorities, legal_criteria |
| **privileged.sqlite** | 2 | privileged_sources, fact_provenance |

6 cross-database FK trigger pairs enforce referential integrity across ATTACH boundaries (see `triggers.sql`).

### Valid enum values

| Column | Values |
|--------|--------|
| `legal_concepts.concept_type` | cause_of_action, doctrine, test, defence, remedy |
| `legal_criteria.requirement_type` | element, factor |
| `concept_authorities.relationship` | establishes, refines, applies, distinguishes |
| `positions.position` | claim, admit, deny, silent |
| `sources.category` | court, correspondence, production, work_product, disbursements |
| `privileged_sources.category` | solicitor_client, privileged_correspondence, privileged_work_product, other |

---

## Deferred Design Capital

Some schema changes were considered during v6.1 design but deferred because the current matter (Duckworth v. Pathfinder) does not exercise the case they solve. Each deferred item is preserved as a **problem+insight memo** — not a spec — so future Codex can reconstruct the reasoning when a real trigger arrives and then design fresh against the then-current schema.

When you recognize one of the situations described below, read the named memo, absorb the rationale, then draft an implementation against the current schema. Do not copy the memo's "Direction" section into a plan verbatim — it is non-binding and may be stale relative to the schema as it exists when you read it.

### Memos

| Memo path | Semantic trigger (practice language) |
|---|---|
| `references/deferred/judicial-notice-semantics.md` | A user asks "which eligible-for-judicial-notice facts have not yet been noticed?"; the court takes judicial notice of a fact on the record and the user wants to record that event distinctly from eligibility; a pleading specifically invokes judicial notice. |
| `references/deferred/counterclaim-asymmetry.md` | Any matter with a counterclaim, response to counterclaim, or third-party notice (common in defended actions); a user asks about posture of a fact against a party-by-counterclaim; the same fact has different response postures across proceedings. |
| `references/deferred/hearsay-foundation-tagging.md` | Opposing counsel challenges a specific document's admissibility on hearsay grounds; a voir dire is scheduled on admissibility; counsel needs structured records of the exception claimed and its foundation materials. *(Needs v6 revision — formerly referenced `evidence_items` table, now eliminated.)* |
| `references/deferred/real-evidence-chain-of-custody.md` | A matter involves real/physical evidence and counsel needs to record chain of custody; opposing counsel challenges the integrity of a physical exhibit; a real evidence item has been held by multiple custodians. *(Needs v6 revision — formerly referenced `evidence_items.evidence_type = 'real'`, now eliminated.)* |
| `references/deferred/adr-event-tracking.md` | A mediation produces a partial settlement resolving some but not all facts; counsel needs to record the mediation event (date, mediator, outcome) separately from the per-fact position consequences; a matter has multiple ADR events with distinct outcomes. |

### How this section works

Skills do not auto-scan subdirectories. This section is the discovery layer: it enumerates every memo so routing decisions can find them at ingestion or query time. If a memo is added to `references/deferred/` without a row being added here, that memo will never fire.
