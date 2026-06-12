---
name: dates-and-deadlines
description: Manage BC litigation deadlines for active matters. Use when the practitioner uploads a court document (Notice of Trial, Trial Management Conference Order, court orders containing deadlines), asks what deadlines exist for a matter, needs to record or update a court date, reports a trial adjournment, or asks about limitation periods. Handles anchor date extraction, source reconciliation, BC rule-based derived deadline calculation, and cascade recalculation when dates change. Invoke whenever a document that could contain a court date is mentioned, even if the practitioner doesn't explicitly ask about deadlines.
user-invocable: true
---

# Dates and Deadlines

Pure data skill — extracts, calculates, and stores deadline data for BC litigation matters. Scope is BC only: BC Limitation Act (SBC 2012, c 13), BC Supreme Court Civil Rules, BC Court of Appeal Rules.

Does not rank, surface urgency, or alert. Those belong to `executive-assistant`.

## Database

All data access via `/practice-data`. Tables for anchors, anchor sources, and deadlines are defined in `/practice-data`'s schema. This skill uses the `upsert-anchor`, `upsert-deadline`, and `active-deadlines` operations.

## Core Workflows

### 1. Store anchor from document

When the practitioner uploads or references a document containing a court date:

1. Extract the date and identify the anchor type
2. **If extraction is uncertain** — date is ambiguous, document is unclear, multiple interpretations exist, or no date is found — stop immediately and tell the practitioner exactly what was unclear. Never guess.
3. Invoke `/practice-data` `upsert-anchor` to check for an existing anchor matching this matter and anchor type
4. **No existing anchor:** create the anchor (status: active) and record the source (status: confirmed) via `/practice-data`, proceed to [Derive deadlines](#2-derive-deadlines)
5. **Existing anchor, dates match:** record the new source (status: confirmed) via `/practice-data`, proceed to [Derive deadlines](#2-derive-deadlines)
6. **Existing anchor, dates conflict:** record the new source (status: conflicted) and set the anchor status to conflicted via `/practice-data`. Surface the conflict: show both dates and their source documents. Do not calculate any deadlines. Wait for the practitioner to resolve before proceeding.

### 2. Derive deadlines

Read `references/bc-rules.md` for the current rule set. Apply all rules appropriate to the anchor type.

For each applicable rule:
1. Calculate the deadline date from the anchor date
2. Check for an existing deadline row with the same `matter_id`, `anchor_id`, and `deadline_type`
3. If existing: set old row `status='superseded'`, insert new row
4. If new: insert row

For **order terms** (rules stated in a court order rather than BC statute):
- Extract each term as stated in the order
- Store with `source_type='order_term'`, `source_document` = order name/date
- `rule_ref` = the paragraph or term number in the order; `rule_description` = the term as written

After writing all derived deadlines, report a summary table to the practitioner showing deadline type, date, and rule source.

### 3. Cascade recalculation on anchor change

When the practitioner updates an anchor date (adjournment, correction, etc.):

1. Record the new source document in `anchor_sources`
2. Update `anchors.anchor_date` and `anchors.updated_at`
3. Retrieve all `deadlines` rows where `anchor_id = this anchor AND source_type IN ('bc_rules', 'order_term') AND status = 'active'`
4. For each row, recalculate the deadline date using the same `rule_ref` and the new anchor date
5. Set old rows `status='superseded'`, insert recalculated rows
6. Report: each deadline type with old date → new date

**Manual deadlines** (`source_type='manual'`) are never auto-recalculated. After cascade, flag them: "These manually-entered deadlines were not recalculated — please review: [list with dates]"

### 4. Resolve anchor conflict

When the practitioner provides the authoritative date to resolve a conflict:

1. Update `anchors.anchor_date` to the authoritative value, set `status='active'`
2. Update each `anchor_sources` row: set `status='confirmed'` for sources that match the authoritative date, `status='conflicted'` for those that don't
3. Proceed to [Derive deadlines](#2-derive-deadlines) then [Cascade recalculation](#3-cascade-recalculation-on-anchor-change) for any existing derived deadlines

### 5. Query deadlines for a matter

When the practitioner asks what deadlines exist:

1. Invoke `/practice-data` `active-deadlines` for the matter — returns all active deadlines ordered by date, and any conflicted anchors
2. If any anchors are conflicted, report them prominently before the deadline list

## Uncertainty Rules

Stop and ask — never store a date you're not confident in:

- Date is ambiguous (e.g., "sometime in March", "next Tuesday")
- Document references a date by offset without stating the base date (e.g., "7 days after service" — service date unknown)
- Extracted date is inconsistent with context (e.g., trial date is already past)
- Two parts of the same document give different dates for the same event

State exactly what you found and what you need the practitioner to clarify.

## References

- `references/bc-rules.md` — BC court rule deadlines, organized by anchor type. Read before calculating any derived deadlines.

## Anti-Patterns

- **Storing a date you're uncertain about** — a wrong deadline is worse than a missing one
- **Calculating derived deadlines before reconciling sources** — always reconcile first
- **Auto-recalculating manual deadlines** — these require practitioner judgment
- **Ranking or surfacing urgency** — that is `executive-assistant`'s job
