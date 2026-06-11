# GitHub Workflows: Anti-Patterns and Fixes

> Extracted from this repository's commit history.

## Top 10 Most Common Mistakes

1. **Missing permissions** — Adding an explicit `permissions:` block but forgetting it revokes all defaults (including `contents: read` for checkout)
2. **Matrix job outputs are non-deterministic** — Last-write-wins when parallel matrix jobs write to the same output key
3. **Unbounded polling loops** — `while true` with no timeout burns runner minutes forever
4. **Workflow lookup by display name** — GitHub's name index goes stale; always use file path
5. **Service name typos** — Cloud Run silently creates a new service instead of erroring
6. **Deploying unchanged resources** — Rules, configs, and IAM bindings re-applied on every run
7. **Orchestrator infinite loops** — Agent finds no work, exits without updating the completion signal, gets re-triggered
8. **`--no-traffic` on Cloud Run updates** — Deploys new revision but callers keep hitting old code
9. **Job-level `outputs:` not declared** — Step writes to `$GITHUB_OUTPUT` but job never exposes it; downstream gets empty string
10. **YAML indentation errors** — Action inputs placed outside `with:` block; syntactically valid YAML, semantically broken workflow

---

## Quick Diagnostic Checklist

When a workflow fails, check in this order:

1. **Permissions** — Does the `permissions:` block include all needed permissions? Is `contents: read` present?
2. **Outputs wiring** — Is there both a step-level `>> $GITHUB_OUTPUT` AND a job-level `outputs:` declaration?
3. **Service names** — Are Cloud Run/Function names correct? Check against `gcloud run services list`.
4. **File path vs display name** — Are `gh workflow` commands using filename or display name?
5. **Matrix outputs** — Are you relying on matrix job outputs for values that differ per matrix run?
6. **YAML structure** — Are action inputs inside `with:`? Is `name:` on line 1?
7. **Timeouts** — Does every polling loop have a maximum iteration count?
8. **Trigger context** — Are you using OIDC in a `schedule` trigger? Does the auth method match the trigger type?
9. **Completion signals** — In orchestrated workflows, does the worker always update the "done" signal?
10. **Traffic routing** — Is `--no-traffic` being used when it shouldn't be?

---

## 1. Permissions and Authentication

### 1.1 Explicit `permissions:` revokes all defaults

**Anti-pattern:** Adding `permissions: { actions: write }` to enable/disable workflows. This silently removes the default `contents: read`, breaking `actions/checkout`.

**Symptom:** Checkout step fails with "resource not accessible by integration."

**Fix:** Declare every permission you need:
```yaml
permissions:
  contents: read    # Always needed for checkout
  actions: write    # For workflow enable/disable
```

### 1.2 `workflows: write` is separate from `contents: write`

**Anti-pattern:** A workflow that copies `.yml` files into `.github/workflows/` uses `contents: write` but not `workflows: write`.

**Symptom:** Push or PR creation fails with 403 when modifying workflow files.

**Fix:** Add `workflows: write` to permissions. GitHub treats workflow files as a separate security boundary.

### 1.3 OIDC auth fails in scheduled workflows

**Anti-pattern:** Third-party actions (e.g., `anthropics/claude-code-action`) default to OIDC token exchange, which doesn't work reliably in `schedule`-triggered workflows.

**Symptom:** 401 Unauthorized during OIDC exchange.

**Fix:** Explicitly pass the built-in token:
```yaml
with:
  github_token: ${{ secrets.GITHUB_TOKEN }}
```

### 1.4 Cloud Build log streaming requires project Viewer role

**Anti-pattern:** Synchronous `gcloud builds submit` streams logs by default, which requires project-level Viewer permissions. `roles/logging.viewer` alone is NOT sufficient — the error message says "Viewer/Owner of the project." `--suppress-logs` also does not help — gcloud still fails during the polling phase.

**Symptom:** Build completes in Cloud Console but `gcloud builds submit` exits with code 1. Error: "The build is running, and logs are being written to the default logs bucket. This tool can only stream logs if you are Viewer/Owner of the project."

