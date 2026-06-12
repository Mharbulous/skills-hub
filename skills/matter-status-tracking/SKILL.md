---
name: matter-status-tracking
description: >
  Track and derive the engagement lifecycle status of every client matter — from intake through
  offboarding — using universal signals and configurable policy rules. Use this skill whenever the
  user asks about the current state of a file, which files are active or closing, whether a conflict
  check or retainer agreement is on file, or which matters need engagement lifecycle attention.
  Also use it when downstream skills (executive-assistant, file-prioritization, billing-summary,
  ar-follow-up) need current matter status and the status column in the database may be stale or
  unset. Trigger on phrases like "what's the status of", "which files are active", "do I have a
  retainer agreement on file for", "which matters are closing", or "update the status on".
---

# Matter Status Tracker

Infrastructure skill that owns the engagement lifecycle layer. Derives a status label for every
matter from per-matter signal states evaluated against user-configurable policy rules, then writes
the result back to `matters.status` for downstream consumption. Signals are updated explicitly
(practitioner confirms) or auto-advanced when positive evidence exists and data is fresh; they are
never advanced on absence alone, never advanced on stale data.

## Scope

This skill tracks the client engagement lifecycle — intake, active representation, and offboarding
— using signals that apply universally to every matter regardless of practice area. It does not
track litigation milestones, filing deadlines, or matter-specific planning. See vision.md for the
full litmus test.

## Schema Requirements

**These tables do not yet exist in `practice.db`.** A follow-up handover must request their
addition from `practice-data`, which is the sole owner of schema.

```
matter_signals                          -- per-matter signal state (one row per matter × signal)
  id             INTEGER PRIMARY KEY
  matter_id      INTEGER REFERENCES matters(id)
  signal_key     TEXT NOT NULL          -- e.g. 'conflict_check_completed'
  state          TEXT NOT NULL          -- 'confirmed' | 'unconfirmed' | 'absent'
  confirmed_at   TEXT                   -- ISO 8601; NULL until confirmed
  note           TEXT                   -- optional practitioner note
  UNIQUE (matter_id, signal_key)

status_policies                         -- configurable rules per status label
  id              INTEGER PRIMARY KEY
  status_label    TEXT UNIQUE NOT NULL  -- e.g. 'active'
  required_signals TEXT NOT NULL        -- JSON array of signal keys that must be 'confirmed'
  blocking_signals TEXT                 -- JSON array of signal keys whose 'confirmed' state blocks this label
  auto_advance    INTEGER NOT NULL DEFAULT 1  -- 1 = auto-advance when signals satisfied; 0 = suggest only
  description     TEXT
```

Until these tables exist, queries to `matter_signals` and `status_policies` will fail. Surface the
error — do not fall back to guessing status from other data.

## Status Labels (defaults)

| Label              | Meaning                                                            |
|--------------------|--------------------------------------------------------------------|
| `prospective`      | File opened; conflict check not yet completed                      |
| `intake`           | Conflict check done; retainer agreement not yet signed             |
| `active`           | Retainer agreement signed and deposit received; work in progress   |
| `retainer_warning` | Active matter; retainer balance at or below replenishment threshold |
| `retainer_depleted`| Active matter; retainer balance confirmed zero                     |
| `closing`          | Work substantially complete; representation not yet formally ended  |
| `closed`           | Representation formally ended (off record or file closed)          |
| `declined`         | Conflict identified or matter not accepted                         |

These defaults ship in `status_policies`. The practitioner can modify `auto_advance` and
`required_signals` per label at any time.

## Signals (defaults)

| Signal key                   | Description                                              |
|------------------------------|----------------------------------------------------------|
| `conflict_check_completed`   | Conflict search run and cleared                          |
| `retainer_agreement_signed`  | Signed retainer agreement on file                        |
| `deposit_received`           | Initial retainer deposit confirmed received              |
| `retainer_funded`            | Current trust balance above replenishment threshold      |
| `representation_ended`       | Practitioner formally off record or file closed          |

All signals are tri-state: `confirmed` / `unconfirmed` / `absent`.
- **confirmed** — positive evidence exists (practitioner-confirmed or auto-advanced from fresh DB data)
- **unconfirmed** — signal has not been evaluated for this matter
- **absent** — practitioner has explicitly confirmed the signal artifact does not exist

Absent signal artifact in the DB (e.g., no retainer deposit record) → surface a suggestion and
wait. Never auto-set `absent`.

## Database

All path resolution, schema initialization, and connection setup owned by `practice-data`. See
`../practice-data/SKILL.md`. This skill reads from `matters`, `retainer_notices`, and (when
they exist) `matter_signals` and `status_policies`.

