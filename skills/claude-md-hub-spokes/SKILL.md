---
name: claude-md-hub-spokes
description: Use when a project has a bloated CLAUDE.md (and optionally a CLAUDE.local.md) that needs to be restructured into a lean hub that routes by session type, with per-session spoke files in .claude/sessions/. NOT for topic-based reorganization (development.md, gotchas.md, etc.) — that is the wrong organizing principle. Use this skill to apply session-type routing.
disable-model-invocation: true
---

# CLAUDE.md Hub-and-Spoke Restructuring

## Overview

Transform bloated CLAUDE.md (and CLAUDE.local.md) into a lean hub + session-type spokes. The organizing principle is **what kind of session the developer is starting**, not topic or concern.

**Critical:** Do NOT organize spokes by topic (deployment, gotchas, development). Organize by **session type**. A topic-based split misses the point — the hub should answer "what do I need to know for this kind of session?" not "where can I look up this fact?"

## The 13 Session Types

These are the spoke files to create in `.claude/sessions/`:

| File | When it applies |
|------|----------------|
| `design.md` | Brainstorming new features/skills/schemas; pre-brainstorm investigation |
| `plan.md` | Design doc exists; creating TDD implementation plan |
| `execute.md` | Plan exists; executing via /subagent-driven-development or plan mode |
| `validate.md` | Plan executed; Playwright visual verification |
| `polish.md` | E2E walkthrough of existing features; small frontend fixes |
| `test.md` | E2E finds broken functionality; systematic debugging |
| `maintain.md` | Adjusting Claude Code config — settings, hooks, permissions |
| `refactor.md` | Making code more concise, readable, simple, or elegant |
| `skill.md` | Writing or improving .claude/skills/ SKILL.md files |
| `audit.md` | Systematic consistency check across code, config, or data |
| `devops.md` | CI/CD workflows, cloud infrastructure, deployment config |
| `verify.md` | Post-deploy backend smoke test via logs and Firestore |
| `spec.md` | Writing detailed visual/functional specs from screenshots |

Not every project needs all 13. Create only the spokes that have content to put in them.

## What Goes Where

**Hub (CLAUDE.md) — target ~40 lines, hard maximum ~60:**
- Project identity (1-2 lines)
- Tech stack (one line)
- Dev commands (dev server, pre-commit, test)
- Conventions that apply in every session (path format, branch rules, linting delegation)
- Gotchas that apply in every session (framework pitfalls, tool quirks)
- Rules pointer (`.claude/rules/` note if applicable)
- Session routing table → `.claude/sessions/<type>.md`

**Hub does NOT contain:**
- Planning workflow detail → `plan.md`
- TDD rules → `execute.md`
- Deployment pipeline steps → `devops.md`
- Test commands (beyond a quick reference) → `execute.md` + `test.md`
- Deployment verification steps → `verify.md`
- Skill authoring patterns → `skill.md`

**Each spoke contains:**
Everything a developer needs to start that session type, including:
- Which skill(s) to invoke
- File paths for inputs/outputs
- Relevant commands
- Pointers to domain docs (e.g., "if working on Upload, also read docs/Features/Upload/CLAUDE.md")

## Process

### Step 1: Inventory
Read CLAUDE.md and CLAUDE.local.md (if present). List every piece of content and label it:
- **Hub** — needed every session
- **Spoke: X** — only needed for session type X

### Step 2: Identify which spokes to create
Only create spokes that have real content. For a typical project:
- `execute.md` gets: TDD rules, test commands, git workflow
- `plan.md` gets: plan templates, save paths, TDD overview
- `devops.md` gets: the full deployment section
- `design.md` gets: design-software skill invocation, design doc save path

### Step 3: Write hub first
Write the lean CLAUDE.md with just universal content + routing table. If it exceeds 60 lines, something that isn't universal snuck in — move it to a spoke.

### Step 4: Write spokes
One file per session type. Each spoke is self-contained — no need to read other spokes for that session type.

### Step 5: Consolidate CLAUDE.local.md
If CLAUDE.local.md exists and the developer is solo (no team), merge its content into hub or spokes as appropriate, then **delete CLAUDE.local.md**. The public/private split has no value for a solo developer.

If the developer has a team, preserve CLAUDE.local.md for genuinely private/machine-specific config (secrets, personal paths). Move everything else to hub or spokes.

## Hub Routing Table Format

```markdown
## Session Context

Identify your session type and read the corresponding file:

| Session | File | When |
|---------|------|------|
| Design | `.claude/sessions/design.md` | Brainstorming new features or schemas |
| Plan | `.claude/sessions/plan.md` | Writing a TDD implementation plan |
| Execute | `.claude/sessions/execute.md` | Running an implementation plan |
| Validate | `.claude/sessions/validate.md` | Playwright visual verification |
| Polish | `.claude/sessions/polish.md` | E2E walkthrough, small UI fixes |
| Test | `.claude/sessions/test.md` | Debugging broken functionality |
| Maintain | `.claude/sessions/maintain.md` | Claude Code config changes |
| Refactor | `.claude/sessions/refactor.md` | Code simplification/decomposition |
| DevOps | `.claude/sessions/devops.md` | Deployment, CI/CD, infrastructure |
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Organizing spokes by topic (gotchas.md, development.md) | Re-organize by session type — topic splits miss the routing value |
| Hub stays at 80+ lines | Anything session-specific must move to a spoke |
| Keeping TDD rules in hub | TDD only applies during Execute and Plan — move to those spokes |
| Keeping full deployment section in hub | Move to `devops.md` spoke |
| Creating spokes with no real content | Only create spokes that have content; stub files add noise |
| Leaving CLAUDE.local.md intact for solo developer | For solo devs, merge and delete — the split is meaningless |

## Domain Files Are Separate

Feature-level domain docs (e.g., `docs/Features/Upload/CLAUDE.md`) are **not** spokes — they already exist and don't change. Session spokes reference them inline when relevant:

```markdown
<!-- in execute.md -->
If working on the Upload feature, also read `docs/Features/Upload/CLAUDE.md`.
```

Do not duplicate domain doc content into session spokes.
