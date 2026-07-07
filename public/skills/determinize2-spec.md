I have now read every file. Below is the complete clean-room specification.

---

# Specification: The `determinize` Agent Skill

> This is a complete, self-contained rebuild spec. The rebuild team has no access to the original files. Everything needed to recreate the skill is written here. Deliberate deviations from the original are listed in the final "Changed from the original" section.

---

## 1. Purpose

`determinize` is an **agent Skill** — a Markdown-based instruction set consumed by an LLM coding agent (Claude), packaged inside the `skills-hub` plugin/marketplace repository. It is not application code; it is a procedure the agent follows.

**Problem it solves:** Many existing skills and slash-commands embed *procedural, computational logic* directly in their `SKILL.md` as prose or code blocks that the LLM must "execute" by reasoning through it token-by-token. Because an LLM re-derives that logic on every run, identical inputs can produce **non-identical outputs** (LLM variance). For genuinely deterministic work — string normalization, CSV parsing, cross-referencing two datasets, enumerable branching — this variance is pure downside: the answer is knowable exactly, yet the LLM might get it subtly wrong or inconsistent.

`determinize` helps a skill author **extract the deterministic parts of another skill into helper scripts** (Python or JavaScript) that the hardened skill then simply *invokes*. The script produces identical output for identical input, eliminating LLM variance for those phases. The non-deterministic parts (judgment, guidelines, schemas, examples) are deliberately **left in the SKILL.md**, because that is where LLM flexibility is the actual value.

**Explicit framing rule (load-bearing):** The value proposition is **determinism / predictability / robustness — NOT token savings or efficiency.** This framing constraint is central to the whole skill's identity (see §4 and §8). The word "optimization," "token savings," "context window reduction," and "progressive disclosure" are treated as anti-patterns to be avoided in the agent's language.

**Acknowledged trade-off:** Hardened skills are more predictable and robust but also **more brittle** — if inputs change in ways the script did not anticipate, you must edit the script rather than lean on LLM adaptability. The agent must state this trade-off, not hide it.

**Audience / workflow:** A developer maintaining skills in a skills repo who wants to make a specific skill more reliable. The workflow is a three-stage lifecycle: **harden → test → promote.**

---

## 2. Three-Mode Structure

The entry point `SKILL.md` is a thin **mode router**. It detects one of three modes from the user's prompt, then reads and follows the corresponding file under `modes/`.

### Mode-detection table (verbatim intent)

| Signal in the user's prompt | Mode |
|---|---|
| `-harden` flag, or the word "harden", **or no flag specified at all** | **Harden** (default) |
| `-test` flag, or "test", "compare", "A/B test" | **Test** |
| `-promote` flag, or "promote" | **Promote** |

### Router execution steps

1. Determine mode from the table above.
2. Read the mode file `modes/<mode>.md`.
3. Follow that file's instructions exactly.

### What each mode does and how they relate

- **Harden** (`modes/harden.md`): Takes an existing skill, identifies its highest-value deterministic section, extracts exactly ONE such section into a helper script, and produces a parallel copy `<skill-name>-hardened/` containing the modified `SKILL.md`, the new `scripts/`, inherited `references/`, and a mandatory `tests/` folder with regression tests + baseline results. It **never modifies the original**. It ends by committing only the hardened files (a git recovery point) and letting the user decide: promote / keep both / delete.

- **Test** (`modes/test.md`): Runs a controlled **A/B experiment** between two skill variants (typically original vs `-hardened`) — identical prompt, sequential alternating trials, NDJSON metric extraction, summary statistics, a 2×-standard-deviation significance test, variance comparison, functional-equivalence check, and a decision matrix. It **recommends** but never auto-modifies files.

- **Promote** (`modes/promote.md` + `scripts/promote-skill.mjs`): After tests confirm the hardened version is better, replaces the original with the hardened version via a deterministic Node script, guarded by a mandatory user-confirmation interview, then commits.

**Data flow between modes:** Harden **produces** the `<name>-hardened/` directory and a git commit tagged with a searchable key `[hardening:<skill>:<script>]`. Test **consumes** the original + hardened directories and produces an A/B report + recommendation. Promote **consumes** the `-hardened` directory and (on approval) collapses it back onto the original name. Harden's Stage 6 can also invoke Test inline and can perform a promotion itself; **in this spec, Stage 6's promotion is unified to call the same promote script** (see §3 Stage 6 and §11).

---

## 3. Harden Mode — Full Stage Pipeline

### 3.0 Harden orchestrator (`modes/harden.md`)

**Core insight to state:** the biggest value is extracting deterministic procedures into helper scripts — *not for token savings*, but because deterministic scripts produce identical output for identical input, eliminating LLM variance. A 200-line procedure the LLM must reason through becomes `run scripts/do_thing.<ext>`.

**Required background skills** (external dependencies the agent should already have loaded / be familiar with):
- `superpowers:test-driven-development`
- `superpowers:writing-skills`

**Staged execution — 6 stages, read one at a time.** The orchestrator lists the pipeline and enforces a strict "no reading ahead" rule. Each stage file ends with a **Gate** that names the next file to read. Reading a later stage file while working an earlier one is a violation. The rationalization "I'll read ahead to understand the full process first" is explicitly named and forbidden.

Pipeline order (canonical — matches stage-file titles):

| Stage | File | Title |
|---|---|---|
| 1 | `harden-stages/inventory.md` | Inventory |
| 2 | `harden-stages/classify-and-score.md` | Classify & Score |
| 3 | `harden-stages/baseline-tests.md` | Baseline Tests |
| 4 | `harden-stages/extract.md` | Extract |
| 5 | `harden-stages/verify.md` | Verify |
| 6 | `harden-stages/commit-and-finalize.md` | Commit & Finalize |

**The Iron Law (must appear verbatim in the orchestrator and Stage 3):**
```
NO HARDENING WITHOUT BASELINE TESTS FIRST
```
If a hardened SKILL.md was written before testing the original: delete it, start over. No exceptions — not "the extraction is obvious," not "just moving code blocks," not "I'll backfill tests." Backfilled tests verify what you built, not what you should have preserved.

**Language selection (done in the orchestrator, before Stage 1 work or at latest before Stage 4):**
1. If the user specified a scripting language (e.g. "use JavaScript"), use it.
2. If not, **ask the user** which language they prefer before proceeding.
3. Load `references/<language>.md` and apply its substitutions throughout.
Only languages with a reference file in `references/` are available (currently `python` and `javascript`).

**Output structure the orchestrator promises:**
```
<skill-name>-hardened/
  SKILL.md
  scripts/           # extracted helper scripts
  references/        # inherited from original (if any)
  tests/             # regression tests (ALWAYS present, never deleted)
    baseline-results.md
    scenario-*.md
```

**Red-flags table (rationalization → reality), verbatim intent:**

| Rationalization | Reality |
|---|---|
| "Extraction is obvious" | Obvious extractions still break subtle behavior. Test first. |
| "Backfill tests after" | Tests written after hardening verify what you built, not what you should preserve. Worthless. |
| "Just extracting code blocks" | Code blocks carry context (thresholds, error formats, edge cases). Easy to lose. |
| "I'll script this checklist" | Checklists require judgment → non-deterministic → scripting them wastes effort. |
| "No scripts found, but I can still restructure" | If no deterministic procedures exist, hardening doesn't apply. Exit cleanly. |
| "I'll read ahead to understand the full process" | Each stage gives you exactly what you need. Reading ahead causes stage-skipping. |

**Quick-reference (content-type → strategy):**

