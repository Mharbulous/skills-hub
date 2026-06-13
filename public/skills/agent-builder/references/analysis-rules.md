# Gap Report Analysis Rules

Evaluate each category in order. For each finding, assign a severity and generate a one-line description.

## Category 1: System Prompt

Check for:
- **No escalation protocol** when model is Haiku and tools include Bash — Haiku needs explicit "STOP and return" rules (`!!`)
- **No output format defined** — agent has no structured output contract (`!`)
- **Prompt too thin for tool set** — agent grants 5+ tools but system prompt is under 3 sentences (`!`)
- **No safety rules** when Bash or Write/Edit are granted (`!!`)
- **Model-inappropriate complexity** — complex multi-step reasoning in system prompt but model is Haiku (`!`)

## Category 2: Tool Hygiene

Check for:
- **Write/Edit granted but description says read-only** — tool set contradicts stated purpose (`!!`)
- **Bash granted with no safety rules** — no hooks or system prompt restrictions on dangerous commands (`!!`)
- **No tools specified** — agent inherits everything from parent, may have excessive permissions (`!`)
- **tools vs disallowedTools interaction** — denylist applies first, then allowlist. Flag if both are set without understanding this ordering (`i`)

## Category 3: Model Fit

Check for:
- **Complex reasoning on Haiku** — multi-step analysis, architecture decisions, or nuanced judgment expected (`!`)
- **Simple task on Opus** — read-only, single-step tasks that don't need Opus-level reasoning (`i`)
- **No model specified** — inherits caller's model, which may be inappropriate (`i`)

## Category 4: Scope Placement

Check for:
- **Local script hooks but user scope** — hooks referencing `./scripts/` won't work from other projects (`!!`)
- **User memory but project-specific purpose** — knowledge accumulates in wrong scope (`!`)
- **Project-specific skills in user-scoped agent** — skill paths won't resolve from other projects (`!`)

## Category 5: Advanced Fields

Check for:
- **MCP servers configured globally that could be scoped** — agent uses specific servers that others don't need (`i`)
- **No maxTurns on agentic workflow** — runaway risk for agents that loop (`!`)
- **No memory configured** — agent accumulates useful knowledge but has nowhere to store it (`i`)
- **permissionMode not set** — defaults to `default`, which may prompt unnecessarily for background agents (`i`)

## Category 6: Untapped Fields

Check for:
- **External scripts in use but no hooks** — hooks could validate inputs/outputs (`i`)
- **Agent always invoked with same setup** — consider `initialPrompt` (only for `--agent` mode) (`i`)
- **Destructive operations without isolation** — consider `isolation: worktree` (`!`)
- **No skills loaded** — agent could benefit from existing skills in `~/.claude/skills/` (`i`)

## Severity Levels

| Marker | Meaning | Action |
|---|---|---|
| `!!` | Critical — security or correctness risk | Fix before using agent |
| `!` | Warning — best practice gap | Recommended fix |
| `i` | Informational — optimization opportunity | Optional enhancement |

## Ordering

Present findings highest severity first, then by category order within same severity.
