---
name: design-software
description: "Use to clarify, understand and stress test ideas for skills, apps, or features.  Outputs the refined idea as design document."
---

# Design Software (Custom Override)
OVERRIDES superpowers:brainstorming. 

## Step 0: Ask about collaboration mode

Before doing anything else, ask the user which collaboration mode they prefer for this brainstorming session:

1. **Hands-on** — I answer all questions myself
2. **Technical delegate** — Opus answers technical questions autonomously; I answer product/UX/business questions
3. **Review only** — Opus drives the entire brainstorming and presents me the final design for approval

Wait for the user's answer before proceeding. Do NOT skip this question or assume a default.

**If the user picks mode 2 or 3**, spawn an Opus subagent (using the Agent tool with `model: "opus"`) to handle the delegated questions. The subagent receives the full brainstorming skill instructions plus the user's initial request, and works autonomously on the delegated scope. Present its outputs to the user at the appropriate checkpoints (after each design section for mode 2, or the complete design for mode 3). If the Agent tool or Opus model is unavailable, inform the user and fall back to mode 1.

## Step 1: Load the marketplace skill

**PREREQUISITE:** Step 0 must be completed (user has chosen a collaboration mode) before proceeding.

Use the Glob tool to find `C:/Users/Brahm/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/SKILL.md` and READ the matching file. Follow ALL instructions from that file exactly, with the overrides below. Note: the marketplace checklist begins at "Explore project context" — this comes AFTER Step 0, not instead of it.

## Step 2: Apply these overrides

**Persona override** — Act as my Senior Technical Lead. Do not simply ask me for technical preferences. Instead, evaluate my goals and provide a Primary Recommendation with a brief Justification. Explain the "Why" behind your choice in plain language, focusing on the practical benefits rather than the syntax.

**File path override** — Wherever the marketplace skill specifies a design doc path, use this instead:

`planning/1. Design/YYYY-MM-DD_<2-3-word-description>-design.md`

Note: date format is `YYYY-MM-DD` (ISO 8601) with underscore separator before the description.

**Transition override** — Do NOT invoke writing-plans, writing-skills, or any implementation skill in this session. After committing the design doc, check the design content to determine the correct next skill:

- **Skill work** — If the design doc's write targets or subject matter involve skill files (paths containing `.claude/skills/`, or the design is about creating/refactoring a skill/SKILL.md), tell the user: "Design committed. Start a fresh session and run `/writing-skills <design_doc_filepath>` for maximum skill quality."
- **Code work** — Otherwise (code implementation, scripts, features, bug fixes), tell the user: "Design committed. Start a fresh session and run `/writing-plans <design_doc_filepath>` for maximum plan quality."

**Visual companion override** — When the marketplace checklist says "Offer visual companion", do NOT offer the HTML companion server. Instead, invoke `/playwright` which uses Playwright MCP tools for all visual work. Skip the companion consent message entirely — the user has pre-authorized Playwright.

**Learned patterns** — Before starting the "Explore project context" step, read `learned-patterns.md` in this skill folder for past mistakes and rules learned from real brainstorming sessions.

All other behavior (process, checklist, questions, design presentation, key principles, hard gates) comes from the marketplace skill unchanged.
