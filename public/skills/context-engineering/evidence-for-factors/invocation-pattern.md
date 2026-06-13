# Factor 5: Invocation Pattern (Discovery vs Direct)

## Evidence For

- **Well-established engineering tradeoff.** Imperative (predictable, explicit) vs declarative (flexible, discovered). Maps to IaC literature.
- **Claude Code uses description-based routing.** "No regex, no keyword matching" — purely LLM reasoning on descriptions (leehanchung deep dive).
- **Typed registries reduce errors.** 30-50% reduction in planning errors, half task completion time (abstractalgorithms.dev).

## Evidence Against

- **False dichotomy in Claude Code.** Skills support BOTH `/slash-command` AND autonomous invocation. `disable-model-invocation: true` exists because implicit is on by default. Agents can be called by name.
- **Description quality is the real variable.** Poor agent description = poor routing. Excellent skill description = excellent routing. Invocation pattern is downstream.
- **~19% routing error floor.** RouterEval (200M+ records): best routers still gap Oracle. "When Routing Collapses" (arxiv 2602.03478): routers converge to preferred tools regardless of task.
- **Explicit is better for power users.** Salesforce "workflow-first, agent-last": start deterministic, add autonomy where measurable.
- **Silent misrouting.** Microsoft AgentRx: wrong agent selection is often silent — outputs look plausible while wrong tool runs.

## Judge Synthesis

The factor describes a real **behavioral difference in how tools are used in practice** — "I will call this" = skill, "Claude should find this" = agent. But it is a spectrum of defaults, not a binary architectural boundary. Description quality dominates routing quality. For high-stakes operations, prefer explicit invocation even if the tool is technically an agent. Near-zero weight with fewer than ~10 total tools.