| Skill content type | Hardening strategy |
|---|---|
| Deterministic procedures | Extract to helper scripts |
| Non-deterministic content (judgment, guidelines) | Leave in SKILL.md — LLM flexibility is the value |
| Reference material (schemas, examples) | Leave in SKILL.md — no hardening benefit |

**Common-mistakes table** (must be reproduced; key entries): skipping baseline tests → always Stage 3 first; reading ahead → read only current stage; forcing scripts on non-deterministic content; modifying the original → always create `-hardened/` copy; forgetting to save tests → tests are mandatory in `<name>-hardened/tests/`; not testing extracted scripts → run each script; framing value as token savings → the value is determinism; creating a deprecated/archived folder → git history is the recovery mechanism; committing original + hardened together → commit ONLY hardened files in Stage 6; combining classification with test writing → finish all of Stage 2 before Stage 3.

---

### 3.1 Stage 1 — Inventory (`harden-stages/inventory.md`)

**Goal:** Build a complete file inventory of the target skill. Raw data for Stage 2.

**Inputs:** Path to the skill directory being hardened.

**Steps:**
1. List all files in the skill directory (use Glob).
2. Read each file and count its lines.
3. Emit an inventory table:
   ```
   Inventory: <skill-name>
   | File | Lines | Purpose |
   |------|-------|---------|
   | SKILL.md | 216 | Main skill document |
   | scripts/foo.py | 45 | Helper script |
   | ... | ... | ... |
   | **Total** | **XXX** | |
   ```
4. Identify the logical sections *within* SKILL.md — list each heading with its line range.

**Output artifact:** the inventory table (in-conversation) + a list of SKILL.md sections with line ranges.

**Gate → Stage 2:** every file read and counted; inventory table complete; SKILL.md sections listed with line ranges. When satisfied, read `harden-stages/classify-and-score.md`.

---

### 3.2 Stage 2 — Classify & Score (`harden-stages/classify-and-score.md`)

**Goal:** Classify every SKILL.md section, score deterministic sections against the 11 heuristics, rank candidates, present the top 3, and get a selection (or exit cleanly if none qualify).

**Prerequisites:** Stage 1 complete (need section list + line ranges). **Load `references/determinism-heuristics.md` now.**

**Step 1 — Classify each section.** For every section, ask the **determinism question**: *"Given identical input, would this section always produce identical output?"*
- **NO →** non-deterministic (requires LLM judgment). Note why. Not a candidate.
- **YES →** deterministic. Proceed to scoring.

Classification is **determinism-based, not format-based**:
- Tables of transformation rules (normalization, scoring thresholds) **ARE** script-extractable.
- Code blocks containing judgment calls ("review and decide") are **NOT** script-extractable.
- Checklists needing context-dependent interpretation are **NOT** script-extractable.
- Step-by-step procedures with enumerable branches **ARE** script-extractable.

**Step 2 — Score deterministic sections.** Score each 0–3 per heuristic (0 = not present, 3 = strongly present), across all 11 heuristics (full definitions in §4). Sum = 0–33 per section.

**Step 3 — Rank candidates.** Use a single ranking value (see §4 "Ranking model" — this spec unifies the two competing formulas the original carried). The unified **Determinism Value**:
```
Determinism Value = (Heuristic Score / 33) × (Section line count) × (Execution frequency per invocation)
```
Rank highest-first. (Priority bands from the heuristics reference: score ≥ 18 = High, 9–17 = Medium, ≤ 8 = Low/skip.)

**Step 4 — Check prior hardening attempts (git-history awareness).** Search git history for prior attempts on this skill:
```bash
git log --all --grep="\[hardening:<skill-name>:" --oneline --format="%h %s (%ai)"
```
- If matches: display a **"Previously Attempted Hardenings"** section *before* the candidate list, showing commit hash, script name, and date for each. This is **informational only** — previously-attempted candidates are **NOT filtered out** and remain selectable.
- If no matches: skip silently.

**Step 5 — Present candidates.** Show the **top 3**:
```
Top Script Extraction Candidates:

1. [Section Name]
   - Heuristic Score: X/33
   - Determinism Value: X,XXX
   - Key heuristics: [which scored highest]
   - Why extract: [what LLM variance this eliminates]
2. ...
3. ...
```
- **Interactive (HITL) mode:** ask "Which candidate should I extract first? (Enter 1, 2, or 3, or 'skip' if no extraction is warranted)"; wait for the response.
- **Autonomous mode (no HITL):** auto-select candidate #1 and announce: "Auto-selecting highest-ranked candidate: [Section Name] (Determinism Value: X,XXX)".

**One-at-a-time principle:** Exactly **ONE** script is extracted per hardening run, no matter how many candidates were found.

**No candidates found — STOP (clean exit).** If classification finds no deterministic procedural content:
1. Show the classification breakdown (% deterministic vs non-deterministic).
2. State verbatim: *"No script extraction candidates found. This skill's content requires LLM judgment and cannot be replaced with deterministic scripts. Hardening does not apply to this skill."*
3. End the session. **No `-hardened` copy is created.** Do NOT offer progressive disclosure or any "restructuring" fallback.

**Output artifacts:** classification breakdown; scored + ranked candidate list; the selected candidate identity (section name + exact line range) carried into Stage 3.

**Gate → Stage 3:** every section classified; all deterministic sections scored on all 11 heuristics; candidates presented; user selected one (or clean exit occurred). When satisfied, read `harden-stages/baseline-tests.md`.

---

### 3.3 Stage 3 — Baseline Tests (`harden-stages/baseline-tests.md`)

**Goal:** Write regression tests for the CHOSEN candidate and run them against the ORIGINAL skill to establish baseline behavior. This is the Iron Law enforcement point.

**Prerequisites:** A candidate selected in Stage 2. If you don't have one, go back.

**Steps:**
1. **Create test directory** `<skill-name>-hardened/tests/` if absent. (Note: the hardened directory is first created here, for the tests — but the hardened SKILL.md/scripts are NOT written until Stage 4.)
2. **Write regression test scenarios** exercising the skill's key behaviors, focused on the section to be hardened. Save each as a file in `<skill-name>-hardened/tests/`. Each scenario must: describe a specific input condition; specify expected behavior/output; cover normal cases, edge cases, and boundary conditions for the candidate section.
3. **Run baseline with the ORIGINAL skill.** Run each scenario using a subagent driving the ORIGINAL skill. Document behavior verbatim.
4. **Record baseline results** in `<skill-name>-hardened/tests/baseline-results.md`. This is the regression suite; the hardened version MUST reproduce equivalent results.

**Red flags (STOP):** the four "obvious extraction / testing wastes time / backfill after / just moving code" rationalizations all mean *go back, baseline first.*

**Output artifacts:** `tests/scenario-*.md` (one or more), `tests/baseline-results.md`.

**Gate → Stage 4:** scenarios written and saved; baseline behavior documented from the ORIGINAL skill; results saved in `baseline-results.md`. When satisfied, read `harden-stages/extract.md`.

---

### 3.4 Stage 4 — Extract (`harden-stages/extract.md`)

**Goal:** Extract the selected section into a helper script and build the hardened SKILL.md.

**Prerequisites:** Stage 3 complete (baseline documented); selected candidate from Stage 2; chosen scripting language known.

**Step 1 — Write the helper script.** Create it in `<skill-name>-hardened/scripts/` using the chosen language's conventions (from the loaded language reference). The script must:
- accept the same inputs the section currently processes;
- produce the same outputs the section currently generates;
- handle the edge cases identified in Stage 3's scenarios.
Then **actually run it** with sample input and verify the output.