**Fix:** Grant `roles/viewer` to the service account:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/viewer"
```

**Alternative:** Use `--async` with bounded polling via `gcloud builds describe`:
```bash
BUILD_ID=$(gcloud builds submit --async --format='value(id)' ...)
POLL_COUNT=0
MAX_POLLS=40  # 10 min at 15s intervals
while [ $POLL_COUNT -lt $MAX_POLLS ]; do
  STATUS=$(gcloud builds describe "$BUILD_ID" --format='value(status)')
  case "$STATUS" in
    SUCCESS) break ;;
    FAILURE|INTERNAL_ERROR|TIMEOUT|CANCELLED|EXPIRED) exit 1 ;;
    *) POLL_COUNT=$((POLL_COUNT + 1)); sleep 15 ;;
  esac
done
```

### 1.5 Unconditional IAM policy bindings

**Anti-pattern:** Calling `gcloud run services add-iam-policy-binding` on every deploy. It's a read-modify-write operation that generates audit log noise and risks race conditions.

**Symptom:** No error, but unnecessary API calls and audit entries.

**Fix:** Check first, skip if already set:
```bash
EXISTING=$(gcloud run services get-iam-policy "$SERVICE" --region "$REGION" --format json)
if echo "$EXISTING" | grep -q "allUsers"; then
  echo "IAM binding already exists, skipping"
else
  gcloud run services add-iam-policy-binding ...
fi
```

---

## 2. Polling and Async Execution

### 2.1 Unbounded polling loops

**Anti-pattern:** `while true; do ... sleep 10; done` with no iteration counter or timeout.

**Symptom:** Hung build causes workflow to run for hours, burning Actions minutes.

**Fix:** Always add a counter:
```bash
POLL_COUNT=0
MAX_POLLS=90  # 15 min at 10s intervals
while [ $POLL_COUNT -lt $MAX_POLLS ]; do
  # check status...
  POLL_COUNT=$((POLL_COUNT + 1))
  sleep 10
done
echo "::error::Timed out after $MAX_POLLS polls"
exit 1
```

Better: don't poll at all if the CLI supports synchronous mode.

### 2.2 Unnecessary async + custom polling

**Anti-pattern:** Using `gcloud builds submit --async` then writing 30+ lines of custom polling when synchronous mode blocks until completion, streams logs, and exits with the correct status code.

**Symptom:** Fragile, verbose CI code that duplicates built-in CLI behavior.

**Fix:** Remove `--async` and the polling loop. Let the CLI do its job.

### 2.3 Error output lost under `set -e`

**Anti-pattern:** Capturing output with `VAR=$(cmd 2>&1)` under `set -e`. If the command fails, bash exits immediately — before `$VAR` is printed.

**Symptom:** Workflow step fails with no diagnostic output in logs.

**Fix:** Use an error handler:
```bash
BUILD_OUTPUT=$(gcloud builds submit ... 2>&1) || {
  echo "::error::Cloud Build submit failed:"
  echo "$BUILD_OUTPUT"
  exit 1
}
echo "$BUILD_OUTPUT"
```

---

## 3. Variable Scoping and Data Passing

### 3.1 Missing job-level `outputs:` declaration

**Anti-pattern:** Step writes to `$GITHUB_OUTPUT` but the job definition has no `outputs:` block. Downstream jobs receive empty string, not an error.

**Symptom:** Downstream job proceeds with empty variable. No error. Silent misconfiguration.

**Fix:** Wire both levels:
```yaml
jobs:
  build:
    outputs:
      service_url: ${{ steps.get-url.outputs.service_url }}  # Job-level
    steps:
      - id: get-url
        run: echo "service_url=$URL" >> $GITHUB_OUTPUT        # Step-level
