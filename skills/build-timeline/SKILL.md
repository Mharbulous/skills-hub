---
name: build-timeline
description: >
  Assemble a unified chronology of the practitioner's day by fetching activities
  and events from TimeCamp, Telus Business Connect, Google Calendar, and other
  time-stamped sources, then storing them in the cowork-db `timeline` namespace
  as a continuous, source-attributed store. Use whenever the user asks to
  "build the timeline", "fetch timeline data", "pull in TimeCamp/Telus/Calendar
  data for [date]", "refresh today's raw data", "re-import Telus CSV", or any
  request to gather raw time-tracking data from one or more sources. Also use
  when a downstream skill (e.g. time-sorting) needs fresh raw data for a date
  or range. This skill builds the raw chronology ONLY — it does not classify
  activities, assign them to matters, fill gaps with "untracked" periods, or
  reconcile overlapping sources. Those are classification concerns handled by
  time-sorting. Do not use for sorting time, billing, invoice drafting, or any
  interpretation of what the recorded activities mean.
dependencies:
  - cowork-db           # continuous timeline store under the `timeline` namespace
  - google-calendar-mcp # calendar events (optional — degrades gracefully if unavailable)
---

# Build-Timeline

Fetch raw activities and events from time-stamped sources and store them in a
continuous, source-attributed chronology. This skill is strictly a data
assembly layer — it records what sources observed, without interpretation.

## Scope

This skill handles:

- Fetching TimeCamp computer activities, Telus Business Connect telephony
  records, and Google Calendar events for a requested date or date range.
- Storing each record as either an **activity** (start + end) or an **event**
  (single timestamp) in cowork-db under the `timeline` namespace.
- Preserving the raw source payload alongside the normalized row so downstream
  skills and the practitioner can see exactly what came from where.
- Replacing previously-fetched data from a given source within the requested
  range when re-fetched, while preserving row identity so downstream
  annotations survive.

This skill does NOT handle:

- Choosing an "activity type" when sources overlap — both records are stored
  as parallel observations; reconciliation is classification's job.
- Filling quiet periods with "untracked" segments — that requires knowing
  business hours, which is interpretive.
- Inferring activities from clusters of events (e.g., ten file saves over
  forty minutes implying a long screen-work session) — that is classification.
- Assigning activities to matters, projects, or categories.
- Displaying the full day as a unified table — display is limited to 60-minute
  windows on explicit request.

## Core primitives

Two entity types, modelled separately because they behave differently:

- **Activity** — an observation with a start and end time. Examples: a TimeCamp
  screen session, a Telus phone call, a Google Calendar event. Activities have
  duration and can overlap with other activities.
- **Event** — an observation at a single instant. Examples: a file download, an
  email send, a Git commit. Events have no duration and cannot overlap in a
  meaningful sense.

Events are kept as a distinct entity rather than as zero-duration activities
because summing durations across a mixed set of rows produces misleading math,
and because events are primarily enrichment signals for activity classification
downstream, not timeline segments in their own right.

## Data model

All data lives in the `timeline` namespace in cowork-db.

### Row identity

Each activity or event row has a deterministic ID derived from its source and
the source's native record identifier:

- **Format:** `{source}:{native_id}`
- **Examples:**
  - `timecamp:a48291` — TimeCamp activity with internal id 48291
  - `telus:c2026-04-15T14:30+16045551234` — Telus call record (composite key
    from timestamp + phone number when no native call id is available — see
    TODO below)
  - `gcal:{ical-uid}` — Google Calendar event by its iCal UID
  - `download:{filename}:{mtime}` — file in Downloads folder (future source)

The source is responsible for producing a stable native_id. When a source
provides no stable identifier, compose one from immutable fields (timestamp +
phone number, filename + modification time, etc.). Never use a random or
time-of-fetch component — that would break re-fetch idempotency.

Stable IDs matter because downstream skills (classification, corrections,
time-entry drafting) store their own records keyed to these IDs. If the IDs
changed on every re-fetch, every downstream annotation would be orphaned.