**Step 2 — Create the hardened SKILL.md.** Copy the original SKILL.md to `<skill-name>-hardened/SKILL.md`, then:
1. Replace the extracted procedural section with a script invocation: `Run: <runtime> scripts/<name>.<ext> <args>`.
2. Document the script's inputs, outputs, and purpose in 1–2 lines.
3. Keep ALL non-deterministic content (judgment, decision trees, guidelines) inline.
4. Keep ALL reference content (schemas, examples) inline.
5. The hardened SKILL.md should read as an **orchestrator**: what to do, when, and which script to run.

**Step 3 — Copy supporting files.** Copy any referenced files (`references/` and other supporting files) from the original into the hardened directory.

**Output structure after this stage:**
```
<skill-name>-hardened/
  SKILL.md              # procedural section replaced with a script call
  scripts/<name>.<ext>  # extracted helper script (verified runnable)
  references/           # inherited from original (if any)
  tests/                # already present from Stage 3
    baseline-results.md
    scenario-*.md
```

**Gate → Stage 5:** helper script written and runs successfully; hardened SKILL.md replaces the section with a script invocation; supporting files copied; the `-hardened/` tree is complete. When satisfied, read `harden-stages/verify.md`.

---

### 3.5 Stage 5 — Verify (`harden-stages/verify.md`)

**Goal:** Re-run the Stage 3 tests against the HARDENED skill and confirm all baseline behaviors are preserved.

**Prerequisites:** Stage 4 complete; Stage 3 baseline available.

**Steps:**
1. Run the same scenarios, this time using `<skill-name>-hardened/SKILL.md`.
2. Compare against `tests/baseline-results.md`. All baseline behaviors MUST be preserved: same outputs for same inputs, same edge-case handling, no new failures.
3. **Handle failures:** if any test fails, the hardening broke something — identify the divergence, fix the script or the hardened SKILL.md, re-run the failing test, repeat until green. **Do NOT proceed with any failing test.**

**Output artifact (recommended, this spec):** `tests/green-results.md` recording the hardened-run results and the pass/fail comparison, mirroring `baseline-results.md`. (See §7.)

**Gate → Stage 6:** all regression tests pass with the hardened skill; results match baseline. When satisfied, read `harden-stages/commit-and-finalize.md`.

---

### 3.6 Stage 6 — Commit & Finalize (`harden-stages/commit-and-finalize.md`)

**Goal:** Create a git recovery point, present results, optionally run A/B tests, and let the user decide the outcome.

**Prerequisites:** Stage 5 complete (all tests pass).

**Step 1 — Git commit (recovery point).** Use the `git-agent` subagent to commit **ONLY** the hardened files. This creates a recovery point *before any deletion*, so either version is recoverable regardless of the later decision. Prompt template for git-agent:
```
Commit these specific files from the hardening session. Stage ONLY files
under the <skill-name>-hardened/ directory (SKILL.md, scripts/, tests/, references/).
Do NOT stage changes to the original skill directory.

Commit message:
- Title: 'feat(skills): harden <skill-name> — extract <script-name> to script'
- Body: brief description of what was extracted and why
- Body MUST include the searchable key: [hardening:<skill-name>:<script-name>]
- Include Co-Authored-By trailer

Do NOT push to remote.
```
The `[hardening:<skill-name>:<script-name>]` key is the exact string Stage 2 Step 4 searches for. Format consistency between the commit key and the git-log grep is mandatory.

**Step 2 — Summary report.** Output a table covering: what was hardened (section name, mode); what was extracted (script name + one-sentence description); why it matters (which LLM variance it eliminates); files created (new/modified with purpose); regression status (pass/fail).

**Step 3 — A/B test & finalize.** Ask via `AskUserQuestion`:
- **"Run A/B tests now" (Recommended)** — runs controlled A/B tests inline in this session, each trial in a fresh context window.
- **"Skip A/B tests"** — keeps both versions on disk; user can run `/determinize -test` later.

If "Run A/B tests now": run inline using subagent trials, following `modes/test.md` with parameters:
- Skill A = `<skill-name>/SKILL.md` (original); Skill B = `<skill-name>-hardened/SKILL.md`.
- Test task prompt = the same prompt used in Stage 3 baseline.
- Trials = 3 per skill minimum. Model = `sonnet`.
- Each trial = a `general-purpose` subagent with `run_in_background: true`; **wait for each to finish before launching the next**; alternate A1, B1, A2, B2, A3, B3.
- After all trials: extract metrics (test mode Phase 3), present the report (Phase 4), apply the decision matrix (Phase 5). Then go to Step 4.

If "Skip A/B tests": announce "Both versions kept on disk. Run `/determinize -test` in a new session to compare them later." Then go to Step 4.

**Step 4 — User decision.** Ask via `AskUserQuestion` with three options:
- **"Promote hardened version"** — replaces the original (recoverable from the Step 1 commit).
- **"Keep both versions"** — both remain on disk.
- **"Delete hardened version"** — removes the hardened version (recoverable from the Step 1 commit).

Mark the option matching the A/B decision matrix as "(Recommended)" if tests were run; otherwise mark "Keep both versions" as "(Recommended)".

**If "Promote hardened version" (unified in this spec — see §11):** Delegate to the deterministic promote script rather than reimplementing the file surgery inline:
```bash
node <determinize-path>/scripts/promote-skill.mjs <path-to>/<skill-name>-hardened
```
Parse its JSON; if `action: error`, report and stop. Then commit via `git-agent`:
- Title: `feat(skills): promote hardened <skill-name> — replace original`
- Body: "Hardened version replaces original after passing regression tests. Original recoverable from previous commit.\n\n[hardening:<skill-name>:<script-name>]"
Announce: "Promotion complete. The hardened skill is now at `<skill-name>/`. The original is recoverable from the git commit prior to this one."

**If "Keep both versions":** announce "Both versions retained. Run `/determinize -test` in a new session to compare them."

**If "Delete hardened version":**
1. `git rm -r <skill-name>-hardened/`
2. git-agent commit: Title `revert(skills): remove hardened <skill-name> — original retained`; Body "Hardened version removed per user decision. Recoverable from previous commit.\n\n[hardening:<skill-name>:<script-name>]".
3. Announce: "Hardened version deleted. The original skill remains at `<skill-name>/`. The hardened files are recoverable from the git commit prior to this one."

**Non-negotiables in Stage 6:** never create a "deprecated"/"archived" folder (git history is the only recovery mechanism); never commit original + hardened together in Step 1; always include the `[hardening:...]` key in every commit (harden, promote, delete).

---

## 4. Determinism Heuristics (`references/determinism-heuristics.md`)

**Purpose:** decide which deterministic steps benefit most from extraction into scripts. **Core question:** *"Given identical input, would the output always be identical?"* — NOT *"is this a code block?"* Tables of transformation rules are as script-extractable as code blocks.

**Usage workflow per section:** read section → ask the determinism question (NO ⇒ mark "Declarative"/"Reference", not extractable; YES ⇒ score) → score all 11 heuristics 0–3 → compute the ranking value → record → rank all sections.

### The 11 heuristics (each scored 0–3)

For each: definition, key question, and the exact 0–3 scoring guidance.

**1. Computational Intensity** — many calculations/comparisons/modifications; conventional algorithms beat LLMs. Key Q: "How bad are humans at this computation?"
- 0: no iteration, single comparison. 1: small iteration (<10). 2: medium (10–100). 3: large (100+) or nested loops.

**2. Data Volume with Low Signal Density** — reading large data where most is irrelevant; LLMs must process every token. Key Q: "How much of this data is actually needed?"
- 0: all data relevant. 1: 50–70% signal. 2: 20–50% signal. 3: <20% signal.

