---
write_targets:
  - bootstrap/claude-setup.sh
  - bootstrap/codex-setup.sh
  - bootstrap/cowork-wrapper-template/SKILL.md
read_only_targets:
  - .github/workflows/publish.yml
  - dist/index.json
---

# Handover: Wire All Environments

## Task

Configure all 4 harness environments (Claude sandboxes, Claude CLI local, Codex, Cowork) to pull skills from the live Firebase Hosting URL.

## Current State

**Done:**
- All skills migrated and built
- Firebase Hosting live with skills published at unguessable URL
- Bootstrap script templates exist in `bootstrap/`

**Remaining:**
- Claude sandboxes (web/Desktop): create or update environment setup script that fetches and extracts skills tarball into `~/.claude/skills/` — this MUST be a setup script, NOT a SessionStart hook (skills are enumerated before hooks run)
- Claude CLI local: configure `bootstrap/claude-setup.sh` to symlink `dist/claude/skills` into `~/.claude/skills/`, or fetch from the hosted URL
- Codex: confirm Codex skills directory location, configure `bootstrap/codex-setup.sh`
- Cowork: convert 42 Coclerk wrappers to thin fetchers using `bootstrap/cowork-wrapper-template/SKILL.md` — each wrapper's description must come from `dist/index.json` for routing
- E2E test: SyncoPaid web session should have `commit` skill with `gather-context.sh` and `sanitize-commit.sh` working — this proves the full pipeline

## Key Discoveries

- Claude Code web sandboxes scan `~/.claude/skills` at session start only; mid-session additions don't register
- Setup scripts run before Claude Code launches; SessionStart hooks run AFTER skill enumeration — use setup scripts
- SyncoPaid's `.claude/settings.json` already grants permissions for `~/.claude/skills/commit/scripts/gather-context.sh` and `sanitize-commit.sh --message *` — these paths must remain unchanged
- Cowork wrappers fetch at invocation time (not session start) — different pattern from the other harnesses
- Reference docs: https://code.claude.com/docs/en/claude-code-on-the-web (setup scripts, network allowlists)

## Next Step

REQUIRED SKILL: superpowers:writing-plans

Configure each environment's bootstrap script to pull from the published Firebase URL, then run E2E verification with SyncoPaid.
