# How to write an excellent AGENTS.md in 2026

**AGENTS.md is the single highest-leverage file in your Claude Code workflow** — a markdown file loaded into every session that acts as an onboarding document for your AI agent. The convergent advice from Anthropic's official documentation, enterprise practitioners, and community experts is clear: keep it ruthlessly concise (under 300 lines), include only universally applicable instructions, and use the newer modular systems (`.claude/rules/`, Skills, imports) for everything else. The most important insight many developers miss: Claude Code wraps CLAUDE.md content with an internal directive saying "this context may or may not be relevant to your tasks," meaning **bloated files cause Claude to ignore your actual instructions**.

This report synthesizes official Anthropic documentation (including their November 2025 blog post and engineering best practices), enterprise usage patterns from developers processing billions of tokens monthly, community consensus across 12+ expert sources, and the latest changes through February 2026.

---

## The memory hierarchy determines what loads and when

Claude Code reads CLAUDE.md files from four distinct locations, each with different scope and priority. Understanding this hierarchy is essential before writing a single line.

| Priority | Type | Location | Sharing |
|----------|------|----------|---------|
| Highest | Enterprise policy | Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | All org users |
| High | Project (local) | `./CLAUDE.local.md` | Just you (auto-gitignored) |
| Medium | Project (shared) | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team via git |
| Lowest | User global | `~/.claude/CLAUDE.md` | Just you, all projects |

Claude Code also recurses upward from your working directory, loading any CLAUDE.md files it finds in parent directories — useful for monorepos where `root/CLAUDE.md` and `root/frontend/CLAUDE.md` both apply. Child-directory CLAUDE.md files load **on demand** only when Claude works with files in those subdirectories, which keeps startup context lean.

The import system (`@path/to/file` syntax) allows modular composition. Imports resolve relative to the containing file, support recursive depth up to 5 hops, and work with home-directory paths (`@~/.claude/my-rules.md`). First-time external imports trigger an approval dialog. **Imports are now the preferred alternative to CLAUDE.local.md** for personal per-project instructions, especially across git worktrees.

For your Windows 11 VS Code setup, all of this works identically across CLI, VS Code extension, JetBrains, and web interface — the underlying engine is the same. Install via WinGet (`winget install Anthropic.ClaudeCode`), not npm (which is now deprecated).

---

## What every CLAUDE.md should contain — and what it shouldn't

The strongest convergence across all sources lands on a short list of essential sections and a longer list of things to exclude.

**Include these sections, in roughly this order:**

A one-line project description and tech stack. Key build, test, lint, and type-check commands with exact CLI syntax. A brief architecture map covering major directories and what they contain. Critical code conventions — but only the **3–5 rules** Claude wouldn't infer from existing code. Git workflow expectations like branch naming and merge-vs-rebase preferences. Project-specific gotchas, warnings, and things that break easily. Pointers to deeper documentation with context about when to read them. A final validation checklist — what to run after completing a task.

Here is a concrete example reflecting current best practices:

```markdown
# Project Context
FastAPI REST API for user auth and profiles. SQLAlchemy ORM, Pydantic validation, PostgreSQL.

## Commands
- `uvicorn app.main:app --reload` — dev server
- `pytest tests/ -v` — run tests
- `ruff check .` — lint

## Architecture
- `app/models/` — database models
- `app/api/` — route handlers
- `app/core/` — config and utilities

## Conventions
- Type hints required on all functions
- Use named exports, not default exports
- All routes use `/api/v1` prefix

## Gotchas
- JWT tokens expire after 24 hours — tests mock this
- Never modify `app/core/security.py` without reviewing auth flow in @docs/authentication.md

## After completing changes
1. Run `ruff check .` and fix lint errors
2. Run `pytest tests/ -v` to verify
3. Run `mypy .` for type checking
```

**Exclude these — they actively degrade performance:**

Detailed code style rules belong in linters and formatters, not CLAUDE.md. As HumanLayer puts it: "Never send an LLM to do a linter's job." Code snippets go stale quickly — use `file:line` references instead. Sensitive information like API keys and credentials should never appear in a file that becomes part of prompts. One-off behavioral "hotfixes" for issues Claude had in a single session pollute the file for every future session. Large embedded documentation — use pointers with context about *why and when* to read them, not raw `@-imports` that embed entire files on every run.

---

## Where experts agree and where they sharply diverge

**Strong convergence exists on these points:** Keep the root CLAUDE.md concise. Use progressive disclosure (pointers to detailed docs, not the docs themselves). Every line must be universally applicable to your sessions. Iterate based on what Claude gets wrong rather than trying to anticipate everything upfront. Treat CLAUDE.md like a prompt — refine it, test it, and Anthropic even recommends running it through their prompt improver. When saying "never do X," always provide an alternative ("use Y instead") or the agent gets stuck.

**Significant disagreement exists in three areas:**

First, **optimal length**. HumanLayer argues for under 60 lines, citing research showing frontier LLMs can follow roughly 150–200 instructions total, and Claude Code's system prompt already consumes ~50 of that budget. Builder.io and community consensus suggest under 300 lines. Enterprise practitioner Shrivu Shankar runs a curated 13KB CLAUDE.md in a monorepo with strict "ad space" allocation per tool. The resolution: **project scale determines acceptable length**, but the principle of minimalism applies universally.

