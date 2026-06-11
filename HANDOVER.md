---
key_files:
  - README.md
  - build/build.py
  - .github/workflows/publish.yml
  - bootstrap/claude-setup.sh
  - bootstrap/cowork-wrapper-template/SKILL.md
---

# Handover: skills-hub — skill migration & publishing setup

(To the incoming session: save this file as `HANDOVER.md` in the repo root and commit it, then begin with **Next Step** at the bottom.)

## Task

skills-hub (github.com/Mharbulous/skills-hub, **private**) is the new single
source of truth for the user's agent skills across four harnesses: Claude Code
CLI (local), Claude Code sandboxes (web/Desktop), Codex, and Cowork.

Architecture: canonical `SKILL.md` per skill + optional per-harness overrides
→ GitHub Action builds per-harness bundles → published to static hosting at an
unguessable URL → each environment pulls at session start (Cowork uses thin
wrappers that fetch at invocation).

Your job: migrate the user's scattered skills into this repo, then (when the
user is ready) set up publishing and wire up each environment.

## Current State

**Done:**
- Repo scaffolded and pushed to `main` (initial commit `fd1db50`); local clone
  at `C:\Users\Brahm\Git\skills-hub`
- Layout: `skills/<name>/SKILL.md` (canonical) +
  `skills/<name>/overrides/{claude,codex}.md` (optional); subfiles
  (`scripts/`, `references/`) ship as-is
- `build/build.py` verified working. Merge semantics: override frontmatter
  keys REPLACE canonical keys; a non-empty override body APPENDS to the
  canonical body. Outputs `dist/{claude,codex}/skills/…`, per-harness
  `skills.tar.gz` (skill folders at archive root, so they extract straight
  into a skills directory), and `dist/index.json` (descriptions + sha256)
- `.github/workflows/publish.yml`: on every push to main it builds and uploads
  `dist/` as an artifact; it deploys to Firebase Hosting ONLY when all three
  secrets exist (`FIREBASE_SERVICE_ACCOUNT`, `FIREBASE_PROJECT_ID`,
  `PUBLISH_PATH_TOKEN`) — none are set yet, so deploy is skipped by design
- Example skill `skills/hello-world` (with a codex override) demonstrates the
  merge end to end
- User was instructed to grant the Claude GitHub App access to skills-hub
  (github.com/settings/installations) — **not yet confirmed done**
- **50 skills migrated** from `C:\Users\Brahm\.claude\skills` into
  `skills/<name>/` — build verified with 51 total (50 migrated + hello-world)

**Remaining:**
1. ~~Migration phase 1~~ — **DONE** (this commit)
2. Migration phase 2 — fold the user's Codex-optimized variants in as
   `overrides/codex.md` (ask where they live), plus any generic skills kept in
   AGENTS.md-style files
3. Hosting decision + setup (OPEN — see Key Discoveries), then record the base
   URL `https://<host>/<token>`
4. Wire environments:
   - Claude sandboxes: environment setup script —
     `mkdir -p ~/.claude/skills` then
     `curl -fsSL $URL/claude/skills.tar.gz | tar -xz -C ~/.claude/skills`
     (hosting domain may need adding to the environment's network allowlist)
   - Claude CLI local: `bootstrap/claude-setup.sh`, or symlink from this clone
   - Codex: `bootstrap/codex-setup.sh` (confirm the Codex skills directory)
   - Cowork: repoint the user's "co-clerk" wrapper repo to the published URL
     using `bootstrap/cowork-wrapper-template/SKILL.md` — each wrapper's
     `description` must be copied verbatim from `index.json` so routing works
5. Eventually retire the old scattered copies and the old global-skills repo

## Key Discoveries

- User requirements, explicitly confirmed: obscure URL with NO auth is
  acceptable (content not sensitive — but never let a skill contain secrets);
  all four harnesses needed; canonical + overrides (not full per-harness
  forks); session-start freshness is enough (no invocation-time fetching
  except the Cowork wrappers)
- **Hosting is undecided.** Firebase Hosting (works on free tier; user already
  has Firebase from SyncoPaid; needs a service-account JSON secret) vs GitHub
  Pages (simpler — no secrets beyond the path token — but requires GitHub Pro
  for private repos, and the site root `mharbulous.github.io/skills-hub` is
  guessable, so content must sit under a secret path). The user dismissed the
  question when last asked — don't push; resolve it when they raise it or when
  publishing becomes the blocker
- Claude Code web sandboxes DO scan `~/.claude/skills` at session start
  (verified live); skills are enumerated at start only — mid-session additions
  don't register
- A web session CANNOT do the migration: the source skills live on the user's
  machine. Migration must run in a LOCAL Claude Code session inside
  `C:\Users\Brahm\Git\skills-hub`

## Red Herrings

- Firestore: rejected — skills are files; a database adds schema, serving, and
  auth work and loses git history/diffs
- Plugin marketplaces (`extraKnownMarketplaces`/`enabledPlugins`): Claude-Code
  only; does nothing for Codex or Cowork
- Multi-repo web sessions: a secondary repo's skills don't get registered as
  invocable

## Working With the User (Brahm)

- Self-described "not very technical" at the terminal. He runs **Windows
  PowerShell 5.1: `&&` does not work there.** Give ONE paste-able block at a
  time, absolute paths, built-in `Test-Path` checks that print red STOP
  messages, and tell him what success looks like
- PowerShell keeps executing lines after a failure — an earlier mishap
  `git init` + `git add -A`'d his entire Downloads folder when a `tar` step
  failed (fully cleaned up since). Always gate git/destructive steps behind
  existence checks
- Chat file downloads have stripped hyphens from filenames before
  (`skillshubscaffold.tar.gz`); prefer .zip over .tar.gz, or better, move
  files via git now that the repo exists
- His repos live in `C:\Users\Brahm\Git`; global Claude skills at
  `C:\Users\Brahm\.claude\skills`; he has a "co-clerk" repo (Cowork thin
  wrappers pointing at a local repo) and Codex-optimized skill copies
  (location unconfirmed)

## Next Step

Run migration phase 2: ask the user where the Codex-optimized skill variants
live, then fold them in as `overrides/codex.md` files.
