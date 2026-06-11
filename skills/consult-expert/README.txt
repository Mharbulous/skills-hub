consult-expert — Design Rationale
==================================

1. Classification Heuristic
   Named technology (language, framework, library, tool, standard, protocol)
   → global agent at ~/.claude/agents/
   Abstract concept (meaning depends on the specific codebase)
   → local agent at .claude/agents/

   Why LLM judgment over a maintained list: zero maintenance, naturally
   extensible, Claude classifies reliably. No list to go stale.

2. Empty References Principle
   References start empty. Populated only when a question reveals knowledge
   the base model doesn't already have. Produces a curated set of surprises
   and gotchas, not a redundant mirror of derivable knowledge.

3. Dynamic Discovery
   No static registry table. Experts discovered at runtime via *-expert.md
   glob. Registry tables go stale when experts are added/removed without
   updating the skill — dynamic discovery eliminates that drift.

4. Two Templates
   Local and global experts have fundamentally different jobs. Local experts
   document repo-specific architecture. Global experts supplement model
   weights with hard-won gotchas. One conditional template would make both
   worse through compromise.

5. Local Precedence
   If a local and global expert share a name, local wins. Repo-specific
   knowledge should override general knowledge for that repo.

6. Active Contamination Cleanup
   Global experts must clean repo-specific content from their references on
   each invocation, not just avoid writing it. Self-healing on every call
   catches contamination from any source.
