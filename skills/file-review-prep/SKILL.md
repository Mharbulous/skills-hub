---
name: file-review-prep
description: >
  Assemble a complete, sourced briefing for a single client matter immediately before the
  practitioner engages with it — before a client call, file review, or task queue item.
  Use when the practitioner says "brief me on", "what's the situation with", "pull up the
  file for", "prep me for [client/matter]", "what do I need to know about [file]", or
  invokes the skill by name. Also trigger when a matter identifier is mentioned in the
  context of an upcoming call or review and no other skill is a better fit.
user-invocable: true
---

# File Review Prep

Pure read-only synthesizer. Assembles a structured, sourced briefing for one matter from the
shared practice database: matter status, retainer picture, open tasks, approaching deadlines,
and AR state. Never writes, never recommends, never owns state.

## Data Sources

| Section | Tables read | Notes |
|---------|-------------|-------|
| Matter identity | `matters`, `clients` | Always present |
| Engagement status | `matter_signals`, `status_policies` | May not exist yet — surface gap per-section |
| Retainer | `matters.regular_trust`, `matters.last_trust_date` | Sign convention required |
| Open tasks | `tasks` | Always present |
| Deadlines | `anchors`, `deadlines` | May not exist yet — surface gap per-section |
| AR state | `retainer_notices`, `payment_in_flight` | `payment_in_flight` may not exist yet |

## Database Access

Path resolution, config reading, and access explanation all follow `../practice-data/SKILL.md`
exactly — use that protocol for locating the DB and explaining the access request to the user.

This skill always opens the database read-only to avoid lock contention:

```python
conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
```

## Workflow

1. Resolve DB path and explain the access request per `practice-data/SKILL.md`
2. Identify the matter (see Matter Lookup below)
3. Run each section query independently — a failure in one section does not block others
4. Render the briefing using the Output Template below

### Matter Lookup

Match against `matters.matt_num`, `matters.file_number`, or `clients.name` (case-insensitive
LIKE). If multiple matters match, list them and ask the practitioner to confirm before
proceeding.

```sql
SELECT m.id, m.file_number, m.matt_num, m.description, m.status,
       m.regular_trust, m.last_trust_date,
       c.name AS client_name, c.client_num
FROM matters m
JOIN clients c ON c.id = m.client_id
WHERE m.matt_num = ?
   OR m.file_number = ?
   OR c.name LIKE '%' || ? || '%'
```

If no row matches, tell the practitioner: "No matter found matching '[input]'. Check the file
number or client name and try again."

## Section Queries

Run each query in its own try/except. When a required table does not exist, note the gap in
that section and continue.

### Matter Identity and Status

```python
# Always available — no try/except needed for this block
matter_row = conn.execute(
    "SELECT m.id, m.file_number, m.matt_num, m.description, m.status, "
    "       c.name AS client_name, c.client_num "
    "FROM matters m JOIN clients c ON c.id = m.client_id WHERE m.id = ?",
    (matter_id,)
).fetchone()
```

For engagement lifecycle signals:

```python
try:
    signals = conn.execute(
        "SELECT signal_key, state, confirmed_at FROM matter_signals WHERE matter_id = ?",
        (matter_id,)
    ).fetchall()
    policies = conn.execute("SELECT * FROM status_policies").fetchall()
    signals_available = True
except sqlite3.OperationalError:
    signals_available = False  # surface in output: "[Status signals not available — matter_signals table not yet migrated]"
```

### Retainer Picture

Check sign convention before interpreting `regular_trust`:

```python
sign_convention = config.get('accounting', {}).get('csv_mapping', {}).get('sign_convention')
if not sign_convention:
    retainer_note = "[Retainer balance cannot be shown — sign convention not configured in coclerk.json. Run a retainer-tracking import to set this up.]"
else:
    balance_raw = matter_row['regular_trust']
    last_date = matter_row['last_trust_date']
    if balance_raw is None or last_date is None:
        retainer_note = "No trust import on file"
    else:
        from datetime import date
        days_old = (date.today() - date.fromisoformat(last_date)).days
        if sign_convention == 'negative_is_funded':
            balance_display = f"${abs(balance_raw):,.2f} (funded)" if balance_raw < 0 else "$0.00 (depleted)"
        else:
            retainer_note = f"[Retainer balance cannot be shown — unrecognised sign_convention '{sign_convention}' in coclerk.json. Supported: 'negative_is_funded'.]"
            balance_display = None
        if balance_display is not None:
            # Staleness threshold: 14 days is a heuristic chosen to prompt the practitioner to weigh data age.
            freshness = f"imported {last_date}, {days_old} days ago"
            if days_old > 14:
                freshness += " ⚠ approaching stale"
            retainer_note = f"{balance_display} — {freshness}"
```

### Open Tasks

```sql
SELECT t.id, t.description, t.task_type, t.deadline_date, t.status, t.created_at
FROM tasks t
WHERE t.matter_id = ?
  AND t.status = 'open'
ORDER BY (t.deadline_date IS NULL), t.deadline_date ASC, t.created_at ASC
```

### Deadlines

