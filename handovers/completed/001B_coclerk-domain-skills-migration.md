---
write_targets:
  - skills/ar-follow-up/SKILL.md
  - skills/billing-summary/SKILL.md
  - skills/build-timeline/SKILL.md
  - skills/case-data/SKILL.md
  - skills/consolidate-memory/SKILL.md
  - skills/court-interest-calculator/SKILL.md
  - skills/dates-and-deadlines/SKILL.md
  - skills/deadline-calculation/SKILL.md
  - skills/draft-bcsc-form/SKILL.md
  - skills/draft-small-claims-form/SKILL.md
  - skills/executive-assistant/SKILL.md
  - skills/file-prioritization/SKILL.md
  - skills/file-review-prep/SKILL.md
  - skills/fill-PDF/SKILL.md
  - skills/invoice-reviewing/SKILL.md
  - skills/invoice-tracking/SKILL.md
  - skills/judicial-decisions/SKILL.md
  - skills/legal-memo-extractor/SKILL.md
  - skills/litigation-fact-extractor/SKILL.md
  - skills/matter-status-tracking/SKILL.md
  - skills/practice-data/SKILL.md
  - skills/prioritizing/SKILL.md
  - skills/proof-read/SKILL.md
  - skills/read-docx/SKILL.md
  - skills/retainer-tracking/SKILL.md
  - skills/skill-updater/SKILL.md
  - skills/task-prioritization/SKILL.md
  - skills/time-entry-drafting/SKILL.md
  - skills/time-sorting/SKILL.md
  - skills/trial-lawyer-correspondence/SKILL.md
  - skills/westlaw-query-optimizer/SKILL.md
  - skills/wip-tracker/SKILL.md
read_only_targets:
  - build/build.py
  - skills/handover/SKILL.md
  - skills/skill-creator-improved/SKILL.md
---

# Handover: Coclerk Domain Skills Migration

## Task

Extract and migrate ~32 legal practice skills from Coclerk wrapper `.skill` files (ZIP packages) at `C:\Users\Brahm\Git\Coclerk\plugins\wrappers\` into skills-hub as new canonical `skills/<name>/SKILL.md` entries.

## Current State

**Done:**
- 50+ skills already in skills-hub (Claude skills + Codex skills from Phase 1)
- Build system verified working

**Remaining:**
- Extract SKILL.md from each `.skill` ZIP file
- Add as new canonical skills to skills-hub
- Handle overlaps: `handover.skill` and `skill-creator-improved.skill` already exist as canonical skills — diff and create overrides if they differ, or skip if identical
- Some wrappers have companion directories (court-interest-calculator, draft-small-claims-form, judicial-decisions, legal-memo-extractor, litigation-fact-extractor, proof-read, read-docx) — check if directories contain additional subfiles (scripts, references) to include
- Run `python build/build.py`, verify, commit, push

## Key Discoveries

- Coclerk wrappers source: `C:\Users\Brahm\Git\Coclerk\plugins\wrappers\`
- `.skill` files are ZIP archives containing `<name>/SKILL.md` — extract with standard unzip
- There's also a `README.txt` in the wrappers directory worth reviewing for context
- 2 overlapping skills: handover, skill-creator-improved (already canonical in skills-hub)
- 7 skills have companion directories alongside their .skill files — these may contain subfiles that need to be preserved
- These are mostly legal practice domain tools (billing, court forms, litigation, time tracking)

## Next Step

REQUIRED SKILL: superpowers:writing-plans

Extract SKILL.md from each .skill ZIP, migrate into skills-hub, handle overlaps with existing canonical skills.
