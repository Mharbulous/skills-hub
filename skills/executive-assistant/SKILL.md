---
name: executive-assistant
description: >
  The single recommendation engine for what to work on next — the only skill that tells the
  practitioner "do this now." Use when the practitioner asks "what should I work on?", "what's
  next?", "what do I tackle today?", wants a morning briefing, or needs a ranked list of tasks with
  context from retainer status, WIP levels, and deadlines. Also invoked automatically by the
  morning briefing cron trigger. Use this skill — not task-prioritization alone — whenever the
  goal is a synthesized, actionable recommendation rather than just a ranked task list.
user-invocable: true
---

# Executive Assistant

Synthesize the ranked task list from `task-prioritization` with deadline urgency, WIP signals, and
matter status into a single actionable recommendation. Two invocation modes share one data layer:

- **On-demand** (`/executive-assistant`): answers "what now?" with a current-state snapshot
- **Morning briefing** (cron-triggered): answers "what today?" with a temporally-framed aggregate
  covering the day ahead. The scheduling trigger is external (configured via the `schedule` skill);
  this skill handles the briefing output when invoked.

**This skill reads. It writes nothing.**

Reads from: `task-prioritization` (ranked task registry), `wip-tracker` (WIP silence signal),
`dates-and-deadlines` (upcoming deadlines), `matter-status-tracking` (matter status),
`retainer-tracking` (trust balances), and the practice database directly for retainer data.

## Core Principle: Surface, Don't Rank

Tier assignments (Remind / Work / Paused) belong to `task-prioritization`. Never recompute tiers
from `regular_trust` or `notice_count` in this skill — that is the violation vision §3.1 names.

Invoke `task-prioritization`'s ranking workflow and consume its ranked output, then layer on
deadline urgency, WIP silence signals, and matter status as supplementary context.

## Data Fetch

Resolve the DB path via `practice-data/SKILL.md` — follow its path resolution protocol
(read `coclerk.json`, explain access before requesting it, handle missing config per its
initialization workflow). Do not reimplement path resolution here.

```python
import sqlite3, json, os
from datetime import date, timedelta

# db_path resolved via practice-data/SKILL.md
conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
today = date.today().isoformat()
seven_days  = (date.today() + timedelta(days=7)).isoformat()
thirty_days = (date.today() + timedelta(days=30)).isoformat()

# 1. Upcoming deadlines (active, not superseded)
# deadlines table is owned by dates-and-deadlines — may not exist yet
try:
    deadlines = conn.execute('''
        SELECT d.matter_id, d.deadline_type, d.deadline_date, d.rule_ref, d.rule_description,
               m.matt_num, cl.name AS client_name
        FROM deadlines d
        JOIN matters m ON m.id = d.matter_id
        JOIN clients cl ON cl.id = m.client_id
        WHERE d.status = 'active'
          AND d.deadline_date BETWEEN ? AND ?
        ORDER BY d.deadline_date ASC
    ''', (today, thirty_days)).fetchall()
    deadlines_available = True
except Exception:
    deadlines = []
    deadlines_available = False

# 2. WIP silence — funded matters with no time entries in the last 21 days
# Replace with wip-tracker's exposed interface when available.
wip_silence = conn.execute('''
    SELECT m.id AS matter_id, m.matt_num, cl.name AS client_name,
           m.regular_trust,
           MAX(te.entry_date) AS last_entry_date,
           CAST(julianday(?) - julianday(COALESCE(MAX(te.entry_date), '2000-01-01')) AS INTEGER)
               AS days_since_entry
    FROM matters m
    JOIN clients cl ON cl.id = m.client_id
    LEFT JOIN time_entries te ON te.matter_id = m.id
    WHERE m.regular_trust < 0          -- funded only
      AND m.status NOT IN ('closed', 'declined')
    GROUP BY m.id
    HAVING days_since_entry >= 21
    ORDER BY days_since_entry DESC
''', (today,)).fetchall()

# 3. Matter status — unconfirmed signals needing attention
# matter_signals table is owned by matter-status-tracking — may not exist yet
try:
    unconfirmed_signals = conn.execute('''
        SELECT ms.matter_id, ms.signal_key, m.matt_num, cl.name AS client_name
        FROM matter_signals ms
        JOIN matters m ON m.id = ms.matter_id
        JOIN clients cl ON cl.id = m.client_id
        WHERE ms.state = 'unconfirmed'
          AND m.status NOT IN ('closed', 'declined')
        ORDER BY m.matt_num
    ''').fetchall()
    matter_status_available = True
except Exception:
    unconfirmed_signals = []
    matter_status_available = False

conn.close()
```

Report data gaps explicitly — never silently omit matters:

| Condition | Report |
|-----------|--------|
| `deadlines_available` is False | "Deadline data unavailable — run `dates-and-deadlines` to record court dates first." |
| `matter_status_available` is False | "Matter status signals unavailable — `matter_signals` schema not yet added. Run `matter-status-tracking` to set up." |
| `tasks` table empty | "No open tasks on file — add tasks via `task-prioritization`." |
| No matters in DB | "No matters found — check that `retainer-tracking` has been imported." |
| `wip-tracker` interface not yet available | Use direct `time_entries` query (as above); note fallback in output. |

