---
name: wip-tracker
description: >
  WIP Tracker — the authoritative source of unbilled work-in-progress per matter. Use this skill
  whenever the user asks about WIP, unbilled time, accumulated hours, retainer headroom, burn rate,
  how much work is sitting on a file, or whether a retainer can cover pending work. Also use when
  the user asks which files have unbilled time, which matters are approaching their retainer ceiling,
  or mentions "WIP" in any billing context. Downstream skills (ar-follow-up, executive-assistant,
  file-prioritization, billing-summary) should query this skill's logic rather than computing WIP
  themselves.
---

# WIP Tracker

Authoritative source of unbilled work-in-progress per matter. For each active matter, identifies the billing cutoff date, sums time entries recorded since that date, calculates retainer headroom when a billing rate is known, and flags matters with a funded retainer but no recorded activity in over 15 days.

Read `vision.md` for the full design philosophy. The four principles that govern every output:

1. **Never serve a wrong WIP total.** When data is incomplete or ambiguous, surface the uncertainty explicitly rather than guessing. A wrong number corrupts every downstream consumer.
2. **Unknown is not zero.** A matter with no time entries since the billing cutoff may have unrecorded work. Report "no data recorded since [date]" rather than $0 or 0.0 hours.
3. **Show the period, not just the total.** Every WIP figure includes its time anchor — the billing cutoff date and the range it covers. "$2,400 in WIP" is meaningless without "Feb 1 – present."
4. **Surface failures explicitly — never silently skip.** If the billing cutoff cannot be determined, say so. If the retainer balance is unavailable, say so. The practitioner cannot act on a gap they cannot see.

## Scope

This skill **reads and reports**. It does not create time entries, generate invoices, recommend when to bill, or calculate tax. It answers one question: "How much unbilled work is on this file, and is there enough retainer to cover it?"

## Data Sources (Read-Only)

All data accessed via `/practice-data` operations. This skill does not own or modify any data.

| Source | What it provides |
|--------|-----------------|
| Time entries | Recorded time since billing cutoff |
| Invoices | Billing cutoff date (most recent invoice issue date — *degrade gracefully if unavailable*) |
| Matters | Trust balance per matter |
| Clients | Client name and number |

**Sign convention:** The accounting system (UNITY) stores funded trust balances as negative numbers (`regular_trust < 0` = funded, `regular_trust = 0` = depleted). When presenting trust balances to the user, always use `abs(regular_trust)`. Internally, funded-retainer checks use `regular_trust < 0`.

### Known Limitation: Billing Cutoff Proxy

The vision defines the billing cutoff as "the day after the `date_to` field on the most recent invoice" — the actual end date of the period billed. The `invoices` table currently stores only `issue_date` (when the invoice was sent), not `date_to`. An invoice issued April 15 might cover work through March 31. Using `issue_date` as the cutoff may undercount WIP by excluding already-billed entries between the period end and the issue date.

This is the best available proxy. Always surface it in output: "Cutoff based on invoice issue date — actual billing period end may differ."

**Migration path:** When `invoice-tracking` adds a `date_to` column to the `invoices` table, this skill should switch to `date_to + 1 day` as the billing cutoff. Until then, `issue_date` is the proxy, and the output caveat is mandatory.

### Graceful Degradation

Three upstream dependencies may be absent. Each produces a specific message — never silently substitute zero.

| Condition | Meaning | Action |
|-----------|---------|--------|
| `invoices` table does not exist | Invoice-tracking schema not yet added | Cannot determine billing cutoff. Report all `time_entries` for the matter with note: "No invoice data available — showing all recorded time entries. Billing cutoff unknown." |
| No `invoices` rows for a matter | No invoices imported for this matter | Same as above for that matter. Other matters with invoice data use their cutoff normally. |
| `time_entries` empty for a matter (but retainer funded) | Possible unrecorded work | Flag: "No time entries recorded since [cutoff]. This does not mean zero WIP — work may not have been entered." |
| `matters.regular_trust` is NULL | Retainer data never imported | Cannot compute headroom. Report WIP hours/dollars only. Note: "Trust balance unavailable — retainer headroom cannot be calculated." |
| `time_entries` table exists but matter has no entries at all | No time data for this matter | Report: "No time entries on file for this matter." |

