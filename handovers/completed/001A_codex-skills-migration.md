---
write_targets:
  - skills/diagnose/SKILL.md
  - skills/dyu/SKILL.md
  - skills/grill-me/SKILL.md
  - skills/grill-with-docs/SKILL.md
  - skills/handoff/SKILL.md
  - skills/maintain-code/SKILL.md
  - skills/migrate-to-shoehorn/SKILL.md
  - skills/promote/SKILL.md
  - skills/prototype/SKILL.md
  - skills/scaffold-exercises/SKILL.md
  - skills/setup-matt-pocock-skills/SKILL.md
  - skills/tdd/SKILL.md
  - skills/to-issues/SKILL.md
  - skills/to-prd/SKILL.md
  - skills/triage/SKILL.md
  - skills/write-a-skill/SKILL.md
  - skills/zoom-out/SKILL.md
  - skills/glimpse/overrides/codex.md
  - skills/goalbuddy/overrides/codex.md
  - skills/handover/overrides/codex.md
  - skills/systematic-debugging/overrides/codex.md
read_only_targets:
  - build/build.py
  - skills/glimpse/SKILL.md
  - skills/goalbuddy/SKILL.md
  - skills/handover/SKILL.md
  - skills/systematic-debugging/SKILL.md
---

# Handover: Codex Skills Migration

## Task

Migrate 21 skills from `C:\Users\Brahm\.codex\skills\` into skills-hub. 4 overlap with existing canonical skills (glimpse, goalbuddy, handover, systematic-debugging) and need diffing to create `overrides/codex.md`. 17 are Codex-only and become new canonical `skills/<name>/SKILL.md` entries.

## Current State

**Done:**
- 50 Claude skills already migrated into `skills/<name>/SKILL.md`
- Build system verified working (51 skills including hello-world)
- 3 commits on main: scaffold, bulk migration, handover doc

**Remaining:**
- Diff the 4 overlapping skills against their canonical versions; create `overrides/codex.md` where they differ
- Add 17 Codex-only skills as new canonical entries
- Review `C:\Users\Brahm\.codex\skills\AGENTS.md` for any additional content worth capturing
- Run `python build/build.py`, verify, commit, push

## Key Discoveries

- Codex skills source: `C:\Users\Brahm\.codex\skills\` (confirmed, 21 skills + AGENTS.md)
- 4 overlapping skills: glimpse, goalbuddy, handover, systematic-debugging
- 17 Codex-only skills: diagnose, dyu, grill-me, grill-with-docs, handoff, maintain-code, migrate-to-shoehorn, promote, prototype, scaffold-exercises, setup-matt-pocock-skills, tdd, to-issues, to-prd, triage, write-a-skill, zoom-out
- Build merge semantics: override frontmatter keys REPLACE canonical; non-empty override body APPENDS to canonical body
- The `promote` skill name may conflict with the existing `/promote` skill in Claude skills — check if there's already a `skills/promote/` directory (there isn't as of Phase 1 completion, but verify)

## Next Step

REQUIRED SKILL: superpowers:writing-plans

Enumerate Codex skills, diff the 4 overlapping ones against canonical, migrate all into skills-hub with appropriate override files.