```

### 3.2 Matrix job outputs are non-deterministic

**Anti-pattern:** A matrix job deploys to multiple regions. Each matrix run writes a different URL to the same output key. GitHub uses last-write-wins — the value depends on which matrix run finishes last.

**Symptom:** Downstream job gets URL from a random region (usually the fastest runner).

**Fix:** Don't use matrix outputs for per-region values. Query them directly in the downstream step:
```bash
for REGION in $(echo '${{ env.REGIONS }}' | jq -r '.[]'); do
  URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)')
  # Wire this URL to the correct region's function
done
```

### 3.3 Region lists hardcoded in multiple locations

**Anti-pattern:** Same region list appears in 4 places — 2 matrix strategies and 2 shell loops. Adding a region requires updating all 4.

**Symptom:** New region works in some steps but not others.

**CRITICAL:** The `env` context is NOT available in `jobs.<id>.strategy.matrix`. Only `github`, `needs`, `vars`, and `inputs` are allowed. Using `fromJSON(env.REGIONS)` in a matrix strategy causes the workflow to fail at parse time with 0 jobs queued and "Failed to queue workflow run" in the UI.

**Fix:** Use a GitHub repository variable (`vars` context) for the region list:
```bash
gh variable set REGIONS --body '["us-west1", "northamerica-northeast1"]'
```
```yaml
jobs:
  deploy:
    strategy:
      matrix:
        region: ${{ fromJSON(vars.REGIONS) }}    # vars context works in matrix
    steps:
      - run: |
          for REGION in $(echo '${{ vars.REGIONS }}' | jq -r '.[]'); do  # vars also works in shell
```

---

## 4. Workflow Identity and Naming

### 4.1 Workflow lookup by display name

**Anti-pattern:** Using `gh workflow list --json name,id` and filtering by `name:` field. GitHub's name index goes stale after renames.

**Symptom:** `gh workflow enable/disable` targets wrong workflow or fails.

**Fix:** Always filter by file path:
```bash
gh workflow list --json id,path | jq -r '.[] | select(.path == ".github/workflows/orchestrate.yml") | .id'
```

### 4.2 `${{ github.workflow }}` resolves to display name, not filename

**Anti-pattern:** Using `gh workflow disable "${{ github.workflow }}"` — this passes the `name:` field value, not the filename.

**Symptom:** Wrong workflow disabled when names are similar, or command fails when name index is stale.

**Fix:** Hardcode the filename:
```bash
gh workflow disable "orchestrate.yml"
```

### 4.3 `name:` field not on first line

**Anti-pattern:** Large comment block before `name:` in workflow YAML. GitHub's parser may fail to extract the display name.

**Symptom:** Actions UI shows the filename instead of the display name.

**Fix:** Always put `name:` on line 1 (or immediately after a single-line comment).

### 4.4 GitHub caches stale workflow filenames

**Anti-pattern:** Renaming a workflow's `name:` field doesn't update the Actions UI display. GitHub cached the old filename.

**Symptom:** Actions tab shows old name despite correct `name:` field.

**Fix:** Rename the file itself to force re-indexing. This is a GitHub platform quirk.

---

## 5. Orchestrator Lifecycle and Infinite Loops

### 5.1 Self-disabling workflows with no guaranteed wake-up

**Anti-pattern:** Workflow disables itself when daily work is done, relying on a separate "wake-up" workflow. If the wake-up breaks, the orchestrator is permanently dead.

**Symptom:** Orchestrator stops running and never recovers.

**Fix options:**
- (a) Don't self-disable — accept idle cron runs.
- (b) Self-disable, but make wake-up unconditional: `if: always()` in the upstream workflow.

### 5.2 AI agent exits without changing the completion signal

**Anti-pattern:** Orchestrator detects work by checking a condition (e.g., "files over 700 lines exist"). Agent selects a file, finds nothing to change, exits. Condition unchanged. Orchestrator re-triggers. Infinite loop.

**Symptom:** Same file selected and processed every run with no progress.

**Fix:** Enforce: if you select a work item, you MUST commit something — either do the work or add an explicit exception entry.

### 5.3 Completion signal conditional on findings

**Anti-pattern:** A "last reviewed" date prefix is only updated when content issues are found. Files with 0 issues never get their date updated, so the orchestrator keeps selecting them.

**Symptom:** Same "clean" file re-processed every cycle.

**Fix:** Update the completion signal unconditionally. "Reviewed and found no issues" is still a valid review.

### 5.4 Inter-workflow state via human-readable text

**Anti-pattern:** Orchestrator parses a markdown table for a value like "Total uncategorized: 5". When the table format changes ("Files needing review: 5"), the regex breaks silently.

**Symptom:** Orchestrator always reads 0, never triggers work.

**Fix:** Use machine-readable markers:
```markdown
<!-- AUTO_PROCESSABLE: 5 -->
<!-- TOTAL_FILES: 12 -->

