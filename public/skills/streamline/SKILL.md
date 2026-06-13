Streamline: `$ARGUMENTS`

Parse `$ARGUMENTS`: if it contains `--autophagy`, enter Autophagy-Only Mode (add `yolo` for non-interactive). If it is `yolo` alone, enter Full Flow with YOLO mode active. If it is a file path, enter Direct File Mode. If empty, enter Full Flow (interactive).

## Master Workflow (MANDATORY — Follow Steps in Order)

Every `/streamline` invocation MUST execute these steps sequentially. **Do NOT skip ahead.**

### Step 1: Mode Detection

| `$ARGUMENTS` | Mode | Go to |
|---|---|---|
| `--autophagy` | Autophagy-Only | Step 6 |
| `--autophagy yolo` | Autophagy-Only (unattended) | Step 6 |
| file path | Direct File | Step 3 |
| `yolo` | Full Flow (auto-approve) | Step 2 |
| (empty) | Full Flow (interactive) | Step 2 |

---

### Step 2: Folder-Structure Date Check *(Full Flow only)*

Run: `node .claude/skills/streamline/scripts/update-folder-structure.mjs --check-only`

- **Outdated** → rebuild → tell user "Folder-Structure.md was outdated and has been updated. Please start a new chat window to run /streamline with a fresh context." → **STOP**
- **Current** → select a file (see File Selection). Check for virtual scrolling — **WARN** before proceeding. → Step 3

### Step 3: Exception List Check

- **Exempt** → run autophagy gate (Step 4) → update ledger (autophagy fields only) → **STOP**
- **Not exempt** → Step 4

### Step 4: Autophagy Gate

**BLOCKING: Complete before any decomposition, rebuild, or file-selection discussion.**

If you find yourself analyzing file structure, planning decomposition, or discussing module boundaries — **STOP**. You skipped the autophagy gate. Go back.

1. Read file — enumerate every named export, default export, component name, and composable return value.
2. Search `src/` for each export across:
   - Static `import` statements
   - Dynamic `import()` calls (search filename as bare string)
   - Bare name grep across all `src/` files
   - `provide`/`inject` calls (search export name in provide/inject usages)
   - Component template registrations, router lazy-load references, Pinia store usage, barrel re-exports (`index.js`)
3. A file imported only by its own test is dead.

**Act on status:**

| Status | Action | Ledger | Then |
|---|---|---|---|
| Entirely dead | `git rm` file + test; commit `chore: remove dead file` | `deleted` | **STOP** |
| Partially dead | Remove dead portions, lint, commit `chore: remove dead code from` | `trimmed` | Re-count lines → Step 5 |
| Clean | (no changes) | `clean` | Step 5 |
| Inconclusive | (no changes) | `skipped` | Step 5 |

**Safety Rules (NON-NEGOTIABLE):** When in doubt → `skipped`. See Autophagy Safety Reference below.

### Step 5: Churn Check

Run: `git rev-list --count <lastStreamlinedAt>..HEAD -- "<filePath>"`

- SHA invalid (rebased) → treat as never streamlined → Step 7
- **0 commits** → update autophagy fields only → **STOP**
- **>0 commits** → Step 7

### Step 6: Autophagy-Only Mode

1. `node .claude/skills/streamline/scripts/prioritize.mjs --limit 5`
2. Report: "Scanned X test files. Y orphaned (no matching source file)." (X = total test files found by walkTests; Y = orphaned count in queue)
3. Empty → "All files are up to date" → **STOP**
4. For each file:
   - If `orphaned: true` → source file no longer exists; `git rm` it; ledger: `deleted`; commit `chore: remove orphaned test`; yolo: loop; interactive: prompt to continue
   - Otherwise → run Step 4 → update ledger → yolo: loop; interactive: prompt to continue
5. After processing all orphaned entries: report "Deleted N orphaned test files."
6. **STOP** — no decomposition/rebuild in this mode

### Step 7: Decomposition / Rebuild

**Only reachable after Steps 4 and 5.**

- **> 300 lines** → Decomposition Plan (target ≤200 lines/module)
  - YOLO → execute immediately; Interactive → present plan, await approval
- **≤ 300 lines** → Rebuild from scratch
  - Fewer lines → update Folder-Structure.md; ledger: `rebuilt`
  - Same or more → ledger: `skipped`; offer to lengthen instead

After decomposition/rebuild: update Folder-Structure.md (line count + `decomposed`), ledger: `decomposed`, suggest manual tests (interactive only).

### Step 8: Ledger Update

Update `.claude/data/streamline-ledger.json`. Stage ledger with code changes in the same commit. For clean/skipped (no code changes), ledger update remains uncommitted until next run.

---

## YOLO Mode

