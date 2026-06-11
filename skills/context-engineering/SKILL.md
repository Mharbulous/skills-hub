---
name: context-engineering
description: >
  Restructures a Claude Code capability (skill, agent, or command) into the
  three-layer architecture (Orchestration / Isolation / Operation) and uses
  eight validated decision factors to distribute content across layers. Use when
  creating new capabilities, refactoring existing ones, or evaluating whether
  current architecture follows validated principles. Do NOT use for general
  prompt engineering or for writing skill/agent content — use /skill-creator
  or /writing-skills for those.
arguments: The skill, agent, or command to restructure (name or path)
---

# Context Engineering: Three-Layer Architecture + 8-Factor Distribution

## Default: Always Three Layers

Every non-trivial capability gets three layers. Read `reference/three-layer-architecture.md` for the full pattern, sequence diagram, and context budget model.

| Layer | Artifact | Primary concern |
|-------|----------|-----------------|
| **Orchestration** | Slash command | Context extraction, delivery mode, agent spawn, result routing |
| **Isolation** | Custom agent | Context boundary, model pin, tool restrictions, escalation |
| **Operation** | Custom skill | Core instructions, progressive disclosure, output contract |

**Why always three?** Any workflow simple enough to skip a layer is simple enough to not automate. The 2-3K token overhead of the three-layer structure is negligible against the 10K+ working tokens that any automation-worthy workflow generates.

## How to Apply

When invoked on a target capability:

1. **Read** `reference/three-layer-architecture.md` for the structural pattern.
2. **Inventory** the target's current prompts, instructions, guardrails, patterns, anti-patterns, and gotchas.
3. **Distribute** that content across the three layers using the 8 factors below.
4. **Define contracts** — the orchestration layer specifies: (a) delivery mode (passthrough or direct-write); (b) spawn mode (background or foreground); and (c) execution guard. The operation layer defines its output contract to match and carries its own agent-only guard. See `reference/three-layer-architecture.md` for guard boilerplate.
5. **Organize** the operation layer's conditionally relevant content into subfolders: `references/` (read-only knowledge), `scripts/` (deterministic executables), `memory/` (persistent state).

## The 8 Distribution Factors

These factors determine which layer owns each piece of content. Each factor is ADOPT WITH CAVEATS — a real signal but not absolute.

**Only if a factor's verdict is ambiguous or contested**, read the evidence file in `evidence-for-factors/` (e.g., `evidence-for-factors/context-isolation.md`). Do not load evidence preemptively.

### Factor 1: Context Isolation — What Stays Where

**Rule:** Content that generates large working state belongs in the operation layer behind the isolation boundary. Content that selects and extracts context belongs in orchestration.

- The orchestration layer identifies what tasks need doing, what information those tasks need, and what tools/skills they require — then passes only that subset through.
- The isolation layer admits necessary tokens and excludes superfluous ones. It also enables parallel and background inference.
- The operation layer is where intelligence is most valuable. The other two layers exist so that it can operate with minimal, high-signal context.
- Instructions are cheap (~hundreds of tokens). Working state (file reads, iteration cycles, error output) is expensive. Distribute accordingly.

**Distribution:** Orchestration owns context extraction logic. Isolation owns the boundary definition. Operation owns the task-specific instructions and working state.

### Factor 2: Persona — Task-Dependent Steering

**Rule:** Persona steers methodology, not identity. Place persona framing in the operation layer where it guides task execution.

- **Expert personas damage accuracy on retrieval tasks** (MMLU: -3.6 to -5.3 points) by activating confident assertion over careful reasoning
- **Expert personas help on generative tasks** (writing, extraction, STEM explanation) where structured output matters
- **Methodological personas are safer for analytical tasks** — "investigate," "verify," "critically analyze"
- Placement matters: system prompt (agent definition) has stronger steering than user prompt

| Task type | Recommended | Avoid |
|-----------|-------------|-------|
| Code review, architecture analysis | "systematically identify issues" | "you are an expert" |
| Debugging | "identify all causes before proposing fixes" | "you are a senior debugger" |
| Code generation | Expert acceptable ("write following X patterns") | -- |
| Research/exploration | "search for evidence, cite sources" | "you are a specialist in X" |

**Distribution:** Methodological framing in the agent definition (isolation layer). Task-specific persona guidance in the skill (operation layer).

### Factor 3: Authority Boundaries — Tool Restrictions + Delivery Mode