## Workflows

### 1. Evaluate and update status for a single matter

1. Resolve DB path via `practice-data`
2. Read the matter row: `SELECT id, status, last_trust_date FROM matters WHERE file_number = ? OR matt_num = ?`
3. Read all signal rows: `SELECT signal_key, state FROM matter_signals WHERE matter_id = ?`
4. Load policy for each candidate status label from `status_policies`
5. Determine the highest-fidelity matching label (see "Label Resolution" below)
6. If the derived label differs from `matters.status`, update it and report to the practitioner:
   ```sql
   UPDATE matters SET status = ? WHERE id = ?
   ```
   Always show: old status → new status, which signals drove the change, and the timestamp.
7. If the derived label is the same as `matters.status`, confirm to the practitioner that status is current.

### 2. Update a signal for a matter

When the practitioner confirms a signal (e.g., "the retainer agreement is signed for Smith"):

1. Upsert into `matter_signals`:
   ```sql
   INSERT INTO matter_signals (matter_id, signal_key, state, confirmed_at)
   VALUES (?, ?, 'confirmed', ?)
   ON CONFLICT (matter_id, signal_key) DO UPDATE
     SET state = 'confirmed', confirmed_at = excluded.confirmed_at
   ```
2. Re-run Workflow 1 (evaluate and update status) for that matter
3. Report: the signal updated, the old status, the new status

### 3. Bulk evaluate all active matters

When the practitioner asks "update all matter statuses" or the executive assistant triggers a
refresh:

```sql
SELECT id, file_number, matt_num, status FROM matters
WHERE status NOT IN ('closed', 'declined')
ORDER BY file_number
```

For each row, run Workflow 1. Report a summary: how many statuses changed, which labels they moved
from and to, and how many had stale or missing trust data (see Workflow 4 staleness check).

### 4. Auto-advance from retainer data

`retainer_funded` can be auto-advanced from `matters.regular_trust`, but only when the data is
fresh.

**Step 1: Check sign convention.** Read `accounting.csv_mapping.sign_convention` from `coclerk.json`
before interpreting the sign of `regular_trust`. If `sign_convention` is missing or the
`accounting.csv_mapping` key is absent, halt and tell the practitioner:

> "Your accounting sign convention is not configured — I can't safely interpret trust balances. Please run an import with retainer-tracking to set this up."

Do not default to any assumed sign convention.

**Step 2: Check data freshness.** Read `last_trust_date` from the matter row.

- If `last_trust_date` is NULL → data has never been imported. Leave `retainer_funded` `unconfirmed`; tell the practitioner trust balance data is missing for this matter.
- If `last_trust_date` is more than 14 days old → data is stale. Do not auto-advance. Warn:

> "Trust balance for [matter] was last imported [N days ago] — too stale to auto-advance retainer_funded. Import a fresh trust listing to update."

**Step 3: Interpret balance (fresh data only).**

```python
# Only reached after sign_convention confirmed and last_trust_date within 14 days
if sign_convention == 'negative_is_funded':
    is_funded = matter['regular_trust'] is not None and matter['regular_trust'] < 0
    is_depleted = matter['regular_trust'] == 0
else:
    # Other sign conventions: apply the configured mapping
    is_funded = interpret_per_convention(matter['regular_trust'], sign_convention)
    is_depleted = matter['regular_trust'] == 0  # zero is always depleted regardless of convention

if is_funded:
    upsert_signal(matter_id, 'retainer_funded', state='confirmed', confirmed_at=matter['last_trust_date'])
elif is_depleted:
    upsert_signal(matter_id, 'retainer_funded', state='absent', confirmed_at=matter['last_trust_date'])
# None (no row / no import) → leave signal unconfirmed; do not auto-set absent
```

The 14-day staleness threshold is a default; practitioners can configure it in `status_policies`.

## Label Resolution

Evaluate candidate labels in priority order. Apply the first label whose conditions are satisfied:

| Priority | Label              | Condition                                                             |
|----------|--------------------|-----------------------------------------------------------------------|
| 1        | `declined`         | `conflict_check_completed` = confirmed AND practitioner marked declined |
| 2        | `closed`           | `representation_ended` = confirmed                                    |
| 3        | `closing`          | Work-complete flag set (practitioner-only; no auto-advance)           |
| 4        | `retainer_depleted`| `retainer_funded` = absent AND `retainer_agreement_signed` = confirmed |
| 5        | `retainer_warning` | `retainer_funded` = confirmed AND balance ≤ threshold (from policy)   |
| 6        | `active`           | `retainer_agreement_signed` = confirmed AND `deposit_received` = confirmed |
| 7        | `intake`           | `conflict_check_completed` = confirmed                                |
| 8        | `prospective`      | Default — conflict check not yet confirmed                            |

