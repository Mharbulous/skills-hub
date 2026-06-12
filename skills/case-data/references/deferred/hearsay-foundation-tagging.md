# Deferred memo: Hearsay exception / business-records foundation tagging

> **v6 status:** Trigger language references eliminated tables (`ev.evidence_items`, `ev.fact_evidence_contests`). The underlying problem (hearsay challenge tracking) may still be relevant but the proposed direction needs fresh design against v6.1 schema. In v6.1, evidence is `evidence_links` connecting `sources` to `facts` — there is no `evidence_type` field on evidence anymore and no `fact_evidence_contests` table.

## Problem

`ev.evidence_items` has no structured field for hearsay exceptions or the foundation elements required to invoke them. When opposing counsel objects to a document's admissibility on hearsay grounds at trial, there is nowhere in the schema to record: the basis of the objection, the exception claimed, or the foundation materials needed to establish the predicate (e.g., a Rule 7-1(3) affidavit or a business-records certification under BC Evidence Act s.42).

## Insights

Hearsay challenges in BC civil practice are resolved at voir dire, not in pre-trial pleadings. Pre-trial tagging of every document with a potential hearsay exception adds ingestion overhead that rarely affects strategy — the vast majority of documents admitted at trial are admitted by consent or under a routine exception whose foundation is obvious. The schema overhead pays off only when a specific item is challenged.

The `fact_evidence_contests` table (`contest_basis IN ('hearsay', 'admissibility')`) is the natural home for recording a hearsay challenge once it arises. The gap is not a challenge record — that exists — but a structured foundation record: what exception is claimed, and what is the supporting foundation (rule citation, foundation documents).

The `judicial-notice-semantics.md` memo (eligibility vs. actual-notice event) is structurally adjacent: both problems involve distinguishing a static property of an evidence item (could be admitted on this basis) from a trial event (was admitted, via this exception, on this ruling). The two-memo cluster may resolve together.

## Direction (non-binding)

Add a `hearsay_exception` column to `ev.fact_evidence_contests` (only relevant when `contest_basis = 'hearsay'`): an enum of the common BC exceptions (business records s.42, public documents s.29, electronic records s.41, prior consistent statement, res gestae, etc.). Add a `foundation_doc_id` FK to `core.documents` (trigger-enforced, ev → core) pointing at the affidavit or certificate that establishes the predicate.

Do not add hearsay tagging to `ev.evidence_items` as a pre-ingestion field — that conflates potential and actual challenge, and pre-tagging every document is not how BC civil practice works.

## Left open

- Whether the exception enum should track the specific s.41/s.42/s.29 distinction or use a broader grouping
- Whether the foundation document linkage needs its own junction table (one item, multiple foundation docs)
- Whether and how the `judicial-notice-semantics.md` resolution changes this design (both may want an "admissibility event" sub-table under `fact_evidence_contests`)

## When this memo fires

Invoked when:
- Opposing counsel challenges the admissibility of a specific document on hearsay grounds and the file needs a structured record of the exception claimed and its foundation.
- A voir dire is scheduled on a specific document's admissibility.
- Counsel needs to answer "which evidence items have outstanding admissibility challenges, and what foundation materials are prepared for each?"

Do NOT fire this memo for routine document ingestion — pre-tagging every document with a potential hearsay exception is not warranted until a challenge arises on a specific item.
