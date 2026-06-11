# Baseline Results: Co-Authored-By Enforcement

## Test Environment
- Date: 2026-04-10
- Skill version: Original `skills/commit/SKILL.md` (L30: "NO attribution lines")
- Observed in conversation: user manually amended commit f988693 to strip Co-Authored-By

## Baseline Behavior (Original Skill)

The original skill has a soft instruction on L30:
```
- **NO attribution lines** — never add Co-Authored-By or any Claude/Anthropic credit
```

This instruction is **unenforceable** because the system prompt contains a hard instruction to add `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` to every commit. The system prompt takes precedence.

### Results by Test Case

| TC | Description | Original Behavior | Expected After Hardening |
|----|-------------|-------------------|--------------------------|
| TC1 | Previous commit has Co-Authored-By | Not checked | Amend to strip |
| TC2 | Previous commit is clean | Not checked | No action |
| TC3 | New message has Co-Authored-By | LLM adds it despite L30 instruction | Script strips before commit |
| TC4 | New message is clean | Commits normally | Commits normally |
| TC5 | Post-commit verification | Not performed | Amend if found |
| TC6 | Multiple Co-Authored-By lines | LLM adds one | Script strips all |
| TC7 | Non-Anthropic Co-Authored-By | N/A (never occurs naturally) | Preserved |
| TC8 | Pattern variants | All variants added by system prompt | All variants stripped |

## Key Observation

The original skill **always fails** TC1, TC3, TC5, TC6, TC8 because the system prompt overrides the skill instruction. This is not a bug in the skill — it's a fundamental limitation of soft LLM instructions competing with hard system prompt instructions. Only a deterministic script can enforce this.
