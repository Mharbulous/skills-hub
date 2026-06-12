---
name: task-prioritization
description: >
  Maintain and rank the practitioner's task registry using a retainer-first model.
  Use when the user asks "what should I work on?", "what's next?", wants to add or complete
  a task, asks to see the task list, wants to know which files need attention, or asks about
  priorities. Also invoke when a retainer replenishment notice is sent, when a matter's trust
  balance changes, or when a deadline is updated — these events trigger re-ranking.
user-invocable: true
---

# Task Prioritization

Maintain a ranked registry of tasks — client work, administrative duties, and professional
obligations — and answer "what should I work on next?" The registry is persistent (tasks
are never deleted) and every ranked output shows the reasoning behind each placement.

**Reads from:** `matters`, `clients`, `time_entries`, `retainer_notices` (via practice-data)
**Writes to:** `tasks`, `retainer_notices`
**Tables defined in:** `practice-data/SKILL.md` — do not redefine here

## Three-Tier Ranking Model

Tasks are ranked into three tiers, in this order:

| Tier | Condition | Action |
|------|-----------|--------|
| **Remind** | `regular_trust = 0` AND no `retainer_notices` row for this matter | Send written replenishment notice — quick, high-leverage, creates paper trail |
| **Work** | Funded matter (`regular_trust < 0`), OR admin/professional task, OR retainer status unknown (no matters row) | Active work |
| **Paused** | `regular_trust = 0` AND a `retainer_notices` row exists (client warned in writing) | Work on hold pending replenishment |

**Sign convention:** A funded retainer is stored as a negative number (`regular_trust < 0` = funded, `regular_trust = 0` = depleted). No `matters` row = unknown → treat as Work tier with a `[retainer unknown]` flag.

### Tie-Breaking Within the Work Tier

1. **Deadline proximity** — due within 30 days → highest; due beyond 30 days → middle; no deadline → lowest. Among tasks due within 30 days: sooner deadline wins.
2. **Net available trust** (when deadline status is equal) — `abs(regular_trust) − unbilled_wip_hours`. Higher net trust wins. Admin/professional tasks: treat net trust as 0.

## Core Workflows

### 1. Rank and display the task list

When the user asks "what should I work on?", "what's next?", or wants the ranked list:

1. Fetch all open tasks (see [Read query](#read-query-ranked-task-list))
2. Assign each task to Remind, Work, or Paused per the tier model
3. Within Work tier, apply tie-breaking (deadline proximity → net trust)
4. Display using the [Output format](#output-format) — always show the reasoning

### 2. Add a task

1. If a client task: match against `matters.matt_num` or `clients.name`; confirm if ambiguous
2. Collect: description, time estimate (optional), deadline (optional)
3. Invoke `/practice-data` `upsert-task` to create the task
4. Confirm: "Added: [description] — [matter name if applicable]"
5. Ask if they want to see the updated ranked list

### 3. Complete a task

1. Identify the task by description or ID
2. Ask for actual time spent (optional — feeds billing and estimate calibration)
3. Invoke `/practice-data` `complete-task` with the task ID and actual hours
4. Confirm completion; offer to draft a time entry via `time-entry-drafting`

### 4. Send retainer replenishment notice

When the user confirms a replenishment notice has been sent:

1. Identify the matter
2. Invoke `/practice-data` `record-retainer-notice` for the matter
3. Confirm: "Recorded notice for [matter name]. Tasks for this file will move to Paused."
4. Show updated tier assignment for that matter's tasks

### 5. Retainer replenished

When a formerly-depleted matter is now funded (after a new import via `retainer-tracking`):

- Tasks automatically re-enter the Work tier on next ranking — no action in this skill
- Retainer data is live from the `matters` table

## Read Query: Ranked Task List

Invoke `/practice-data` `open-tasks` operation to retrieve all open tasks with their associated matter, client, trust balance, unbilled hours, and retainer-notice count.

**Note on WIP value:** The operation returns hours (not dollar value) because hourly rates are not yet stored.

**Tier assignment and sort logic:**

For each task returned by the operation:
1. **Tier assignment:**
   - Admin/professional task (no matter): → Work
   - Trust balance unknown (no matter record): → Work, flagged as `[retainer unknown]`
   - Trust balance = 0, no retainer notice sent: → Remind
   - Trust balance = 0, retainer notice on file: → Paused
   - Trust balance funded (non-zero): → Work
2. **Deadline ranking** (within Work tier):
   - Due within 30 days: highest priority (sorted by deadline date)
   - Due beyond 30 days: middle
   - No deadline: lowest
3. **Net trust tie-breaker:** `abs(trust_balance) − unbilled_hours` — higher net trust wins. Admin/professional tasks: treat as 0.

Final sort key: `(tier_order, deadline_rank, -net_trust)`

## Output Format

```
## Task List — [date]

### Remind (2)
1. Send retainer replenishment notice — Smith v Jones [L1234]
   Why: Retainer depleted ($0). No written notice on file. Quick action; creates paper trail.

### Work (3)
2. File response to notice of civil claim — Patel v Chen [L2201]
   Why: Funded retainer ($4,200 net of WIP). Deadline: 2026-05-01 (8 days). Est. 3 h.

3. Complete annual CLE reporting  [admin]
   Why: No retainer signal. No deadline on file. Est. 2 h.

### Paused (1)
4. Draft statement of claim — Hernandez v BC Hydro [L0991]
   Why: Retainer depleted ($0). Written notice sent 2026-04-10. Awaiting replenishment.
```

Rules:
- Show all three tier headings even when empty (mark as "(0)")
- Every item must have a "Why:" line citing tier assignment, deadline, and net trust
- Display `abs(regular_trust)` — never the raw negative value
- Flag unknown retainer status: append `[retainer unknown]` to the Why line
- Admin/professional tasks always show `[admin]` or `[professional]` label

## Anti-Patterns

- **Ranking by retainer balance within the Work tier** — net trust is a tie-breaker after deadline proximity, not a primary signal
- **Classifying Remind/Paused when matter has no `matters` row** — unknown retainer status belongs in Work, flagged
- **Displaying raw negative trust values** — always `abs(regular_trust)`
- **Deleting completed tasks** — set `status='completed'`; keep the row for billing and estimate calibration
- **Calculating or storing deadlines** — read `deadline_date` from `tasks` (manual entry) or from `dates-and-deadlines`; never recalculate
- **Parsing the accounting CSV directly** — trust data enters only through `retainer-tracking`'s import workflow