**Implementation:** `/practice-data`'s `wip-hours` operation handles graceful degradation internally — if invoice data is unavailable, it returns results without cutoff filtering and signals that invoice data was absent.

## Database Access

All data access via `/practice-data` `wip-hours` operation. This skill never writes — read-only access only.

## Billing Rate

WIP in dollars requires a billing rate. The `time_entries` table stores hours only — no rate column.

- **If the practitioner has previously provided a rate** (stored in conversation context or a future config field): use it to compute `wip_dollars = total_hours * rate`.
- **If no rate is known:** report WIP in hours only. Do not compute headroom (hours and dollars cannot be compared). State: "Billing rate not provided — WIP reported in hours. Provide a rate to calculate dollar amounts and retainer headroom."
- **When the practitioner provides a rate:** use it for the current calculation and note: "Using $[rate]/hr for WIP calculations."

Retainer headroom (`abs(regular_trust) - wip_dollars`) is meaningful only when both the trust balance and a billing rate are available. When presenting trust balances in output, always use `abs(regular_trust)` — the raw value is negative for funded matters (UNITY convention).

## Workflow: WIP Summary (All Matters)

Triggered by: "show WIP", "unbilled time across files", "WIP report", "which files have unbilled work."

1. Resolve DB path per `practice-data/SKILL.md`
2. Run the consolidated WIP query (see below)
3. For each matter with time entries since the cutoff:
   - Report the billing cutoff date and WIP hours
   - If a rate is known, report WIP dollars and retainer headroom
   - If retainer is funded but no entries recorded in 15+ days, flag as suspicious silence
4. Present results in the summary format

### WIP Data Retrieval

Invoke `/practice-data` `wip-hours` operation for all non-closed matters. The operation returns per-matter:
- Matter description and identifiers
- Client name and number
- Trust balance and last update date
- Billing cutoff date (from most recent invoice, if available)
- Total hours, entry count, earliest and latest entry dates since cutoff

**Graceful degradation:** If invoice data is unavailable, the operation returns all time entries (no cutoff filtering) and sets the cutoff date to null. Always note this in output.

## Suspicious Silence Detection

A matter qualifies as "suspicious silence" when ALL of these are true:

1. The retainer is funded (`regular_trust < 0`)
2. The most recent time entry is more than 15 days ago (or there are no entries since the cutoff)
3. The matter is not closed

This means the practitioner has a funded retainer but no recorded work activity — either the work is happening without time entries, or the file has gone dormant without the practitioner realizing it.

Flag these matters separately in the output with: "No time entries recorded since [date] — [N] days of silence on a funded retainer."

## Workflow: Single Matter WIP

Triggered by: "WIP on [matter]", "how much is sitting on [file]", "unbilled time for [client/matter]."

1. Resolve the matter by file number, matter number, or client name
2. Run the per-matter query
3. Present the full breakdown

### Output Format (Single Matter)

```
Smith (C1234) — File L3948 (Smith v Jones)

Billing cutoff:          2026-03-15 (most recent invoice issue date)
                         ⚠ Cutoff based on invoice issue date — actual period end may differ
WIP period:              2026-03-16 – present (39 days)
Time entries:            18.5 hours across 12 entries
                         Earliest: 2026-03-18  Latest: 2026-04-20

[If rate known:]
WIP amount:              $3,700.00 (18.5 hrs × $200/hr)
Trust balance:           $4,200.00 (as of 2026-04-01)
Retainer headroom:       $500.00
                         ⚠ Approaching retainer ceiling — 88% consumed

[If rate unknown:]
WIP amount:              Cannot calculate — billing rate not provided
Trust balance:           $4,200.00 (as of 2026-04-01)
Retainer headroom:       Cannot calculate (hours vs dollars)
                         Provide a billing rate to compute dollar amounts.

[If no invoice on record:]
Billing cutoff:          Unknown — no invoices on record for this matter
WIP:                     18.5 hours across 12 entries (all recorded time)
                         ⚠ All time entries shown — cannot determine which have been billed
```

