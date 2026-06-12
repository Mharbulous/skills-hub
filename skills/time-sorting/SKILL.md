---
name: time-sorting
description: >
  Use when the practitioner asks to sort time — "sort today's time", "sort time for
  [date]", or "re-sort [date] after corrections". Classifies raw activities and events
  from the `timeline` namespace (populated by build-timeline) into billable client
  matters and admin categories; views stored time records for any date; queries hours
  spent on a specific matter or file number; and logs hours to a LEAP matter. This
  skill answers "what did I work on and for how long?" — not "what did I bill". Do not
  use for invoice generation, billing totals, AR balances, file status updates, or
  drafting time entry narratives. Do NOT use to fetch raw data from TimeCamp, Telus,
  or Google Calendar — that is build-timeline's job.
dependencies:
  - cowork-db          # `timeline` namespace (input) and `timesort` namespace (output)
  - retainer-tracking  # matter list required for task assignment
---

## Quick Navigation

**Jump to any major section:**

- [Workflow Overview](#workflow)
  - [Step 0: Check timeline data](#step-0-check-timeline-data)
  - [Step 1: Sync TimeCamp Project/Task Tree](#step-1-sync-timecamp-projecttask-tree)
  - [Step 2: Load Activities from Timeline](#step-2-load-activities-from-timeline)
  - [Step 3: Reconcile Overlapping Sources](#step-3-reconcile-overlapping-sources)
  - [Step 4: Fill Gaps](#step-4-fill-gaps)
  - [Step 5: Assign Activities to Tasks](#step-5-assign-activities-to-tasks)
  - [Step 6: Replay Corrections](#step-6-replay-corrections)
  - [Step 7: Store Results](#step-7-store-results)
  - [Step 8: Present Results](#step-8-present-results)
- [Data Model](#data-model)
- [Queries & Integration](#queries)
- [User Corrections](#user-corrections)

# Time-Sorting

Classify raw activities from the timeline into TimeCamp Projects and Tasks, representing client matters and non-billable administrative categories.

## Overview

This skill takes the raw, source-attributed chronology assembled by `build-timeline` and interprets it: reconciling overlapping sources, filling untracked gaps during business hours, assigning each period to a known TimeCamp Task or admin category, and storing the classified day under the `timesort` namespace.

**Why:** This creates an audit trail for billing and accountability, ensures no client data leaves the practitioner's machine, and handles real-world complexity where a single time period might be documented in multiple sources.

**Prerequisite:** Before sorting, the `timeline` namespace must contain activity data for the target date, loaded by `build-timeline`. If the timeline is empty or stale, tell the practitioner: "No timeline data found for {date}. Run `/build-timeline` for that date first."

### Core Principle: Reconcile First, Hierarchy as Tiebreaker

When sources provide conflicting signals, **first attempt to reconcile** — use context from all sources to find a consistent interpretation. Only fall back to the source reliability hierarchy (Telus → TimeCamp → Google Calendar) when signals genuinely conflict and cannot be resolved.

**Reliability order (for unresolvable conflicts only):**
1. Telus Business Connect — most reliable for activity type (phone calls, voicemail, texts, fax)
2. TimeCamp (computer activities) — highest volume
3. Google Calendar (meetings/court) — least reliable

All sources contribute context for task assignment regardless of hierarchy.

### Critical Constraints

- **Read-only on timeline:** Never modify `timeline` namespace data. This skill reads from `timeline` and writes only to `timesort`.
- **Classify before assigning:** Complete overlap reconciliation and gap-fill before assigning any activity.
- **Source attribution:** Every assigned activity traces back to the raw data that produced the assignment.
- **Surface failures:** Report any data gaps or anomalies explicitly; never silently omit periods.

## Configuration

Source-specific reconciliation and assignment context:

- **TimeCamp activities:** `raw_payload.application` and `raw_payload.window_title` are the primary signals. `raw_payload.timecamp_task_id` is respected if non-zero (pre-assigned in TimeCamp).
- **Google Calendar:** Event title and description are signals. GCal has no native `raw_type` — derive activity type during classification from event title keywords.
- **Telus Connect:** `raw_payload.phone_number`, `raw_payload.direction`, `raw_payload.contact_name`. `raw_type` is already set (`phone_call`, `voicemail`, `text`, `fax`).

## Data Model

### Namespaces

- **Input:** `timeline` namespace — `activity:{id}`, `event:{id}`, index keys. Read-only.
- **Output:** `timesort` namespace — classified day objects, project tree, corrections, metadata.

### Key Schema (timesort namespace)

| Key pattern | Value | Purpose |
|------------|-------|---------|
| `projects:tree` | JSON tree of TimeCamp Projects/Tasks | Task assignment lookup |
| `projects:lookup` | JSON map of taskId → {name, parentId, level, billable} | Fast task matching |
| `projects:synced_at` | ISO timestamp | Staleness check for project tree |
| `day:{YYYY-MM-DD}` | Day JSON object | Classified timeline for a single day |
| `corrections:{YYYY-MM-DD}` | JSON array of correction objects | User edits that survive re-sorts |
| `sort:latest` | Sort metadata JSON | Last sort summary |

Note: `config:timecamp_token` lives in the `timeline` namespace (build-timeline owns it). To sync the project tree, read the token with:

```bash
cowork-db get timeline "config:timecamp_token"
```

### Day Object Schema

```json
{
  "date": "YYYY-MM-DD",
  "sorted_at": "ISO 8601 timestamp",
  "sources_present": ["timecamp", "gcal"],
  "sources_absent": ["telus"],
  "activities": [
    {
      "id": "a1",
      "timeline_ids": ["timecamp:a48291"],
      "start": "HH:MM",
      "end": "HH:MM",
      "activity_type": "screen_work | phone_call | meeting | court | untracked",
      "activity_source": "timecamp | telus | gcal | none",
      "task_id": "TimeCamp taskId or null",
      "task_name": "Smith v Jones (L3948) or null",
      "project_name": "Client Matters or null",
      "matter": "L3948 or null",
      "category": "admin | billing | training | professional_development | business_development | tech_troubleshooting | onboarding | bookkeeping | null",
      "confidence": "high | medium | low",
      "attribution": {
        "activity_from": "source that determined activity type",
        "assigned_from": "source/signal that determined task assignment",
        "signals": ["list of raw signals used"]
      }
    }
  ],
  "summary": {
    "total_hours": 8.2,
    "assigned_hours": 7.5,
    "unassigned_hours": 0.7,
    "by_matter": {"L3948": 3.2},
    "by_category": {"admin": 1.5}
  }
}
```

`timeline_ids` — one or more `activity:{id}` or `event:{id}` keys from the `timeline` namespace that contributed to this classified activity. Preserves traceability back to raw source data.

An activity is **assigned** if it has either a non-null `task_id` or a non-null `category`. Activities with both null are **unassigned**.

Activities use source-native granularity — no rounding to billing increments. The time-entry-drafting skill handles rounding downstream.

### Correction Object Schema

```json
{
  "activity_id": "a2",
  "field": "task_id | category",
  "old_value": "12345",
  "new_value": "67890",
  "corrected_at": "ISO 8601 timestamp"
}
```

### Sort Metadata Schema

```json
{
  "date": "YYYY-MM-DD",
  "sorted_at": "ISO 8601 timestamp",
  "sources": ["timecamp", "gcal"],
  "activities": 14,
  "assigned": 12,
  "unassigned": 2
}
```

## Workflow

### Step 0: Check Timeline Data

Read `coclerk.json`. Check for `time_tracking.sources`.

**If `time_tracking` is absent, or `time_tracking.sources` is absent or empty:** run the First Setup Protocol at `protocols/FirstSetup.md`. After the protocol completes, continue from Step 1.

Check that build-timeline has populated data for the target date:

```bash
cowork-db get timeline "index:activity:by-date:{YYYY-MM-DD}"
```

If the key is absent or the array is empty, tell the practitioner: "No timeline data found for {date}. Run `/build-timeline` for that date first, then re-sort." Do not proceed.

Note which sources are present by checking `source:{source}:ranges` in the `timeline` namespace for each known source (timecamp, telus, gcal). Report absent sources to the practitioner before sorting (they affect completeness, not correctness).

### Step 1: Sync TimeCamp Project/Task Tree

Before assigning activities, ensure the project tree is loaded. Check:

```bash
cowork-db get timesort "projects:synced_at"
```

If not found or stale (> 24 hours), sync the tree. Read the token from the `timeline` namespace:

```bash
cowork-db get timeline "config:timecamp_token"
```

Then fetch the full project/task tree:

```bash
curl -s -X POST "https://www.timecamp.com/third_party/api/v3/projects" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"parentId": 0, "status": "active", "perPage": 250}'
```

Response includes `taskId`, `name`, `parentId`, `level`, `hasChildren`, `billable`, `archived`, and `children[]`. Walk the tree recursively to get all Tasks.

Store the tree in the `timesort` namespace:

```bash
cowork-db set timesort "projects:tree" '{json_tree}'
cowork-db set timesort "projects:synced_at" '{ISO_timestamp}'
```

Also build a flat lookup for quick matching:

```bash
cowork-db set timesort "projects:lookup" '{task_id_to_name_map}'
```

**When to sync:**
- On first run (no `projects:tree` key exists)
- When the practitioner asks to refresh the project list
- When an activity's window title mentions a matter not in the current tree
- At most once per session to avoid API rate limits

If the token is absent, skip the sync and proceed — task assignment will rely on retainer-tracking matter names only. Tell the practitioner: "TimeCamp token not configured in timeline namespace. Project tree not synced — task IDs will not be resolved."

### Step 2: Load Activities from Timeline

Load all activity IDs for the target date from the `timeline` namespace:

```bash
cowork-db get timeline "index:activity:by-date:{YYYY-MM-DD}"
```

For each ID in the array, fetch the full activity row:

```bash
cowork-db get timeline "activity:{id}"
```

Build a working list of activity rows sorted by `start_ts`. Convert UTC timestamps to local time (from `coclerk.json` → `time_tracking.timezone`, default `"America/Vancouver"`) for display and gap-fill calculations. Work in local time for business-hours logic; store results in local `HH:MM` strings in the day object.

Also load events for context signals:

```bash
cowork-db get timeline "index:event:by-date:{YYYY-MM-DD}"
```

Events do not become classified activities — they are enrichment signals for task assignment only.

### Step 3: Reconcile Overlapping Sources

Build-timeline may store parallel observations from multiple sources for the same time period (e.g., a TimeCamp screen session and a Google Calendar event both covering 14:00–14:30). Reconcile these before assigning.

#### Overlap Detection

Two activities overlap if one's `start_ts` falls before the other's `end_ts` AND one's `end_ts` falls after the other's `start_ts`.

#### Reconciliation Procedure

For each overlapping group:

1. **Attempt reconciliation** — look for a consistent interpretation using context from all overlapping sources. Example: a GCal event titled "Smith hearing" + TimeCamp showing LEAP open to the Smith file → consistent. Use both as signals; keep the Telus or TimeCamp row as the primary (more reliable for duration).

2. **Apply source hierarchy only when signals genuinely conflict** — Telus → TimeCamp → GCal. The source that "wins" determines `activity_type` and `activity_source`. The losing source's signals go into `attribution.signals` for task assignment.

3. **Telus during TimeCamp:** If irreconcilable: the Telus activity replaces the overlapping portion of the TimeCamp activity. Split the TimeCamp activity into up to three segments:
   - Pre-Telus segment (TimeCamp, before Telus start)
   - Telus segment (Telus — keep TimeCamp window titles during this period as attribution signals)
   - Post-Telus segment (TimeCamp, after Telus end)
   Drop any resulting segment shorter than 1 minute.

4. **Telus during GCal:** If irreconcilable: Telus takes precedence for activity type. Calendar event context preserved as attribution signal.

5. **GCal during TimeCamp (no Telus):** If irreconcilable: TimeCamp takes precedence.

`activity_source` is always set to the source that determined the **activity type** for that segment. Context from other sources goes into `attribution.signals`.

Populate `timeline_ids` with all source IDs that contributed to each reconciled activity.

### Step 4: Fill Gaps

After reconciliation, scan the period 07:00–19:00 in local time. Any continuous gap of 1 minute or more with no activity from any source becomes an activity with:
- `activity_type: "untracked"`
- `activity_source: "none"`
- `task_id: null`, `category: null`
- `confidence` omitted (not applicable)

These "untracked" periods represent time the practitioner was working but not captured by any connected source. They are kept in the day object so the practitioner can review and assign them manually if needed.

### Step 5: Assign Activities to Tasks

For each reconciled activity (including untracked periods), determine the TimeCamp Task it belongs to — either a client matter Task or a non-billable category Task.

#### Load Assignment Targets

Two sources provide the set of valid assignment targets:

1. **TimeCamp Project/Task tree** (from Step 1) — the authoritative list of Tasks
2. **Retainer-tracking matter list** — provides matter numbers and client names that map to TimeCamp Tasks

Fetch the retainer matter list:

```bash
cowork-db list retainer "balance:"
```

For each key returned, fetch the value:

```bash
cowork-db get retainer "balance:{matt_num}"
```

Note: retainer-tracking keys use the canonical form (e.g., `L3948`, no leading dot). Match window titles against the matter number directly.

Build a combined lookup: matter numbers → TimeCamp Task IDs + client names. Where a matter number appears in both the TimeCamp tree and retainer-tracking, use the TimeCamp `taskId` as the canonical reference.

#### Assignment Rules

For each activity, analyze the attribution signals:

1. **Window title matching** — Look for matter numbers (e.g. "L3948"), client names (e.g. "Smith"), or matter descriptions in window titles. LEAP windows typically contain the client/matter name.

2. **Application context** — LEAP indicates client work. Gmail/Outlook likely admin unless the subject line indicates a specific matter. Chrome depends on the URL/page title.

3. **Phone call context** — For Telus activities, check TimeCamp window titles in `attribution.signals` for the same period. If the practitioner had a client file open during the call, assign to that matter's Task with `confidence: "medium"`.

4. **Calendar context** — GCal event titles often name the matter, client, or court proceeding.

5. **Non-billable assignment** — If signals clearly indicate non-client work, assign a category from this fixed enum (these correspond to non-billable Tasks in TimeCamp):
   - `admin` — General administration, email triage, scheduling
   - `billing` — Invoice preparation, AR follow-up, accounting system work
   - `training` — CLE, legal education
   - `professional_development` — Non-CLE professional growth
   - `business_development` — Marketing, networking, client development
   - `tech_troubleshooting` — IT issues, software setup
   - `onboarding` — New client/matter intake
   - `bookkeeping` — Financial record-keeping

6. **Pre-assigned activities** — If a TimeCamp activity's `raw_payload.timecamp_task_id` is non-zero, respect that assignment. Set `confidence: "high"` and `assigned_from: "timecamp_preassigned"`.

#### Confidence Levels

- **high** — Unambiguous match: matter number in window title, LEAP window with exact client name matching a known Task, or pre-assigned in TimeCamp
- **medium** — Likely but uncertain: client name appears in a non-LEAP window, or phone call while client file is open
- **low** — Best guess: weak signals, multiple possible Tasks, or ambiguous context

#### Confidence Scoring Examples

**Example 1 (HIGH Confidence)**

Activity: Screen work in LEAP window titled "Smith v Jones (L3948) - Settlement Memo" (45 min)

Signals: Matter number L3948 in title + LEAP application + retainer-tracking confirmation

→ **Confidence: HIGH** — Explicit matter identification. No competing interpretation.

**Example 2 (MEDIUM Confidence)**

Activity: Incoming phone call at 13:45 (18 min). TimeCamp signal shows Chrome: "Client Portal - Doe v BC"

Signals: Telus confirms call type, TimeCamp signal shows Doe v BC context, but no caller ID name

→ **Confidence: MEDIUM** — Call type certain (Telus), task assignment relies on concurrent window. Could be unrelated call.

**Example 3 (LOW Confidence)**

Activity: Chrome window titled "Re: Update" (45 min). No other context.

Signals: Generic title could be email about any matter, client portal, research, or admin work

→ **Confidence: LOW** — Multiple possible interpretations. Practitioner must review manually.

#### Unassigned Activities

If an activity cannot be assigned to any known Task AND does not clearly fit a non-billable category, leave `task_id: null` and `category: null`. Do NOT invent Task IDs or guess. The practitioner resolves these during review.

### Step 6: Replay Corrections

Check for stored corrections from a previous sort of this date:

```bash
cowork-db get timesort "corrections:{YYYY-MM-DD}"
```

If corrections exist (exit code 0), parse the JSON array. For each correction:
1. Find the activity with matching `activity_id` in the current assignment
2. If found, apply the correction: set `activity.{field}` to `new_value`
3. If the activity_id no longer exists (timeline was merged differently), silently skip — the practitioner will see the unmodified assignment and correct again if needed

Track how many corrections were re-applied vs. skipped for the summary.

### Step 7: Store Results

Build the Day object from the classified activities. Calculate the summary:
- `total_hours`: sum of all activity durations (end - start)
- `assigned_hours`: sum of durations for activities with non-null `task_id` or non-null `category`
- `unassigned_hours`: `total_hours - assigned_hours`
- `by_matter`: map of matter number → total hours
- `by_category`: map of category → total hours

Store the Day object:

```bash
cowork-db set timesort "day:{YYYY-MM-DD}" '{day_json}'
```

Update sort metadata:

```bash
cowork-db set timesort "sort:latest" '{"date":"{YYYY-MM-DD}","sorted_at":"{ISO_NOW}","sources":[{sources_present}],"activities":{N},"assigned":{M},"unassigned":{U}}'
```

### Idempotency

Re-running "sort time" for a date that already has assignments:
1. Re-reads from `timeline` namespace (may include new data if build-timeline was re-run)
2. Re-classifies from scratch
3. Replays stored corrections where activity IDs still match
4. Overwrites `day:{date}` with the new assignments
5. Reports what changed: "Re-sorted {date}: {N} activities classified, {M} corrections re-applied, {K} corrections skipped (activities changed)"

### Step 8: Present Results

After storing, present the classified timeline as a table:

```
Time         Duration  Type         Task/Category              Confidence  Source
09:02-09:47  0:45      Screen work  Smith v Jones (L3948)       High       TimeCamp
09:47-10:05  0:18      Phone call   Smith v Jones (L3948)       Medium     Telus + TimeCamp
10:05-10:30  0:25      Screen work  Admin                       High       TimeCamp
10:30-10:32  0:02      Untracked    — (unassigned)              —          —
...

Summary: 8.2h total | 7.5h assigned (91%) | 0.7h unassigned
By matter: Smith v Jones 3.2h, Doe v BC 2.1h
By category: Admin 1.5h, Billing 0.7h
```

If any sources were absent from the timeline, note them above the table:
"Note: Telus data not in timeline for this date — phone calls are not included."

If corrections were re-applied, note: "Re-applied {N} corrections from previous sort."

## User Corrections

The practitioner can correct any activity after presentation (equivalent to "moving" activities between Tasks in TimeCamp):
- "Change the 09:47 activity to the Doe file" → Update the activity's `task_id` and `task_name` to the Doe file's Task
- "That admin activity was actually billing" → Update the activity's `category` to `"billing"`, clear `task_id`/`task_name` if set
- "The 10:05 activity was for L4201" → Update the activity's `task_id`, `task_name`, and `matter`

When processing a correction:

1. Identify the activity by time or description
2. Validate the new value (if task, must exist in the project tree or retainer-tracking; if category, must be in the fixed enum)
3. Update the activity in the Day object
4. Store the correction:

```bash
# First, get existing corrections (may not exist)
cowork-db get timesort "corrections:{YYYY-MM-DD}"
# Append the new correction to the array (or create new array)
cowork-db set timesort "corrections:{YYYY-MM-DD}" '{updated_corrections_json}'
```

5. Re-store the updated Day object:

```bash
cowork-db set timesort "day:{YYYY-MM-DD}" '{updated_day_json}'
```

6. Update the sort metadata
7. Confirm: "Updated: {time} activity now assigned to {new_value}"

## Queries

| Question | How to answer |
|----------|---------------|
| Sort today's time | Full workflow for today |
| Sort time for March 15 | Same workflow with `date=2026-03-15` |
| How much time on the Smith file this week? | `cowork-db list timesort "day:"` for each date in the week → sum activities where `matter` matches |
| What's unassigned this week? | Same day list → filter activities where `task_id` is null AND `category` is null |
| When was the last sort? | `cowork-db get timesort "sort:latest"` |
| Show the sorted day for April 10 | `cowork-db get timesort "day:2026-04-10"` → present as table |
| Refresh the project list | Re-sync the TimeCamp project tree and update `projects:tree` in `timesort` namespace |

## Integration with Other Skills

| Skill | How it integrates |
|-------|-------------------|
| **build-timeline** | Prerequisite. Populates the `timeline` namespace that time-sorting reads. Run build-timeline first if timeline data is absent or stale. |
| **retainer-tracking** | Provides matter list via `cowork-db list retainer "balance:"` — used alongside the TimeCamp project tree for task assignment |
| **time-entry-drafting** | Reads `cowork-db get timesort "day:{date}"` → rounds activities to billing increments → drafts LEAP time entries |
| **billing-summary** | Reads assigned time across date range → aggregates by matter |
| **file-prioritization** | Uses assigned time to assess file activity levels |
| **matter-status-tracking** | Reads recent activities to determine last-activity dates |
