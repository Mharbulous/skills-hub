# Folder-Level CLAUDE.md: Research Report

**Date:** April 19, 2026
**Scope:** `<repo>/<subdir>/CLAUDE.md` only — advice specific to or differently relevant for the folder/subdirectory variant
**Source:** `2026-04-19_CLAUDE-md-research.md` (research synthesis with sourcing), filtered and adapted for the folder use case

---

### Critical instructions belong in the root, not here — compaction vulnerability

**Advice:** After a `/compact`, only the project-root CLAUDE.md re-injects into context. Folder-level CLAUDE.md files reload only when Claude next reads a file in that subtree. Any instruction that must survive session compaction — hard constraints, shared conventions, security boundaries — must live in the root file. Use this folder file only for information whose absence between compaction and re-trigger is acceptable.

**Source reliability:** Official Anthropic docs — confirmed in Anthropic's Claude Code memory documentation, which explicitly states subdirectory CLAUDE.md files do not re-inject after `/compact`.

**Expected benefit:** High. Without this awareness, a developer may place a genuinely critical rule (e.g., "never commit generated files") in a folder CLAUDE.md and assume it persists across compaction. It does not. Getting this right prevents silent instruction loss.

**How to apply to the Folder template:** Before writing any rule into the `Local Overrides` or `Quirks & Warnings` sections, ask: if this instruction disappeared mid-session after compaction, would that cause a meaningful problem? If yes, it belongs in the root CLAUDE.md instead. The `Local Overrides` section is appropriate only for rules that are subtree-specific AND tolerant of lazy-reload gaps.

---

### Lazy-load behavior: this file loads only on subtree file access

**Advice:** This file does not load at startup. It enters context only when Claude reads or @-mentions a file inside this subtree. This has two practical implications: (1) the file costs zero tokens on sessions that never touch this subtree; (2) the content is completely absent for any work Claude does at the repo level or in other subtrees.

**Source reliability:** Official Anthropic docs — Claude Code memory documentation confirms lazy loading of subdirectory CLAUDE.md files.

**Expected benefit:** Medium. Understanding the trigger changes where you place content. It justifies keeping this file moderately more verbose than the global file — the cost is only paid when the file is actually needed. It also warns against placing content here that needs to be in scope for repo-level tasks.

**How to apply to the Folder template:** The lazy-load behavior is why this template targets 30–80 lines rather than the global file's similar budget — the intent is the same (stay minimal), but the startup-cost argument that makes every global line expensive is weaker here. The "Instructions that do NOT belong here" warning in SKILL.md Phase 5's validation checklist applies directly: folder files must contain only overrides, local stack differences, local commands, and local quirks. Do not use the headroom as license to add architecture narratives.

---

### Never duplicate content from the root CLAUDE.md

**Advice:** The root CLAUDE.md is already loaded into context when this file loads. Every line that restates root content burns extra tokens and introduces a drift risk — if the root instruction changes, the stale copy in the folder file is now contradictory. Write only what differs for this subtree.

**Source reliability:** Quality practitioner + production evidence — stated as anti-pattern #6 in the research synthesis (HumanLayer; Anthropic's own documentation on subdirectory scope), corroborated by the IFScale instruction-density findings (Jaroslawicz et al., 2025, arXiv:2507.11538) showing each additional instruction degrades adherence to all others.

**Expected benefit:** High. Duplicate content wastes tokens, creates silent drift, and increases instruction density — each of which has documented costs. Eliminating upward duplicates is the highest-leverage single action when optimizing a folder CLAUDE.md.

**How to apply to the Folder template:** In Phase 0 of the optimization protocol, step 3 marks any `keep` line that appears verbatim or near-verbatim in any ancestor CLAUDE.md as `upward-duplicate → delete`. This check runs across the full ancestor chain. In the `Local Overrides` section of the template, only include rules that differ from the root — if the rule is the same as what the root already says, delete it. The `Local Stack` section should only list components that differ from the root's stack description; if the folder uses the same framework, that section can be omitted entirely.

