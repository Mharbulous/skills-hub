---
name: promote
description: Use this skill when the user invokes /promote and asks to promote, release, deploy to production, run a production promotion, decide versioning, create release tags, use HITL approvals, or promote a web app or desktop app from main to production. This workflow detects the platform, validates builds and tests, handles stale PR cleanup, versioning, fast-forward production, release tags, build/deploy, backend deployment, and final promotion summaries.
---

# Promote

Promote `main` to `production` as a release operation. Use fast-forward promotion. Do not squash merge. Production should equal main at the release tag.

## Modes

Detect HITL mode from the user's prompt. Treat any case-insensitive mention of `HITL`, `human in the loop`, or `approval at each decision` as HITL.

- Autonomous mode: make routine release decisions, execute the workflow, and stop only on errors or destructive actions that require explicit approval.
- HITL mode: present recommendations with reasoning before each decision point, then wait for approval before continuing.

Maintain a visible checklist in conversation and update it as work completes:

```text
- Pre-flight validation
- Background backend deployment
- Commit analysis and version decision
- Version write, if applicable
- Fast-forward production
- Tag and push release
- Build/deploy from production
- Return to main and summarize
```

## Project Type Detection

Detect the platform from the repository root.

- If only `package.json` exists, this is a Web App. Read `references/web.md`.
- If a root `*.sln` file or `dotnet/` directory exists, this is a Desktop App. Read `references/desktop.md`.
- If both match, stop and ask which platform to promote.
- If neither matches, stop and report: `Cannot detect project type.`

The platform reference defines these procedures used below:

- `PREFLIGHT`: test and build validation commands
- `BACKGROUND_BACKEND_DEPLOY`: backend deploy review/spawn procedure, if any
- `VERSION_SOURCE`: fallback version source when no semver tag exists
- `VERSION_WRITE`: version file updates, if any
- `BUILD_AND_DEPLOY`: production build and deploy steps
- `SUMMARY_EXTRAS`: platform-specific final summary fields
- `ERROR_RECOVERY`: platform-specific recovery notes

## Workflow

### 1. Pre-Flight Validation

Verify branch and cleanliness.

Requirements:

- Must start on `main`.
- Worktree must be clean.
- If either condition fails, stop and tell the user to commit, stash, or switch branches first.

Sync `main`, then follow the platform reference `PREFLIGHT` procedure. If tests or build fail, follow platform `ERROR_RECOVERY`; if the failure remains, stop.

### 2. Background Backend Deployment

After pre-flight passes, backend code is known-good. Follow platform `BACKGROUND_BACKEND_DEPLOY` if present.

### 3. Commit Analysis And Version Decision

Find the latest semver tag. If no semver tag exists, follow platform `VERSION_SOURCE`. If that also yields no version, use `v1.0.0`.

Inspect unreleased commits. Verify GitHub CLI auth before PR or workflow calls.

Close stale promotion PRs (any open `main` to `production` PRs).

Decide the version bump from the full commit set:

- Patch: bug fixes, maintenance, refinement, or partial feature work not yet a complete capability.
- Minor: a complete, functional new workflow or capability.
- Major: breaking changes, incompatible release behavior, or explicit user/product direction.

Autonomous mode: decide and state the reasoning in 2-3 sentences.
HITL mode: recommend Patch, Minor, or Major with reasoning, then ask for approval.

### 4. Version Write

Follow platform `VERSION_WRITE`. If a version file changes, commit and push it to `main` before continuing.

### 5. Fast-Forward Production

Production must be a fast-forward of `main`. Close any stale `main` to `production` PRs; this workflow does not use PRs for promotion.

```bash
git push origin main:production
```

If it fails, inspect divergence. If production has commits not on main, investigate. Prefer the narrowest safe command and require explicit approval before any force push.

### 6. Tag And Push Release

Create an annotated tag with a release description and version bump rationale. Push the tag.

If the tag already exists, stop and ask whether to delete/recreate it or choose a new version. Never silently overwrite a release tag.

### 7. Build And Deploy From Production

Critical: build from the `production` branch, never from `main`. Follow platform `BUILD_AND_DEPLOY`.

### 8. Cleanup And Summary

Return to `main`. Check the backend deployment if one was used.

Final summary format:

```text
Production Promotion Complete!

Version: [VERSION]
Tag: [VERSION]
Release commit: [SHA]
Backend deployment: [completed successfully / in progress / failed with details]

Version bump rationale: [reasoning]
Verified:
- [exact command and result]
Assumptions not verified:
- [any remaining uncertainty]
Non-blocking warnings:
- [warnings that did not block release]
```

## Failure Handling

- Tests fail: follow platform `ERROR_RECOVERY`, rerun once if a repair was made, then stop if still failing.
- Build fails: stop, show the failing command and the relevant error output, recommend fixing on `main`.
- Fast-forward fails: inspect divergence before proposing a force push; require explicit approval for force.
- Tag exists: stop and ask for user direction.
- Deploy fails: follow platform `ERROR_RECOVERY`, report exact status and next command.

## Invariants

- Always fast-forward `production` from `main`.
- Never squash merge for this workflow.
- Never modify production directly.
- Every release gets a semver tag.
- Keep release decisions explicit enough for the user to audit later.
