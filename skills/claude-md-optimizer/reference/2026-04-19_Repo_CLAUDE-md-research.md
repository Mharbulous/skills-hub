# Repo-Root CLAUDE.md: Research-Based Optimization Guide

**Scope:** `<repo>/CLAUDE.md` only — the file loaded at startup for every session in the repo.
**Date:** April 19, 2026
**Source:** Distilled from `2026-04-19_CLAUDE-md-research.md`; filters to repo-root-specific advice.

---

### The repo-root file is the highest-leverage file in your hierarchy

**Advice:** Treat every line as applying to every session, every task, and every subagent invoked in this repo. The root file loads at startup unconditionally and is the only CLAUDE.md that re-injects after `/compact` — subdirectory and folder files do not. One bad line costs you tokens and instruction-following capacity on every single task; one missing line cannot be recovered from a subfolder after compaction.

**Source reliability:** Official Anthropic docs — the "only root file survives compaction" behavior is confirmed in Anthropic's memory documentation; the startup loading behavior is documented and CLI-verified.

**Expected benefit:** High. This framing changes how you evaluate every content decision. A line worth keeping in a subfolder CLAUDE.md might not justify root inclusion; a rule that must survive session compaction cannot live anywhere else.

**How to apply to the Repo template:** Before adding any line, ask: would a new senior engineer need this in *every* session, not just in sessions that touch a specific subfolder? If no, move the content to a subfolder CLAUDE.md or `.claude/rules/`. In Phase 0 of the optimization skill, this maps to detecting lines tagged `obviously-downward` — lines that name a specific subpath and should be relocated out of root.

---

### Keep the file under 200 lines; aim for 60–100

**Advice:** Anthropic's own documentation states that files over 200 lines consume more context and may reduce adherence. The practical target for a repo-root file is 60–100 lines. Under 200 is the soft ceiling; 300 is the hard maximum beyond which the optimization skill will push content down. HumanLayer's production CLAUDE.md is under 60 lines — this is evidence that very short files work, not a mandate.