---

### Phase 0 upward-duplicate detection: how it works and why it matters for folder files

**Advice:** The optimization protocol reads all ancestor CLAUDE.md files and tags any line in the folder file that is verbatim or near-verbatim present in an ancestor as `upward-duplicate`. These are deleted unconditionally — no semantic analysis needed. For folder files this scan is especially productive because folder files are frequently seeded from root content that was never pruned.

**Source reliability:** Quality practitioner + production evidence — this is the SKILL.md protocol's own defined behavior (Phase 0, step 3), derived from the duplication anti-pattern documented across Anthropic docs and HumanLayer.

**Expected benefit:** Medium. For freshly created folder files seeded from a template or from `/init` output, upward-duplicate lines may constitute 20–50% of the initial content. Automated detection makes this cheap to fix.

**How to apply to the Folder template:** When running the optimizer on a folder CLAUDE.md, Phase 0 step 3 handles this automatically — it reads the root CLAUDE.md (and any intermediate CLAUDE.md files) and tags matches. When writing a folder CLAUDE.md by hand, manually scan each section against the root before saving. Pay particular attention to `Local Stack` (often identical to root stack), `Key Files` (often restates root "Where things live"), and generic `Quirks & Warnings` that apply project-wide. The Phase 5 validation checklist item "No line is duplicated in an ancestor CLAUDE.md" is the explicit exit gate.

---

### Override semantics: use this file to state exceptions, not repetitions

**Advice:** More specific rules in a folder CLAUDE.md override the root for files in this subtree. This means you should actively use this file to record exceptions — places where this subtree does something differently. That is exactly the right content here. A rule that merely restates the root is waste; a rule that contradicts the root for this subtree is the core purpose of the file.

**Source reliability:** Official Anthropic docs — confirmed in Claude Code documentation: "more specific rules override less specific rules." The hierarchy of loading levels is documented in the memory hierarchy.

**Expected benefit:** Medium. When used correctly, override semantics let you apply different conventions (e.g., legacy JavaScript in a TypeScript codebase, CommonJS in an ESM codebase) without polluting the root with conditionals. When misused (restating rather than overriding), this becomes the duplication anti-pattern.

**How to apply to the Folder template:** The `Local Overrides` section is explicitly for this purpose. Its template comment reads: "Rules here override the root CLAUDE.md for files in this subtree only." Each bullet in `Local Overrides` should be either (a) an explicit exception to a root rule ("This folder uses CommonJS `require`/`module.exports` — root ESM convention does not apply here"), or (b) a rule with no counterpart at the root (subtree-unique). If you can't articulate which root rule it overrides or which subtree quirk it captures, it should not be in `Local Overrides`.

---

### Size limits: 30–80 lines target, informed by stacking on top of what's already loaded

**Advice:** Target 30–80 lines. The folder file stacks on top of the root CLAUDE.md, which is already in context — so the effective instruction load is root + folder. Keep the folder file short enough that the combined load stays well under 200 lines total. If the folder file alone approaches 80 lines, review it for duplication or content that belongs at the root.

**Source reliability:** Quality practitioner + production evidence — the 30–80 line target is the SKILL.md template's own budget (Variant A). The "under 200 lines" root ceiling comes from Anthropic's own documentation. The IFScale paper (Jaroslawicz et al., 2025, arXiv:2507.11538) provides the decay curve: Claude Sonnet 4 at 94% adherence with ~100 instructions, 77% at 250 — the root+folder combined total is what matters.

**Expected benefit:** Medium. Staying within budget prevents the instruction-density degradation documented in IFScale. The folder file's lazy-load means it won't inflate the startup cost, but once loaded, every line it adds to the combined context counts against adherence.

