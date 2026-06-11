---
name: writing-skills
description: "OVERRIDES superpowers:writing-skills. Use when creating new skills, editing existing skills, or verifying skills work before deployment."
---

# Writing Skills (Custom Override)

## Step 1: Load the marketplace skill

Use Glob to find `C:/Users/Brahm/.claude/plugins/cache/superpowers-marketplace/superpowers/*/skills/writing-skills/SKILL.md` and READ that file. Follow ALL instructions from that file exactly, with ONLY the overrides below.

## Step 2: Apply these overrides

### Override: Description field best practices

The marketplace skill's CSO section covers the basics. Apply these additional principles when writing or reviewing the `description` field:

**1. Don't summarize the workflow** (marketplace skill covers this — reinforce it)
The description must describe triggering conditions only. If it summarizes the process, Claude follows the description as a shortcut and skips reading the skill body.

**2. Escalation pre-conditions belong in the description**
If this skill is a fallback or escalation path, the pre-condition goes in the description itself:
> "Use when a direct Grep/Read of 1–3 files fails to produce an answer."

**3. Pair every exclusion with a positive redirect**
`"Don't use for X"` alone has weak compliance. Always add what to do instead:
> "For single-file changes, read the file directly — escalate here only when the answer spans multiple components."

**4. Escape hatches on MUST rules**
`"MUST trigger for X"` without a qualifier causes over-triggering. Add a qualifier:
> "Trigger when the change spans multiple components or the architecture is not already clear from current context."

**5. The intern test**
Before finalizing: could a new hire correctly decide when to invoke this skill from the description alone, without any other context? If not, add the missing decision boundary.

**6. Both positive and negative framing — together**
Positive framing has stronger pull, but pure positive-only descriptions over-trigger. Pair them:
- Lead with what the skill IS for (positive anchor)
- Follow with what it is NOT for + the alternative (redirect)