> **TODO (Telus implementer):** The composite-key format shown above is a
> fallback. Before implementing the Telus source, inspect an actual Telus
> Business Connect CSV export to see whether it includes a stable call_id
> column. If it does, use `telus:{call_id}` instead of the composite. If it
> does not, document the exact composite fields used (and their ordering) so
> the format is reproducible across runs.

### Key layout

| Key pattern | Value | Purpose |
|-------------|-------|---------|
| `config:timecamp_token` | Plain text API token | TimeCamp authentication |
| `source:{source}:fetched_at` | ISO 8601 UTC timestamp (trailing `Z`) | Last successful fetch for this source |
| `source:{source}:ranges` | JSON array of `[start, end]` UTC timestamps | Ranges of time this source has been fetched for |
| `activity:{id}` | JSON activity row | A single activity observation |
| `event:{id}` | JSON event row | A single event observation |
| `index:activity:by-date:{YYYY-MM-DD}` | JSON array of activity ids | Activities whose interval overlaps this **local** date (local-date indexing matches how the practitioner thinks; mapping to UTC happens at query time) |
| `index:event:by-date:{YYYY-MM-DD}` | JSON array of event ids | Events whose timestamp falls on this **local** date |
| `index:activity:by-source:{source}` | JSON array of activity ids | All activities from a given source |
| `index:event:by-source:{source}` | JSON array of event ids | All events from a given source |

