# Deferred memo: Chain of custody for real evidence

> **v6 status:** Trigger language references eliminated tables and columns (`ev.evidence_items`, `evidence_type = 'real'`, `evidence_items.deemed_undertaking`). In v6.1, there is no `evidence_type` field — sources have `category` (court, correspondence, production, work_product, disbursements). Real/physical evidence would be a `production`-category source. The chain-of-custody problem is narrower now and the proposed direction needs fresh design against v6.1 schema.

## Problem

`ev.evidence_items` records `evidence_type = 'real'` but has no structure to track the chain of custody — collection details, transfers between custodians, storage conditions, or integrity challenges — that courts require before admitting a physical exhibit. Without this structure the schema cannot answer "who has had possession of this item, when, and in what condition?" and cannot support the foundation proof that makes a real exhibit admissible.

## Insights

Real evidence appears rarely in BC civil litigation. Personal injury matters (clothing, vehicle parts) and property disputes (physical samples, documents) are the main triggers; commercial and family matters almost never have real evidence. The rarity means the current gap is survivable — the lawyer's own records serve as the de facto chain.

Chain of custody is structurally a provenance chain: each link is a transfer event with a transferor, a transferee, a date, a location, and a condition note. This is the same SCD-Type-2 pattern the rest of the schema uses for history (bitemporal columns on `ev.evidence_items`). The custody chain could be expressed as a `ev.custody_events` table with a simple `evidence_id` FK and ordered events.

The deemed-undertaking flag (`evidence_items.deemed_undertaking`) interacts with chain of custody: items obtained via compelled disclosure that are physical objects carry both a deemed-undertaking obligation and a chain-of-custody requirement. The intersection is narrow enough to be handled by the lawyer's notes, not the schema, until a real trigger arrives.

## Direction (non-binding)

Add a `ev.custody_events` table: `event_id`, `evidence_id` FK, `custodian_party_id` FK (trigger-enforced ev → core), `from_party_id` FK (nullable), `event_type` (collection / transfer / storage / examination / production), `event_date`, `location`, `condition_note`, `source_ref`. Each row records one link in the chain. The full chain for an item is the ordered set of rows for that `evidence_id`.

## Left open

- Whether custody events need a separate `external_custodians` table (police, labs, experts who are not `core.parties` to the proceeding)
- Whether condition notes need a structured integrity-assessment field (e.g., a flag for "chain challenged by opposing party")
- Whether custody tracking should be limited to `evidence_type = 'real'` rows or made available to all evidence types (sometimes documents also have a custody history — e.g., a will in a vault)

## When this memo fires

Invoked when:
- A matter has `ev.evidence_items` rows with `evidence_type = 'real'` and counsel needs to record the chain of custody to establish foundation for admission.
- Opposing counsel challenges the authenticity or integrity of a physical exhibit and the file needs a documented chain.
- A real evidence item has been in multiple custodians' hands (police → lab → lawyer → court) and counsel needs to be able to trace each transfer.

Do NOT fire this memo for matters without real evidence — `evidence_type IN ('document','lay_witness','expert_witness','judicial_notice')` items do not have chain-of-custody requirements in BC civil practice.