**How to apply to the Folder template:** Phase 5 of the optimization protocol validates against the Variant A budget (30–80 lines target, 300 hard max). If the file exceeds 80 lines, the prescribed actions are: split the subtree further (create CLAUDE.md files in subfolders) or extract long-form content to a sibling `.md` file and replace with an `@path` reference in the `References` section. If the file exceeds 300 lines, Phase 5 requires returning to an earlier phase before the file can be written.

---

### When to create a folder CLAUDE.md vs. putting content in the root

**Advice:** Create a folder CLAUDE.md when the subtree has genuinely distinct characteristics: a different tech stack, different conventions, a different team or owner, or quirks that apply only within this subtree. Do not create one just because the folder is large — a large folder with the same conventions as the rest of the repo needs no folder-level file. Content that is project-wide belongs in the root regardless of which folder prompted you to write it.

**Source reliability:** Quality practitioner + production evidence — Anthropic's own monorepo guidance, HumanLayer, and the ETH Zurich paper (Gloaguen et al., 2026, arXiv:2602.11988) converge on the minimum-viable-context-file principle: only create the file if it carries information not already inferable from the code or the root.

**Expected benefit:** Medium. Unnecessary folder CLAUDE.md files add token cost and maintenance burden with no benefit. Applying this judgment correctly means folder files are created only when they carry load-bearing content.

**How to apply to the Folder template:** In Phase 1 Variant A, the protocol identifies "seed candidates" — non-leaf subfolders that lack a CLAUDE.md. Phase 3 creates them from the template only for non-leaf folders. Before seeding, subagent 1.a reads the subfolder code to determine whether it has distinct scope; if the subfolder is just a code organization convention with no stack differences or quirk-level gotchas, the seed may produce an empty or near-empty file — which is itself fine, but signals the folder may not need one at all. The `Intent` and `Function` sections in the template exist partly to force this question: if you cannot articulate an intent that differs from the root, the file probably should not exist.

---

### Intent and Function sections: drift detection and optimizer handshake

**Advice:** The `Intent` section records the original purpose of this folder when it was created. The `Function` section records what it actually does. These are not documentation for Claude to follow — they are inputs for the optimizer. When they diverge, it signals that the folder's role has drifted from its design, which affects whether the rest of the file's rules are still accurate.

**Source reliability:** Quality practitioner + production evidence — these sections are specific to the `CLAUDE-folder.md` template and the SKILL.md Variant A protocol. They are grounded in the protocol's own design (Phase 1, subagent 1.a explicitly verifies `Function` against the code and reports drift from `Intent`), not in the academic research.

**Expected benefit:** Low to Medium. In a stable codebase, these sections rarely change and add little value per session. Their value is realized during optimization runs: a drifted `Function` section is a reliable signal that the folder's content needs review. The benefit is asymmetric — no upside on average, but catches important cases when they occur.

**How to apply to the Folder template:** Write `Intent` once when creating the file and treat it as immutable unless the folder's fundamental purpose is redesigned. Update `Function` whenever the folder's actual role shifts. During optimization runs, Phase 1 Variant A subagent 1.a reads the code to verify `Function` and reports drift from `Intent` — this is an automated check. Keep both sections to 1–2 sentences; these are not architecture docs.

---

### The `<system-reminder>` filter applies to folder files too — every line must be universally applicable to the subtree

**Advice:** Claude Code wraps CLAUDE.md content in a `<system-reminder>` that explicitly tells Claude the content "may or may not be relevant" and to only respond if "highly relevant." Claude actively filters lines it judges irrelevant to the current task. For folder files, this means every line must apply to essentially any task involving this subtree — not just the specific file Claude is editing at a given moment. A rule that applies only to one specific file in the subtree will be filtered when Claude is working on any other file in the subtree.

**Source reliability:** Quality practitioner + production evidence — HumanLayer reverse-engineered this via `ANTHROPIC_BASE_URL` logging proxy. The mechanism is confirmed indirectly by Anthropic's `<system-reminder>` framing visible in context logs. Not officially documented.

