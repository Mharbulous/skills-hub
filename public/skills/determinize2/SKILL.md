---
name: determinize2
description: Harden a skill's deterministic procedures into standalone scripts so identical inputs always produce identical outputs, then A/B test and promote the result. Use for a skill lifecycle that hardens brittleness-tolerant, judgment-free steps out of prose and into scripts, measures whether the change actually improves consistency, and formally replaces the original once proven.
disable-model-invocation: true
---

# Determinize

Hardening extracts a skill's fully deterministic procedures — the parts
where identical input should always produce identical output — out of
prose and into standalone scripts. This removes LLM variance from those
procedures at the cost of making them more brittle than prose an LLM could
otherwise adapt on the fly. This skill runs that lifecycle end to end:
harden a candidate procedure, measure whether the hardened version is
actually more consistent, and, only with explicit approval, promote it to
replace the original.

## Mode detection

| Signal in the user's prompt | Mode |
|---|---|
| `-harden` flag, or the word "harden", **or no flag specified at all** | **Harden** (default) |
| `-test` flag, or "test", "compare", "A/B test" | **Test** |
| `-promote` flag, or "promote" | **Promote** |

## Router

1. Determine the mode using the table above.
2. Read `modes/<mode>.md`.
3. Follow it exactly — do not skip ahead into other mode files or stage
   files not yet reached.
