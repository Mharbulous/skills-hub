---
key_files:
  - README.md
  - build/build.py
  - .github/workflows/publish.yml
  - bootstrap/claude-setup.sh
  - bootstrap/cowork-wrapper-template/SKILL.md
---

# Skills-hub

## Status

All skill migrations complete. Firebase Hosting live at https://skills-hub.web.app/hub/.

**Completed:**
- 001A: 21 Codex skills migrated (17 new + 3 overrides)
- 001B: 32 Coclerk legal practice skills migrated (+ 2 cowork overrides)
- 001C: 3 slash commands migrated (doc-audit, finalize, review-plan) + promote references
- 001D: Firebase Hosting configured and deployed (103 skills live)
- 001E: Cowork wrappers generated (103 thin fetchers)

**Remaining:**
- 002: Commit handover setup files
- 003: Wire remaining environments (Claude sandboxes, CLI local, Codex) + E2E test
- Retire old skill locations and archive legacy repos

## Architecture

Canonical `SKILL.md` per skill + optional per-harness `overrides/{claude,codex,cowork}.md`
-> GitHub Action builds per-harness bundles -> Firebase Hosting at https://skills-hub.web.app/hub/
-> each environment pulls at session start (Cowork fetches at invocation).

## Build Output

- `dist/claude/skills.tar.gz` — Claude harness bundle
- `dist/codex/skills.tar.gz` — Codex harness bundle
- `dist/index.json` — skill catalog with descriptions and SHA-256 hashes