**Rule:** Use agent tool restrictions to declare intent. Use the orchestration contract to specify delivery mode.

Two orthogonal dimensions:

1. **Tool restrictions** (isolation layer): Read-only agent vs full-access agent. Structural clarity like `const` in code — communicates "output is information, not action." Two levels are sufficient.
2. **Delivery mode** (orchestration contract): Passthrough (structured data returns through all layers) vs direct-write (operation layer writes files, returns lightweight confirmation). The orchestration layer chooses per task.

**Distribution:** Tool restrictions in the agent definition. Delivery mode in the orchestration layer's spawn contract. The skill's output contract reflects whichever mode was specified.

### Factor 4: Model Selection — Cost Optimization

**Rule:** Model pinning lives in the isolation layer. It is a bonus of the architecture, not a reason for it.

- Agents can pin `model: sonnet` or `model: haiku`. Skills inherit caller's model.
- Pin to **tier names** (`model: sonnet`) not versions — reduces deprecation churn.
- Sonnet/Opus gap for coding is ~1.2 points (SWE-bench) — negligible for most tasks.
- Prompt quality matters more than model tier.

**Distribution:** Model pin in the agent definition (isolation layer). No model-related content in orchestration or operation layers.

### Factor 5: Invocation Pattern — Discovery vs Direct

**Rule:** The orchestration layer determines how the capability is found and triggered.

- Explicit invocation (`/command`) = slash command orchestration layer
- Implicit discovery (Claude matches task to description) = agent can serve as its own orchestration when description quality is high
- ~19% routing error floor even for best routers — for high-stakes operations, prefer explicit invocation

**Distribution:** Invocation mechanism and trigger logic in the orchestration layer. The operation layer is invocation-agnostic.

### Factor 6: Reuse Cardinality — Shared Skills

**Rule:** When identical behavior appears in multiple capabilities, extract it into a shared skill that multiple agents load.

- N=1 stays embedded. Extract when duplication actually appears, not speculatively.
- Shared protocols (lookup order, response format, common patterns) are prime extraction candidates.
- Changing extracted behavior updates all consumers simultaneously.
- Keep skill count disciplined — ~15-20 skills is the practical ceiling.

**Distribution:** Shared behavior in a standalone skill (operation layer) loaded by multiple agents. Agent-specific behavior stays in each agent's own skill.

### Factor 7: Instruction Conflict — Isolation as Resolution

**Rule:** When two skills have genuinely incompatible requirements, use separate isolation layers (separate agents).

- Most apparent conflicts are scope problems, not genuine conflicts — fix the authoring first.
- Genuine conflict example: code-simplifier ("reduce abstractions") + philosophy-enforcer ("maintain design principles")
- Frontier models handle coherent multi-instruction well — separation is the last resort.

**Test:** "Could following skill A perfectly cause me to violate skill B?" If yes and unfixable by scoping, they need separate isolation layers.

**Distribution:** Conflicting instructions go behind separate agents. Non-conflicting instructions can coexist in the same operation layer.

### Factor 8: Domain Variance — Procedural vs Exploratory

**Rule:** Procedural, stable content belongs in the skill. Exploratory, judgment-heavy content benefits from agent-level framing.

- Predictable path (lint, test, build, commit) = skill instructions
- Unpredictable path (debug, review, explore) = agent framing with skill guardrails
- Hybrid is common — procedural skill checklist that allows agent judgment at decision points

**Distribution:** Step-by-step procedures, checklists, and deterministic rules in the skill (operation layer). Judgment criteria and exploration guidance in the agent definition (isolation layer). Trigger conditions and routing logic in the orchestration layer.

## Anti-patterns

- Skipping a layer because the workflow "seems simple" — if it's worth automating, it's worth structuring
- Putting context extraction logic in the skill instead of the orchestration layer
- Passing large diffs or generated content back through layers when direct-write is appropriate
- Duplicating behavior across agents instead of extracting to a shared skill
- Using "expert" persona on analytical/retrieval tasks
- Loading reference/evidence material preemptively when it's only needed for contested decisions
- Fine-grained tool permission tiers beyond read-only vs full-access
- Omitting execution guards from the orchestration or operation layer — allows the main model to run the workflow inline, bypassing the agent boundary
- Defaulting to foreground spawn when the operation is self-contained — blocks the main conversation unnecessarily; background is the right default