When a required signal is `unconfirmed` (not yet evaluated), surface a suggestion before advancing.
Example: "conflict_check_completed is unconfirmed for Smith [.L3948] — please confirm to advance
from 'prospective' to 'intake'."

## Query Patterns (for downstream skills)

```sql
-- All non-closed active matters (executive-assistant, file-prioritization)
SELECT m.id, m.file_number, m.matt_num, m.description, m.status,
       cl.name AS client_name
FROM matters m
JOIN clients cl ON cl.id = m.client_id
WHERE m.status NOT IN ('closed', 'declined')
ORDER BY m.file_number;

-- Matters requiring lifecycle attention (executive-assistant)
SELECT m.matt_num, m.description, ms.signal_key, ms.state
FROM matter_signals ms
JOIN matters m ON m.id = ms.matter_id
WHERE ms.state = 'unconfirmed'
  AND m.status NOT IN ('closed', 'declined');

-- Matters needing retainer action (ar-follow-up)
SELECT m.file_number, m.matt_num, cl.name, m.description, m.status, m.regular_trust, m.last_trust_date
FROM matters m
JOIN clients cl ON cl.id = m.client_id
WHERE m.status IN ('retainer_warning', 'retainer_depleted')
ORDER BY m.last_trust_date ASC;  -- oldest data first — most likely to need refresh

-- Status distribution (billing-summary, reporting)
SELECT status, COUNT(*) AS count FROM matters GROUP BY status;

-- Matters in a specific status
SELECT m.file_number, m.matt_num, cl.name, m.description
FROM matters m
JOIN clients cl ON cl.id = m.client_id
WHERE m.status = ?;
```

## Consumer Contract

Downstream skills depend on these guarantees:

| Field           | Table            | Guarantee                                                          |
|-----------------|------------------|--------------------------------------------------------------------|
| `status`        | matters          | One of the eight labels above; never NULL for evaluated matters    |
| `signal_key`    | matter_signals   | One of the five default keys; custom keys may exist if configured  |
| `state`         | matter_signals   | Always one of: `confirmed`, `unconfirmed`, `absent`               |

**NULL status (schema not yet migrated):** If `matter_signals` does not exist, `matters.status`
may be NULL or hand-entered. Downstream skills must not silently treat NULL as `prospective` — that
hides the missing-schema condition. Surface it: "matter_signals table is missing — matter status
cannot be evaluated until the schema is updated."

## Anti-Patterns

**Setting status manually** instead of updating signals and re-evaluating. Status labels are
derived; practitioners confirm signals. A manual write bypasses policy and produces a label that
won't survive the next evaluation cycle.

---

**Treating an absent signal artifact as `absent` state.** No deposit record in the DB may mean the
record hasn't been entered yet, not that no deposit was ever made. Auto-setting `absent` on
missing data produces false negatives. Always request practitioner confirmation before writing
`absent`.

---

**Auto-advancing `retainer_funded` without checking `sign_convention`.** If the accounting system
sign convention is unknown or missing from `coclerk.json`, the `regular_trust` sign is ambiguous.
Defaulting to `negative_is_funded` is a silent assumption that will produce wrong status if the
user's system uses the opposite convention. Halt and surface.

---

**Auto-advancing `retainer_funded` on stale trust data.** A trust balance imported 3 weeks ago
reflects conditions at import time. A deposit may have cleared or a cheque bounced since. Silently
advancing status from stale data gives the practitioner false confidence. Always check
`last_trust_date` before auto-advancing; warn if it exceeds the staleness threshold.

---

**Overwriting `matters.status` without reporting the change.** If a status overwrites silently —
especially if it downgrades a matter (e.g., `active` → `retainer_depleted`) due to stale or
incorrect data — the practitioner has no way to catch the error. Always report old → new, which
signals drove the transition, and the data source.

---

**Silently treating NULL status as `prospective`** in downstream consumers. NULL means the
`matter_signals` table doesn't exist yet and the skill has never evaluated this matter — not that
the matter is in the `prospective` state. Treating NULL as `prospective` hides the schema gap.
Surface the missing-table error.

---

**Defining schema in this skill.** All table definitions belong to `practice-data`. This skill
only documents what tables it expects to exist.

---

**Making recommendations.** "You should request a retainer top-up" belongs to
`executive-assistant`. This skill supplies signal states; it does not advise action.

---

**Querying `matter_signals` or `status_policies` without checking they exist first.** Until the
`practice-data` schema is updated, these tables won't exist. Surface the missing-table error
rather than silently falling back or returning empty results.