**Source reliability:** Official Anthropic docs for the 200-line soft ceiling (explicitly stated in Anthropic's memory docs). The 60-line HumanLayer figure is a quality practitioner anecdote — an existence proof that short works, not a universal target.

**Expected benefit:** Medium-High. The real cost of a long file is not dollars (prompt caching gives a 90% discount on re-read tokens) — it is instruction-following degradation. IFScale (Jaroslawicz et al., arXiv:2507.11538) shows Claude Sonnet 4 holds 98% accuracy at ~50 instructions, dropping to 94% at 100, 77% at 250, and 43% at 500. The decay is smooth and linear — there is no magic cliff at 150-200, but every added line competes with every other line for attention.

**How to apply to the Repo template:** In Phase 5 of the optimization skill (Variant B budget check), a repo-root file that exceeds its 300-line hard max must push content to `.claude/rules/` path-scoped files or into existing subfolder CLAUDE.mds. Before reaching that stage, Phase 0 tagging removes `LINT` lines (style rules a linter enforces), `GENERIC` lines (inferable from the auto-loaded bundle), and `DOC` lines (embedded documentation replaced with a one-line `@reference`).

---

### Never ship `/init` output unedited — LLM-generated context files actively hurt performance

**Advice:** Do not use `/init` output as your CLAUDE.md. Delete README restatements, architecture prose, and any content a model could infer from reading the code. Write the file by hand, line by line, keeping only what the model would otherwise guess wrong.

**Source reliability:** Peer-reviewed research — Gloaguen et al. (ETH Zurich, arXiv:2602.11988) tested LLM-generated vs. human-written vs. no context files across four agents on 138 tasks. LLM-generated files reduced task success by 0.5–2% in every single model × benchmark cell and raised inference costs by over 20%. Human-written files produced only a marginal ~4% improvement. This is the strongest empirical evidence available and directly implicates `/init` as the mechanism that generates exactly these harmful files.

**Expected benefit:** High for teams that currently ship `/init` output. The ETH Zurich result is striking: a file intended to help actively made every tested model worse. The anti-pattern is not the file — it is the generation method. Human-written files still help, marginally.

**How to apply to the Repo template:** Treat `/init` output as a draft inventory only. For each line it generates, apply Phase 0 tagging from the optimization skill: any line that restates what's in `README.md`, `package.json`, or `tsconfig.json` is `GENERIC` (redundant under auto-load) or `DOC` (embedded documentation). Architectural prose that a competent engineer would derive from the file tree is `GENERIC`. What survives should be `CMD` (commands with non-default flags), `RULE` (project-specific constraints), `QUIRK` (empirical gotchas the model would hit and fix wrong), and `STRUCT` (non-obvious tech stack choices). Reference the template's Comments section — only content that meets the "would otherwise guess wrong" bar belongs there.

---

### What belongs in the repo-root file (and what does not)

**Advice:** Include: commands with non-default flags or invocation specifics, stack choices that differ from defaults, non-obvious project rules, and empirical gotchas. Exclude: anything a linter enforces, generic coding advice, architecture overviews, README restatements, content that only applies to one subpath.

**Source reliability:** Official Anthropic docs (code.claude.com/docs/en/memory, best-practices) for the exclusion list, corroborated by ETH Zurich's empirical finding that the specific content type that helped was minimal requirements and non-inferable specifics.

**Expected benefit:** Medium. The benefit is precision, not just length reduction. A shorter file full of generic advice is worse than a longer file of sharp, non-inferable specifics.

**How to apply to the Repo template:** Use the template sections as a filter:
- **Commands:** include only commands Claude would otherwise guess wrong — wrong flags, wrong order, wrong tool (e.g., "use `pnpm`, not `npm`"). If the command is `npm start` with no gotchas, omit it.
- **Tech Stack:** non-default version pins, database or framework choices not obvious from `package.json` imports, runtime constraints.
- **Code Conventions:** the template's comment "Only conventions NOT enforced by linters/formatters" is exactly right. Anything ESLint/Prettier enforces goes in those configs and a hook — Phase 0 tags these as `LINT` and deletes them.
- **Project-Specific Quirks:** this is where ETH Zurich-style "firebase v9 getRedirectResult() returns null (not object with null user) when no redirect occurred" gotchas live. Non-obvious, empirical, high-impact.
- **Project Structure:** one-line directory purposes only. Not an architecture narrative.

---

### The `<system-reminder>` filter: Claude actively ignores what it judges irrelevant

**Advice:** Claude Code wraps CLAUDE.md content in a `<system-reminder>` that explicitly tells Claude the content "may or may not be relevant" and to ignore it unless "highly relevant to your task." Write instructions that are universally applicable in every session — not conditional or task-specific — so they survive this filter.

**Source reliability:** Quality practitioner + production evidence — HumanLayer derived this by running a logging proxy against Claude Code's actual HTTP traffic. The wrapper text is documented in their production analysis. Not confirmed by Anthropic's own documentation but independently verifiable.

**Expected benefit:** Medium. This explains the common complaint that "Claude ignores my CLAUDE.md instructions even in caps." The cure is not emphasis markers — it is writing instructions that apply to the task at hand. Broad, always-applicable rules (commands, stack facts, absolute constraints) pass the filter; conditional or narrow rules fail it.

**How to apply to the Repo template:** In Phase 0 of the optimization skill, the `GENERIC` definition tests whether content would be redundant given the auto-loaded bundle. The `<system-reminder>` adds a second test: would Claude judge this relevant when executing a typical task in this repo? If a line only matters for one type of task (e.g., migration-specific rules), it belongs in a subfolder CLAUDE.md or a `.claude/rules/` file with `globs:` scoping, not at root. Lines at root should pass both tests.

---

### Use emphasis markers sparingly; they dilute each other

**Advice:** Reserve `**YOU MUST**`, `**IMPORTANT**`, `**NEVER**`, and `**ALWAYS**` for rules that would cause real harm if violated. Using all four for routine guidance trains the model to de-weight every marker equally.

**Source reliability:** Quality practitioner + production evidence (HumanLayer) combined with peer-reviewed support from IFScale (arXiv:2507.11538) — as instruction density increases, adherence to all instructions decreases linearly. Emphasis markers are instructions competing in the same pool.

**Expected benefit:** Low-Medium. The effect is subtle but real in high-instruction-density files. In a lean file, a single `**NEVER**` on a genuinely critical rule stands out; in a file full of `**YOU MUST**` on every bullet, none stands out.

**How to apply to the Repo template:** The template's **Critical Rules** section populates four emphatic bullets by default. In practice, a typical repo has zero to two rules that genuinely warrant this treatment (e.g., "NEVER commit directly to `main`" or "NEVER touch `src/generated/`"). The other slots should either be deleted or written as plain bullets without emphasis markers. In Phase 4 of the optimization skill (tighten wording), the instruction is explicit: "Emphasis markers on critical rules only — overuse dilutes them."

---

### Progressive disclosure: push subfolder-specific content down, not up

**Advice:** At the repo root, keep only universals — content every session needs regardless of which part of the codebase is being touched. Move subpath-specific rules to `.claude/rules/` with `globs:` scoping, and move subtree-specific context to subfolder CLAUDE.mds. In a monorepo, root holds only cross-package universals (monorepo tooling, shared conventions); each package gets its own CLAUDE.md.

**Source reliability:** Official Anthropic docs for the hierarchy mechanics (root + subdirectory + .claude/rules/ loading behavior). Progressive disclosure as a principle is also endorsed by Anthropic's engineering blog ("Effective context engineering for AI agents," Sep 2025).

**Expected benefit:** Medium. The main benefit is keeping root within target line counts without losing information. Subfolder CLAUDE.mds lazy-load when Claude reads files in those directories. The tradeoff: they do not reload after `/compact`, so truly critical information must stay at root.

**How to apply to the Repo template:** In Phase 1 of the optimization skill (Variant B — Repo root), the skill enumerates immediate child folders and identifies lines that "explicitly name a single subpath" as `obviously-downward` — these are relocated without semantic analysis. The **References** section of the template (`@docs/architecture.md`, `@docs/AUTH.md`) is the correct pattern for deep documentation: pointer at root, content loaded on demand.

---

### `.claude/rules/` for path-scoped rules — but verify it actually loads

**Advice:** Use `.claude/rules/` with `globs:` frontmatter for rules that should activate only when Claude reads matching files (e.g., TypeScript rules for `src/`, SQL conventions for `migrations/`). Use `globs:` not `paths:` — the documented `paths:` frontmatter has confirmed YAML parsing bugs. After writing a rules file, verify it loads using the `InstructionsLoaded` hook.

**Source reliability:** Official Anthropic docs for the feature itself and its intended YAML format. The specific bugs are GitHub issues on the `anthropics/claude-code` repository, which is quality practitioner evidence with reproducible reports.

**Expected benefit:** Medium when working correctly. The feature reduces root file length by moving path-specific rules out without losing them. But there are three bugs to know before relying on it:
1. `paths:` frontmatter (the documented key) fails in several configurations; `globs:` works more reliably (issue #17204).
2. Path-scoped rules do not fire on Write tool use — only on Read (issue #23478). Rules meant to enforce conventions on newly created files require a hook workaround, not a `.claude/rules/` file.
3. User-level `~/.claude/rules/` with `paths:` frontmatter is ignored on Windows (issue #21858). Use project-level `.claude/rules/` instead.

**How to apply to the Repo template:** In Phase 5 (Variant B budget check), when the root file exceeds its hard max, content is pushed to `.claude/rules/` path-scoped files. Before treating this as a resolution, verify the rule fires: add an `InstructionsLoaded` hook and confirm the rule name appears in the log when Claude reads a matching file. If using Windows, use project-level `.claude/rules/` only.

---

### Skills are unreliable as passive triggers — inline critical knowledge or invoke explicitly

**Advice:** Do not rely on Skills to self-invoke when their content is needed. If knowledge is critical to task correctness in every session, embed it in the repo-root CLAUDE.md directly (compressed if large). If a Skill is optional, explicitly invoke it via slash command rather than hoping the model reaches for it.

**Source reliability:** Quality practitioner + production evidence — Vercel's hardened eval suite (Jan 2026) found Skills were not invoked in 56% of test cases even when they were the correct tool for the task. Explicit invocation instructions helped but were fragile to wording changes. Vercel's methodology is reasonable but not blinded — they have a commercial interest in AGENTS.md adoption.

**Expected benefit:** Medium for teams currently relying on Skills for correctness-critical knowledge. The 56% non-invocation rate is specific to Vercel's Next.js eval — other domains may differ, but passive invocation is generally unreliable across models.

**How to apply to the Repo template:** For framework-specific APIs outside training data (the Vercel case), consider the compressed-index pattern: embed a pipe-delimited index of doc file paths in the **References** section, not the full content. This is equivalent to Vercel's approach of pointing the agent to where knowledge lives rather than forcing it to invoke a Skill. The optimization skill's `REF` tag (`@path` or "see …" pointer) is the correct form. Full content embedded inline gets tagged `DOC` and replaced with a reference.

---

### Prompt caching changes the cost calculus — but not the instruction-following math

**Advice:** Prompt caching (90% discount on re-read tokens, applied automatically by Claude Code to CLAUDE.md) means the dollar cost of a slightly-too-long repo-root file is much lower than it appears. The real cost of length is instruction-following degradation (IFScale linear decay), not API dollars. Do not use caching as permission to bloat.

**Source reliability:** Official Anthropic docs for caching pricing and Claude Code's automatic application. The IFScale decay curve is peer-reviewed research (arXiv:2507.11538).

**Expected benefit:** Low as standalone advice; important as a correction. Teams who calculated that their 250-line CLAUDE.md costs too much in tokens can relax the cost concern — but should still trim it because adherence at 250 instructions is ~77% (vs. 98% at 50).

**How to apply to the Repo template:** When doing a Phase 5 budget check, the justification for pushing content to subfolder files should be "instruction-following degradation at current line count" not "token cost." The caching discount applies to the root file only after the first turn (cache TTL is 5 minutes), so very-long files still have a first-turn cost.

---

### Maintenance: add rarely, prune quarterly, watch for degradation signals

**Advice:** Add a line to the repo-root CLAUDE.md only when you have corrected Claude on the same issue in two or more separate sessions. Prune quarterly — or whenever auto-memory looks cluttered. Delete lines that Claude ignored anyway; their token cost is real and their effect is zero.

**Source reliability:** Quality practitioner + production evidence — HumanLayer and the optimization skill both give this two-corrections threshold. Not from systematic research but consistent across independent practitioner sources.

**Expected benefit:** Low per-cycle, High over time. A CLAUDE.md that was accurate at project start drifts as the project evolves. Stale lines fail the optimization skill's `GENERIC` definition ("facts that contradict other auto-loaded content") and should be removed.

**How to apply to the Repo template:** Degradation signals to watch for:
- Claude asks questions already answered in CLAUDE.md.
- Instructions ignored despite emphasis markers.
- Quality drops late in sessions (last 20% of context window).
- Repeated corrections for the same class of mistake after a `/compact`.

The last signal is the repo-root-specific one: if a rule needs to survive compaction but isn't being followed after `/compact`, it may be there in text but getting filtered by the `<system-reminder>`. Fix: rewrite it as a universally applicable instruction, or move it to a hook in `settings.json` for deterministic enforcement.

---

## Quick Reference

| Advice | Source reliability | Expected benefit magnitude |
|---|---|---|
| Repo-root is highest-leverage file (survives compaction) | Official Anthropic docs | High |
| Keep under 200 lines; target 60–100 | Official Anthropic docs | Medium-High |
| Never ship `/init` output unedited | Peer-reviewed research | High |
| What belongs here vs. what to exclude | Official Anthropic docs | Medium |
| `<system-reminder>` filter: write universal instructions | Quality practitioner + production evidence | Medium |
| Emphasis markers sparingly (dilute each other) | Quality practitioner + production evidence | Low-Medium |
| Progressive disclosure: push subfolder content down | Official Anthropic docs | Medium |
| `.claude/rules/` for path-scoped rules — verify it loads | Official Anthropic docs (bugs: practitioner evidence) | Medium |
| Skills passive invocation unreliable (56%) — inline or invoke explicitly | Quality practitioner + production evidence | Medium |
| Prompt caching lowers dollar cost but not adherence degradation | Official Anthropic docs | Low (corrective) |
| Add rarely, prune quarterly, watch for degradation signals | Quality practitioner + production evidence | Low per-cycle, High over time |
