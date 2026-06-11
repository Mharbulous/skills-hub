# skills-hub

Single source of truth for agent skills, served to every harness: Claude Code
(CLI, Desktop sandbox, web), Codex, and Cowork.

Skills are edited **here**, in git, with history and review. A GitHub Action
builds per-harness variants and publishes them to static hosting at an
unguessable URL. Each environment pulls at session start (Cowork uses thin
wrappers that fetch at invocation).

```
skills/            canonical definitions + per-harness overrides   ← edit here
   │  push to main
   ▼
GitHub Action      build/build.py merges overrides, builds bundles
   │
   ▼
Static hosting     https://<site>.web.app/<token>/
   ├── index.json                   catalog: name, description, hash
   ├── claude/skills.tar.gz         ready-to-extract bundle
   ├── claude/skills/<name>/…       individual files (Cowork wrappers fetch these)
   └── codex/skills.tar.gz
   │
   ▼
Environments       pull at session start via bootstrap/ snippets
```

## Repo layout

```
skills/<name>/SKILL.md              canonical skill definition
skills/<name>/overrides/claude.md   optional Claude-Code-specific override
skills/<name>/overrides/codex.md    optional Codex-specific override
skills/<name>/…                     subfiles (scripts/, references/) — copied as-is
build/build.py                      merge + bundle + catalog generator
bootstrap/                          per-environment install snippets
.github/workflows/publish.yml       builds and deploys on every push to main
firebase.json                       hosting config (public dir: site/)
```

## Override semantics

- Frontmatter keys in `overrides/<harness>.md` **replace** the canonical keys.
- If the override has a body, it is **appended** to the canonical body.
- No override file → that harness gets the canonical skill unchanged.

Run `python3 build/build.py` locally (needs `pip install pyyaml`) to preview
the merged output in `dist/`.

## One-time setup

1. **Firebase Hosting**: create (or reuse) a Firebase project. Pick a
   non-obvious project ID — it appears in the URL (`<id>.web.app`).
2. **Generate the path token**: `openssl rand -hex 16`
3. **Add three repository secrets** (Settings → Secrets and variables → Actions):
   - `FIREBASE_SERVICE_ACCOUNT` — JSON key for a service account with the
     *Firebase Hosting Admin* role (Firebase console → Project settings →
     Service accounts → Generate new private key)
   - `FIREBASE_PROJECT_ID` — the project ID
   - `PUBLISH_PATH_TOKEN` — the token from step 2
4. Push to `main`. The workflow builds, then deploys to
   `https://<project-id>.web.app/<token>/` — that's your **base URL**.
   (Until the secrets exist, the workflow still builds and uploads `dist/` as
   an artifact so you can inspect it; it just skips the deploy step.)
5. Wire up each environment — see **Consuming** below.

## Adding or editing a skill

1. Create `skills/<name>/SKILL.md` with frontmatter (`name`, `description`)
   and the instructions as the body.
2. Add subfiles (scripts, references) inside the skill folder; they ship as-is.
3. Only if a harness needs different wording: add `overrides/<harness>.md`.
4. Commit and push to `main`. Published within ~a minute; environments pick it
   up at their next session start.

## Consuming

**Claude Code sandboxes (web / Desktop)** — in the environment's setup script:

```bash
export SKILLS_BASE_URL="https://<project-id>.web.app/<token>"
mkdir -p ~/.claude/skills
curl -fsSL "$SKILLS_BASE_URL/claude/skills.tar.gz" | tar -xz -C ~/.claude/skills
```

If the hosting domain isn't reachable under the environment's network policy,
add `<project-id>.web.app` to the environment's allowed domains.

**Claude Code CLI (local)** — run `bootstrap/claude-setup.sh` (same one-liner)
manually, from a SessionStart hook, or on a schedule. On the machine where you
*edit* this repo you can instead symlink: `ln -s <clone>/dist/claude/skills
~/.claude/skills` and rebuild after editing.

**Codex** — `bootstrap/codex-setup.sh` extracts the `codex/` bundle into your
Codex skills directory (adjust the destination to your setup), via Codex's
setup/bootstrap mechanism or manually.

**Cowork** — one tiny wrapper per skill from
`bootstrap/cowork-wrapper-template/`; each wrapper fetches the published
`claude/skills/<name>/SKILL.md` at invocation. Wrappers are small and rarely
change, which minimizes exposure to Cowork file-sync bugs.

## Security model

The base URL is unguessable but **unauthenticated**: anyone holding the link
can read everything. Never put secrets (tokens, client data) in skills. To
rotate, change `PUBLISH_PATH_TOKEN`, re-run the workflow, and update the URL
in each environment's bootstrap.
