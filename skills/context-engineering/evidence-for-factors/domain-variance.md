# Factor 8: Skill Domain Variance

## The Rule

Use skills for procedural, stable, repeatable work. Use agents for exploratory, judgment-heavy, or creative work where the path isn't predetermined.

## How It Applies

Skills like `/commit`, `/handover`, `/e2e-test` are procedural — they follow defined checklists. Expert agents like `workbench-expert` are exploratory — they investigate source code, answer open-ended questions, update references. The design-software skill is an edge case: procedural shell (checklist) that spawns agents for exploratory content.

## What Adoption Looks Like

Ask: "Is the path through this task predictable before it starts?" If yes (lint, test, build, commit) = skill. If no (debug, answer architectural question, review for violations) = agent.

## Caveats

- Claude Code skills are not SkillsBench skills. Research measured few-shot prompt libraries. SKILL.md files are terse instruction sets. Directional finding transfers, magnitude doesn't.
- ~19% negative-delta rate is manageable because you can observe when a skill degrades and revise it.
- Hybrid is fine. Procedural shell + exploratory agents. The boundary can exist within a single workflow.