```python
try:
    anchors = conn.execute(
        "SELECT anchor_type, anchor_date, status FROM anchors WHERE matter_id = ? AND status = 'active'",
        (matter_id,)
    ).fetchall()
    deadlines = conn.execute(
        "SELECT deadline_type, deadline_date, rule_ref, rule_description, status "
        "FROM deadlines WHERE matter_id = ? AND status = 'active' ORDER BY deadline_date ASC",
        (matter_id,)
    ).fetchall()
    deadlines_available = True
except sqlite3.OperationalError:
    deadlines_available = False  # surface in output: "[Deadlines not available — dates-and-deadlines schema not yet migrated]"
```

### AR State

```python
notices = conn.execute(
    "SELECT sent_at FROM retainer_notices WHERE matter_id = ? ORDER BY sent_at DESC",
    (matter_id,)
).fetchall()

try:
    pif = conn.execute(
        "SELECT amount, recorded_at, expected_clear_by FROM payment_in_flight "
        "WHERE matter_id = ? AND cleared = 0 AND expected_clear_by >= date('now')",
        (matter_id,)
    ).fetchone()
    pif_available = True
except sqlite3.OperationalError:
    pif = None
    pif_available = False
```

## Output Template

Use this exact structure every time. Every data point includes its source and freshness.
Sections with missing upstream tables show an explicit note — never silently omit.

```
File Briefing — [client_name] ([client_num]) / [matt_num]
[description]
Generated: [today's date]

─── MATTER STATUS ────────────────────────────────────────────────────────────
Status:  [matters.status, or "not set"]
Signals: [list of signal_key: state (confirmed_at) per matter_signals row]
         OR: [Status signals not available — matter_signals table not yet migrated]

─── RETAINER ─────────────────────────────────────────────────────────────────
Balance: [amount] ([sign convention applied]) — imported [last_trust_date], [N] days ago
         [⚠ approaching stale — over 14 days] (if applicable)
         OR: [No trust import on file]
         OR: [Retainer balance cannot be shown — sign convention not configured in coclerk.json]

─── OPEN TASKS ───────────────────────────────────────────────────────────────
[For each task:]
  • [description]
    Type: [task_type] | Created: [created_at] | Deadline: [deadline_date or "none"]
[If no open tasks:] No open tasks on file.

─── DEADLINES ────────────────────────────────────────────────────────────────
Anchors:
  [anchor_type]: [anchor_date] (status: [status])
  OR: [No anchor dates on file]

Derived deadlines:
  [deadline_date] — [deadline_type]: [rule_description] ([rule_ref])
  OR: [No derived deadlines on file]
  OR: [Deadlines not available — dates-and-deadlines schema not yet migrated]

─── AR STATE ─────────────────────────────────────────────────────────────────
Retainer notices sent: [count]
  Last sent: [sent_at of most recent notice, or "none"]
Payment-in-flight: [amount, recorded_at, expected_clear_by]
                   OR: [None recorded]
                   OR: [Payment-in-flight tracking not available — payment_in_flight table not yet migrated]
```

## Anti-Patterns

**Writing to the database.** This skill is called immediately before engaging with a file —
any side-effect write at that moment is dangerous. All five output sections are display artifacts.
If a section looks like it should trigger a DB update (e.g., a status change), it doesn't — that
is `matter-status-tracking`'s job.

---

**Appending recommendations.** "Suggested next step: send a retainer replenishment notice" belongs
to `executive-assistant`. The briefing surfaces what is true; the practitioner decides what to do.
Even phrasing like "needs attention" edges into recommendation territory — avoid it.

---

**Silently omitting a section because its upstream table doesn't exist.** A briefing that looks
complete but is missing the Status section because `matter_signals` hasn't been migrated gives
the practitioner false confidence. Each section must explicitly surface its own schema gap.

---

**Showing a retainer balance without checking sign convention.** If `sign_convention` is missing
from `coclerk.json`, the sign of `regular_trust` is ambiguous. Defaulting to `negative_is_funded`
is a silent assumption that will display the wrong balance if the accounting system uses the
opposite convention. Surface the missing config; do not guess.

---

**Extrapolating a trust balance from time entries.** Computing a current balance by subtracting
recent unbilled hours from the last known import is extrapolation, not data. Show the imported
balance and its age; let the practitioner weigh the staleness.

---

**Treating `regular_trust IS NULL` as $0.00 (depleted).** Per the practice-data consumer
contract: no import on file = unknown. `regular_trust = 0` = confirmed depleted. Collapsing these
two states causes the practitioner to act on a fabricated balance.

---

**Catching all exceptions at the top level and returning a partial briefing that looks complete.**
The per-section try/except pattern exists so each section's failure is localized and visible.
A top-level catch that swallows errors and renders the other sections without flagging the failed
one violates Principle 1.5.

---

**Falling through to `balance_display` undefined when `sign_convention` is unrecognised.** The
`if sign_convention == 'negative_is_funded': ... else: ...` structure must always assign
`balance_display` (or an explicit retainer_note) in the else branch. An unhandled convention
leaves `balance_display` undefined and raises `NameError` at render time — surface the gap
instead.
