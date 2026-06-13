# Deferred memo: Judicial notice semantic ambiguity

> **v6.1 note:** The `judicially_noticeable` column was removed from `facts` in v6.1 (the column no longer exists). The underlying problem remains valid — if judicial-notice tracking is ever re-added, the eligibility-vs-event distinction described here must be addressed. The trigger fires when judicial-notice functionality is being designed or re-introduced.

## Problem

`facts.judicially_noticeable` is ambiguous (in schemas that carry it). It could mean "eligible for judicial notice" (static property set by the lawyer) or "the court has taken judicial notice" (event with a hearing date and source). These are legitimate but distinct concepts; conflating them blocks both "which eligible facts still need noticing?" and "when did the court notice fact X?".

## Insights

Eligibility is static; actual notice is an event. Actual-notice events are a kind of court determination (out of scope in v6.1 — see CLAUDE.md §9). Unifying the two into one column is what caused the ambiguity; the fix is to split the concepts, not tweak the column.

## Direction (non-binding)

Rename the existing flag to something that clearly indicates eligibility only (e.g., `jn_eligible`). Route actual-notice events into the court-determinations table alongside other findings. Keep the eligibility flag cheap — it is a property, not a history.

## Left open

- Whether eligibility needs structured basis (common knowledge, readily verifiable, authoritative source)
- Whether a rename requires a migration path for existing `judicially_noticeable = 1` rows (most likely: they are all eligibility claims and the migration is a column rename)

## When this memo fires

Invoked when:
- A user asks "which eligible-for-judicial-notice facts have not yet been noticed?" — the current schema cannot answer this.
- The court takes judicial notice of a fact on the record, and the user wants to record that event distinctly from the eligibility flag.
- A pleading specifically invokes judicial notice (e.g., "the Plaintiff requests that the court take judicial notice of...").

Do NOT fire this memo for routine fact ingestion where `judicially_noticeable = 1` is being set as an eligibility assessment. That current usage is fine until the ambiguity starts to bite.
