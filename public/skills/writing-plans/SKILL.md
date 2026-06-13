---
name: writing-plans
description: "OVERRIDES superpowers:writing-plans. Creates detailed implementation plans with bite-sized TDD tasks."
---

# Writing Plans (Custom Override)

## Step 1: Load the marketplace skill

Use Glob to find `C:/Users/Brahm/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/writing-plans/SKILL.md` and READ that file. Follow ALL instructions from that file exactly, with ONLY the overrides below.

## Step 2: Auto-discover design (blank invocation)

If `/writing-plans` is invoked with no arguments (no spec, no feature name, no context):

1. Glob `planning/1. Design/*` and `planning/3. Plan/*`
2. For each design file, extract the **slug** (filename without extension, without date prefix like `YY-MM-DD-` or `YYYY-MM-DD-` or `YYYY-MM-DD_`)
3. A design is **planned** if any plan file's slug matches after similarly stripping its date prefix and removing a trailing `-plan` suffix. Match case-insensitively.
4. Filter to **unplanned** designs only. If none found, tell the user.
5. If multiple unplanned designs exist, pick the most recently modified file. Present the selection: "Found unplanned design: `<filename>`. Using this as the planning input." Then READ that design file and use it as the spec.

If `/writing-plans` is invoked with arguments, skip this step entirely and use the arguments as the spec.

## Step 3: Apply these overrides

**Save plans to:** `planning/3. Plan/YYYY-MM-DD_<2-3-word-description>-plan.md`

This replaces the marketplace `docs/plans/YYYY-MM-DD-<feature-name>.md` path and naming convention. Update all references to the save path accordingly (including the "Execution Handoff" section's saved-path message).

**Archive designed specs:** After saving the plan, if the spec came from `planning/1. Design/`, move that design file to `planning/7. Consumed/`. The design has been consumed by the planning process — keeping `1. Design/` clean for unplanned work.

**Execution Handoff:** After saving the plan and archiving the design:

1. Announce: **"Plan complete and saved to `planning/3. Plan/<filename>.md`. Launching subagent-driven development."**
2. Immediately invoke superpowers:subagent-driven-development to execute the plan. Do NOT ask the user — this is automatic. Do NOT offer a choice or mention alternative execution methods.

Everything else — task granularity, plan header, task structure, remember section, plan review loop — comes from the marketplace skill unchanged.
