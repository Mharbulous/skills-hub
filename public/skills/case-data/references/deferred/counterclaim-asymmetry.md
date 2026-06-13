# Deferred memo: Counterclaim posture asymmetry

## Problem

`v_fact_status` aggregates responses across all pleadings per fact. When a fact appears in both an originating pleading and a counterclaim, the responding parties differ (defendants respond to the originating pleading; plaintiff responds to the counterclaim) — global aggregation produces misleading posture. A fact the plaintiff "admitted" in response to the counterclaim is not the same posture as the plaintiff's claim-side assertion of the same fact.

## Insights

The `positions` table already supports multi-pleading assertion (one row per (fact, party, source)). Response interpretation is inherently per-(fact, proceeding). Global aggregation is a simplification that works until a fact spans proceedings; the simplification is fine for the common case and does not block correct design later. The existing architecture is not wrong — it is pre-generalized.

## Direction (non-binding)

Reshape posture computation around `(fact_id, proceeding_id)` grouping. Keep a unified-posture convenience for the common single-proceeding case so existing queries do not break.

## Left open

- Whether to retain a unified-posture convenience for the common single-proceeding case, or require every consumer to pick a proceeding
- How to render this in `v_fact_status` (per-proceeding rows? additional join key? companion view?)

## When this memo fires

Invoked on any matter that includes a counterclaim, response to counterclaim, third-party notice, or response to third-party notice — i.e., any matter where `sources.category = 'court'` includes pleadings of those types. This is the common case in defended actions.

Specifically invoked when:
- A fact is asserted in both an originating pleading and a counterclaim, and posture queries aggregate across all proceedings rather than per-(fact, proceeding).
- A user asks "what is the posture of fact X against the plaintiff by counterclaim?" and the current view returns a misleading aggregate.
- A matter has a third-party notice and the same fact has different response postures between the main action and the third-party proceeding.

Do NOT fire this memo for single-proceeding matters with no counterclaim or TPN — the current aggregation is correct by construction in that case.