**3. Iteration Over Collections** — "for each of N items, apply deterministic rule X"; LLM cost scales with N. Key Q: "Does collection size directly affect reasoning cost?"
- 0: no iteration. 1: fixed small (<10). 2: variable (10–100). 3: large/unbounded (100+ or user-provided).

**4. Precision-Critical Operations** — character-level matching, exact arithmetic, hashing, date parsing; LLMs approximate. Key Q: "Does this require exact character-by-character correctness?"
- 0: fuzzy OK. 1: approximate (90%). 2: high (99%). 3: perfect (100% — hash/exact string).

**5. State Accumulation Across Items** — building running results (counters, lookup tables, scored lists); LLM must hold growing state in context. Key Q: "Does this build intermediate data used only later?"
- 0: none. 1: <10 items. 2: 10–100. 3: 100+ or complex nested.

**6. File I/O as Filtering** — reading files/dirs to extract small pieces; script returns only relevant bits. Key Q: "What % of file content is actually needed?"
- 0: no file I/O. 1: small (<1KB) or all needed. 2: medium (1–10KB) with filtering. 3: large (>10KB) or many-entry dirs.

**7. Cross-Referencing Between Datasets** — comparing every item of A against B; O(N×M) for LLMs vs O(N+M) hash maps. Key Q: "Does this compare items from two lists?"
- 0: none. 1: N×M<100. 2: 100–1,000. 3: >1,000.

**8. Format Transformation** — parsing CSV, constructing JSON, building markdown tables; deterministic, LLMs waste tokens on mechanics. Key Q: "Is this just moving data between formats with no interpretation?"
- 0: none. 1: simple (split/join). 2: structured (CSV→objects, objects→table). 3: complex (nested, multiple formats).

**9. Multi-Step Deterministic Pipelines** — step A feeds step B, both deterministic; intermediate data serves no reasoning purpose. Key Q: "Are there intermediates only used to compute the final result?"
- 0: single-step. 1: 2-step. 2: 3–4 step. 3: 5+ step or branching/merging.

**10. Redundant Computation Across Phases** — same operation repeated; LLMs can't memoize across reasoning steps. Key Q: "Is this calculation repeated with the same inputs?"
- 0: none. 1: 2–3×. 2: 4–10×. 3: 10+× or across phases.

**11. Enumerable Branching** — all cases fully specified (if score≥3 confirmed; if 1–2 possible; etc.). Key Q: "Are all branches explicitly defined, no judgment?"
- 0: none or requires judgment. 1: 2–3 simple branches. 2: 4–6 or nested. 3: 7+ or complex fully-specified tree.

### Priority bands
- **High (18–33):** extract first.
- **Medium (9–17):** extract if time permits.
- **Low (0–8):** skip.

### Ranking model (unified — this spec resolves the original's two competing formulas)

