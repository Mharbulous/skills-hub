---
name: subagent-driven-development
description: "OVERRIDES superpowers:subagent-driven-development. Use when executing implementation plans with independent tasks in the current session"
---

# Subagent-Driven Development (Custom Override)

## Step 1: Load the marketplace skill

Use Glob to find `C:/Users/Brahm/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/subagent-driven-development/SKILL.md` and READ that file. Follow ALL instructions from that file exactly, with ONLY the overrides below.

## Step 2: Apply these overrides

**No worktrees:** All work happens directly on main. Do not create worktrees or feature branches. Subagents work in the main working directory.

**Auto-merge after completion:** Do NOT use `superpowers:finishing-a-development-branch`. After all tasks are complete and the final code review passes, commit directly to main. Execute these steps directly:

1. Run the project's test suite one final time to confirm all tests pass
2. Commit with conventional commit message
3. Report: "All tasks complete. Tests passing. Committed to main."

**Why:** The two-stage review process (spec + quality) already provides sufficient quality gates. Worktrees cause silent data loss due to path confusion bugs in Claude Code.

Everything else — task dispatch, review stages, model selection, prompt templates, red flags — comes from the marketplace skill unchanged.
