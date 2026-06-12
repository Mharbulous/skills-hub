---
name: retainer-tracking
description: >
  Import trust balance data from accounting system CSV exports, store retainer balances in the
  practice database, and answer queries about funded or depleted retainers. Use this skill whenever
  the user uploads or mentions a trust listing CSV, asks which files have a depleted or funded
  retainer, wants to check a specific matter's trust balance, or asks to update retainer data.
  Also use it when downstream skills (invoice-tracking, file-prioritization, ar-follow-up) need
  current trust balance data and the database may be stale or empty.
---

# Retainer Tracker

Infrastructure skill that owns the retainer data layer. Ingests trust listing CSV exports from the user's accounting system, normalizes trust data, and stores current retainer balances in `practice.db`. Downstream skills consume this data — none maintain their own copy.

## Scope

This skill tracks *current status only*. Historical trust ledgers, past transactions, reconciliation, and full trust accounting belong elsewhere. 

## Data Source

This skill caches retainer data in `practice.db` for quick access. The source of truth is the user's accounting system — the database is a working copy updated on each import.

Mandatory data fields for this skill:
| clientID | matterID | responsibleLawyer | TrustBalance | LastTrustDate |

Optional additional fields are determined by the user's accounting system. CSV column mappings and system-specific details are stored in `coclerk.json` under `accounting.csv_mapping` (see `practice-data/SKILL.md` for the full schema).

For UNITY® Accounting (by Dye & Durham, formerly esilaw) — the most common accounting system for this skill — read `reference/UnityAccounting.md` for column names, sign convention, date format, and export instructions before mapping or importing.

### Privacy

The `exclude_client_names` flag in `coclerk.json` controls whether client names are stored. When `true`, `clients.name` is `NULL` for all records and the import skips the name column entirely. This is set during the First Import Protocol and can be changed by the user at any time.


## Database

All path resolution, schema, and initialization owned by `practice-data`. See `../practice-data/SKILL.md`.

## Import Workflow

When the user provides a trust listing CSV:

1. Resolve the database path and ensure it exists (run First Use initialization if needed)
2. Check `coclerk.json` for `accounting.system` and `accounting.csv_mapping`
3. **If either is missing:** run the First Import Protocol at `protocols/FirstImport.md` — this handles accounting system identification, privacy briefing, column mapping, and optional export research. After the protocol completes, continue from step 4 below.
4. Load system-specific CSV mapping from `accounting.csv_mapping` in `coclerk.json` — this defines column names, date format, sign convention, and any quirks for that accounting system
5. If `accounting.exclude_client_names` is `true` in `coclerk.json`, skip the client name column and store `NULL` in `clients.name`
6. Parse the CSV with Python's `csv` module
7. For each row:
   a. Parse the trust date using the format specified in `accounting.csv_mapping.date_format` → ISO 8601 date
   b. Upsert the client row on `client_num`
   c. Upsert the matter row on `matt_num`, updating trust columns and `last_trust_date`
   d. Only overwrite `regular_trust` / `last_trust_date` if the CSV date is strictly newer than the stored value (stale data guard)
8. Report: imported count, skipped (stale), depleted (zero balance)

## Queries

All queries executed via `/practice-data` `trust-summary` operation.

| Question | Operation |
|----------|-----------|
| Balance for a specific matter | `trust-summary` filtered to one matter |
| All funded matters | `trust-summary` filtered to funded |
| Depleted matters (balance = 0) | `trust-summary` filtered to depleted |
| Total trust held | `trust-summary` for all funded matters, summed |

Note: Sign convention varies by accounting system (stored in the practice config). Trust balances are presented as positive numbers to the user.

## Integration with Other Skills
- **Task Prioritization** reads `regular_trust` to rank tasks by the retainer-first model
- **Billing Summary** uses `regular_trust` to calculate remaining retainer vs. WIP
- **AR Follow-Up** identifies matters needing retainer replenishment requests



## Anti-Patterns
- **Downstream skill parsing an accounting CSV directly** instead of reading from `practice.db`. All trust data enters through this skill's import workflow.
- **Treating absence as zero balance.** No row = unknown status. `regular_trust = 0` = depleted retainer.
- **Displaying raw negative trust values to the user.** Always `abs(regular_trust)` in output.
