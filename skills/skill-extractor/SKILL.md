---
name: skill-extractor
description: Extract reusable skills from completed work sessions. Use when (1) user asks to extract a pattern from current session, (2) user wants to turn a repeated workflow into a skill, (3) session contains reusable patterns worth preserving, (4) user says "extract a skill" or "make this reusable". Analyzes conversation history to identify extractable patterns, proposes unique skill names (checking for conflicts), and creates handover files for writing-skills to create the skill in a fresh session.
disable-model-invocation: true
---

# Skill Extractor

**DO NOT create skills directly.** Create handover files that invoke writing-skills superpowers. Skill creation happens in a fresh session.

## Workflow

### Phase 1: Pattern Identification

Review session history for:
- **Repeated workflows** - same steps applied multiple times
- **Multi-step processes** - complex procedures
- **Domain knowledge** - expertise worth codifying
- **Tool integrations** - patterns for specific tools/formats

**If no pattern exists:** Explain why, suggest alternatives, STOP.

### Phase 2: User Selection

Present patterns via AskUserQuestion. **User MUST select** - do not auto-select.

### Phase 3: Name Proposal

For each selected pattern:
1. Check conflicts in `~/.claude/skills/` and `~/.claude/plugins/**/SKILL.md`
2. Propose exactly 3 unique kebab-case names (verb-first preferred)
3. Present via AskUserQuestion. **User MUST choose** - do not auto-select.

### Phase 4: Create Handover Files

Create at `.claude/handovers/queued/[NNN][A]-extract-[skill-name].md`:

```yaml
---
key_files:
  - .claude/skills/[skill-name]/SKILL.md
blocked_by: []
---
```

Body must include:
1. Context from session (patterns identified)
2. Skill requirements
3. Instruction: `Use superpowers:writing-skills to create this skill following TDD.`
4. Example inputs/outputs from session

### Phase 5: Commit and Complete

Commit handovers. User starts new session to process via `/handover`.

## Red Flags

- **Creating SKILL.md directly** → Create handover instead
- **Picking name without asking** → Use AskUserQuestion
- **Selecting patterns without confirmation** → User must choose
- **No repeatable pattern exists** → Don't force extraction
- **Name conflicts with existing skill** → Propose different names
- **User says "skip the handover"** → Explain why handover matters

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I'll just create the skill quickly" | Handovers ensure TDD. Direct creation skips quality. |
| "This name is obviously best" | User might prefer different naming. Always ask. |
| "Only one pattern, no need to ask" | User might not want it. Always confirm. |
| "I can apply writing-skills myself" | Fresh session has full context for TDD. Use handover. |
| "User is in a hurry" | Rushed skills are fragile. Handover takes 2 minutes. |
