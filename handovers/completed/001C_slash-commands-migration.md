---
write_targets:
  - skills/doc-audit/SKILL.md
  - skills/Finalize/SKILL.md
  - skills/promote/SKILL.md
  - skills/review-plan/SKILL.md
  - skills/template/SKILL.md
read_only_targets:
  - build/build.py
  - skills/agents-md-curator/SKILL.md
  - skills/commit/SKILL.md
---

# Handover: Custom Slash Commands Migration

## Task

Migrate 12 custom slash command files from `C:\Users\Brahm\.claude\commands\` into skills-hub. Some may already exist as skills and need deduplication; others are standalone commands that should become new canonical skills.

## Current State

**Done:**
- All skill migrations complete (Claude, Codex, Coclerk in prior phases)
- Build system verified working

**Remaining:**
- Audit all 12 command files against existing skills to determine overlap vs new:
  - `agents-md-curator.md` — likely overlaps with existing `skills/agents-md-curator/`
  - `commit.md` — likely overlaps with existing `skills/commit/`
  - `doc-audit.md` + `doc-audit/doc-audit.md` — check if skill exists
  - `Finalize.md` + `Finalize/Finalize.md` — check if skill exists
  - `promote.md` + `promote/desktop.md` + `promote/web.md` — has subfiles, check overlap
  - `review-plan.md` — standalone command
  - `template.md` + `template/template.md` — may be a boilerplate/scaffold
- For overlapping commands: determine if the command file adds anything beyond invoking the skill; if so, merge the content
- For standalone commands: add as new canonical `skills/<name>/SKILL.md`
- Some commands have subdirectory variants (doc-audit, Finalize, promote, template) — understand the parent/child relationship
- Run `python build/build.py`, verify, commit, push

## Key Discoveries

- Custom slash commands live in `C:\Users\Brahm\.claude\commands\` — separate from skills in `~/.claude/skills/`
- Commands can have subdirectories for sub-commands (e.g., `promote/desktop.md`, `promote/web.md`)
- Some commands may just be thin wrappers that invoke the corresponding skill — these might not need migration if the skill is already canonical
- The relationship between commands and skills needs investigation: are commands aliases, invocation wrappers, or independent implementations?

## Next Step

Read each command file, compare against existing skills, and determine which need migration vs which are redundant wrappers.
