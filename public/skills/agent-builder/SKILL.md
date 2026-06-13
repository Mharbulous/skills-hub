---
name: agent-builder
description: >
  Use when creating a new Claude Code agent with advanced configuration, or
  enhancing an existing agent beyond what the built-in /agents wizard covers
  (system prompt quality, hooks, MCP servers, skills, permissionMode, maxTurns,
  isolation, and other frontmatter fields). For basic agent creation (name,
  model, color, tools), use the built-in /agents wizard first — escalate here
  when the agent needs configuration the wizard does not expose.
arguments: Optional agent name, or "new" to create from scratch
---

# Agent Builder

Advanced configuration companion to the built-in `/agents` wizard. Analyzes agent definitions against best-practice patterns and guides setup for the 10+ frontmatter fields the wizard does not expose.

## Mode Detection

| Invocation | Mode | Behavior |
|---|---|---|
| `/agent-builder` (no args) | **Enhance** | List agents in `~/.claude/agents/`, prompt user to pick one |
| `/agent-builder <name>` | **Enhance** | Load the named agent directly |
| `/agent-builder new` | **Create** | Skip to blueprint generation |

**Scope discovery** when loading by name:
- Found only in `.claude/agents/` (project) or only in `~/.claude/agents/` (user) -> load it
- Found in both scopes -> ask user which to edit

## Workflow

### Enhance Mode (existing agent)

1. **Load** the agent file. Read its frontmatter and system prompt.
2. **Analyze** using the gap report rules in `references/analysis-rules.md`.
3. **Present** findings as a prioritized menu (see format below).
4. **Configure** selected areas one at a time using the module guidance in `references/modules.md`.
5. **Preview** the full diff before writing. User confirms.
6. **Write** the updated file. Print a session summary.

### Create Mode (new agent)

1. **Ask** the user to describe the agent's purpose in plain language.
2. **Generate blueprint** — recommended model, minimal tool set, system prompt structure, relevant advanced fields. Load `references/modules.md` for template guidance.
3. **Present** the blueprint for review. User approves or adjusts.
4. **Write** the agent file after scope recommendation (see below).

## Gap Report Format

```
Analysis complete. Found N improvement areas:

  [1] <severity> <category> -- <one-line finding>
  [2] <severity> <category> -- <one-line finding>
  ...

Which areas to configure? (e.g. "1 2", "all", or "skip")
```

Severity markers: `!!` critical (security/correctness), `!` warning (best practice gap), `i` informational (optimization opportunity).

## Scope Recommendation

Recommend scope based on signals, explain reasoning, let user override.

**Project scope** signals (`.claude/agents/`):
- Hooks reference local scripts (e.g. `./scripts/validate.sh`)
- `mcpServers` includes inline definitions tied to project infrastructure
- System prompt references project-specific paths or conventions
- `skills` field references project-level skills (`.claude/skills/`)

**User scope** signals (`~/.claude/agents/`):
- General-purpose role applicable to any codebase
- No hooks, or only globally-available hooks
- `memory: user`
- Purpose stated in generic terms

When signals conflict, surface the tension: "This agent has user-scope memory but hooks pointing to a local script — those are in tension. If you keep the local hook, project scope is safer."

## System Prompt Templates

Select based on agent role pattern. Templates define which sections to include, not exact wording.

| Role pattern | Template sections |
|---|---|
| **Read-only analyst** | Core responsibility, review checklist, output format |
| **Code modifier** | Core responsibility, workflow steps, safety rules, output format |
| **Automation runner** (Haiku) | Core responsibility, workflow steps, escalation protocol, output format, token efficiency rules |
| **Coordinator/orchestrator** | Core responsibility, delegation logic, structured JSON output |

System prompt scoring dimensions (for review mode): specificity, tool alignment, output format, error handling, model-appropriate complexity.

## Agent Modes

Agents operate in two modes — the configuration implications differ:

- **Spawned as subagent**: Another agent or command creates this agent. `initialPrompt` is irrelevant (the spawner provides the prompt). Focus on: tool restrictions, escalation protocol, output contract.
- **Run as main agent** (`claude --agent <name>`): User invokes directly. `initialPrompt` is useful here to define the default task or greeting. Focus on: user-facing prompt quality, permission mode, memory.

## Configuration Modules

Each gap report item maps to a module. Execute in user-selected order.

Read `references/modules.md` for detailed guidance on each module:
- **Module 1: System Prompt** — review/build mode, templates, scoring
- **Module 2: Tool Configuration** — least-privilege, tools vs disallowedTools, Bash safety
- **Module 3: Hooks** — PreToolUse/PostToolUse/Stop patterns, YAML + script generation
- **Module 4: MCP Servers** — inline definitions vs string references, reading `.mcp.json`
- **Module 5: Skills** — listing, injection semantics, context cost warnings
- **Module 6: Other Fields** — permissionMode, maxTurns, isolation, effort, initialPrompt, background

## Output

### Diff Preview

Before writing, show the full file for new agents or changed sections for enhancements. Wait for user confirmation.

### Session Summary

```
Agent updated: <path>
Changes: <comma-separated list of what changed>
Companion files: <any hook scripts created>

Reload with: /agents (then edit) or restart your session
```

Do NOT commit changes — that is the user's or git-agent's responsibility.