**Expected benefit:** Medium. Understanding this filter changes how you write rules. Broad, applicable-to-the-subtree rules survive the filter; narrow, file-specific rules do not. This means file-specific rules should live in `.claude/rules/` with a `globs:` path scoped to that file, or deeper in a subfolder's own CLAUDE.md — not in this folder file.

**How to apply to the Folder template:** Apply this heuristic when writing content in any section: "Will this instruction be relevant regardless of which file in this subtree Claude is editing?" If no — if the instruction only applies to, say, `src/auth/middleware.ts` — it should not be in a folder CLAUDE.md covering all of `src/auth/`. Move it to a deeper `src/auth/middleware/CLAUDE.md` or a `.claude/rules/` scoped rule. During Phase 4 (wording tightening), instructions that are too narrow for the folder's scope are a signal to either push down or scope explicitly.

---

### `@path` references for deeper docs within the subtree

**Advice:** Use `@path` references in the `References` section to point to deeper documentation, README files, or design docs within the subtree. Do not embed their content — embed an index entry that lets Claude read the file on demand. This keeps the folder file within budget while still making the documentation discoverable.

**Source reliability:** Official Anthropic docs — `@path` syntax is confirmed in official Claude Code memory documentation. The "embed index not content" principle comes from Vercel's compressed-index pattern (Jan 2026) and Anthropic's "just-in-time context" framing (Sep 2025 engineering blog).

**Expected benefit:** Medium. Replacing embedded content with `@path` references can reduce a folder file's line count substantially without losing the ability to access the content. The file is only read when Claude needs it, avoiding cost on every session.

**How to apply to the Folder template:** The `References` section of the template is explicitly for this purpose. Replace any embedded architecture overview, API reference, or multi-paragraph explanation with a single line like `@./docs/design.md` or `@./README.md`. The Phase 0 tag `DOC` (embedded documentation) marks these for deletion and replacement with a `@reference` pointer. Phase 5's validation checklist includes: "External references use `@path` or explicit 'see `path`' — no embedded documentation."

---

### Content that belongs here and content that does not

**Advice:** Content that belongs here: local stack differences (different framework, different test runner), local commands (filter-scoped monorepo commands), local overrides (exceptions to root rules), key file list for this subtree, and non-obvious gotchas specific to this subtree. Content that does not belong here: anything already in the root CLAUDE.md, generic coding advice, architecture overviews, content that applies to the whole project.

**Source reliability:** Quality practitioner + production evidence — Anthropic's folder-file scope guidance, HumanLayer's anti-pattern documentation, and ETH Zurich (Gloaguen et al., 2026, arXiv:2602.11988) all converge on "minimal, non-inferable, non-redundant" as the content standard.

**Expected benefit:** High for initial file creation; Medium for ongoing maintenance. The most common failure mode when creating a folder CLAUDE.md is filling it with project-wide content. Applying this filter at creation time prevents the most expensive class of folder-file waste.

**How to apply to the Folder template:** The template sections map directly to this content taxonomy: `Local Overrides` = exceptions to root rules; `Local Stack` = stack differences; `Local Commands` = subtree-specific commands; `Quirks & Warnings` = gotchas; `Key Files` = local navigation; `References` = `@path` pointers. Sections without content should be omitted entirely — an empty `Local Stack` section costs lines and signals a file that was created from the template without thought. The Phase 5 validation checklist item "Folder files contain only overrides, local stack differences, local commands, and local quirks — plus the `Intent` and `Function` sections" is the explicit gate.

---

### Monorepo pattern: each package gets its own folder CLAUDE.md with only package-specific content

**Advice:** In a monorepo, each package with a meaningfully different stack, team, or convention set should have its own `packages/<name>/CLAUDE.md`. Each of these files covers only the differences specific to that package. The root CLAUDE.md covers only what is universal across all packages — monorepo tooling, workspace conventions, shared CI setup. Cross-cutting rules that apply to multiple-but-not-all packages belong in `.claude/rules/` with `globs:` scoped to those packages, not duplicated across package files.

