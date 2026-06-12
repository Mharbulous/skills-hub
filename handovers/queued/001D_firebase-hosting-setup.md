---
write_targets: []
read_only_targets:
  - .github/workflows/publish.yml
  - firebase.json
  - build/build.py
---

# Handover: Firebase Hosting Setup

## Task

Set up Firebase Hosting to serve the built skill bundles at an unguessable URL. This is an interactive session — guide the user through Firebase project setup, secret configuration, and deployment verification.

## Current State

**Done:**
- All skill migrations complete (Claude, Codex, Coclerk)
- CI workflow (`publish.yml`) already has Firebase deploy logic, gated on 3 secrets
- `firebase.json` exists in repo
- User already has Firebase from SyncoPaid project

**Remaining:**
- Verify CI is green from prior migration pushes (check GitHub Actions tab)
- Guide user through Firebase project decision: reuse SyncoPaid project or create new one
- Generate path token: `openssl rand -hex 16`
- Add 3 repo secrets via GitHub Settings or `gh secret set`:
  - `FIREBASE_SERVICE_ACCOUNT` (service account JSON)
  - `FIREBASE_PROJECT_ID`
  - `PUBLISH_PATH_TOKEN` (the generated token)
- Push to trigger deploy
- Verify site is live at `https://<project-id>.web.app/<token>/`

## Key Discoveries

- The publish workflow skips Firebase deploy gracefully when secrets are missing — no CI failures from this
- Firebase Hosting works on free Spark tier
- User runs Windows PowerShell 5.1 — give one paste-able block at a time, no `&&` chaining
- The path token makes the URL unguessable; no auth layer needed (user confirmed this is acceptable)
- Hosting decision was previously deferred — now is the time to resolve it

## Next Step

Verify CI status on GitHub Actions, then walk the user through Firebase project setup and secret configuration.
