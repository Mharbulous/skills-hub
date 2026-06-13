# Web App Platform — Promote Subfile

Platform-specific procedures for promoting web applications (npm + Firebase Hosting). Loaded by the main `/promote` orchestrator — do not invoke directly.

## PREFLIGHT

### Run Tests
```bash
npm run test:run 2>&1 | tail -20
```

**If tests fail:** Spawn a subagent to run `/regression-test-repair`. After the subagent completes, re-run the test command above. If tests now pass, continue. If tests still fail, STOP — do NOT proceed.

### Run Build
```bash
npm run build
```

**If build fails:** STOP. Do NOT proceed.

## BACKGROUND_BACKEND_DEPLOY

This is a two-phase step: first review the workflow for completeness, then trigger it.

### Phase 1: Review deploy workflow (foreground, Opus)

Spawn a **foreground Opus subagent** (`model: opus`) to audit the deploy workflow before triggering it. The subagent should:

1. Read `.github/workflows/deploy-backend.yml`
2. Read `firebase.json` to identify all configured Firebase targets (hosting, functions, firestore, storage, extensions)
3. List Cloud Run service directories under `cloud-run/`
4. List all Cloud Functions in `functions/` (entry points in `functions/index.js` or individual function files)
5. Check for any other deploy workflows in `.github/workflows/`

**Evaluate comprehensiveness**: Does the workflow deploy everything it should? Check for:
- All Cloud Run services have matching deploy jobs
- All Firebase config targets (rules, indexes, storage) are included
- Trigger paths cover all relevant source directories
- The `vars.REGIONS` repo variable matches the regions used in `firebase.json` or function configs

**If gaps are found**: The subagent should fix `deploy-backend.yml` directly, commit the changes with a conventional commit message, and push to main — so the subsequent workflow trigger deploys with the updated workflow.

**If no gaps found**: Report "Workflow is comprehensive" and return.

### Phase 2: Deploy (background, Sonnet)

After Phase 1 completes, spawn a **background Sonnet subagent** (`run_in_background: true`, `model: sonnet`) to deploy all backend services. The subagent should:

1. **Trigger the deploy-backend GitHub Action** (deploys Cloud Run, Cloud Functions, rules, and indexes):
```bash
gh workflow run deploy-backend.yml
```

2. **Wait for the run to start** (poll up to 30 seconds):
```bash
gh run list --workflow=deploy-backend.yml --limit 1 --json databaseId,status,createdAt
```

3. **Monitor until completion**:
```bash
gh run watch <RUN_ID>
```

4. **Report results**: Return a summary including success/failure status and duration.

**If `gh workflow run` fails** (e.g., workflow not found), fall back to direct deploy:
```bash
npx firebase-tools deploy --only functions,firestore:rules,firestore:indexes,storage --force --project coryphaeus-ed11a
```
**Report these limitations** if the fallback is used:
- Cloud Run services (pdf-converter, lawyer-validator) cannot be built/deployed locally — they require Cloud Build
- Cloud Function → Cloud Run URL wiring is skipped (the functions will use previously wired URLs)

## VERSION_SOURCE

Git tags are the sole version source for web apps. No fallback file.

If no semver tags exist, this is the first promotion — use `v1.0.0`.

## VERSION_WRITE

No version file to update. Git tags are the single source of truth.

(This is a no-op — return to the main orchestrator.)

## BUILD_AND_DEPLOY

**Critical:** Must be on the `production` branch.

### Build
```bash
git branch --show-current  # Must show "production"
npm run build
```

**If build fails:** STOP. Do NOT deploy.

### Detect Firebase Hosting Target

Check `firebase.json` for hosting configuration:
```bash
cat firebase.json | grep -A2 '"target"'
```

- If a single hosting target exists → use `firebase deploy --only hosting`
- If multiple targets exist → identify which target has `"public": "dist"` (the app build output) and deploy that specific target: `firebase deploy --only hosting:[TARGET_NAME]`

### Deploy

**HITL mode only:** Ask "Deploy to Firebase Hosting now?" before proceeding.

```bash
firebase deploy --only hosting:[TARGET]
```

**If deploy fails:** Check `firebase login` status. STOP and report.

## SUMMARY_EXTRAS

```
Deployed: Firebase Hosting ([TARGET])
```

## ERROR_RECOVERY

- **Test failures**: Use `/regression-test-repair` subagent, then re-run tests
- **Deploy failures**: Check `firebase login`, verify `firebase.json` target configuration