cowork-db is a key-value store, so relational queries (e.g., "all activities
overlapping this hour") are computed in Python at read time by loading the
relevant by-date indexes and filtering. At daily granularity the row counts
are small enough that this is cheap.

### Reference data is not stored here

TimeCamp also exposes a Projects/Tasks tree — a taxonomy used by classification
to resolve TimeCamp `task_id` foreign keys on activity records. That tree is
**reference data**, not timeline data: it has no temporal dimension, is
refreshed on a different cadence, and exists solely to support interpretation.

Build-timeline stores each activity's `task_id` verbatim inside `raw_payload`
and never resolves it. The tree itself lives in the `timesort` namespace,
fetched and maintained by the time-sorting skill. This is a deliberate
ownership rule: the timeline namespace holds observations in time; reference
data belongs wherever it is consumed.

### Activity row schema

```json
{
  "id": "timecamp:a48291",
  "source": "timecamp",
  "native_id": "a48291",
  "start_ts": "2026-04-15T16:02:00Z",
  "end_ts": "2026-04-15T16:47:00Z",
  "raw_type": "screen_work",
  "raw_payload": {
    "application": "LEAP",
    "window_title": "Smith v Jones (L3948) - Settlement Memo",
    "timecamp_task_id": "0"
  },
  "fetched_at": "2026-04-16T02:30:00Z"
}
```

- `start_ts` / `end_ts` — always ISO 8601 in **UTC** (trailing `Z`). Storage
  is in UTC so that timestamps are unambiguous and independent of local
  offset changes (DST, travel). Display and user input use the practitioner's
  local timezone, read from `coclerk.json` → `time_tracking.timezone`
  (default `"America/Vancouver"` if unset) — converted to UTC before storage
  and back to local for display.
- `raw_type` — the source's native classification, kept as-is, or `null` when
  the source does not provide one. TimeCamp → `"screen_work"`. Telus →
  `"phone_call"`, `"voicemail"`, `"text"`, `"fax"` (Telus exposes a subtype
  directly). GCal → `null`; Google Calendar has no native type taxonomy for
  our purposes, so we pass through GCal's raw fields inside `raw_payload` and
  leave classification to derive a type from them. Never infer `raw_type`
  from content that isn't a structured source field (e.g., a title string);
  that is interpretation and belongs to classification.
- `raw_payload` — the source's native fields, kept verbatim so downstream
  skills and humans can see exactly what was observed.
- `fetched_at` — when this row was most recently written. Overwritten on
  re-fetch.

### Event row schema

```json
{
  "id": "download:Settlement-Memo.docx:1713193820",
  "source": "download",
  "native_id": "Settlement-Memo.docx:1713193820",
  "ts": "2026-04-15T20:43:40Z",
  "raw_type": "file_download",
  "raw_payload": {
    "filename": "Settlement-Memo.docx",
    "path": "C:/Users/Brahm/Downloads/Settlement-Memo.docx",
    "size_bytes": 48213
  },
  "fetched_at": "2026-04-16T02:30:00Z"
}
```

- `ts` — a single ISO 8601 instant in UTC (same rule as `start_ts` / `end_ts`
  on activity rows). Events have no duration, so there is no corresponding
  end field.
- `source`, `native_id`, `raw_type`, `raw_payload`, `fetched_at` — same
  semantics as on the activity row schema above.

## Workflow

### Step 0: First-run setup

Read `coclerk.json`. Check for `time_tracking.sources`. If absent or empty,
run the first-setup protocol at `protocols/FirstSetup.md`. On subsequent runs
this check passes through immediately.

### Step 1: Resolve target range

Default target is today in the practitioner's local timezone. Accepted user
inputs: a single date ("build timeline for 2026-04-15"), a relative date
("yesterday", "today"), or a range ("build timeline for this week"). Interpret
the input in local time (from `coclerk.json` → `time_tracking.timezone`),
then convert to UTC for the concrete `[start_ts, end_ts]` pair used
downstream. For example, "2026-04-15 in Vancouver" becomes the UTC range
`[2026-04-15T07:00:00Z, 2026-04-16T07:00:00Z)` during PDT.

### Step 2: Iterate over enabled sources

For each source in `coclerk.json` → `time_tracking.sources` where `enabled` is
true, perform the source-specific fetch per its reference file:

- **TimeCamp** — `reference/TimeCamp.md`
- **Google Calendar** — `reference/GoogleCalendar.md`
- **Telus Business Connect** — `reference/TelusConnect.md`
- **Downloads folder** (future) — `reference/Downloads.md`

A failed source must never block other sources. Record the failure and
continue. Surface all failures to the practitioner in the final summary — do
not silently omit data.

### Step 3: Normalize each raw record

For each raw record returned by a source:

1. Decide whether it is an **activity** (has meaningful start + end) or an
   **event** (single timestamp only).
2. Compute the row ID: `{source}:{native_id}`. Refer to the source's reference
   file for how `native_id` is derived.
3. Build the row per the activity/event schemas above.
4. Do not make classification decisions. Do not collapse overlaps. Do not
   drop records because they overlap with another source. Each source's
   records are stored independently.

### Step 4: Replace-by-source within range

Before inserting new rows for a given source and range:

1. Load `index:activity:by-source:{source}` and `index:event:by-source:{source}`.
2. For each id, load the row and check whether its timestamp (for events) or
   interval (for activities) falls within the requested range. Activities that
   overlap the range — even partially — are considered in-range.
3. Delete every in-range row (`activity:{id}` or `event:{id}`) and remove its
   id from the by-source and by-date indexes.
4. Insert the freshly-fetched rows and update all indexes.

The practical effect: re-fetching Telus for 2026-04-15 wipes only Telus rows
in that date; TimeCamp and GCal rows for the same day are untouched.

Note on stable IDs: because IDs are derived from source + native_id, a row
that existed before and still exists now gets the same ID both times. Any
downstream classification or correction record keyed to that ID continues to
point to valid data.

**Scaling note:** Step 4.2 scans every id in `index:activity:by-source:{source}`
to find the in-range rows, which is O(all rows from that source) on each
fetch. At daily/weekly scale with a single-user practice this is cheap, but
row counts will grow unbounded over months. When a fetch starts taking more
than a second or two, add a sharded index like
`index:activity:by-source-and-date:{source}:{YYYY-MM-DD}` so replace-by-source
can load only the dates touched by the requested range.

### Step 5: Update source metadata

After a successful fetch:

- Set `source:{source}:fetched_at` to now.
- Update `source:{source}:ranges` by taking the union of the existing stored
  ranges with the newly-fetched range, then normalizing. Normalization: sort
  ranges by start_ts; merge any two ranges where the earlier's end_ts is
  greater than or equal to the later's start_ts (touching or overlapping
  intervals collapse into one). The result is a minimal, non-overlapping,
  sorted list of `[start_ts, end_ts]` pairs expressing exactly which instants
  this source has been fetched for.