Second, **using `/init` to bootstrap**. Anthropic's official documentation recommends `/init` as a starting point. HumanLayer strongly disagrees, calling CLAUDE.md "the highest leverage point of the harness" that should be hand-crafted. The practical resolution most experts land on: use `/init` to generate a draft, then ruthlessly prune and refine.

Third, **custom slash commands and subagents**. Shrivu Shankar considers extensive custom slash command libraries an anti-pattern ("you've created an anti-pattern"), preferring Claude's built-in Task dispatch. Other practitioners build rich slash command ecosystems for repeatable workflows. The dividing line appears to be team size — solo developers benefit from custom commands, while enterprise teams find they fragment context.

---

## The modern distributed architecture replaces monolithic files

The biggest shift from early 2025 to early 2026 is the move from a single CLAUDE.md containing everything to a **distributed system** where each component serves a distinct purpose:

```
CLAUDE.md              → High-level project context only (concise)
.claude/rules/         → Modular, path-specific conventions
.claude/skills/        → Domain knowledge loaded on demand
.claude/agents/        → Custom subagent definitions
.claude/commands/      → Reusable slash commands
.claude/settings.json  → Permissions, hooks, tool config (JSON)
~/.claude/projects/<project>/memory/MEMORY.md → Auto memory (Claude's self-notes)
```

The `.claude/rules/` directory (introduced v2.0.64) is particularly powerful. Each `.md` file loads automatically with the same priority as CLAUDE.md. Rules can target specific file paths via YAML frontmatter:

```yaml
---
paths:
  - "src/api/**/*.ts"
---
# API Development Rules
- All API endpoints must include input validation
- Use the standard error response format
```

**Auto memory** (rolling out February 2026) is a separate system where Claude records its own learnings in `~/.claude/projects/<project>/memory/MEMORY.md`. Only the first 200 lines load at startup. Control it with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=0` (enable) or `=1` (disable). This replaces the old pattern of manually documenting everything Claude discovers.

**Skills** (SKILL.md files in `.claude/skills/`) load on-demand rather than every session, making them ideal for specialized domain knowledge that bloats CLAUDE.md unnecessarily.

**Hooks** provide deterministic enforcement that CLAUDE.md instructions cannot. An instruction saying "never delete production files" can be forgotten under context pressure. A `PreToolUse` hook that blocks `rm -rf` on specific paths fires every time. Use hooks for hard constraints, CLAUDE.md for guidance.

---

## Deprecated patterns that will trip you up

Several practices from Claude Code's early days are now outdated or actively harmful:

The **`#` shortcut** for quick memory entry was removed in December 2025. Tell Claude directly to edit your CLAUDE.md, or use the `/memory` command to open it in your editor. The **`ignorePatterns`** configuration in `.claude.json` is deprecated — use `permissions.deny` in `settings.json` instead. The **`.claudeignore`** file is not an official Anthropic feature at all; it's a third-party npm package. Multiple `.claude.json` keys (`allowedTools`, `env`, `todoFeatureEnabled`) have migrated to `settings.json`. The **`includeCoAuthoredBy`** setting is being replaced by a broader `attribution` setting. On Windows, the managed settings path changed from `C:\ProgramData\ClaudeCode\` to **`C:\Program Files\ClaudeCode\`**. And npm installation (`npm install -g @anthropic-ai/claude-code`) is deprecated in favor of native installers.

The most consequential deprecated *pattern* is the monolithic CLAUDE.md. A single file containing project context, style rules, testing instructions, API documentation, and workflow conventions was standard in early 2025. Today, that content should be distributed across rules files, skills, hooks, and auto memory — with CLAUDE.md serving as a concise index and high-level guide.

---

## Practical tips for your Windows 11 VS Code setup

For your specific environment, a few targeted recommendations apply. Set the `CLAUDE_CODE_GIT_BASH_PATH` environment variable to `C:\Program Files\Git\bin\bash.exe` to avoid shell issues. If you have Cursor installed alongside VS Code, ensure VS Code appears first in your PATH to prevent the `code` command being intercepted. Run `/terminal-setup` after installation to configure Shift+Enter for multi-line prompts in the VS Code terminal. The VS Code extension (2M+ installs) provides a native sidebar panel, inline diffs with accept/reject, and `@`-mention files with line ranges.

Claude Code works identically across CLI and VS Code extension — your CLAUDE.md, settings, MCP servers, and rules all carry over. The web interface at claude.ai/code reads CLAUDE.md from connected GitHub repositories but runs in a sandboxed environment with limitations on local file access and auto memory persistence. For development work, the CLI and VS Code extension are the primary surfaces; use the web interface for brainstorming or when away from your development machine.

## Conclusion

The core insight that unifies all expert advice is that **CLAUDE.md quality matters far more than quantity**. Research shows instruction-following quality degrades uniformly as instruction count increases — adding one mediocre instruction makes every other instruction slightly less likely to be followed. The modern best practice is a concise CLAUDE.md (60–300 lines) containing only universally applicable project context, backed by modular `.claude/rules/` files for path-specific conventions, Skills for on-demand domain knowledge, and hooks for hard enforcement. Start by running `/init`, prune aggressively, then iterate based on what Claude actually gets wrong. The days of the monolithic CLAUDE.md are over — the distributed architecture introduced through late 2025 and early 2026 is demonstrably more effective.
