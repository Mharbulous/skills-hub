---
name: claude-md-optimizer
description: Optimization protocol for a specified CLAUDE.md file. Takes a target CLAUDE.md path, determines its variant from which template it uses, then applies one of three protocols (folder / repo-root / global) that trim noise and relocate information to the shallowest scope where it still applies. Use when (1) optimizing an existing CLAUDE.md, (2) creating a new one from a template, (3) rebalancing content across a CLAUDE.md hierarchy, or (4) seeding missing CLAUDE.md files in a subtree.
---

# CLAUDE.md Optimization Protocol

**Input:** path to a target CLAUDE.md. **Goal:** every line of every CLAUDE.md in the hierarchy lives at the shallowest scope it applies to — no shallower. Narrower content pushed down, broader pulled up, noise deleted.

Variant from the target's template:

| Template used by target | Variant |
|-------------------------|---------|
| [templates/CLAUDE-folder.md](templates/CLAUDE-folder.md) | A — Folder |
| [templates/CLAUDE-repo.md](templates/CLAUDE-repo.md) | B — Repo root |
| [templates/CLAUDE-global.md](templates/CLAUDE-global.md) | C — Global |

Background: [reference/consolidated-research.md](reference/consolidated-research.md)

---

## Phase 0 — Setup

1. Identify variant. If target missing, create from template and exit.
2. Read the target exactly once. Tag each line exactly once:

   | Tag | Meaning | Action |
   |-----|---------|--------|
   | `CMD` | Command Claude runs repeatedly | keep |
   | `RULE` | Project-specific MUST/NEVER/ALWAYS | keep |
   | `CONV` | Convention a linter can't enforce | keep |
   | `QUIRK` | Non-obvious gotcha | keep |
   | `STRUCT` | Tech stack, layout, key files | keep |
   | `REF` | `@path` or "see …" pointer | keep |
   | `LINT` | Style rule a linter/formatter enforces (or could) | delete — move to ESLint/Prettier + hook |
   | `GENERIC` | Redundant under auto-load (see definition) | candidate — verify in 3b |
   | `DOC` | Embedded documentation | delete — replace with one-line `@reference` |

   **GENERIC definition:** a line is GENERIC if the auto-loaded bundle (global + ancestor + target CLAUDE.mds) already implies, restates, or trivially covers it. Subagents with narrow tasks often never run Glob, Read, or Grep beyond the files they were handed — so the test is **not** "could a subagent derive this by exploring the repo." Test: given *only* what auto-loads into its context, is the line already implied, restated, or trivially inferable? Lines encoding non-default choices (specific pattern, rule, convention, working directory) are NOT GENERIC — they are load-bearing. Do not tag them. Stale lines contradicted by other auto-loaded content also qualify.

3. Read every ancestor CLAUDE.md once (cached for the rest of the protocol). Mark verbatim/near-verbatim `keep` lines **upward-duplicate → delete**.

3b. **Verify GENERICs via chat-only subagent** (no read/grep/bash/web tools — it must not be able to explore the repo). Spawn **one** Sonnet subagent. Paste the full auto-load bundle verbatim, labeling each block with its path. Provide GENERIC-candidate line numbers and text. Ask: *"Which of these lines are obvious, redundant, or derivable from the bundle? Be strict — a line is only obvious if a reasonably competent engineer reading the bundle would already assume it. Lines encoding non-default choices are NOT obvious — flag as load-bearing. Also flag any line conflicting with other bundle content as stale."* Confirmed obvious/stale → delete. Not confirmed → re-tag `keep`. Record subagent justifications in the run log.

4. Classify remaining `keep` lines: **obviously-downward** (names a single subpath that exists) → relocate directly; **ambiguous** → hold for Phase 1.

5. **Early exit** if, after steps 2–3b and 4, within line budget AND ambiguous bucket empty AND no subfolders are missing a CLAUDE.md → skip to Phase 3.

**Budgets:**

| Variant | Target | Hard max |
|---------|--------|----------|
| A | 30–80 | 300 |
| B | 60–100 | 300 |
| C | 30–80 | 200 |

---

## Phase 1 — Variant-specific semantic analysis

### A — Folder