Active when `$ARGUMENTS` contains `yolo`. Auto-selects best candidate, skips all approval steps, commits directly. With `--autophagy`, processes all queued files without pausing.

---

## Folder-Structure.md Rules

- `docs\Miscellaneous\YYYY-MM-DD-Folder-Structure.md` contains line counts only — no docs, diagrams, or migration notes
- Do NOT add newly decomposed files (added during next full rebuild); do NOT update in autophagy-only mode

---

## Exception List

Exempt from 300-line limit (autophagy gate still runs; no streamlining):

- `src/components/base/DocumentTable.vue` — Virtual scrolling (tight coupling required)
- `src/features/documents/components/table/DocumentTable.vue` — Virtual scrolling (tight coupling required)
- `src/shared/components/tabs/FolderTabs.vue` — Single stacking context (tight coupling required)

**Both Direct File Mode and Full Flow check the exception list.** Exempt files run the autophagy gate, update the ledger with autophagy fields only, then STOP. They never reach ChurnCheck, SizeCheck, or decomposition.

---

## Autophagy Safety Reference

Before marking any export dead, verify it is not referenced via:
- Dynamic `import()` — search for filename as bare string
- `provide`/`inject` — search for export name in provide/inject calls
- String-key lookups — search for export name as **string literal**

Do NOT remove:
- Dynamically imported, lazy-loaded, or string-key referenced code
- Vue lifecycle hooks, route guards, Pinia store actions
- Event handlers, watchers, computed properties, CSS classes in templates, `provide`/`inject` references

**Confirm-dead checklist:** Mark dead ONLY when ALL searches return zero. If ANY search is inconclusive, mark as `skipped`.

---

## Unified Ledger

```js
const sha = execSync('git rev-parse HEAD').toString().trim();

const ledger = existsSync('.claude/data/streamline-ledger.json')
  ? JSON.parse(readFileSync('.claude/data/streamline-ledger.json', 'utf-8'))
  : { files: {} };

ledger.files[filePath] = {
  ...ledger.files[filePath],
  lastReviewedAt: sha,                     // always update (autophagy ran)
  lastAutophagyResult: "clean",            // "clean" | "trimmed" | "deleted" | "skipped"
  // Only set these when streamline actually runs (not in --autophagy mode):
  // lastStreamlinedAt: sha,
  // lastStreamlineResult: "decomposed"    // "decomposed" | "rebuilt" | "skipped"
};

writeFileSync('.claude/data/streamline-ledger.json', JSON.stringify(ledger, null, 2) + '\n');
```

Do NOT commit the ledger separately — it gets committed with the next streamline/autophagy run.

---

## Scripts

| Step | Command |
|---|---|
| Folder-Structure check | `node .claude/skills/streamline/scripts/update-folder-structure.mjs --check-only` |
| Folder-Structure rebuild | `node .claude/skills/streamline/scripts/update-folder-structure.mjs` |
| Autophagy queue | `node .claude/skills/streamline/scripts/prioritize.mjs --limit 5` |
| Churn check | `git rev-list --count <lastStreamlinedAt>..HEAD -- "<filePath>"` |

---

## File Selection *(Full Flow only)*

Review `docs\Miscellaneous\YYYY-MM-DD-Folder-Structure.md` for top 3 candidates by size/complexity. Select the obvious win.

**Virtual Scrolling:** Check for `virtual-scroller`, `virtual-scroll`, `v-virtual-scroll`. Cannot be safely decomposed — warn before proceeding.

---

## Excluded Directories

The following directories are excluded from all file scanning (scripts, autophagy, file selection):
- `deprecated/` — backup files created by decomposition; never candidates for re-decomposition or autophagy. All deprecated files are auto-cleaned when Folder-Structure is updated.
- `node_modules/`, `.git/`, `bin/`, `obj/`

---

## Decomposition Details

- **Backup:** Copy original to `/deprecated` with today's date prepended (e.g., `2025-12-08-folderExtractionService.js`). Retention is ~1 day; files are auto-deleted on the next Folder-Structure update.
- **DRY vs KISS:** Apply DRY unless it adds complexity or reduces readability — KISS wins
- **Build from scratch:** Rebuild each new file elegantly; don't just copy-paste chunks
- **Preserve everything:** Design, appearance, behavior, functionality must be identical
- **Test suggestions:** Interactive mode only; skip in YOLO mode
- **Linting:** Interactive → delegate to beautifier agent; YOLO → pre-commit hooks

**Collision guard:** Before creating any new file during decomposition, verify the target path does not already exist on disk.

**Constraints:** No functional, design, or behavioral changes. Follow existing patterns. Consult `@docs/architecture/overview.md`.

---

See [references/workflow.md](references/workflow.md) for the Mermaid flowchart.