## Workflow 1: On-Demand ("What should I work on?")

1. Run `task-prioritization`'s rank-and-display workflow to get the current ranked task list with tier assignments.
2. Fetch upcoming deadlines and WIP silence data using the queries above.
3. Enrich each task in the ranked list:
   - Append deadline proximity if the task's matter has a deadline within 30 days
   - Append WIP silence flag if the matter qualifies
   - Append matter status if unconfirmed signals exist
4. Output using the [On-Demand Format](#on-demand-format).

## Workflow 2: Morning Briefing

Fired by an external cron trigger. Frames the day ahead rather than repeating the ranked queue.

1. Fetch task list from `task-prioritization` (ranked output).
2. Fetch deadlines, WIP silence, and matter status using the queries above.
3. Compose the briefing in four sections (omit sections with nothing to report):
   - **Requires action today** — tasks whose deadline is today or tomorrow; Remind-tier tasks
   - **Due within 7 days** — deadlines in the 2–7 day window, with retainer balance context
   - **Due within 30 days** — deadlines in the 8–30 day window worth planning for
   - **Flags** — WIP silence on funded files; unconfirmed matter lifecycle signals
4. Conclude with the top 3 tasks from the full ranked list, for practitioners who want to work straight through the queue.
5. Output using the [Morning Briefing Format](#morning-briefing-format).

## On-Demand Format

```
## Task Recommendation — [date]

### Remind (N)
1. Send retainer replenishment notice — Smith v Jones [.L1234]
   Tier: Remind | Retainer: $0, no written notice on file | Est. 5 min

### Work (N)
2. File response to notice of civil claim — Patel v Chen [.L2201]
   Tier: Work | Retainer: $4,200 | Deadline: 2026-05-01 (8 days) | Est. 3 h

3. Complete annual CLE reporting [admin]
   Tier: Work | No retainer signal | No deadline on file | Est. 2 h

### Paused (N)
4. Draft statement of claim — Hernandez v BC Hydro [.L0991]
   Tier: Paused | Retainer: $0, written notice sent 2026-04-10

---
[Data gaps, if any — e.g. "⚠ Deadline data unavailable"]
```

Rules:
- Show all three tier headings even when empty — mark as "(0)"
- Every item must show: tier, retainer status, deadline (if any), estimate (if any)
- Display `abs(regular_trust)` as the trust balance — never the raw negative
- Flag unknown retainer status: append `[retainer unknown]` to the item
- Admin/professional tasks always show `[admin]` or `[professional]`
- Report data gaps explicitly at the bottom — never silently omit matters

## Morning Briefing Format

```
## Morning Briefing — [day, date]

### Requires Action Today
- Send retainer replenishment notice — Smith v Jones [.L1234]
  Retainer depleted, no notice on file. Quick action; creates paper trail.

### Due Within 7 Days
- File response to civil claim — Patel v Chen [.L2201]
  Deadline: 2026-05-01 (3 days) | Rule 3-3 | Retainer: $4,200

### Due Within 30 Days
- Witness list — Harrison v Chan [.L1887]
  Deadline: 2026-05-14 (24 days) | Rule 11-6(3) | Retainer: $6,200

### Flags
- ⚠ WIP silence — Harrison v Chan [.L1887]: funded ($6,200), no time entries in 23 days
- ⚠ Matter signal unconfirmed — Boyd v Metro [.L2044]: retainer_agreement_signed unconfirmed

---
Top 3 tasks for today (full ranked list via /task-prioritization):
1. Send retainer replenishment notice — Smith v Jones [.L1234]  [Remind]
2. File response to civil claim — Patel v Chen [.L2201]  [Work, deadline 3 days]
3. Draft factual summary — Boyd v Metro [.L2044]  [Work]

[Data gaps, if any]
```

Rules:
- The briefing is temporally framed — group by urgency window, not by tier
- Omit sections that have nothing to report; if all sections are empty, say so explicitly
- Every deadline item must show the deadline date, days remaining, and rule reference
- Every WIP silence flag must show the trust balance and exact days since last entry
- The "Top 3" footer is always present — it anchors the briefing to the ranked queue
- Show raw `abs(regular_trust)` as the retainer balance; note "(wip-tracker not yet available)" if applicable

## Anti-Patterns

- **Assigning tiers from `regular_trust`** — read tiers from `task-prioritization`'s output
- **Fetching retainer data differently in each mode** — both modes use the same DB queries
- **Treating the morning briefing as a dump of the ranked task list** — it must be temporally framed
- **Silently skipping matters with no `matters` row** — surface them with `[retainer unknown]`
- **Treating `regular_trust = NULL` as depleted** — NULL = unknown; only `= 0` is depleted
- **Drafting notices or invoices** — surface the need; leave execution to the appropriate skill
- **Re-calculating deadline dates** — read from `deadlines` table; never recalculate
- **Reimplementing DB path resolution** — always delegate to `practice-data/SKILL.md`
- **Wrapping `deadlines` queries but not `matter_signals` (or vice versa)** — both tables are
  externally owned and may not exist; handle both symmetrically with try/except