### Output Format (WIP Summary)

```
WIP Summary — 2026-04-23
Data as of: trust balances [last_trust_date], time entries through [latest entry date]
[Note any missing data: "Invoice data unavailable — all time entries included, billing cutoff unknown"]
[If rate used: "Using $200/hr for WIP calculations"]

Matter              Client           Cutoff      Hours   WIP $      Trust $    Headroom
─────────────────── ──────────────── ─────────── ─────── ────────── ────────── ──────────
L3948 Smith v Jones Smith (C1234)    2026-03-15  18.5    $3,700     $4,200     $500 ⚠
L4021 Doe v Roe     Doe (C5678)      2026-02-28  24.0    $4,800     $8,000     $3,200
L4100 Chan Estate   Chan (C9012)     —           6.0     $1,200     $3,000     $1,800

⚠ Suspicious Silence (funded retainer, no activity 15+ days):
L4055 Park v West   Park (C3456)     2026-04-01  —       —          $5,000     —
  No time entries recorded since 2026-04-01 — 22 days of silence on a funded retainer

Notes:
- Cutoff based on invoice issue date — actual billing period end may differ
- [Matter] has no invoices on record — all time entries shown
```

When WIP dollars or headroom cannot be computed (no rate), omit those columns entirely rather than showing blanks — switch to a narrower format with Hours only.

## Queries

| Question | Action |
|----------|--------|
| Show WIP / WIP report | Full WIP summary workflow |
| Which files have unbilled time? | WIP summary, filtered to matters with `total_hours > 0` |
| WIP on [matter/file] | Single matter workflow |
| How much is sitting on [file]? | Single matter workflow |
| Retainer headroom for [matter] | Single matter workflow (requires rate) |
| Which files are approaching the retainer ceiling? | WIP summary, filtered to headroom < 20% of trust balance |
| Any files with no activity? | Suspicious silence detection only |

## Integration with Other Skills

| Skill | Relationship |
|-------|-------------|
| **practice-data** | Owns schema and path resolution. All queries go through the practice DB. |
| **invoice-tracking** | Provides billing cutoff via `invoices.issue_date`. Without it, cutoff is unknown. |
| **retainer-tracking** | Provides `matters.regular_trust` for headroom calculation. |
| **time-entry-drafting** | Creates time entries that this skill reads. New entries are immediately visible. |
| **ar-follow-up** | Consumes WIP data to build the consolidated AR picture per client. |
| **executive-assistant** | Queries WIP to surface files approaching retainer ceiling. |
| **file-prioritization** | Uses WIP accumulation as a ranking signal. |
| **billing-summary** | May query WIP data for billing prep reports. |

## Anti-Patterns

- **Treating absence as zero.** No `time_entries` rows since cutoff ≠ zero WIP. No `invoices` row ≠ billing cutoff of today. No `regular_trust` value ≠ no retainer. Each is a distinct unknown that must be surfaced.
- **Substituting `issue_date` silently for `date_to`.** Always note in output that the cutoff is based on invoice issue date, which is a proxy.
- **Computing headroom without a rate.** Hours minus dollars is meaningless. When no rate is available, report hours and trust balance separately — do not attempt to compare them.
- **Caching or storing WIP totals.** WIP is always computed on demand from `time_entries` and `invoices`. Storing a pre-computed value creates a stale-data risk with no performance benefit at sole-practitioner scale.
- **Defining schema or CREATE TABLE.** Schema belongs to `practice-data/SKILL.md`.
- **Querying upstream CSVs directly.** All data enters through the practice database import workflows. Never parse accounting CSVs.
- **Recommending when to bill or what to write off.** This skill reports the numbers; the practitioner decides what to do with them.
- **Rounding or truncating hours.** Report time entries at the precision stored in the database. The practitioner's rounding policy (if any) is applied at billing time, not at WIP reporting time.
- **Displaying raw negative trust values to the user.** Always `abs(regular_trust)` in output. The raw negative value is an internal convention, not something the practitioner should see.
