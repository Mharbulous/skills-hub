---
name: prioritizing
---

# Prioritizing

The single recommendation engine for what to work on next. Combines retainer status, WIP accumulation, retainer age, and impending deadlines into a ranked daily file list. Extends file-prioritization's static retainer-first model with dynamic scheduling factors.

Owns the daily scheduled check — surfaces the most important approaching work across all active matters. Consumes deadline data from `dates-and-deadlines` (via shared DB) alongside retainer, WIP, and matter status data to produce a unified prioritized recommendation. This is the only skill that tells the practitioner what to work on next; `dates-and-deadlines` and other data skills have no surfacing or alerting responsibility.

**Status:** Not yet implemented.
