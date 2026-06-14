---
write_targets:
  - bootstrap/claude-setup.sh
  - bootstrap/codex-setup.sh
read_only_targets:
  - .github/workflows/publish.yml
  - dist/index.json
  - bootstrap/cowork-wrapper-template/SKILL.md
---

# Handover: Wire Remaining Environments

## Task

Complete environment wiring for Claude sandboxes, Claude CLI local, and Codex. Cowork wrappers were already generated in 001E.

## Current State

**Done:**
- Firebase Hosting live at https://skills-hub.web.app/
- Cowork: 103 thin fetcher wrappers generated in Coclerk plugins/wrappers/
- Bootstrap scripts exist and are functional (`bootstrap/claude-setup.sh`, `bootstrap/codex-setup.sh`)

**Remaining:**
- Claude sandboxes (web/Desktop): configure environment setup scripts to run `curl -fsSL "https://skills-hub.web.app/claude/skills.tar.gz" | tar -xz -C ~/.claude/skills` — this MUST be a setup script, NOT a SessionStart hook
- Claude CLI local: run `SKILLS_BASE_URL="https://skills-hub.web.app" ./bootstrap/claude-setup.sh` or set up a local symlink from dist/
- Codex: confirm skills directory location, run `SKILLS_BASE_URL="https://skills-hub.web.app" ./bootstrap/codex-setup.sh`
- E2E test: verify SyncoPaid web session has `commit` skill with `gather-context.sh` and `sanitize-commit.sh` working
- Add `skills-hub.web.app` to sandbox network allowlists if needed

## Key Discoveries

- Skills tarball verified accessible at https://skills-hub.web.app/claude/skills.tar.gz (HTTP 200)
- Claude Code web sandboxes scan `~/.claude/skills` at session start only; mid-session additions don't register
- Setup scripts run before Claude Code launches; SessionStart hooks run AFTER skill enumeration
- SyncoPaid's `.claude/settings.json` already grants permissions for `~/.claude/skills/commit/scripts/gather-context.sh`

## Next Step

Interactive session to configure each environment and run E2E verification.