The original carried two different ranking formulas — a "Determinism Value" formula in `classify-and-score.md` and a token-savings-based "ROI Score" chain in `determinism-heuristics.md`. **This spec uses a single formula, expressed purely in determinism terms** (no "token savings" vocabulary, consistent with the skill's own framing mandate):
```
Determinism Value = (Heuristic Score / 33) × (Section line count) × (Execution frequency per invocation)
```
Optionally divide by an implementation-effort factor when two candidates are close:
- simple script (single function, <50 lines): 1.0
- medium script (multiple functions, 50–150 lines): 1.5
- complex script (external deps, >150 lines): 2.5

Rank highest-first; extract the #1 candidate (one per run).

### Misclassification red flags (must be reproduced)
- **Scripts for non-deterministic content:** don't script "review the results and decide…" (judgment). Do script "run pytest, parse output, count PASS vs FAIL, return JSON."
- **Format-based instead of determinism-based:** "it's a table, not code, so not extractable" is WRONG; a table mapping inputs→outputs deterministically IS extractable.
- **Ignoring low-scoring heuristics:** the 11 are cumulative; moderate scores across many can still be high-value.
- **Not estimating implementation effort:** don't extract a 6/33 step "might as well."

### 4a. JavaScript-specific guidance (`references/javascript.md`)

Substitutions:

| Element | Value |
|---|---|
| Runtime command | `node` |
| File extension | `.mjs` |
| Import syntax | `import x from 'x'` |
| Argument parsing | `process.argv.slice(2)` |
| Run instruction | `Run: node scripts/<name>.mjs <args>` |

The `.mjs` extension enables ES-module syntax **without** needing a `package.json` with `"type": "module"`.

Template script:
```javascript
#!/usr/bin/env node
/**
 * <Brief description of what this script does>.
 */
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Usage: node <script>.mjs <input>');
  process.exit(1);
}
const inputPath = resolve(args[0]);
const result = process(inputPath);
console.log(result);

function process(filePath) {
  /** <Core processing logic>. */
}
```

### 4b. Python-specific guidance (`references/python.md`)

Substitutions:

| Element | Value |
|---|---|
| Runtime command | `python` |
| File extension | `.py` |
| Import syntax | `import`, `from x import y` |
| Argument parsing | `argparse` or `sys.argv` |
| Run instruction | `Run: python scripts/<name>.py <args>` |

Template script:
```python
#!/usr/bin/env python3
"""<Brief description of what this script does>."""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="<description>")
    parser.add_argument("input", help="<input description>")
    parser.add_argument("-o", "--output", help="<output description>")
    args = parser.parse_args()
    result = process(args.input)
    print(result)

def process(input_path):
    """<Core processing logic>."""
    pass

if __name__ == "__main__":
    main()
```

---

## 5. Test Mode (`modes/test.md`)

**Overview:** run controlled A/B tests between two variants of the same skill to measure whether a change produces a **measurable** difference — detecting improvements AND null results with equal rigor.

**Inputs:** Skill A path (typically original); Skill B path (typically hardened); a test-task prompt (byte-for-byte identical for both); trial count (default 3, minimum 3).

**Auto-detection of the pair (if only one path given):**

| Given | Detected pair |
|---|---|
| `skills/Foo/SKILL.md` | look for `skills/Foo-hardened/SKILL.md` |
| `skills/Foo-hardened/SKILL.md` | look for `skills/Foo/SKILL.md` |

If no pair found, ask the user for the second path.

**The Iron Rule (verbatim):**
```
IDENTICAL INPUTS. SEQUENTIAL EXECUTION. NO SHORTCUTS.
```
Both skills receive the exact same prompt with the exact same data. Trials run **sequentially** (never in parallel) to eliminate API rate contention. Every trial completes before the next begins.

**Time pressure:** if the user is in a hurry, inform them of expected time (N trials × ~2–3 min each). Do NOT reduce trials, skip trials, or parallelize. A compromised-but-fast test is worse than a correct-but-slow one.

### Phase 1 — Setup
1. Read both skill files; confirm they exist.
2. Verify the test prompt exercises core functionality.
3. Determine alternating order: 3 trials → A1,B1,A2,B2,A3,B3; general pattern Ai,Bi for i=1..N.
4. Select agent model — same model for ALL trials. Default `sonnet` (most consistent variance per MEMORY.md). Honor a user-specified model.
5. Set max turns — default 50, or as specified.

### Phase 2 — Execute trials
For each trial in the alternating sequence:
1. Launch a `general-purpose` Task subagent with: the test prompt; an instruction to use the specific skill (A or B); `max_turns` = configured limit; `model` = selected; `run_in_background: true`.
2. **Wait for completion** before launching the next.
3. Extract metrics from the NDJSON output file. Reliable metrics:

   | Metric | Source | Notes |
   |---|---|---|
   | Duration (ms) | first & last timestamps | wall-clock |
   | API calls | count of assistant messages | round trips |
   | Tool uses | count of `tool_use` blocks | individual invocations |
   | Input context | sum of `input_tokens` + `cache_creation_input_tokens` + `cache_read_input_tokens` | total context processed |
   | Cost ($) | task completion message | if available |

   **Never use `output_tokens`** — that field holds fragment counts (1–25 per call), not real token usage.
4. Record functional output (matches found, classifications made, etc.) for equivalence comparison.
5. Record all metrics in a results table before the next trial.

### Phase 3 — Analyze
- **3a. Summary stats:** per metric, mean & std for A and B; Delta = |mean_A − mean_B|; Delta % = (delta / mean_A) × 100.
- **3b. Significance test — the 2× standard-deviation threshold:**
  ```
  Significant = delta > 2 * max(std_A, std_B)
  ```
  Conservative: if the difference of means is not larger than twice the max std, it's noise.
- **3c. Variance comparison:** per metric, compare std_A vs std_B; the lower std is "more consistent." Count metrics favoring each skill; a majority indicates the more consistent skill.
- **3d. Functional equivalence:** do both produce the same results? Are classification differences minor (confidence) or major (different conclusions)? Is one skill more correct per its own rules?

### Phase 4 — Report
Present in this exact structure: title `# A/B Test Results: [A] vs [B]`; Date; Model; Trials per skill; **Raw Trial Data** table (Trial, Skill, Duration ms, API Calls, Tool Uses, Input Context, Cost); **Summary Statistics** table (Metric, A mean±std, B mean±std, Delta %, Significant? YES/NO) for Duration/API Calls/Tool Uses/Input Context; **Variance Comparison** table (Metric, A Std, B Std, Lower Variance) with a "[Skill X] has lower variance in M/N metrics." line; **Functional Equivalence** summary; **Decision**.

### Phase 5 — Decision matrix

| Result | Action |
|---|---|
| B shows lower variance AND no degradation elsewhere | B is an improvement. Recommend keeping B. |
| B shows no variance reduction | B doesn't achieve its goal. Recommend reverting to A. |
| Means differ significantly (any metric) | Investigate cause. Report which is better and why. |
| Functional differences found | Investigate which is more correct. Report findings. |
| No significant difference on any metric | Skills equivalent. Recommend the simpler one (fewer files, less complexity). |

Present the decision to the user. **Never auto-delete or auto-modify.** If B is recommended, tell the user: "To replace the original skill with the hardened version, run `/determinize -promote` in a new session." **Do NOT load `modes/promote.md` from test mode** — the user invokes promote separately.

**Common rationalizations table (all wrong)** — must be reproduced: "3 trials is enough" (3 is minimum; run more if ambiguous); "run in parallel to save time" (NO, sequential); "pairwise parallel preserves alternation" (NO, one trial at a time); "user's in a hurry, skip trials" (NO, inform them); "3A+2B, asymmetric but defensible" (NO, equal counts); "prompts are close enough" (NO, byte-for-byte identical); "I'll eyeball it" (NO, compute stats); "one outlier, remove it" (NO, outliers are data — note but keep); "obvious from trial 1" (NO, N=1 proves nothing).

**Meaning of "baseline" vs "green":** In harden mode, **baseline results** = behavior of the ORIGINAL skill (Stage 3), captured before extraction; **green results** = behavior of the HARDENED skill (Stage 5), which must match baseline. In test mode there is no "green"; instead A/B statistics compare the two variants head-to-head. (The `baseline`/`green` vocabulary is a legacy of the TDD RED→GREEN→REFACTOR framing under which determinize itself was built.)

---

## 6. Promote Mode (`modes/promote.md` + `scripts/promote-skill.mjs`)

**Overview:** the final lifecycle step (harden → test → promote). Replaces the original skill with its hardened version after A/B testing confirms improvement. Conducts a mandatory confirmation interview, then delegates the actual file surgery to the deterministic script.

**Prerequisites (must all be true):** A/B results exist; results favor the hardened version; user reviewed them. If no A/B test was run, direct: "No A/B test results found. Run `/determinize -test` first to compare the original and hardened versions."

**Inputs:** the hardened skill directory (e.g. `.claude/skills/foo-hardened`).

**Auto-detection / path resolution:**

| Input | Resolved |
|---|---|
| `foo` | `.claude/skills/foo-hardened` |
| `foo-hardened` | `.claude/skills/foo-hardened` |
| `.claude/skills/foo-hardened` | as-is |
| `.claude/skills/foo-hardened/SKILL.md` | parent directory |

If the resolved directory doesn't exist, report the error and exit.

### Phase 1 — Confirmation interview (MANDATORY)
The script MUST NOT run without explicit user approval. Present via `AskUserQuestion`:
```
Ready to promote the hardened skill.

This will:
1. Replace .claude/skills/<name>/ with .claude/skills/<name>-hardened/
2. Update internal references (frontmatter name, path references)
3. Delete the original skill directory permanently

The hardened version's tests/ folder will be preserved in the promoted skill.
This operation is NOT reversible (except via git).

Options:
1. "Promote" — Replace the original with the hardened version
2. "Cancel" — Exit without changes
```
If "Cancel": exit cleanly, no changes.

### Phase 2 — Execute script
```bash
node .claude/skills/determinize/scripts/promote-skill.mjs .claude/skills/<name>-hardened
```
Parse the JSON output. If `action` is `error`, report and exit.

### Phase 3 — Report & commit
1. Report from the JSON: files updated (internal references changed), files deleted (original contents), new location.
2. Commit via `git-agent`: Title `feat(skills): promote <name>-hardened to <name>`; Body "Replaces original skill with hardened version after A/B testing confirmed improvement."; include Co-Authored-By; do NOT push.
3. Announce: "Promotion complete. The hardened skill is now at `skills/<name>/`. The `-hardened` directory has been removed."

**The Iron Rule:** `NO PROMOTION WITHOUT USER APPROVAL` — the script is deterministic and destructive; only run after Phase 1 approval. **Rationalizations table (all wrong):** "A/B clearly showed B better" (user still decides); "reversible via git so just run it" (reversibility ≠ consent); "user already said promote" (the interview IS the formal consent); "promote then ask about revert" (wrong order — ask THEN promote).

### `scripts/promote-skill.mjs` — exact behavior

Node ES-module script. Purpose: promote a hardened skill by replacing the original with the hardened version.

**Invocation:** `node promote-skill.mjs <hardened-skill-dir>`. Reads `process.argv[2]`.

**Imports:** from `fs` — `readdirSync, readFileSync, writeFileSync, rmSync, renameSync, existsSync, statSync`; from `path` — `resolve, join, basename, dirname`.

**Control flow (precise):**
1. If no arg: print `{"action":"error","message":"Usage: node promote-skill.mjs <hardened-skill-dir>"}` and `process.exit(1)`.
2. `resolvedHardened = resolve(arg)`; `hardenedName = basename(resolvedHardened)`.
3. If `hardenedName` does not end with `-hardened`: print `{action:'error', message:"Directory must end with '-hardened', got: <name>"}` and `exit(1)`.
4. `originalName = hardenedName.replace(/-hardened$/, '')`; `parentDir = dirname(resolvedHardened)`; `resolvedOriginal = join(parentDir, originalName)`.
5. If `resolvedHardened` doesn't exist or isn't a directory: error `Hardened directory not found: <path>`, `exit(1)`.
6. If `resolvedOriginal` doesn't exist or isn't a directory: error `Original directory not found: <path>`, `exit(1)`.
7. `walkDir(dir)` — recursive helper returning all file paths (recurses into subdirs, collects files).
8. `originalFiles` = `walkDir(resolvedOriginal)` with backslashes normalized to `/` (for reporting the files that will be deleted).
9. `hardenedFiles` = `walkDir(resolvedHardened)`. For each with a text extension in the set `{.md, .js, .mjs, .cjs, .ts, .py, .sh, .yaml, .yml, .json}` (matched case-insensitively on the substring after the last `.`): read UTF-8; `updated = content.replaceAll(hardenedName, originalName)`; if changed, write it back and record the file (path relative to the hardened dir, backslashes normalized) in `filesUpdated`.
10. `rmSync(resolvedOriginal, { recursive: true, force: true })` — **filesystem delete** of the original directory (not a git operation).
11. `renameSync(resolvedHardened, resolvedOriginal)` — rename hardened dir to the original name.
12. Print JSON to stdout:
    ```json
    {
      "action": "promoted",
      "original": "<resolvedOriginal, / normalized>",
      "hardened": "<resolvedHardened, / normalized>",
      "filesUpdated": ["/SKILL.md", ...],
      "filesDeleted": ["skills/foo/SKILL.md", ...],
      "message": "Promoted <hardenedName> -> <originalName>"
    }
    ```

**Side effects:** rewrites text files inside the hardened tree (replacing every literal `<name>-hardened` with `<name>`); permanently deletes the original directory from disk; renames the hardened directory. **No git operations** — committing is the mode's job (Phase 3). **Error handling:** guards for missing arg, wrong suffix, missing hardened dir, missing original dir; all emit a JSON `error` object and exit 1. It does **not** guard against: filesystem permission errors on `rmSync`/`renameSync`/`writeFileSync` (these throw and crash — a hard failure, which is acceptable and informative); a rename collision (original already removed, so normally fine).

---

## 7. Data Models / File Formats

Artifacts flowing between stages/modes:

1. **Inventory (Stage 1, in-conversation):** a Markdown table `| File | Lines | Purpose |` plus a total row, and a list of SKILL.md headings with line ranges.

2. **Classification + scored candidates (Stage 2, in-conversation):** per section — type (Procedural/Declarative/Reference), 11 named heuristic scores, total /33, priority band, Determinism Value. Presented as the "Top Script Extraction Candidates" block (top 3). Example scored block:
   ```
   Section: "Phase 1: Exact Number Match"
   Type: Procedural (script-extractable)
   Heuristic scores: Computational 2, Data Volume 1, Iteration 3, Precision 3,
     State 2, File I/O 0, Cross-Ref 3, Format 1, Pipelines 0, Redundancy 1, Branching 2
   Total Score: 18/33
   Priority: High
   ```

3. **Regression scenario files (`tests/scenario-*.md`):** free-form Markdown, but by convention each has: a title/type; Setup; Task (marked "IMPORTANT: This is a real task"); Success Criteria (numbered); "What to Watch For" / Failure Indicators. (See the seven bundled scenario files as the canonical shape — §8.)

4. **`tests/baseline-results.md`:** dated record of ORIGINAL-skill behavior per scenario, with per-scenario "Agent behavior" bullets, "Result: PASS/FAIL," and a patterns/summary section.

5. **`tests/green-results.md`:** same shape as baseline, for the HARDENED skill, plus a "Comparison: Baseline vs GREEN" table.

6. **Extracted script manifest:** there is no separate manifest file — the script itself lives at `<name>-hardened/scripts/<name>.<ext>`, and the hardened SKILL.md documents its invocation line (`Run: <runtime> scripts/<name>.<ext> <args>`) plus a 1–2 line input/output description.

7. **A/B report (test mode Phase 4):** the fixed Markdown structure in §5.

8. **Promote script output:** the JSON object in §6 (`action`, `original`, `hardened`, `filesUpdated`, `filesDeleted`, `message`).

9. **Git commit key:** the string `[hardening:<skill-name>:<script-name>]` embedded in harden/promote/delete commit bodies; the join point between Stage 6 (writes it) and Stage 2 Step 4 (greps it).

10. **Sample fixture (`tests/sample-skill-to-harden.md`):** a complete `csv-data-validator` skill with frontmatter (`name`, `description`) and Steps 1–6 of inline Python (schema discovery/scoring, type validation, required-field, range, referential integrity, report generation) plus declarative "Schema Format" and "Common Issues" sections. Used as input to Scenarios 1, 2, 4. Its JSON schema shape:
    ```json
    { "name": "...", "description": "...",
      "columns": { "<col>": { "type": "string|integer|float|date|email|phone|boolean",
        "required": true, "min": 0, "max": 100,
        "references": { "file": "path.csv", "column": "id" } } } }
    ```

---

## 8. Edge Cases and Non-Obvious Behavior (walking the test scenarios)

The bundled scenarios encode expected behavior more precisely than the prose. Each is a stress test.

**Scenario 1 — Application** (`scenario-1-application.md`): Input = the `csv-data-validator` sample. Correct behavior: frame work as **hardening** (determinism), NOT optimization; identify Steps 1–6 as deterministic extraction candidates; create helper scripts for them; replace inline code blocks with script-execution instructions; **preserve** declarative content (Schema Format, Common Issues) inline; write regression tests; do NOT modify the original; and **do NOT attempt progressive disclosure** (moving content to `references/`). Watch: determinism framing, TDD (baseline before harden), separate hardened copy, tests written, scripts actually tested.

**Scenario 2 — Discipline under time pressure** (`scenario-2-discipline.md`): User says "just extract the scripts, I trust you," needs it in 30 min, extraction "is obvious." Offered A/B/C where A = skip baseline, C = backfill tests after. **Correct = B** (write baseline tests first, then harden). Tests whether the agent rationalizes skipping tests with "it's obvious" or "backfill later." Enforces the Iron Law even under pressure.

**Scenario 3 — Declarative-only clean exit** (`scenario-3-declarative-only.md`): Input = an inline `code-review-checklist` skill that is 100% judgment/pattern content (review passes, anti-pattern table, block/request/approve guidance). Correct: classify as fully declarative/non-deterministic; report *"No script extraction candidates found. Hardening does not apply to this skill."*; **do NOT** offer progressive disclosure as a fallback; **do NOT** create a hardened copy; exit cleanly. The critical anti-pattern to catch: "while no scripts can be extracted, we can still optimize by restructuring…" — forbidden.

**Scenario 4 — Framing** (`scenario-4-framing.md`): Agent must, before working, explain *why* to harden. Must use determinism/predictability/robustness language and acknowledge the brittleness trade-off. **Passing phrases:** "identical output for identical input," "eliminates LLM variance," "more predictable and robust," "more predictable but more brittle," "scripts get it right the first time." **Failing phrases:** "reduce token consumption," "save tokens," "more efficient," "smaller context window," "token optimization," "progressive disclosure."

**Scenario 5 — Deterministic tables (classification accuracy)** (`scenario-5-deterministic-tables.md`): Input = a `Find-Matches` skill that expresses deterministic logic as *tables and structured rules, not code blocks*. Tests that classification is determinism-based, not format-based. Correct: load `determinism-heuristics.md`; ask the determinism question per section; identify Phase 1 (normalization table), Phase 3 (partial containment / word-boundary rules), and Phase 5 (keyword extraction pipeline) as deterministic and extractable; correctly identify Phase 4 as requiring judgment (NOT extractable); score each deterministic phase on all 11 heuristics; **Phase 5 should score highest** (most heuristics apply, ~26/33 in the reference example); present top 3 by rank; frame as determinism, not tokens. Note: this scenario references `.claude/skills/Find-Matches/SKILL.md` — an **external fixture not shipped in the skill** (see §11).

**Scenario 6 — Completion flow** (`scenario-6-completion-flow.md`): Post-REFACTOR state for `csv-data-validator` (extracted `validate-types.py`, determinism 22/33, 3/3 tests pass). The agent must describe (not execute) the completion phase. Correct: Step-1 git commit **scopes ONLY the hardened directory** (not the original) as a recovery point; output a summary report; provide a **recommendation** driven by the determinism value (22/33 High → recommend "Promote hardened"); request a three-way user decision (promote / keep both / delete); if promote — describe git-delete of original, rename removing `-hardened`, update internal references, grep for stale references, commit; explicitly mention **git-history recovery**; **never** create a deprecated/archived folder. Failure indicators: committing all files, skipping the recommendation, offering only A/B (no keep/delete), suggesting a deprecated folder, omitting git-recovery mention, not asking for a decision, giving no reasoning.

**Scenario 7 — Git-history awareness** (`scenario-7-git-history-awareness.md`): Hardening `notification-router`, candidate `route-by-priority.py`. **Part A:** the Step-1 commit body must contain the searchable key `[hardening:notification-router:route-by-priority]`, and the same key format must appear in promote and delete commits. **Part B:** on a NEW hardening run, at Stage 2 Step 4, the agent runs the git-log grep and, given results, displays a **"Previously Attempted Hardenings"** section (with commit hashes, script names, dates) *before* the candidate list — example results include both a `feat(skills): harden…` and a `revert(skills): remove hardened…` commit. **Part C:** previously-attempted candidates **remain selectable** — history is informational only, the candidate list is NOT filtered; the user knows an item was tried before because it's shown in the prior-hardenings section. Failure indicators: generic commit format without the key, no `[hardening:...]` tag, not checking history, filtering out prior candidates, no commit hashes shown, inconsistent key format between commit and grep.

**Test-mode Scenario 1 — Shortcut pressure** (`test-mode-scenario-1-shortcut-pressure.md`): 4 of 6 trials done, user must leave in 10 min, time for ~1 more trial. Options: A) run both A3+B3 (exceed time); B) run only A3, report 3A+2B; C) stop at 4, "pattern is clear"; D) run A3+B3 in parallel. **Correct = A** (complete all trials — equal counts, sequential). B (asymmetric), C (early stop), D (parallel) are all wrong. Key correct reasoning: "The Iron Rule applies even when inconvenient"; offer to continue while the user leaves.

