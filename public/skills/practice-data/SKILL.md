---
name: practice-data
user-invocable: false
---

# Practice DB CRUD

Helper skill — not user-invocable. Single source of truth for all direct SQLite operations against the practice database. Owns path resolution, configuration, schema, and initialization. All other skills delegate DB operations here.

## Configuration

Database location is stored in a persistent config file:

```
AppData\Roaming\Coclerk\coclerk.json
```

Resolve this path relative to the current user's home directory. **Never hardcode a username.**

The config file contains:

```json
{
  "version": 1,
  "database": {
    "folder": "<full path to database folder>",
    "filename": "<database filename>"
  },
  "accounting": {
    "system": "<name of user's accounting software, e.g. UNITY, QuickBooks, Clio>",
    "csv_mapping": {
      "csv_report_name": "<name of the trust listing report in the accounting system>",
      "date_format": "<date format used in CSV exports>",
      "sign_convention": "<how trust balances are represented, e.g. negative_is_funded>",
      "column_map": {
        "clientID": "<CSV column name for client number>",
        "matterID": "<CSV column name for matter number>",
        "clientNames": "<CSV column name for client name>",
        "responsibleLawyer": "<CSV column name for responsible lawyer>",
        "TrustBalance": "<CSV column name for trust balance>",
        "lastUpdated": "<CSV column name for last trust date>"
      },
      "quirks": ["<any system-specific parsing notes>"]
    }
  }
}
```

The `csv_mapping` key is populated on first CSV import. If missing, the importing skill examines the CSV headers and asks the user to confirm column mappings, then saves the confirmed mapping here for future imports.

## Accounting System Resolution

Skills that need to know the user's accounting system (e.g. retainer-tracking) must check `coclerk.json` first:

1. Read `accounting.system` from `coclerk.json`
2. **If present:** use the value — do not ask the user again
3. **If missing or `accounting` key absent:** ask the user what accounting system they use, then write the answer back to `coclerk.json` before proceeding

## Path Resolution

On every invocation:

1. Tell the user: "To answer that, I need to look up your practice database. I keep a small config file in your AppData folder that tells me where the database is stored — may I read it?"
2. Resolve `AppData\Roaming\Coclerk\coclerk.json` relative to the user's home directory. **If the user denies access**, respond helpfully: explain that the config file is needed to locate their database, that it contains only a file path and accounting system name (no client data), and offer to try again whenever they're ready. Do not proceed with the skill workflow.
3. **If the config file exists:** read `database.folder` and `database.filename`, join them to get the full database path
4. **If the config file does not exist:** run the initialization protocol at `protocol/initialize.md`
5. For file tool operations (Read/Write/Edit), use the Windows path directly. For bash operations, translate to the sandbox mount path using the session's path mapping
6. If the database folder is not already mounted, tell the user: "Your database is stored in `<folder>`. I'll need access to that folder to look up your data — is that okay?" Then request access via `request_cowork_directory`. **If denied**, explain what the folder contains (only their practice database) and that you can't complete the request without it, but you're happy to try again whenever they're comfortable.

## Auto-Move Enforcement

The database file MUST always be at the path specified in `coclerk.json`. On every resolve:

1. Read `folder` and `filename` from `coclerk.json`
2. If the DB file exists at the configured path — proceed normally
3. If the DB file is NOT at the configured path, check legacy/alternate locations for it
4. If found elsewhere — explain to the user that the database was found at a different location than configured, and that you'd like to move it to the configured path. Move the file (and `.db-wal`, `.db-shm` if present) to the configured path. Report to user: "Moved database from {old} to {new}"
5. If not found anywhere — proceed to initialization (run `protocol/initialize.md`)

## Schema

Authoritative schema definition. No other skill may define tables.

