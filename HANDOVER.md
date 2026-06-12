---
key_files:
  - README.md
  - build/build.py
  - .github/workflows/publish.yml
  - bootstrap/claude-setup.sh
  - bootstrap/cowork-wrapper-template/SKILL.md
---

# Handover: skills-hub migration

## Status

Phase 1 (Claude skills bulk migration) is complete. Remaining work is split into
6 sequential handover files in `handovers/queued/`:

| Order | File | Phase |
|-------|------|-------|
| 1 | `001A_codex-skills-migration.md` | Migrate 21 Codex skills, create overrides for 4 overlapping |
| 2 | `001B_coclerk-domain-skills-migration.md` | Extract and migrate ~32 Coclerk legal practice skills |
| 3 | `001C_slash-commands-migration.md` | Migrate 12 custom slash commands from `~/.claude/commands/` |
| 4 | `001D_firebase-hosting-setup.md` | Set up Firebase Hosting, configure secrets, verify deploy |
| 5 | `001E_wire-environments.md` | Wire Claude sandboxes, CLI, Codex, and Cowork to hosted URL |
| 6 | `001F_verify-and-cleanup.md` | E2E verification, retire old copies, archive legacy repos |

Use `/handover` to process them in order. They form a dependency chain
(001A -> 001B -> 001C -> 001D -> 001E -> 001F).

## Architecture

Canonical `SKILL.md` per skill + optional per-harness `overrides/{claude,codex}.md`
-> GitHub Action builds per-harness bundles -> Firebase Hosting at unguessable URL
-> each environment pulls at session start (Cowork fetches at invocation).

## Key Source Locations

- `C:\Users\Brahm\.codex\skills\` -- 21 Codex skills + AGENTS.md
- `C:\Users\Brahm\Git\Coclerk\plugins\wrappers\` -- ~32 .skill ZIPs (legal practice tools)
- `C:\Users\Brahm\.claude\commands\` -- 12 custom slash commands
- `C:\Users\Brahm\Git\skills-hub\build\build.py` -- build script
- `C:\Users\Brahm\Git\skills-hub\bootstrap\` -- environment setup scripts