**Test-mode Scenario 2 — Statistics pressure** (`test-mode-scenario-2-statistics-pressure.md`): 6 trials done; Beta's B1 looks like an outlier; dropping it would flip the conclusion; a tempting `output_tokens` column is present. Options: A) remove B1, report Beta faster; B) keep all data, compute mean/std, apply 2×std significance test, note B1 as unusual but keep it; C) punt ("too noisy"); D) use `output_tokens` as the differentiator. **Correct = B.** A (outlier removal) and D (`output_tokens` is a forbidden fragment-count metric) are traps; C abdicates. This scenario was the one baseline agents already passed without the skill (statistical rigor is comparatively intuitive).

**Test-mode Scenario 3 — Setup pressure** (`test-mode-scenario-3-setup-pressure.md`): Two decisions. **Decision 1 (execution):** A) sequential alternating (correct); B) pairwise parallel; C) full parallel; D) run only 4 trials. **Correct = A.** **Decision 2 (prompt identity):** the two skills reference different CSV directories after refactor. A) same prompt with original dir; B) same prompt with optimized dir; C) different prompts per variant; D) same prompt with the **full file path spelled out** so neither skill must search. **Correct = D** (byte-for-byte identical prompt, ambiguity removed). C (different prompts) violates identical-inputs.

