# Configuration Modules Reference

Detailed guidance for each configuration module. Load this file when executing a module from the gap report.

## Module 1: System Prompt

### Review Mode (existing prompt)

Score the prompt on 5 dimensions (1-5 scale):

| Dimension | What to check |
|---|---|
| **Specificity** | Does the prompt define a clear, narrow role? Or is it vague ("help with code")? |
| **Tool alignment** | Does the prompt mention how to use each granted tool? Are there tools granted but never referenced? |
| **Output format** | Is the expected output structure defined? JSON contract? Markdown format? |
| **Error handling** | Does the prompt say what to do when things go wrong? Escalation protocol? |
| **Model-appropriate complexity** | Is the prompt complexity matched to the model? Haiku needs simpler instructions; Opus handles nuance. |

For each dimension scoring below 3, offer a concrete fix. User approves incrementally.

### Build Mode (new or thin prompt)

Select a structural template based on agent role, then guide user through each section:

**Read-only analyst template:**
```
You are a [role]. [Core responsibility in 1-2 sentences.]

## Review Checklist
- [Item 1]
- [Item 2]

## Output Format
[Specify exact structure]
```

**Code modifier template:**
```
You are a [role]. [Core responsibility in 1-2 sentences.]

## Workflow
1. [Step]
2. [Step]

## Safety Rules
- [Rule about destructive operations]
- [Rule about scope limits]

## Output Format
[Specify exact structure]
```

**Automation runner template (Haiku):**
```
You are a [role]. [Core responsibility in 1 sentence — keep simple for Haiku.]

## Workflow
1. [Step — be explicit, Haiku needs clear instructions]
2. [Step]

## Escalation Protocol
STOP and return to caller when:
- [Condition 1]
- [Condition 2]

Return: {"status": "escalation", "reason": "...", "details": "..."}

## Output Format
[Keep simple — Haiku handles structured output well]

## Token Efficiency
- [Avoid reading large files unnecessarily]
- [Use targeted Grep over full file reads]
```

**Coordinator/orchestrator template:**
```
You are a [role]. [Core responsibility in 1-2 sentences.]

## Delegation Logic
- When [condition] -> dispatch to [agent/approach]
- When [condition] -> handle directly

## Output Format
Return structured JSON:
{"status": "...", "results": [...], "next_steps": [...]}
```

## Module 2: Tool Configuration

### Least-Privilege Reasoning

For each tool in the current set, ask: "Does the system prompt or purpose require this tool?"

| Tool | Grant when | Deny when |
|---|---|---|
| **Bash** | Agent runs scripts, installs packages, or executes commands | Read-only analysis, code review |
| **Write/Edit** | Agent modifies files as part of its workflow | Read-only roles, analysis-only agents |
| **Read** | Almost always needed | Rarely denied |
| **Glob/Grep** | Search and discovery tasks | Simple single-file tasks |

### tools vs disallowedTools

- `disallowedTools` (denylist) applies first, then `tools` (allowlist)
- Use `tools` (allowlist) when agent needs a small, specific set
- Use `disallowedTools` (denylist) when agent needs most tools except a few dangerous ones
- Flag when both are set — the interaction can be confusing

### Bash Safety

When Bash is granted, check:
1. Does the system prompt restrict dangerous commands? (rm -rf, git push --force, etc.)
2. Are there PreToolUse hooks that validate Bash commands?
3. If neither exists, flag as critical (`!!`) and offer to add either hooks or prompt rules

## Module 3: Hooks

Generate YAML frontmatter config and starter scripts for common patterns.

### PreToolUse Bash Validator

Frontmatter addition:
```yaml
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: "./scripts/validate-bash.sh $INPUT"
```

Starter script validates against a blocklist of dangerous patterns.

### PostToolUse Linter/Formatter

Frontmatter addition:
```yaml
hooks:
  PostToolUse:
    - matcher: Write
      hooks:
        - type: command
          command: "./scripts/lint-written-file.sh $OUTPUT"
```

### Stop Cleanup Hook

Frontmatter addition:
```yaml
hooks:
  Stop:
    - hooks:
        - type: command
          command: "./scripts/cleanup.sh"
```

For each hook: generate the YAML and the companion script. Scripts go to the path matching the `command` field. Note whether companion files should be version-controlled or gitignored.

## Module 4: MCP Servers

### Discovery

Read `.mcp.json` (project root) to list available servers. Ask which servers this agent needs.

### Two Configuration Types

**Inline definition** — for servers scoped to this agent only:
```yaml
mcpServers:
  my-server:
    command: npx
    args: ["-y", "@some/mcp-server"]
    env:
      API_KEY: "${API_KEY}"
```

**String reference** — for servers the parent already has configured:
```yaml
mcpServers:
  my-server: shared
```

Use inline when: server is only needed by this agent, or agent needs different config than parent.
Use string reference when: parent already has the server configured and agent needs the same connection.

## Module 5: Skills

### Discovery

List skills in both scopes:
- `~/.claude/skills/` (user-level)
- `.claude/skills/` (project-level)

### Injection Semantics

Skills listed in the agent's `skills` field have their full content injected into the agent's system prompt at startup. This is NOT on-demand loading — the entire skill body is always present.

**Implications:**
- Large skills consume significant context budget
- Only include skills the agent genuinely needs for every invocation
- For occasional reference, the agent can Read skill files on demand instead

### Recommendation Logic

Match agent purpose keywords against skill descriptions. Suggest relevant skills with context cost estimate (approximate word count of each skill).

## Module 6: Other Fields

| Field | Values | Guidance |
|---|---|---|
| `permissionMode` | `default`, `acceptEdits`, `dontAsk` | `dontAsk` for background/automated agents that should never prompt. `acceptEdits` for code modifiers where you trust the agent's file changes but want to approve Bash. `default` when human oversight is desired. |
| `maxTurns` | integer | Set based on workflow complexity. Simple tasks: 5-10. Multi-step workflows: 20-50. Unbounded is risky for agentic agents — always set a ceiling. |
| `isolation` | `none`, `worktree` | `worktree` for agents that make destructive or exploratory changes. Creates a git worktree so changes don't affect the main working directory. |
| `effort` | `low`, `medium`, `high`, `max` | `max` is Opus 4.6 only. `high` is a good default for complex tasks. `low` for simple, mechanical tasks. |
| `initialPrompt` | string | Only relevant when running as main agent via `--agent`. Defines the default task or greeting. Irrelevant for spawned subagents (the spawner provides the prompt). |
| `background` | boolean | When true, agent auto-denies all permission requests. Do NOT use for agents that need user clarification or use AskUserQuestion. Good for fully autonomous background tasks. |
| `memory` | `user`, `project`, `local` | `user` for knowledge that applies across projects. `project` for project-specific learnings. Match to scope placement. |