| File | Status | ... |
```

### 5.5 Premature STOP gates in AI agent workflows

**Anti-pattern:** Instructions tell the agent to "STOP (do not proceed)" after a preliminary step. The agent only ever does the preliminary step, requiring a separate run for the real work.

**Symptom:** Orchestrator runs twice for what should be one task.

**Fix:** Only add STOP gates when there's a genuine dependency or human review is needed between steps.

---

## 6. Deployment Configuration

### 6.1 Service name typos create phantom services

**Anti-pattern:** Typing `extractmattertodocument` instead of `extractmatterfromdocument`. Cloud Run silently creates a new service.

**Symptom:** Wiring step targets a service that exists but has no code deployed to it. Or: deploy succeeds but nothing changes.

**Fix:** Copy service names from `gcloud run services list`, never type from memory.

### 6.2 `--no-traffic` on Cloud Run updates

**Anti-pattern:** Using `--no-traffic` during standard deploys. New revision is created but receives no traffic. Callers keep hitting the old revision.

**Symptom:** Deploy succeeds, new revision appears in console, but behavior doesn't change. Stale code runs for days.

**Fix:** Remove `--no-traffic` for standard deploys. Only use it for canary/blue-green deployments with explicit traffic splitting.

### 6.3 Firebase Admin SDK `.exists` is a property, not a method

**Anti-pattern:** Writing `userDoc.exists()` (client SDK pattern). Admin SDK uses `.exists` as a property.

**Symptom:** `TypeError: userDoc.exists is not a function`

**Fix:** `if (userDoc.exists)` — no parentheses.

### 6.4 YAML indentation: inputs outside `with:` block

**Anti-pattern:** Action parameter like `claude_args:` placed at the step or workflow root level instead of inside `with:`. Syntactically valid YAML, semantically broken.

**Symptom:** Parameter silently ignored. Action runs with defaults.

**Fix:** Validate with `actionlint` before committing. Ensure all action inputs are inside `with:`.

### 6.5 Deploying unchanged resources on every run

**Anti-pattern:** Firestore/Storage security rules deployed on every backend push, even when rule files haven't changed.

**Symptom:** Unnecessary deploy time and API calls. Potential for deployment race conditions.

**Fix:** Use `dorny/paths-filter` for change detection. Keep cron/manual triggers as safety net:
```yaml
- uses: dorny/paths-filter@v3
  id: changes
  with:
    filters: |
      rules:
        - 'firestore.rules'
        - 'storage.rules'

- if: steps.changes.outputs.rules == 'true' || github.event_name != 'push'
  run: firebase deploy --only firestore:rules,storage:rules
```

### 6.6 Separate pipelines for coupled services

**Anti-pattern:** Cloud Functions and Cloud Run deployed by independent workflows. Cloud Function references a Cloud Run URL that may not exist yet, or URL wiring runs before Cloud Run is ready.

**Symptom:** Intermittent failures depending on which workflow triggers first.

**Fix:** Single `deploy-backend.yml` with job dependencies:
```yaml
jobs:
  deploy-cloud-run:
    ...
  deploy-functions:
    needs: deploy-cloud-run
    ...
```