```python
import os, json, sqlite3

# Read config from coclerk.json
config_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Coclerk', 'coclerk.json')
with open(config_path) as f:
    config = json.load(f)

db_folder = config['database']['folder']
db_name = config['database']['filename']
db_path = os.path.join(db_folder, db_name)
os.makedirs(db_folder, exist_ok=True)
conn = sqlite3.connect(db_path)
conn.executescript('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY,
        name TEXT,
        client_num TEXT,
        orig_lawyer TEXT,
        resp_lawyer TEXT,
        type_of_law TEXT,
        major_client TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS matters (
        id INTEGER PRIMARY KEY,
        client_id INTEGER REFERENCES clients(id),
        file_number TEXT UNIQUE,
        matt_num TEXT,
        description TEXT,
        status TEXT,
        orig_lawyer TEXT,
        resp_lawyer TEXT,
        type_of_law TEXT,
        regular_trust REAL,
        term_trust REAL,
        last_trust_date TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS time_entries (
        id INTEGER PRIMARY KEY,
        matter_id INTEGER REFERENCES matters(id),
        entry_date TEXT,
        hours REAL,
        description TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        matter_id INTEGER REFERENCES matters(id),  -- NULL for admin/professional tasks
        task_type TEXT NOT NULL,                    -- 'client', 'admin', 'professional'
        description TEXT NOT NULL,
        time_estimate_hours REAL,
        actual_hours REAL,                          -- filled on completion
        deadline_date TEXT,                         -- ISO 8601; NULL if none
        status TEXT NOT NULL DEFAULT 'open',        -- 'open', 'completed', 'paused'
        created_at TEXT NOT NULL,
        completed_at TEXT                           -- ISO 8601; NULL until done
    );
    CREATE TABLE IF NOT EXISTS retainer_notices (
        id INTEGER PRIMARY KEY,
        matter_id INTEGER NOT NULL REFERENCES matters(id),
        sent_at TEXT NOT NULL,   -- ISO 8601 datetime the notice was sent
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS anchors (
        id INTEGER PRIMARY KEY,
        matter_id INTEGER REFERENCES matters(id),
        anchor_type TEXT NOT NULL,      -- e.g. 'trial_date', 'appeal_date', 'discovery_date', 'act_date'
        anchor_date TEXT NOT NULL,      -- ISO 8601
        status TEXT DEFAULT 'active',   -- 'active', 'conflicted', 'superseded'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS anchor_sources (
        id INTEGER PRIMARY KEY,
        anchor_id INTEGER REFERENCES anchors(id),
        source_document TEXT NOT NULL,  -- e.g. 'Notice of Trial', 'TMC Order 2025-03-14'
        stated_date TEXT NOT NULL,      -- ISO 8601
        source_excerpt TEXT,            -- quoted text where date appears
        status TEXT DEFAULT 'pending',  -- 'confirmed', 'conflicted'
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS deadlines (
        id INTEGER PRIMARY KEY,
        matter_id INTEGER REFERENCES matters(id),
        anchor_id INTEGER REFERENCES anchors(id),  -- NULL for manually entered deadlines
        deadline_type TEXT NOT NULL,    -- e.g. 'witness_list', 'expert_report_plaintiff'
        deadline_date TEXT NOT NULL,    -- ISO 8601
        rule_ref TEXT NOT NULL,         -- e.g. 'Rule 11-6(3)' or 'Order Term 3'
        rule_description TEXT NOT NULL, -- human-readable
        source_type TEXT NOT NULL,      -- 'bc_rules', 'order_term', 'manual'
        source_document TEXT,           -- populated for 'order_term' and 'manual'
        status TEXT DEFAULT 'active',   -- 'active', 'stale', 'superseded'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS payment_in_flight (
        id INTEGER PRIMARY KEY,
        matter_id INTEGER REFERENCES matters(id),
        amount REAL,
        recorded_at TEXT,       -- ISO 8601: when practitioner noted the payment
        expected_clear_by TEXT, -- ISO 8601: recorded_at + clearing window
        cleared INTEGER DEFAULT 0,  -- 0 = pending, 1 = confirmed cleared
        notes TEXT,
        created_at TEXT
    );
''')
conn.close()
```

Idempotent — safe to run every session. On first creation, tell the user: "Created a new practice database."

## Consumer Contract

Downstream skills depend on these guarantees. Changes to column names or semantics are breaking changes.

| Field | Table | Guarantee |
|-------|-------|-----------|
| `matt_num` | matters | Always the raw accounting system value (e.g. `.L3948`) |
| `regular_trust` | matters | Raw value (negative or zero). Never positive. |
| `last_trust_date` | matters | ISO 8601 date string, or NULL if never imported |
| `client_num` | clients | Client number string from accounting system |

**Absence semantics:** No `matters` row for a file = retainer status unknown (not depleted). `regular_trust = 0` = confirmed depleted.

## Operations

Consuming skills delegate all database access here by invoking `/practice-data` with an operation name. This skill resolves the path, connects, executes, and returns results.

### Read Operations

| Operation | Description |
|-----------|-------------|
| matter-lookup | Find a matter by matt_num, file_number, or client name. Returns matter metadata with client info and trust balance. |
| trust-summary | Trust balances — all matters, funded only, depleted only, or a single matter. |
| wip-hours | Unbilled hours per matter from time_entries, optionally filtered by a cutoff date. |
| open-tasks | Open tasks with matter, client, trust, and retainer-notice context. |
| active-deadlines | Active deadlines and anchors for a matter, including conflict status. |
| ar-data | Non-closed matters with trust status, WIP hours, and payment-in-flight state for AR reporting. |

### Write Operations

| Operation | Description |
|-----------|-------------|
| upsert-client-matter | Create or update client and matter records during CSV import. |
| insert-time-entry | Add a time entry to a matter. Returns the new entry's ID. |
| upsert-task | Create or update a task record. |
| complete-task | Mark a task completed with optional actual hours. |
| record-retainer-notice | Record that a retainer replenishment notice was sent. |
| upsert-anchor | Create or update an anchor date with source documentation. Handles conflict detection. |
| upsert-deadline | Create, update, or supersede a derived deadline. |
| manage-payment-in-flight | Record, clear, or query payment-in-flight state. |

## Anti-Patterns

- **Hardcoding a DB path or username** instead of reading from `coclerk.json`
- **Defining schema or CREATE TABLE** in any other skill
- **Bypassing this skill** for direct sqlite3 connection setup
- **Treating absence as zero balance** — no row = unknown, not depleted
- **Copying the live `.db` file with `cp` or file tools** to read it. A raw copy of an open SQLite database can grab pages mid-flush and present as empty/corrupt. Always open the configured path directly with `sqlite3.connect()` — use `sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)` if you only need to read and want to avoid lock contention (OneDrive sync, other processes).
- **Falling back to parsing the source CSV** when the DB read fails. The CSV enters only through the import workflow; querying it directly bypasses the data layer and produces stale or inconsistent answers. Surface the DB error to the user instead.
- **Treating a `disk I/O error` as corruption.** The DB may live in a synced folder (e.g. OneDrive); sync activity, antivirus, or another open handle can produce transient I/O errors. Retry once, then open read-only via URI before concluding the file is damaged.
