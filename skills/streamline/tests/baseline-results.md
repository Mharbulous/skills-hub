# Baseline Results

## Scenario 1: Exception List File

**Input:** `src/features/documents/components/table/DocumentTable.vue`

**Execution trace:**
1. Parse arguments → file path provided → Direct File Mode
2. Exception list check → MATCH (entry #2, "Virtual scrolling (tight coupling required)")
3. Inform user file is exempt from 300-line limit
4. Autophagy Gate runs → analyze exports and references
5. Status: clean → Ledger: clean/skipped
6. IsExempt check → YES → ExemptStop
7. Update ledger (autophagy fields only) → STOP

**Tool calls:** Read (target file) + Grep (reference searches)
**Files modified:** Ledger only (autophagy fields)
**Key invariants:**
- Exception list check runs for BOTH Direct File Mode and Full Flow
- Autophagy gate runs on exempt files
- Exempt files NEVER reach ChurnCheck, SizeCheck, or decomposition
- ExemptStop is a terminal node

---

## Scenario 2: Folder-Structure Date Check (Outdated)

**Input:** No file argument (empty)

**Execution trace:**
1. Parse arguments → empty → Full Flow
2. Run `update-folder-structure.mjs --check-only`
3. Result: outdated → run `update-folder-structure.mjs`
4. Script walks `src/`, counts LOC, generates new file, deletes old
5. Output: "Folder-Structure.md was outdated and has been updated. Please start a new chat window..."
6. STOP — no streamlining performed

**Key invariant:** Must STOP after rebuild and instruct user to start new chat.

---

## Scenario 3: Specific File >300 Lines

**Input:** `src/views/Upload.vue`

**Execution trace:**
1. Parse arguments → file path → Direct File Mode
2. Exception list check → NO MATCH → continue
3. Autophagy Gate: analyze exports and references
4. Status: clean → Ledger: clean
5. IsExempt? → NO → ChurnCheck
6. Churn check: `git rev-list --count <sha>..HEAD -- "src/views/Upload.vue"`
7. Result: >0 → SizeCheck
8. Count lines → >300 → Create Decomposition Plan
9. Interactive: present plan → PAUSE for approval
10. (After approval) Backup → Create modules → Refactor → Update Folder-Structure → Ledger: decomposed

**Key invariants:**
- Plan presented BEFORE any file modifications
- Approval is a hard stop in interactive mode
- Dated backup is first file operation after approval

---

## Scenario 4: Specific File ≤300 Lines

**Input:** `src/router/index.js`

**Execution trace:**
1-5. Same as Scenario 3 through IsExempt check
6. Churn check → >0 or never streamlined → SizeCheck
7. Count lines → ≤300 → Rebuild file from scratch
8. Compare rebuilt LOC to original LOC
9. If fewer: update Folder-Structure + Ledger: rebuilt
10. If equal or more: Ledger: skipped, offer to lengthen

**Key invariant:** Rebuild (not decomposition) is attempted. LOC comparison drives outcome.

---

## Scenario 5: YOLO Mode

**Input:** `yolo`

**Execution trace:**
1. Parse arguments → "yolo" → Full Flow with YOLO mode active
2. Folder-Structure date check runs
3. If outdated: update + STOP
4. If current: auto-select best candidate (no user prompt)
5. Auto-proceed with decomposition/rebuild (no approval pause)
6. Create commits directly

**Key invariant:** Zero interactive prompts throughout entire execution.

---

## Scenario 6: Exception List + Autophagy Continuation

**Input:** `src/features/documents/components/table/DocumentTable.vue`

**Execution trace:**
1. Parse → Direct File Mode → ExCheck → MATCH (exempt)
2. Inform user: exempt from 300-line limit
3. Autophagy Gate runs (ExInfo → AG1)
4. Status: clean/trimmed → IsExempt? → YES → ExemptStop
5. Update ledger (autophagy fields only) → STOP
6. File NEVER reaches ChurnCheck, SizeCheck, or decomposition

**Key invariants:**
- Direct File Mode checks exception list (fixed: previously bypassed)
- ExemptStop is a dedicated stop node for exempt files
- Autophagy runs but streamlining does NOT

---

## Scenario 7: --autophagy Mode

**Input:** `--autophagy`

**Execution trace:**
1. Parse → `--autophagy` detected → Autophagy-Only Mode
2. Run `node .claude/skills/streamline/scripts/prioritize.mjs --limit 5`
3. If empty → "all files up to date" → STOP
4. If files found → enter loop
5. For each file: AG2 (autophagy gate — delete/trim/clean, loop continues)
6. Update ledger (autophagy fields ONLY, NOT streamline fields)
7. Interactive: ask "Continue to next file?" between files
8. YOLO: auto-continue without pausing

**Key invariants:**
- prioritize.mjs script is actually executed
- AG2 always continues the loop (even after deletion)
- Only autophagy fields written to ledger
- No streamlining (decomposition/rebuild) occurs

---

## Scenario 8: Churn Check with 0 Commits

**Input:** `src/views/Upload.vue` (with ledger entry `lastStreamlinedAt: "abc123"`)

**Execution trace:**
1. Parse → Direct File Mode → ExCheck → NO MATCH
2. Autophagy Gate → clean
3. IsExempt? → NO → ChurnCheck
4. `git rev-list --count abc123..HEAD -- "src/views/Upload.vue"` → 0
5. SkipStream → Update autophagy fields only → STOP
6. File NEVER reaches SizeCheck or decomposition

**Key invariants:**
- Churn check command is actually executed
- 0 commits → skip streamlining entirely
- Ledger: only autophagy fields updated (lastStreamlinedAt preserved)
- Edge case: invalid SHA → treat as "never streamlined"

---

## Scenario 9: Safety Rules — Dynamic Import False Positive

**Input:** `src/composables/useSpecialHandler.js`

**Execution trace:**
1. Parse → Direct File Mode → ExCheck → NO MATCH
2. Autophagy Gate: identify exports (`useSpecialHandler`, `SPECIAL_CONFIG`)
3. Static import search → ZERO matches
4. Dynamic import search (`import\(.*useSpecialHandler`) → MATCH found
5. Bare name search (`useSpecialHandler` as string) → MATCH found
6. Confirm-dead checklist: NOT all searches returned zero → file is NOT dead
7. Status: clean → continue to ChurnCheck

**Key invariants (defense in depth):**
- Mandatory bare name search catches dynamic imports
- Confirm-dead checklist requires ALL searches to return zero
- Safety rules are proactive: "Before marking ANY export as dead, verify..."
- Default when ANY search is inconclusive: mark as `skipped`
