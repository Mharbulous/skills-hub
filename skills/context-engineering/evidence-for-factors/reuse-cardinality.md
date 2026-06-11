# Factor 6: Reuse Cardinality

## The Rule

When the same behavioral instruction appears in more than one agent, extract it into a skill that both agents load on demand.

## How It Applies

Expert agents already share identical patterns — Knowledge Lookup Order, Response Format, Firestore read snippets — copy-pasted across multiple agent definitions. Changing the lookup order requires updating all files.

## What Adoption Looks Like

Extract shared behaviors into a skill (e.g., `expert-behaviors/SKILL.md`) that each agent loads via a reference line. The agent keeps only what's unique — persona, domain description, source path, reference file list. Shared protocol lives in one place.

## Caveats

- N=1 stays embedded. Don't pre-extract something only one agent uses.
- Reactive, not proactive. Extract when duplication actually appears.
- Keep skill count disciplined. ~15-20 skills is the practical ceiling before organization overhead degrades selection accuracy.
