---
name: skill-creator
description: "OVERRIDES skill-creator:skill-creator. Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, update or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy."
---

# Skill Creator (Custom Override)

## Step 1: Load the marketplace skill

Use Glob to find `C:/Users/Brahm/.claude/plugins/cache/claude-plugins-official/skill-creator/*/skills/skill-creator/SKILL.md` and READ that file. Follow ALL instructions from that file exactly, with ONLY the additions and overrides below.

## Step 2: Apply these design principles

These principles supplement the marketplace skill's "Skill Writing Guide" section. They do not replace any existing guidance — they fill gaps.

### Be Precise and Concise

The context window is a public good. Every token in a skill competes with the system prompt, conversation history, other skills, and the user's actual request.

**Default assumption: Claude is already very smart.** Only add context Claude doesn't already have. Say exactly what you mean in as few words as possible — vague instructions waste tokens AND produce worse results. Challenge each piece of information: "Is this precise enough to act on?" and "Can I say this in fewer words without losing meaning?"

Prefer concrete examples over lengthy explanations — a single well-chosen example is both more precise and more concise than a paragraph of description.

### Set Appropriate Degrees of Freedom

Match the level of specificity to the task's fragility and variability:

- **High freedom (text-based instructions)**: Multiple approaches are valid, decisions depend on context, heuristics guide the approach.
- **Medium freedom (pseudocode or scripts with parameters)**: A preferred pattern exists, some variation is acceptable, configuration affects behavior.
- **Low freedom (specific scripts, few parameters)**: Operations are fragile/error-prone, consistency is critical, a specific sequence must be followed.

Think of Claude as exploring a path: a narrow bridge with cliffs needs specific guardrails (low freedom), while an open field allows many routes (high freedom).

### What to Not Include in a Skill

Do NOT create extraneous files: README.md, INSTALLATION_GUIDE.md, QUICK_REFERENCE.md, CHANGELOG.md, etc. The skill should only contain information needed for an AI agent to do the job. No auxiliary context about creation process, setup procedures, or user-facing documentation.

### Duplication Avoidance

Information should live in either SKILL.md or references files, not both. Prefer references files for detailed information unless truly core to the skill — keeps SKILL.md lean while making information discoverable without consuming the context window.

### Planning Step (insert between Interview and Write SKILL.md)

Before writing, analyze each concrete example by:
1. Considering how to execute it from scratch
2. Identifying what scripts, references, and assets would be helpful for executing these workflows repeatedly

This produces a list of reusable resources to include before drafting SKILL.md.

## Step 3: Use these additional resources

### Scaffolding

When creating a new skill from scratch, run `init_skill.py` from this skill's `scripts/` directory to generate a template skill directory with proper structure and TODO placeholders:

```bash
python scripts/init_skill.py <skill-name> --path <output-directory>
```

### Design pattern references

Consult these based on the skill's needs:
- **Multi-step processes**: See [references/workflows.md](references/workflows.md) for sequential and conditional workflow patterns
- **Specific output formats or quality standards**: See [references/output-patterns.md](references/output-patterns.md) for template and examples patterns

Everything else — eval pipeline, benchmarking, description optimization, packaging, environment adaptations, blind comparison — comes from the marketplace skill unchanged.