If the fetch failed, leave both keys untouched.

### Step 6: Report

Print a one-line summary per source plus an overall total:

```
TimeCamp:  47 activities fetched for 2026-04-15 (18 new, 29 replaced)
Telus:     3 activities fetched for 2026-04-15 (3 new, 0 replaced)
GCal:      4 activities fetched for 2026-04-15 (4 new, 0 replaced)
Downloads: 12 events fetched for 2026-04-15 (12 new, 0 replaced)

Total: 54 activities, 12 events stored in timeline.
```

If any source failed, list the failures explicitly:

```
Telus: failed — CSV not found at C:/Users/Brahm/Downloads/telus-2026-04-15.csv
```

Do not present the fetched rows as a table unless the practitioner asks. See
Queries below.

## Queries

| Question | How to answer |
|----------|---------------|
| Build today's timeline | Full workflow for today. |
| Build the timeline for 2026-04-15 | Full workflow with target=2026-04-15. |
| Re-import Telus CSV at {path} for {date} | Run Telus source only, with the supplied CSV, target={date}. Replaces only Telus rows in that range. |
| What sources are fetched for {date}? | Read `source:{source}:ranges` for each known source; report which cover {date}. |
| Show me the raw timeline for {window} | Require a window ≤ 60 minutes. Load `index:activity:by-date:{date}` and `index:event:by-date:{date}`, filter to the window, sort by start_ts/ts, present as a table with columns: Time, Duration (activities only), Source, Raw Type, Key Fields. |
| When was {source} last fetched? | `cowork-db get timeline "source:{source}:fetched_at"` |

## Display rules

The practitioner can ask to inspect the raw timeline, but:

- The window must be **≤ 60 minutes**. If a larger window is requested, ask
  the practitioner to narrow it — full-day dumps are what downstream skills
  are for, not this one.
- The Time column is rendered in the practitioner's local timezone (from
  `coclerk.json` → `time_tracking.timezone`), even though rows are stored in
  UTC. Conversion happens at render time only.
- Overlapping activities are shown as separate rows, sorted by start time.
  When an activity's start falls inside another activity already printed,
  prefix its row with `↳ ` (U+21B3) to make the overlap visible at a glance.
  Do not collapse overlapping rows.
- Events are interleaved with activities by timestamp (events have no
  Duration value; the column reads `—`).
- Show `raw_type` and the most useful raw_payload fields (e.g., window title
  for TimeCamp, phone number for Telus, event title for GCal). Do not show a
  `task`, `matter`, or `category` column — those are classification concerns
  and this skill does not produce them.

## Integration with other skills

| Skill | How it integrates |
|-------|-------------------|
| **time-sorting** | Consumes `activity:*` and `event:*` rows via the by-date indexes. Handles reconciliation, gap-filling, and task assignment. Writes its results under a separate namespace. |
| **retainer-tracking** | Independent — build-timeline does not need the matter list. Classification does. |
| **time-entry-drafting** | Reads the classified day from time-sorting, not from build-timeline directly. |

## Critical constraints

- **Read-only sources.** Never write back to TimeCamp, Google Calendar, Telus,
  or any other source. This skill is strictly downstream of those systems.
- **No silent data loss.** Every source either succeeds (rows stored, indexes
  updated, metadata recorded) or fails loudly (reported in the summary).
  There is no middle state.
- **No interpretation.** If there is a choice to make about what a period
  "really was," defer it. This skill's job is faithful recording.
