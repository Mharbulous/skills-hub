---
name: prompt-analyzer
description: Analyzes LLM prompts for quality, clarity, safety, and effectiveness. Provides quality scores, detailed feedback, and improvement suggestions. Use when (1) reviewing code containing LLM prompts, (2) user explicitly requests prompt analysis, (3) designing or improving prompts for any LLM. Covers system prompts, user-facing prompts, and parameterized prompt templates.
disable-model-invocation: true
---

# Prompt Analyzer

Analyze prompts across four dimensions, provide scores, and generate actionable improvements.

## Locating the Prompt

**CRITICAL: Resolve paths before reading.** Do not use `~` in file paths on Windows - it won't expand.

### Skills (most common)

When user provides a skill name (e.g., "scoping", "handover"):

1. **First**: Resolve the harness's native skill entry for `{skill-name}`. If it is a Myskillium stub, fetch the authoritative `SKILL.md` with the stub protocol before analyzing.

2. **Second**: Check project-local skills:
   - `.claude\skills\{skill-name}\SKILL.md` (relative to working directory)

3. **If not found**: Use Glob with the skill name:
   ```
   Glob: **/{skill-name}/SKILL.md
   ```

### Other Prompts

| Source | Location Pattern |
|--------|------------------|
| Code prompts | Grep for `system:`, `prompt:`, or string literals passed to LLM APIs |
| CLAUDE.md | Check `.claude/CLAUDE.md` or `CLAUDE.md` in project root |
| Config files | Look in `.claude/`, `config/`, or project root |

### Path Resolution

Always expand paths before reading:
- Get username from environment or working directory path
- Convert relative paths to absolute
- Use backslashes on Windows, forward slashes on Unix

## Execution: Parallel Subagent Analysis

Analyze prompts using parallel subagents, each evaluating against a single criterion.

### Step 1: Discover Criterion Files

Use Glob to find all markdown files in the criterion folder:
```
Glob: {skill-directory}/criterion/**/*.md
```

Exclude `index.md` from the list. This yields ~13 files (7 patterns + 6 anti-patterns).

### Step 2: Spawn Parallel Subagents

For each best practice file, spawn a subagent using the Task tool with these parameters:
- `model`: "haiku" (fast, cost-effective)
- `subagent_type`: "general-purpose"
- Launch ALL subagents in a SINGLE message (parallel execution)

### Step 3: Subagent Prompt Template

Each subagent receives this minimal prompt:

```
You are evaluating a prompt against a single criterion.

FILES TO READ:
1. Target prompt: {absolute-path-to-prompt-file}
2. Criterion: {absolute-path-to-criterion-file}

TASK:
1. Read both files
2. Evaluate how well the target prompt follows (or avoids) this specific pattern/anti-pattern
3. Return a brief assessment in this exact format:

CRITERION: {name from criterion file}
CATEGORY: {Pattern or Anti-Pattern}
COMPLIANCE: {Follows | Partially Follows | Violates | N/A}
SCORE_IMPACT: {point adjustment, e.g., "-3" or "+0" or "N/A"}
FINDING: {1-2 sentence description of what you found}
LOCATION: {line numbers or "Throughout" or "N/A"}
FIX: {brief fix suggestion, or "None needed"}

Do not add commentary. Return only the structured assessment.
```

### Step 4: Aggregate Results

After all subagents complete:
1. Collect all findings
2. Sum score impacts by dimension (see Scoring Dimension Mapping in criterion/index.md)
3. Calculate final scores (start at 25 per dimension, apply deductions)
4. Compile into Output Format below

## Analysis Framework

### Scoring Dimensions (each 0-25, start at 25, apply deductions)

1. **Clarity & Specificity** — task definition, output format, scope, edge cases
2. **Safety & Guardrails** — input validation, output restrictions, injection resistance
3. **Token Efficiency** — redundancy, verbosity, repeated concepts
4. **Best Practices** — Sandwich structure (System → Context → Examples → Input LAST), recency bias

Detailed rubrics and patterns are in [criterion/index.md](criterion/index.md).

## Output Format

```markdown
## Prompt Analysis Report

**Overall Score: XX/100** (Excellent/Good/Fair/Poor)

### Scores by Dimension
- Clarity & Specificity: XX/25
- Safety & Guardrails: XX/25
- Token Efficiency: XX/25
- Best Practices: XX/25

### Strengths
- [List 2-3 things the prompt does well]

### Issues Found
1. **[Issue Category]**: [Specific problem]
   - Location: [Where in prompt]
   - Impact: [Why it matters]
   - Fix: [Concrete suggestion]

### Suggested Rewrite
[If score < 70, provide improved version]
```

## Prompt Types

- **System prompts**: Focus on role definition, capability boundaries, output format, safety constraints
- **User-facing prompts**: Focus on clarity, guidance level, error prevention
- **Parameterized templates**: Focus on injection resistance, variable validation, context preservation
