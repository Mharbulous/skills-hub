# Deferred memo: Mediation / ADR event tracking

## Problem

The schema has no structured record of mediation or ADR events. A mediation date, mediator, and outcome are invisible. More importantly, a binding partial settlement — one that disposes of some but not all facts — cannot be recorded in a way that updates the fact posture model. The settlement agreement is a source (`sources`), and the facts it resolves can be entered as `positions` rows (`position = 'admit'`, sourced to the settlement document). But there is no place to record the mediation event itself or link settled facts to the mediation that produced the settlement.

## Insights

Most mediation outcomes do not require schema-level tracking: a failed mediation produces no binding positions, and a successful mediation produces a settlement agreement (a source) whose per-fact consequences flow naturally to `positions`. The schema gap only bites when a partial settlement resolves some facts but not others and counsel needs to distinguish "facts admitted in the settlement agreement" from "facts admitted in pleadings" or "facts still disputed."

The existing `positions` model handles the settlement-agreement admission correctly — the settlement agreement is a source, the admission is a `position = 'admit'` row sourced to that document via `source_id`. The gap is not position tracking; it is event tracking (when did the mediation occur, who was the mediator, what was the outcome at the event level rather than the fact level).

ADR events are matter-management data, but they have a case-data angle when the ADR produces binding positions. This places them at the boundary between the practice DB (which tracks matter-management events) and main.sqlite (which tracks fact and position history).

## Direction (non-binding)

Add an `adr_events` table (in main.sqlite): `event_id`, `proceeding_id` FK, `event_type` (mediation / arbitration / settlement_conference / judicial_settlement_conference), `event_date`, `mediator_name`, `outcome` (failed / settled / partial_settlement / ongoing), `settlement_source_id` FK (nullable, → `sources`), `source_ref`. One row per ADR event.

For partial settlements, the per-fact consequences are still recorded on `positions`; `adr_events` is the header. A view or query can join `adr_events` to `positions` via `positions.source_id = adr_events.settlement_source_id` to show "facts settled at mediation vs. facts still disputed."

## Left open

- Whether the practice DB (which tracks matter-management events like mediations) should be the owner, with the case-data DB only receiving the per-fact consequence rows on `positions`
- Whether without-prejudice session notes (never producible) should be recorded in `privileged_sources` (in privileged.sqlite) and whether the event record should FK to such notes
- Whether a multi-session mediation should be one `adr_events` row (with a `sessions` sub-table) or multiple rows

## When this memo fires

Invoked when:
- A mediation produces a partial settlement that resolves some facts but not others and counsel needs to track which facts are agreed vs. still disputed.
- Counsel needs to report "when did the mediation occur and who was the mediator?" to the court in a case-management context.
- A matter has multiple ADR events (e.g., failed mediation followed by settlement conference) and counsel needs to distinguish the outcomes of each.

Do NOT fire this memo for matters where mediation either failed entirely (no binding positions result; no schema change needed) or produced a full settlement (action dismissed; the schema becomes read-only). The existing `positions` model handles partial-settlement position recording adequately until the event-header structure is needed.
