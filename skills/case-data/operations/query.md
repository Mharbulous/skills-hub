# Query -- Run Analytical Queries Against the Case-Data Store

## Connection Setup

Copy `.sqlite` binaries from native `case_data_dir` to a fresh temp directory before opening them. Do not read `evidence.sql` for query or status answers.

```python
import json, os, re, shutil, sqlite3, tempfile

matter_root = '<matter_root>'

def is_abs(path):
    return bool(os.path.isabs(path) or re.match(r'^[A-Za-z]:[\\/]', path) or path.startswith('\\\\'))

def join_rel(root, rel):
    return os.path.normpath(os.path.join(root, *[p for p in re.split(r'[\\/]+', rel) if p]))

def load_pointer(matter_root):
    for path in (os.path.join(matter_root, 'coclerk.json'), os.path.join(matter_root, '9. AI', 'coclerk.json')):
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f)
    raise RuntimeError('coclerk.json not found')

def resolve_case_data_dir(matter_root, stored_path):
    if is_abs(stored_path) and os.path.isdir(stored_path):
        return stored_path
    if not is_abs(stored_path):
        candidate = join_rel(matter_root, stored_path)
        if os.path.isdir(candidate):
            return candidate
    folder = os.path.basename(stored_path.replace('\\', '/').rstrip('/'))
    candidate = os.path.normpath(os.path.join(matter_root, '..', '0. CASE DATA', folder))
    if os.path.isdir(candidate):
        return candidate
    raise RuntimeError(f'Cannot resolve case_data_dir: {stored_path}')

pointer = load_pointer(matter_root)
case_data_dir = resolve_case_data_dir(matter_root, pointer['case_data_dir'])
tmpdir = tempfile.mkdtemp(prefix='case-data-query-')
tmp_paths = {}
for db in ('main', 'law', 'privileged'):
    tmp_paths[db] = os.path.join(tmpdir, f'{db}.sqlite')
    shutil.copy2(os.path.join(case_data_dir, f'{db}.sqlite'), tmp_paths[db])

con = sqlite3.connect(tmp_paths['main'])
con.execute(f"ATTACH DATABASE '{tmp_paths['law']}' AS law")
con.execute(f"ATTACH DATABASE '{tmp_paths['privileged']}' AS privileged")
```

## Available Queries

Read `references/queries.sql` with Codex's host-side Read tool for the full SQL. Validate that it contains `CREATE VIEW IF NOT EXISTS v_current_positions AS` and `@query_17_concepts_by_type_jurisdiction`.

| # | Name | What it answers |
|---|---|---|
| 01 | Denied, no evidence | Facts denied by a party with no current positive evidence link |
| 02 | Universally admitted | Facts with an admit position and no current deny position |
| 03 | COA gap analysis | Criteria for a cause of action with element/factor severity |
| 04 | Witness/source dependencies | Sources that are the sole positive evidence for any fact |
| 05a | AI verification backlog | Rows with `verified = 0` |
| 05b | Human review backlog | Rows with `verified = 2` |
| 06 | Drift detection | Sources with hashes for recompute-and-compare checks |
| 08 | Issue heat map | Issues ranked by linked facts and criteria |
| 09a | Fact position history | Position history for a fact |
| 09b | Fact evidence history | Evidence-link history for a fact |
| 10 | Privileged-only provenance | Facts known only from privileged provenance with no positive evidence link |
| 12 | Unreviewed sources | Sources without ingestion timestamps |
| 13 | Concept requirements | Elements/factors for a legal concept |
| 14 | Concept authorities | Authorities shaping a legal concept |
| 15 | Criterion test hierarchy | Requirements of the test that determines one criterion |
| 16 | COA gap analysis v6.1 alias | Documentation alias for query 03; use query 03 in practice |
| 17 | Concepts by type and jurisdiction | Browse the legal concept catalogue |

## Running a Query

1. Copy the `.sqlite` files from `case_data_dir` to a fresh temp directory and attach all three databases.
2. Execute the relevant SQL from `references/queries.sql`.
3. Format results for the user. For citations, join through `sources` and display `<sources.file_path>#<source_locator>` when a locator exists.

## Ad Hoc Queries

Write SQL against the v6.2 schema. Two views are especially useful:

- `v_current_positions` - current position rows where `valid_to IS NULL AND verified >= 0`.
- `v_fact_status` - one row per fact with a derived `posture` label.

Both views include unverified rows and exclude only rejected rows (`verified = -1`). This keeps active ingestion visible while honoring verifier rejections.

## Posture Values

`v_fact_status.posture` is derived from current `main.positions` rows for the fact.

| Value | Condition | Meaning |
|---|---|---|
| `agreed` | Two different parties both claim the same fact | Both sides assert it |
| `admitted` | Any current admit position exists and no deny position takes priority | Proof may be unnecessary, subject to context |
| `not_denied` | A current silent position exists and no deny/admit priority applies | Not actively disputed yet |
| `disputed` | Any current deny position exists | Must be proven or otherwise resolved |
| `claimed` | A current claim exists with no response posture | Alleged but not answered |
| `unclaimed` | No current positions exist | Fact is recorded but not pleaded or adopted |

The view intentionally does not represent court findings. Court findings are outside the active v6.2 case-data model.

## Example Queries

```sql
-- Facts currently needing proof
SELECT fact_id, description
FROM v_fact_status
WHERE posture = 'disputed';

-- Facts admitted or agreed on current posture
SELECT fact_id, description
FROM v_fact_status
WHERE posture IN ('admitted', 'agreed');

-- Current positions for a specific fact
SELECT p.position, pa.name AS party, s.file_path, p.source_locator
FROM v_current_positions p
JOIN main.parties pa ON pa.party_id = p.party_id
LEFT JOIN main.sources s ON s.source_id = p.source_id
WHERE p.fact_id = :fact_id;
```

## Legal Taxonomy Queries

Queries 13-17 operate against `law.sqlite`.

### Query 13: Concept Requirements

Lists all elements/factors for a legal concept.

Parameter: `? = concept_id`.

Rows with `requirement_type = 'element'` are mandatory. Rows with `requirement_type = 'factor'` are weighed considerations.

### Query 14: Concept Authorities

Lists authorities that establish, refine, apply, or distinguish a concept.

Parameter: `? = concept_id`.

### Query 15: Criterion Test Hierarchy

Expands one level of nesting for a criterion that is determined by a legal test.

Parameter: `? = criterion_id`.

Use when an element such as duty of care points to a determining test through `law.legal_criteria.determined_by_concept_id`.

### Query 16: COA Gap Analysis Alias

Query 16 is documentation-only. Query 03 already implements the v6.1/v6.2 element-vs-factor gap analysis.

Parameter for query 03: `? = coa_id`.

### Query 17: Concepts by Type and Jurisdiction

Browses `law.legal_concepts` by `concept_type` and `jurisdiction`.

Parameters: `?1 = concept_type`, `?2 = jurisdiction`.