**Source reliability:** Quality practitioner + production evidence — Anthropic's own monorepo guidance and the research synthesis section 2 ("Monorepo pattern"). The pattern is widely confirmed in practitioner sources (alexop.dev, HumanLayer).

**Expected benefit:** Medium. Correctly partitioned monorepo CLAUDE.md files mean a session working only on `packages/frontend/` never pays the token cost of `packages/backend/`'s stack context. The cost savings scale with the number of packages and the size of each package file.

**How to apply to the Folder template:** Each package CLAUDE.md is a Variant A file using `CLAUDE-folder.md` as its template. In Phase 1 Variant A, subagent 1.b specifically checks whether ambiguous lines in one package file also apply to sibling packages — if they do, those lines are moved up to the root, not duplicated. The monorepo structure does not require that every package have a CLAUDE.md; Phase 3 seeds only non-leaf folders that have distinct enough scope to warrant one. The `Intent` section of each package file should make the package's distinct purpose explicit — if you can't state a distinct purpose, the package may not need its own file.

---

### Phase 1 Variant A upward/downward rebalancing for folder files

**Advice:** The Variant A protocol runs two subagents in parallel: one (1.a) evaluates whether ambiguous lines should move down into subfolder CLAUDE.md files; one (1.b) evaluates whether ambiguous lines should move up to the parent CLAUDE.md because they apply to sibling folders too. Lines that belong at the parent level are moved immediately by subagent 1.b before 1.a gets the final set. Only after 1.b reports does 1.a complete its downward moves, ensuring lines already promoted upward are not also pushed down.

**Source reliability:** Quality practitioner + production evidence — this is the SKILL.md protocol's defined Phase 1 Variant A behavior. The design rationale (avoid double-moving content) is observable in the protocol's explicit sequencing instruction.

**Expected benefit:** Medium. The rebalancing step is where content that has drifted to the wrong level of the hierarchy gets corrected — common after months of organic growth. The expected outcome is a folder file that contains only lines narrower than the root and broader than any single subfolder.

**How to apply to the Folder template:** This phase runs automatically during an optimization pass. When creating or reviewing a folder CLAUDE.md by hand, apply the same logic manually: for each line, ask whether it applies to sibling folders too (if yes, move to parent) and whether it applies only to one specific subfolder (if yes, move to subfolder or `.claude/rules/` scoped rule). The `Local Overrides` section is the most common source of upward-drift: override rules that apply across multiple subtrees were probably placed here rather than at the root, and should be promoted.

---

## Quick Reference

| Advice | Source reliability | Expected benefit magnitude |
|---|---|---|
| Critical instructions belong in root — compaction vulnerability | Official Anthropic docs | High |
| Lazy-load behavior: file loads only on subtree file access | Official Anthropic docs | Medium |
| Never duplicate content from the root CLAUDE.md | Quality practitioner + production evidence | High |
| Phase 0 upward-duplicate detection | Quality practitioner + production evidence | Medium |
| Override semantics: use this file to state exceptions | Official Anthropic docs | Medium |
| Size limits: 30–80 lines, stacking on loaded root | Quality practitioner + production evidence | Medium |
| When to create a folder CLAUDE.md vs. root content | Quality practitioner + production evidence | Medium |
| Intent and Function sections: drift detection | Quality practitioner + production evidence | Low to Medium |
| `<system-reminder>` filter — every line must apply across the subtree | Quality practitioner + production evidence | Medium |
| `@path` references for deeper docs | Official Anthropic docs | Medium |
| Content that belongs here vs. does not | Quality practitioner + production evidence | High |
| Monorepo pattern: one CLAUDE.md per distinct package | Quality practitioner + production evidence | Medium |
| Phase 1 Variant A upward/downward rebalancing | Quality practitioner + production evidence | Medium |
