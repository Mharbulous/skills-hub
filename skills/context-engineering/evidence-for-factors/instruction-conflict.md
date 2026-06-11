# Factor 7: Instruction Conflict

## The Rule

When two skills loaded into the same context have genuinely incompatible behavioral requirements — where the tension is inherent to the task, not fixable by rewriting — use agent isolation.

## How It Applies

Most skills compose cleanly because they address orthogonal concerns. But loading a code-simplifier skill ("reduce complexity, remove abstractions") alongside a vision-awareness skill ("enforce design principles, flag violations") could genuinely conflict — the simplifier might inline a helper that exists to enforce a design principle.

## What Adoption Looks Like

Before composing skills, ask: "Could following skill A's instructions perfectly cause me to violate skill B's instructions?" If yes and can't be resolved by narrowing each skill's scope, put them in separate agents.

## Caveats

- Authoring discipline first. Most apparent conflicts are skill scope problems. Fix the skills before reaching for isolation.
- Frontier models handle coherent multi-instruction well. 2025 research across 6 LLM families found no systematic degradation when composed instructions are non-overlapping.
- The test is **intrinsic tension**. "These skills disagree because I wrote them sloppily" = fix the skills. "These skills disagree because their goals are inherently in tension" = separate agents.
