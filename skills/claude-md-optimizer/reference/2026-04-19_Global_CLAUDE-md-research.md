# Research Report: Global CLAUDE.md (`~/.claude/CLAUDE.md`)

**Date:** April 19, 2026
**Scope:** Advice specific to or differently weighted for the global-scope file (`~/.claude/CLAUDE.md`).
**Source:** Distilled from `2026-04-19_CLAUDE-md-research.md`.

---

### Keep the global file inside 30–80 lines; treat 200 as a hard ceiling

**Advice:** Target 30–80 lines. Never exceed 200. The global file is loaded at startup for every session — meaning its token cost and instruction-following load accumulate across every single task you run, regardless of how irrelevant the project.

**Source reliability:** Official Anthropic docs — Anthropic explicitly documents the 200-line adherence boundary at code.claude.com/docs/en/memory, and the 30–80 target is the SKILL.md Variant C budget validated by multiple independent practitioner reports (HumanLayer's production root is under 60 lines).

**Expected benefit:** Medium-to-high. Staying within the target band means instructions in this file are more likely to be followed — IFScale (Jaroslawicz et al., 2025) shows Claude Sonnet 4 holds 98% accuracy at 50 instructions and drops to 77% at 250 on a smooth linear curve. Since the global file cannot be scoped to a task, every instruction it carries is always in the count.

**How to apply to the Global template:** In Phase 0 of the optimization protocol, the Variant C budget is 30–80 lines (hard max 200). Use the line-indexed inventory to tag everything that exceeds the target. In Phase 5, if the file is over budget, any content that is not truly cross-project should be relocated to a repo-root CLAUDE.md — run Variant C to find it.

---

### Only put content here that applies in every project, every session

**Advice:** The global file is the wrong place for anything project-specific, repo-specific, or task-specific. Limit it to personal working principles, communication preferences, default tooling choices, and git conventions that hold regardless of which repo you are in.

**Source reliability:** Official Anthropic docs — Anthropic's memory hierarchy documentation defines the global file as the "user memory" layer, distinct from project memory. The SKILL.md Variant C protocol reinforces this: any line that clearly applies to one specific repo is relocated into that repo's root CLAUDE.md during Phase 1.

**Expected benefit:** High for precision. Project-specific content in the global file loads even when you are working on an unrelated project, consuming attention budget and triggering the `<system-reminder>` filter for content that is genuinely irrelevant to the current task.

**How to apply to the Global template:** In Phase 0, tag any line that names a specific repo, framework, path, or project as `GENERIC` (redundant under auto-load for sessions in other projects) or `RULE` that is actually repo-scoped. In Phase 1 (Variant C), resolve each ambiguous line by asking: does this apply to exactly one specific repo? If yes, relocate it there. The Global template's five sections — Principles, Communication Preferences, Default Tooling, Git Etiquette, Personal Overrides — are the right scope: each maps to a cross-project preference.

---

### The `<system-reminder>` filter de-weights instructions Claude judges irrelevant

**Advice:** Claude Code wraps CLAUDE.md content in a `<system-reminder>` telling Claude the content "may or may not be relevant" and that it should not respond unless the content is "highly relevant to your task." Write instructions that apply universally — do not try to make niche project instructions work harder through capitalization.

**Source reliability:** Quality practitioner + production evidence — HumanLayer reverse-engineered this behavior via a logging proxy (`ANTHROPIC_BASE_URL`). The exact wrapper text has been confirmed by multiple developers reproducing the technique. It is not in Anthropic's public docs.

**Expected benefit:** Medium. This explains the common failure mode where instructions are "ignored even in all caps." The fix is not formatting — it is narrowing content so that what remains is always relevant. For the global file specifically, because it loads with every project, the risk of the filter discarding instructions is higher: instructions about one project's conventions will be filtered in sessions about another.

**How to apply to the Global template:** In Phase 4 (tighten wording), remove the `**IMPORTANT**` / `**NEVER**` / `**YOU MUST**` markers from instructions unless the rule would cause genuine harm if violated. Emphasis markers are reserved for critical rules only — overuse trains Claude to treat the file as noise. Keep instructions to cross-project rules that a universally applicable task would recognize as always relevant.

---

### Instruction-following degrades smoothly with count — and the global file always contributes

**Advice:** Treat every line in the global file as occupying a slot in the total instruction budget for every session. When project-specific content also loads, the global file's lines add on top. Keep the global file as short as possible so it does not erode the available budget for project-specific instructions.

**Source reliability:** Peer-reviewed research — Jaroslawicz et al. (2025), arXiv:2507.11538. Keyword-inclusion benchmark across 20 models at 10–500 instruction densities. Claude Sonnet 4 follows a linear decay: 98% at 50, 94% at 100, 77% at 250, 43% at 500. No hard cliff, but no safe ceiling either — fewer instructions reliably outperforms more.

**Expected benefit:** Medium. The global file's contribution is small in absolute terms if it is under 80 lines, but it is the one part of the instruction budget you can trim without touching any project. A 30-line global file leaves significantly more headroom for the repo-root and folder CLAUDE.mds that contain actionable project knowledge.

**How to apply to the Global template:** In Phase 0, any line tagged `GENERIC` (obvious, restatable, or inferable from context) should be deleted — not relocated. In Phase 5, if the Variant C file exceeds 80 lines, audit the Principles and Communication Preferences sections first: generic advice like "write clean code" or "prefer clarity over cleverness" has no behavioral effect and consumes budget.

---

### Prompt caching makes the token dollar-cost low; the real cost is attention quality

**Advice:** Do not use token cost as a reason to shorten the global file — Claude Code automatically caches CLAUDE.md and charges only 10% on cache reads. Shorten the file to improve instruction-following quality, not to save money.

**Source reliability:** Official Anthropic docs — the 90% cache-read discount is documented at platform.claude.com/docs/en/about-claude/pricing. Cache application to CLAUDE.md is confirmed in Anthropic's memory documentation. Practitioners report 40–50% reduction in daily input-token costs as a directional estimate (single-source anecdote, not a controlled measurement).

**Expected benefit:** Low for cost, high for framing. Understanding that the real penalty is degraded adherence — not dollars — prevents premature optimization for the wrong variable. It also means a slightly-over-target global file will not hurt your bill meaningfully, but it will hurt Claude's ability to follow the rules it contains.

**How to apply to the Global template:** No change to the template structure. When deciding whether to remove a line, apply the instruction-following degradation reasoning above — not a token-count calculation.

---

### Do not include linter rules, project architecture, or specific commands

**Advice:** Omit anything a linter enforces deterministically, any architecture overview, and any project-specific commands. These categories actively harm performance (per ETH Zurich, arXiv:2602.11988) and are misplaced in a cross-project file regardless.

**Source reliability:** Quality practitioner + production evidence, backed by peer-reviewed research — Gloaguen et al. (2026, arXiv:2602.11988) found that LLM-generated context files reduced task success rates by 0.5–2% and that the only content with consistent value was minimal, non-inferable, developer-written specifics. HumanLayer makes the same point from a leverage standpoint: "never send an LLM to do a linter's job."

**Expected benefit:** Medium. For the global file, the risk of including these categories is higher than for project files because there is no project context to make them relevant. Architecture overviews for one repo are noise in every other repo's sessions.

**How to apply to the Global template:** In Phase 0, tag as `LINT` any rule about code style, formatting, or static analysis that a configured linter could enforce. Tag as `DOC` any embedded architecture description or command reference that names a specific project. Both are deleted in Phase 2. The Global template has no Commands or Where-Things-Live sections by design — those belong in the Repo-root template.

---

### `~/.claude/rules/` with `paths:` frontmatter is ignored on Windows

**Advice:** On Windows, do not attempt to use user-level path-scoped rules in `~/.claude/rules/` — they are silently ignored. Use project-level `.claude/rules/` for path-scoped rules, or use hooks in `settings.json` as a deterministic alternative.

**Source reliability:** Official bug report — GitHub issue #21858 in the `anthropics/claude-code` repository. The behavior is confirmed and filed; no workaround is documented at the project level beyond moving to project-scoped rules.

**Expected benefit:** High if you are on Windows and currently relying on user-level rules — the rules are not loading at all, so any expected behavior from them is absent. Discovering this prevents silent failures.

**How to apply to the Global template:** The Global template's Personal Overrides section uses `@~/.claude/personal.md` imports rather than `~/.claude/rules/`. This is the correct pattern on Windows — `@import` syntax works; `paths:`-scoped rules in the user-level rules directory do not. If you have existing `~/.claude/rules/` files, verify they are loading by checking the `InstructionsLoaded` hook or `/context`.

---

### The global file re-injects every session; project files do not survive compaction the same way

**Advice:** Instructions that must persist across long sessions belong in the global file, not in subdirectory CLAUDE.mds. After `/compact`, only the project-root CLAUDE.md re-injects automatically — the global file re-injects fresh regardless. Subdirectory files reload only when Claude next reads a file in that directory.

**Source reliability:** Official Anthropic docs — the compaction recovery behavior is documented in Anthropic's memory documentation and confirmed by Anthropic's engineering blog posts on context management.

**Expected benefit:** Medium for architecture decisions. Understanding the re-injection hierarchy prevents the failure mode where a cross-project rule lives in a nested file and disappears after compaction, causing unexpected behavior in long sessions.

**How to apply to the Global template:** If a rule currently lives in a nested file but must survive compaction, consider whether it is truly cross-project (belongs in the global file) or project-universal (belongs in the project root). The Global template is the right home for rules that must persist regardless of session length and regardless of project.

---

### Prune on a quarterly cadence; watch for these degradation signals

**Advice:** Audit the global file roughly quarterly. Remove any instruction you have not seen Claude actually apply in the past month. Instructions in the global file accumulate silently and erode attention quality across every session.

**Source reliability:** Quality practitioner + production evidence — HumanLayer, multiple practitioner blog posts, and the SKILL.md maintenance guidance all converge on periodic pruning. No controlled study on cadence specifically.

**Expected benefit:** Low per cycle, high compounded. A global file that started at 40 lines and grew unchecked to 150 over a year will be measurably less effective. The IFScale linear decay means every 50 instructions added costs roughly 4–5 percentage points of adherence.

**How to apply to the Global template:** Add instructions only after you have corrected Claude on the same cross-project behavior two or more times in different sessions. Degradation signals for the global file specifically: Claude asks questions whose answers are in the Principles section; git conventions from the Git Etiquette section are ignored; communication preferences are not applied in a new project session. Any of these signals means the global file is overloaded or contains instructions the `<system-reminder>` filter is discarding.

---

### Every instruction competes with the project-specific instructions loaded on top

**Advice:** The global file does not run alone — in every real session, it loads first, then project-root and folder CLAUDE.mds stack on top of it. Every line you add to the global file reduces the effective instruction budget available for the project content that is doing the actual task-specific work.

**Source reliability:** Peer-reviewed research (IFScale linear decay, Jaroslawicz et al. 2025) + Official Anthropic docs (confirmed hierarchy and loading order). The stacking behavior is documented; the attention competition follows directly from IFScale's finding that instruction-following accuracy is a function of total instruction count, not per-file count.

**Expected benefit:** High as a framing principle. Developers who think of the global file as "my personal settings, separate from project instructions" underestimate its cost. A 120-line global file loaded alongside a 90-line repo root means Claude is starting every task near the 200-instruction range where adherence is already measurably degraded.

**How to apply to the Global template:** In Phase 1 of the optimization protocol (Variant C), after enumerating known repos, compare the global file's line count against each repo root's line count. If the combined total exceeds 150 lines for any common project, apply Phase 5 budget enforcement: trim the global file first (cross-project content is less critical per session than task-specific project content), then trim the repo root if needed.

---

## Quick Reference

| Advice | Source reliability | Expected benefit magnitude |
|---|---|---|
| Keep to 30–80 lines; 200 hard max | Official Anthropic docs | High |
| Only cross-project content belongs here | Official Anthropic docs | High |
| `<system-reminder>` filter de-weights irrelevant content | Quality practitioner + production evidence | Medium |
| Instruction-following decays smoothly with count | Peer-reviewed research | Medium |
| Prompt caching: real cost is attention, not dollars | Official Anthropic docs | Low (framing) |
| No linters, architecture, or project-specific commands | Peer-reviewed research + practitioner | Medium |
| `~/.claude/rules/` with `paths:` ignored on Windows | Official bug report | High (if on Windows) |
| Global file re-injects every session; plan compaction accordingly | Official Anthropic docs | Medium |
| Prune quarterly; watch for degradation signals | Quality practitioner + production evidence | Low per cycle |
| Every global line competes with project-specific instructions | Peer-reviewed research + Anthropic docs | High |
