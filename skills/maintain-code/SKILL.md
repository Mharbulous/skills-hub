---
name: maintain-code
description: Explicitly invoked umbrella for codebase maintenance workflows such as /streamline, standardizing divergent patterns, and improving architecture. Use when the user invokes $maintain-code, /streamline, or asks to run code maintenance/refinement work in downtime; not for normal feature implementation, TDD, debugging, issue triage, or release work.
---

# Maintain Code

Use this skill as a router for maintenance-only workflows. Do not run maintenance work unless the user explicitly invokes `$maintain-code`, invokes `/streamline`, or clearly asks for code maintenance/refinement work.

Private subskills live under `subskills/*/SUBSKILL.md`. They intentionally use `SUBSKILL.md` instead of `SKILL.md` so recursive skill loaders do not expose them as global top-level skills.

## Routing

1. Inspect available private subskills under `subskills/*/SUBSKILL.md`.
2. Read only each subskill frontmatter and description first.
3. Choose exactly one matching subskill unless the user asks for a broad maintenance pass.
4. Read the chosen subskill's full `SUBSKILL.md` and follow it as the active workflow.
5. If no subskill fits, say so and ask whether to create or adjust a maintenance workflow.

## Available Subskills

- `subskills/streamline/SUBSKILL.md` - reduce oversized files, run autophagy/dead-code cleanup, and maintain the streamline ledger.
- `subskills/standardize/SUBSKILL.md` - standardize divergent implementation patterns on the best existing pattern.
- `subskills/improve-codebase-architecture/SUBSKILL.md` - find architecture deepening opportunities and repository hygiene work.
- `subskills/agents-md-curator/SUBSKILL.md` - maintain AGENTS.md curated blocks through empirical commit analysis, including bootstrap, introspect, and predict modes.

## Boundaries

- Do not use this skill for normal feature work, TDD, bug diagnosis, issue triage, release work, or promotion.
- Do not silently invoke private subskills; route only after explicit maintain-code intent. Treat `/streamline` as explicit maintain-code intent.
- Preserve each subskill's approval gates, planning requirements, and stop conditions.
