# Scenario 1: Correct Hardening Application

**Type:** End-to-end application check.

## Setup

The agent is given `determinize2` (harden mode) and asked to harden the
skill defined in `tests/sample-skill-to-harden.md` (the `csv-data-validator`
fixture).

## Task

**IMPORTANT: This is a real task.** Actually run the harden mode pipeline
against the fixture skill, in order, one stage at a time.

## Success Criteria

1. The agent frames the value of hardening in determinism/robustness terms
   ("identical output for identical input", "eliminates LLM variance") —
   never in token-savings terms.
2. The agent writes baseline tests against the ORIGINAL fixture skill
   before writing or running any extraction script.
3. The agent creates a `csv-data-validator-hardened/` copy rather than
   modifying `tests/sample-skill-to-harden.md` in place.
4. The extracted script is actually run and verified against sample input,
   not just written and assumed correct.
5. Declarative content (the "Schema Format" and "Common Issues" sections)
   is preserved inline in the hardened SKILL.md, not deleted or
   summarized away.
6. No progressive-disclosure or restructuring language appears anywhere in
   the agent's output.

## What to Watch For

- Skipping straight to writing a script without a baseline test pass.
- Editing the fixture file directly instead of creating a `-hardened`
  sibling.
- Claiming a script "should work" without actually running it.
- Dropping the declarative sections because they "aren't code."
