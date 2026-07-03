---
name: review-plan
description: "Review an implementation plan for flaws and improvement opportunities, sanity-check it against the actual codebase, and produce an improved version."
---

# Review Plan

Launch a **read-only subagent** (subagent_type: `code-reviewer`) to review the plan
below. This applies even when the main agent is already running the chosen model — the
point is an independent second opinion in a fresh context, not self-review.

## Model Selection

**Default model is `fable`** (Fable 5). Before doing anything else, check whether the
plan text below opens with an override line of the form `using <model>` (e.g. `using
Opus 4.8`, `using Sonnet`, `using Haiku 4.5`). If it does:
- Strip that line out — it is an instruction to you, not part of the plan — and pass the
  remaining text as "Plan to review" to the subagent.
- Map the named model to the Agent tool's family alias (`sonnet`/`opus`/`haiku`/`fable`)
  and use that alias instead of the `fable` default.
- If the name doesn't clearly map to one of those families, ask the user to clarify
  rather than guessing.

If there is no `using <model>` line, use the full plan text as-is and default to
`fable`.

"Best available" means best by name **and version number**, not just family. The Agent
tool's `model` param only accepts a family alias (`sonnet`/`opus`/`haiku`/`fable`) — the
harness resolves that alias to a specific version, and the resolved version can lag
behind the newest release in that family (e.g. an `opus` alias resolving to Opus 4.6
when Opus 4.8 was already out). Before spawning, cross-check the resolved family alias
(default or user-overridden) against the most-recent-models line in your
environment/system info. If it looks like it could resolve to a stale version, say so to
the user instead of silently proceeding.

Note: `fable` (Fable 5) is currently the best available model by default and is only
temporarily accessible on subscription plans — it will become API-only and unavailable
here. When that happens, switch the default above back to `opus` (or whatever is then
the best available subscription model), and re-verify against the current-models line
per the paragraph above. This default-model note does not apply when the user has
explicitly overridden the model via a `using <model>` line.

## Subagent Instructions

The subagent has read access to the repo (`Glob`/`Grep`/`LS`/`Read`) — it should use it,
not review the plan in a vacuum.

The subagent should:

1. **Codebase sanity check** — Before critiquing the plan's internal quality, read the
   actual code the plan touches and form an opinion on whether implementing this plan
   would genuinely improve on what's there now. Would it actually leave the codebase
   better, or is it solving a non-problem, duplicating existing functionality,
   overengineering something simple, or introducing regressions? State the verdict
   plainly (e.g. worth implementing / worth implementing with changes / not worth
   implementing) and ground it in what the code actually does, not just whether the plan
   is internally coherent.
2. **Analysis** — Briefly list the flaws found and improvements identified.
3. **Improved Plan** — The complete rewritten plan that incorporates everything good
   about the original, correcting any flaws and adding the improvements identified. If
   the sanity check concludes the plan shouldn't be implemented as-is, say so here
   instead of polishing a plan that shouldn't proceed.

Pass the plan text verbatim to the subagent. When it returns, relay its full response to
the user without summarizing or filtering.

## Input

Plan to review:

$ARGUMENTS