1. Glob (a) non-leaf child subfolders and (b) non-leaf sibling folders. Record CLAUDE.md-less ones as **seed candidates**.
2. **Collapse decision.** If ≤1 subfolder AND ≤1 sibling AND ≤10 ambiguous lines: spawn **one** Sonnet subagent that does both analyses in a single pass. Otherwise: spawn 1.a and 1.b in parallel.
3. **1.a (downward).** Read subfolders to determine scope. Full semantic analysis is allowed. Verify the target's `Function` section against the code — if stale, propose updated wording; if `Function` drifted from `Intent`, report the drift. For each ambiguous line, decide if it applies only within specific subfolders. Report line numbers — do **not** move anything yet — wait for the main agent's go-ahead.
4. **1.b (upward/sibling).** Read sibling CLAUDE.mds and enough sibling content to determine scope. Report any intent/function contention with sibling CLAUDE.mds. For each ambiguous line, decide if it applies to target plus ≥1 sibling. If yes and target is not repo root: **execute** move to parent CLAUDE.md (creating from template if missing). Report moved line numbers. If target is repo root, upward moves are forbidden — treat as keep.
5. **Reconcile.** After 1.b reports, give 1.a the moved line numbers; 1.a applies remaining downward moves to the affected subfolder CLAUDE.md files (creating them via template if missing).

### B — Repo root

1. Glob non-leaf child folders; record CLAUDE.md-less ones as seed candidates.
2. No upward semantic phase (only Phase 0 duplicate check vs. `~/.claude/CLAUDE.md`). Cross-repo rebalancing (multi-repo content → global) happens only under Variant C.
3. Short-circuit if ambiguous bucket empty and no seed candidates → Phase 3.
4. Spawn one Sonnet subagent (downward) with target text, ambiguous line numbers, child folders, seed candidates. Instructions identical to 1.a above, minus the `Intent`/`Function` drift check.
5. Main agent applies recommendations.

### C — Global

1. **Guard:** abort with an error if cwd is not under `~/.claude/`.
2. Find `## Known Repos` section in global CLAUDE.md listing repo paths. If absent, ask user for the list of repo roots to consider and offer to write it into that section for next time.
3. Read each repo's root CLAUDE.md only — do not walk subfolders.
4. Per ambiguous line:
   - **Yes, exactly one repo:** relocate there.
   - **No, applies to multiple repos or is truly cross-project:** keep in global.
   - **Cannot tell from the repo roots:** escalate to one Sonnet subagent.

---

## Phase 2 — Apply changes

1. Delete all Phase 0 deletions (LINT, DOC, upward-duplicate, confirmed GENERIC). Unconfirmed GENERIC candidates stay.
2. Apply downward (A, B) and global→repo (C) relocations. Create missing CLAUDE.mds from template.
3. Apply 1.b upward relocations already executed (A only).
4. Reshape to template section order. Do **not** move content as whole sections — evaluate bullet-by-bullet and sentence-by-sentence. Section headings stay fixed.

## Phase 3 — Seed missing CLAUDE.md files (A and B)

For each seed candidate, spawn a Sonnet subagent in parallel to generate a CLAUDE.md from `templates/CLAUDE-folder.md`, based on reading that folder's code and any immediate child folders.

## Phase 4 — Tighten wording

Each surviving line must be:
1. Imperative and specific. "Use 2-space indentation" — not "format code properly."
2. Reason included when non-obvious. "Use `--bar` (`--foo` causes memory leaks)" — not "never use `--foo`."
3. Emphasis markers (`**YOU MUST**`, `**IMPORTANT**`, `**ALWAYS**`, `**NEVER**`) on critical rules only.

## Phase 5 — Budget and validate

Recount lines. If over hard max: split subtree further or extract to `@path` (A), move to `.claude/rules/` path-scoped files or push down into existing folder CLAUDE.mds (B), push to repo roots — run Variant C again to find content that isn't truly cross-project (C).

Validate each touched file:
- [ ] Within target line band
- [ ] No LINT, GENERIC, DOC items remain
- [ ] No line duplicated in ancestor
- [ ] Every line's scope matches file scope
- [ ] Critical rules have emphasis markers; non-critical do not
- [ ] External references use `@path` or explicit "see `path`" — no embedded documentation
- [ ] Folder files contain only overrides, local stack/commands/quirks, plus `Intent` and `Function` sections

Any failure → return to the producing phase for that file only.

## Phase 6 — Write

Write all modified and created files. No changelog, metadata block, or preface — open directly into first section.

---

## Output

Per file touched: path, action (`created | modified | untouched`), line count before → after, moves (list of `{lines, direction, destination}` for every relocation), seeded subfolder paths (paths of any new CLAUDE.md files created).