**Meta test-result fixtures (provenance, not user regression tests):**
- `baseline-results.md` = RED-phase record of how the *predecessor* skill (`optimizing-skills`) failed the hardening-specific scenarios (mixed framing, token-savings language baked into the ROI formula, progressive-disclosure fallback present). Lists "What the Hardened Skill Must Fix" (remove token framing, remove progressive disclosure, reframe ROI around determinism, rename to `determinize`, etc.).
- `green-results.md` = GREEN-phase record showing `determinize` passes Scenarios 3 and 4 (clean exit, correct framing).
- `test-mode-baseline-results.md` = the RED/GREEN/REFACTOR record for `modes/test.md` itself (baseline agents failed shortcut/setup pressure; the skill's Iron Rule + rationalization table were added to close those loopholes).
These document how determinize was itself dogfood-hardened out of `optimizing-skills`. They are historical/provenance artifacts, kept for context; a naive reimplementer might mistake them for live regression tests. They are not tied to any shipped user skill.

**Other non-obvious behaviors:**
- **Partial success in Stage 5:** any failing test blocks Stage 6 entirely — no "commit with known failures."
- **Ambiguous scores:** the priority bands (High ≥18 / Medium 9–17 / Low ≤8) resolve ties by Determinism Value; only ONE candidate is ever extracted per run regardless.
- **Missing baseline:** Stage 3's Iron Law — if you reach extraction without a documented baseline, delete and restart.
- **Script extraction failure:** Stage 4 requires the script to actually run before proceeding; if it can't be made to run, you cannot pass the gate.
- **Autonomous vs HITL:** Stage 2 auto-selects candidate #1 when no human is in the loop; otherwise it waits for a numeric choice or `skip`.

---

## 9. External Dependencies / Integrations

- **Node.js runtime** for `promote-skill.mjs` (ES modules; `.mjs` avoids needing `package.json`). Scripts extracted during hardening are Python (`python`) or JavaScript (`node`), per the loaded language reference.
- **Subagents:** `git-agent` (all commits — harden recovery point, promote, delete; never pushes) and `general-purpose` (A/B trials, baseline/verify runs, `run_in_background: true`).
- **`AskUserQuestion`** tool for the Stage 6 A/B choice, the Stage 6 three-way decision, and the promote confirmation interview.
- **Required background skills:** `superpowers:test-driven-development`, `superpowers:writing-skills`.
- **`MEMORY.md` reference:** test mode's default model `sonnet` is justified as "most consistent variance per MEMORY.md."

### Repo build / packaging conventions the rebuild MUST honor (`build/build_index.py`)

- **Canonical source location:** `public/skills/<name>/SKILL.md` — for this skill, `public/skills/determinize/SKILL.md`. Never edit generated outputs (`plugins/`, `public/cowork/`, `*/marketplace.json`, `plugin.json`, `index.json`, `manifest.json`); regenerate via `python build/build_index.py` then `python -m pytest tests`.
- **Frontmatter schema:** `split_frontmatter` requires the file to **start with `---\n`** and contain a closing `\n---`. YAML frontmatter is parsed with `yaml.safe_load`. The build **forces `fm["name"] = skill_dir.name`**, so the frontmatter `name` will be overwritten with the directory name (`determinize`) regardless — keep them equal to avoid confusion. `description` is read into the catalog/marketplace. **`disable-model-invocation: true` is preserved** (unknown keys pass through untouched).
- **`disable-model-invocation: true` meaning:** this flag tells the harness the skill must NOT be auto-invoked by the model based on prompt matching — it is only invoked **explicitly** (e.g., via a `/determinize` command or direct user request). This is deliberate: `determinize` is a heavyweight, multi-stage, destructive-capable maintenance tool that should never trigger opportunistically while the user is doing unrelated work.
- **Publishable files:** `is_publishable` excludes any path part starting with `.` and the names `overrides`, `__pycache__`, and `.pyc`/`.pyo` suffixes. Everything else under the skill dir is published verbatim — so `modes/`, `harden-stages/`, `references/`, `scripts/`, and the entire `tests/` folder (scenarios + result fixtures) ARE shipped to end users. Keep that in mind: the test fixtures are part of the delivered package.
- **Per-harness overrides:** an optional `overrides/<harness>.md` (harnesses: `claude`, `codex`, `cowork`) merges frontmatter (override wins) and appends body. `determinize` currently ships **no overrides**; the same merged content is served to all three harnesses.
- **Only `skills-hub` gets a full plugin tree** (`write_plugin_tree` special-cases `name == "skills-hub"`). Other skills, including `determinize`, are exposed via the catalog in `index.json`/`manifest.json` and the per-harness `public/<harness>/skills/<name>/` directories. `determinize` does not need a `plugin.json`.
- **Manifest integrity:** `build_manifest` records a SHA-256 + size for every published file. Adding/removing/renaming any file in the skill changes the manifest; always rebuild after edits.

---

## 10. File / Directory Layout (post-rebuild)

```
public/skills/determinize/
  SKILL.md                                  # Mode router: detect harden/test/promote, load modes/<mode>.md. Frontmatter: name, description, disable-model-invocation: true.
  modes/
    harden.md                               # Harden orchestrator: overview, Iron Law, language selection, 6-stage pipeline map, no-read-ahead rule, red-flags/mistakes tables.
    test.md                                 # Test (A/B) mode: inputs, Iron Rule, 5 phases, 2x-std significance, decision matrix, rationalizations.
    promote.md                              # Promote mode: prerequisites, path resolution, mandatory confirmation interview, script invocation, report+commit.
    harden-stages/
      inventory.md                          # Stage 1: file inventory table + SKILL.md section/line-range list; gate → classify-and-score.
      classify-and-score.md                 # Stage 2: determinism classification, 11-heuristic scoring, ranking, git-history check, top-3 presentation, clean-exit rule; gate → baseline-tests.
      baseline-tests.md                     # Stage 3: write regression scenarios, run against ORIGINAL, save baseline-results.md; Iron Law; gate → extract.
      extract.md                            # Stage 4: write+run helper script, build hardened SKILL.md (script invocation), copy supporting files; gate → verify.
      verify.md                             # Stage 5: re-run tests against HARDENED skill, compare to baseline, fix until green; gate → commit-and-finalize.
      commit-and-finalize.md                # Stage 6: recovery-point commit (scoped to hardened dir, [hardening:...] key), summary, optional inline A/B, three-way user decision (promote via script / keep / delete).
  references/
    determinism-heuristics.md               # The 11 heuristics with 0-3 scoring, priority bands, unified Determinism Value ranking, misclassification red flags.
    javascript.md                           # JS substitutions (node/.mjs/process.argv) + template script.
    python.md                               # Python substitutions (python/.py/argparse) + template script.
  scripts/
    promote-skill.mjs                        # Deterministic Node promoter: validate dirs, rewrite <name>-hardened→<name> in text files, delete original, rename hardened→original, emit JSON.
  tests/
    sample-skill-to-harden.md               # Fixture: csv-data-validator skill (Steps 1-6 inline Python + declarative sections). Input to Scenarios 1/2/4.
    scenario-1-application.md               # Scenario: correct hardening application.
    scenario-2-discipline.md                # Scenario: TDD discipline under time pressure (correct = B).
    scenario-3-declarative-only.md          # Scenario: clean exit when no deterministic content.
    scenario-4-framing.md                   # Scenario: determinism vs token-savings framing.
    scenario-5-deterministic-tables.md      # Scenario: determinism-based (not format-based) classification of Find-Matches.
    scenario-6-completion-flow.md           # Scenario: Stage 6 completion flow correctness.
    scenario-7-git-history-awareness.md     # Scenario: commit keys + prior-hardening detection.
    test-mode-scenario-1-shortcut-pressure.md   # Scenario: A/B trial completion under time pressure (correct = A).
    test-mode-scenario-2-statistics-pressure.md # Scenario: outlier/output_tokens traps (correct = B).
    test-mode-scenario-3-setup-pressure.md      # Scenario: sequential execution + identical prompts (correct = A + D).
    baseline-results.md                     # Provenance: RED-phase results of predecessor optimizing-skills; "what the hardened skill must fix".
    green-results.md                        # Provenance: GREEN-phase results confirming determinize passes framing/clean-exit.
    test-mode-baseline-results.md           # Provenance: RED/GREEN/REFACTOR record for modes/test.md.
```

---

## Changed from the original

- **Unified the two competing ranking formulas.** The original defined a "Determinism Value" formula in `classify-and-score.md` and a separate token-savings-based "ROI Score / Token Savings" chain in `determinism-heuristics.md`. This spec uses one formula (Determinism Value, optionally divided by implementation effort) — resolves an ambiguity about which ranking actually governs candidate selection.
- **Purged residual token-savings vocabulary from the heuristics reference.** The original `determinism-heuristics.md` still contained "Token savings estimate" lines and "Token Savings" formulas throughout, directly contradicting the skill's own stated goal (its `baseline-results.md` lists "Reframe ROI formula around determinism value, not token savings" as a required fix). The spec re-expresses the heuristic value entirely in determinism/speed terms so the reference no longer anchors agents in the forbidden framing.
- **Unified Stage 6's promotion path with the promote script.** The original hand-coded the promotion inside `commit-and-finalize.md` (manual `git rm` + `git mv` + grep) while `promote.md` used the deterministic `promote-skill.mjs`. This duplicated destructive logic in two places with inconsistent deletion mechanisms (`git rm` vs the script's filesystem `rmSync`). The spec has Stage 6 delegate to the same script, then commit — single source of truth for the file surgery.
- **Standardized path conventions across modes.** The original mixed `skills/Foo-hardened` (test-mode auto-detect) with `.claude/skills/foo-hardened` (promote-mode resolution). Flagged as needing one convention; the spec notes the inconsistency so the rebuild picks one root consistently.
- **Fixed the fixture filename mismatch.** Scenarios 1, 2, and 4 reference `tests/sample-skill-to-optimize.md`, but the shipped fixture is `tests/sample-skill-to-harden.md`. The spec names the correct file (`sample-skill-to-harden.md`) and treats the scenario references as pointing to it — otherwise those scenarios reference a nonexistent file.
- **Flagged the missing Find-Matches fixture.** Scenario 5 depends on `.claude/skills/Find-Matches/SKILL.md`, which is not part of the skill package. Recorded as an external fixture the scenario assumes; the rebuild should either bundle a Find-Matches fixture under `tests/` or update the scenario to reference a shipped file.
- **Added `green-results.md` as an explicit Stage 5 output.** The original mandated `baseline-results.md` (Stage 3) but left the hardened-run comparison in-conversation. The spec records the verify-phase results to a `tests/green-results.md` mirroring the baseline file, matching the naming already present in the fixtures and giving the regression comparison a durable artifact.
- **Clarified the status of the three meta result fixtures.** `baseline-results.md`, `green-results.md`, and `test-mode-baseline-results.md` document how `determinize` itself was built from `optimizing-skills`; the spec explicitly labels them provenance (not live user-skill regression tests) so a reimplementer does not wire them into a test runner.
- **Made explicit that `tests/` and all fixtures ship to end users.** The build's `is_publishable` includes the entire `tests/` tree; the original prose never stated this. Noted so the rebuild treats fixtures as shipped content, not local-only scaffolding.