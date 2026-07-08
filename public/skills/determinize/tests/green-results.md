> **Provenance note:** this file is a historical artifact documenting
> `determinize`'s own construction (GREEN phase of the TDD cycle under which
> this skill was built). It is not a live regression suite for end users to
> run — it records how this skill's earlier draft behaved, for reference
> only.

# Green Results: `determinize` — GREEN phase

**Date:** 2026-02-21
**Commit under test:** `c47e816` (first commit of `determinize` mode files
after the RED-phase rewrite)

## Summary

After rewriting the skill around determinism framing and adding the Iron
Law, `determinize` was re-run against the same two scenarios that
`optimizing-skills` failed (recorded in `baseline-results.md`), now
formalized as Scenario 3 and Scenario 4 of this suite.

## Scenario 3: Clean Exit on 100% Judgment Content

**Result: PASS**

Given the same 100%-judgment fixture, `determinize` classified every
section as non-extractable and produced the exact clean-exit sentence:

> "No script extraction candidates found. This skill's content requires
> LLM judgment and cannot be replaced with deterministic scripts.
> Hardening does not apply to this skill."

No `-hardened` directory was created. No progressive-disclosure or
restructuring fallback was offered.

## Scenario 4: Determinism Framing

**Result: PASS**

Asked why hardening matters, `determinize` answered using determinism
vocabulary throughout: "identical output for identical input," "eliminates
LLM variance," "more predictable but more brittle." No token-savings,
efficiency, or context-window language appeared anywhere in the answer.

## Conclusion

Both scenarios that motivated the rewrite now pass. The framing and
clean-exit fixes recorded in `baseline-results.md` are considered closed as
of this commit.
