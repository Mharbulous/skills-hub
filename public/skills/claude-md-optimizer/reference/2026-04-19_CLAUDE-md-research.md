# CLAUDE.md Optimization: Updated Research Report

**Date:** April 19, 2026
**Supersedes:** `consolidated-research.md` (original, undated but c. Feb 2026)
**Scope:** Validates, caveats, and extends the original memo with academic-first sourcing. All quantitative claims have been either confirmed, revised, or flagged as anecdotal.

---

## Executive summary of what changed

1. **Major new finding that inverts some original guidance.** A peer-style empirical study from ETH Zurich (Gloaguen et al., Feb 2026, arXiv:2602.11988) tested coding agents on 138 real-world tasks with and without AGENTS.md/CLAUDE.md files and found that **LLM-generated context files reduced task success rates by 0.5–2% and raised inference costs by over 20%**, while human-written files produced only a **marginal ~4% improvement**. This is the first rigorous empirical evidence we have, and it significantly tempers the "just write a CLAUDE.md" advice in the original memo. The `/init` command in Claude Code is the exact mechanism the paper warns against.

2. **A contradictory-looking result that is actually compatible.** A separate study (arXiv:2601.20404, Jan 2026) across 10 repos and 124 PRs found AGENTS.md was associated with a **28.64% lower median runtime and 16.58% reduced output tokens**. The metrics differ — Gloaguen measures task success rate and *input* cost; 2601.20404 measures wall-clock and *output* tokens. Read together: context files may shorten paths when tasks succeed but make success itself less likely, and both studies are consistent with the conclusion that *minimal, human-written, non-inferable* context is what actually helps.

3. **The "150–200 instructions" cap in the original memo is not what the cited paper actually shows.** The IFScale paper (Jaroslawicz et al., 2025, arXiv:2507.11538) has been examined. Claude Sonnet 4 holds ~98% accuracy at 50 instructions, ~94% at 100, ~77% at 250, and ~43% at 500. The "150–200" figure in HumanLayer's post refers to the primacy-effect inflection point, not a performance cliff. Performance degrades smoothly in Claude's case (linear decay pattern), with no hard wall at 150.

4. **A critical context-injection detail the original memo missed.** HumanLayer demonstrated via a logging proxy that Claude Code wraps CLAUDE.md content in a `<system-reminder>` that tells Claude the content "may or may not be relevant" and not to respond unless "highly relevant." This means **Claude actively decides to ignore CLAUDE.md content it judges irrelevant** — the memo's "every line is loaded into context" framing is technically correct but practically understates how much gets filtered out at inference time.

5. **Vercel's evaluation (Jan 2026) cuts the other way on Skills.** In their Next.js-specific eval, Skills were not invoked in 56% of test cases, and embedding a compressed 8KB docs index directly in AGENTS.md achieved 100% pass rate vs. 79% for Skills-with-explicit-instructions and 53% baseline. This caveats the original memo's advice to push content into skills for progressive disclosure — it depends on whether the agent will actually invoke them, and models currently don't do so reliably.

6. **Specific percentages in the original memo (62% token reduction, 47,000→9,000 words, 90–95% retrieval accuracy) are single-anecdote Medium posts, not systematic measurements.** They should be stripped from the report or framed as anecdotes.

7. **Prompt caching changes the cost calculus.** Anthropic's prompt caching (now on all active models) gives a 90% discount on cached input tokens and is applied automatically in Claude Code to CLAUDE.md and the system prompt. This means the raw token cost of a slightly-too-long CLAUDE.md is much lower than the original memo implies — the real cost is *instruction-following degradation*, not dollars.

8. **`.claude/rules/` is real but has known bugs.** The feature works, but (a) the documented `paths:` YAML syntax fails in several configurations — community-reported `globs:` works more reliably; (b) rules do not fire on Write in some cases (only Read); (c) user-level `~/.claude/rules/` is ignored on Windows. Teams should verify their rules are actually loading.

9. **The original memo's "v2.0.64+" version reference for `.claude/rules/` could not be independently verified** — it's in the original memo without a citation chain. The feature is currently in production and documented on Anthropic's docs site, but I removed the version claim.

---

## 1. File size and token limits — revised

### What's solid

- **Root CLAUDE.md should be concise.** Anthropic's own docs ([code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory)) state that files over 200 lines consume more context and may reduce adherence. Multiple independent sources converge on **under ~200 lines** as the soft ceiling, with many practitioners targeting far less.
- **HumanLayer's production root CLAUDE.md is under 60 lines** — cited as a concrete existence proof, not a universal target.
- **Context window:** 200K tokens on all standard Anthropic paid plans; 500K on Enterprise; 1M available on Opus 4.6, Sonnet 4.6, and newer on select tiers at standard pricing. Claude Code's effective window is smaller because it reserves a buffer for compaction.
- **"Lost in the middle" is a real, well-documented phenomenon.** Liu et al. (TACL 2024) found a U-shaped performance curve: models perform best when relevant info is at the start or end of context, worse in the middle. This is an independent, peer-reviewed academic finding. Mechanistic work (Wu et al. 2025, referenced in dev.to coverage) attributes it partly to RoPE positional encoding decay and attention sinks.

### What was soft in the original memo and should be flagged

| Original claim | Status | What the evidence actually shows |
|---|---|---|
| "62% token reduction by trimming from 2,800 to 180 lines" | **Anecdotal** — single Medium post (Jpranav, 2025). Not a controlled measurement. | Directionally correct but the specific percentage is a single author's self-report. |
| "One developer reduced monorepo CLAUDE.md from 47,000 to 9,000 words (80% reduction)" | **Anecdotal** — traceable to blog posts (Agent Native, Apr 2026), not research. | Again, directionally correct; the specific numbers reflect one project. |
| "90–95% retrieval accuracy" for "token-efficient CLAUDE.md" | **Unverified / probably fabricated in the original memo.** No source I could find uses this specific figure in this context. | Remove. |
| "Teams report 62% token reduction" (plural) | **Overstated.** Single source. | Revise to "one practitioner reported…" |
| "Context window quality degrades at 75%+ utilization" | **Partially supported.** Practitioner guidance recommends compacting at 85–90% (before auto-compact at 95%), and Chroma's "context rot" research shows degradation starts well before filling the window. But "75%" as a specific threshold is not from research — it's practitioner heuristic. | Keep as heuristic, attribute as such. |
| 5-level @import depth | **Confirmed.** Anthropic's own docs ([code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory)) state "maximum depth of five hops". |

### What's new

- **Prompt caching changes the math.** Cache reads cost 10% of standard input tokens, and Claude Code automatically caches CLAUDE.md. Practitioners report this translates to an estimated 40–50% reduction in daily input-token costs for typical use. This means the dollar cost of an overweight CLAUDE.md is lower than the original memo implies; the real cost is **degraded instruction-following**, not dollars.
- **Claude Sonnet 4.5+ and Opus 4.6+ have "context awareness"** — they can see their remaining context budget and self-manage accordingly. This is new since the original memo and reduces the need for some manual context discipline.

---

## 2. File structure — revised

### What's solid

- **Root file + supporting files pattern** is consistent with official Anthropic guidance and multiple independent sources. Anthropic's own docs recommend splitting large projects into `.claude/rules/` for path-scoped instructions.
- **Progressive disclosure as a principle** is sound and supported by both HumanLayer and Anthropic's engineering blog ("Effective context engineering for AI agents", Sep 2025), which introduces "just-in-time context" — loading via lightweight file path references that the agent resolves as needed.
- **Hierarchical loading:** subdirectory CLAUDE.md files lazy-load when Claude reads files in those directories. Confirmed in official docs.

### Important nuance the original memo missed

**Anthropic's own context-injection mechanism undermines the "every line is precious" framing.** HumanLayer's reverse-engineering via `ANTHROPIC_BASE_URL` logging shows Claude Code prepends:

```
<system-reminder>
IMPORTANT: this context may or may not be relevant to your tasks.
You should not respond to this context unless it is highly relevant to your task.
</system-reminder>
```

Practical implications:
- Broader CLAUDE.md content that Claude judges irrelevant will be filtered at inference time — it still consumes tokens but has reduced behavioral effect.
- This explains the common complaint that "Claude ignores my CLAUDE.md instructions even in all caps."
- **The cure is to make instructions universally applicable**, not to shout louder.

### What's new since the original memo

- **Anthropic has formalized `.claude/rules/`** with documented YAML frontmatter (`paths:` field). Rules without `paths:` load at startup with the same priority as CLAUDE.md; scoped rules load on-demand when matching files are accessed.
- **Known bugs in `.claude/rules/`** (GitHub issues on `anthropics/claude-code`):
 - #13905: Documented `paths:` examples use invalid YAML (glob patterns starting with `{` or `*` are YAML reserved indicators).
 - #17204: `globs:` frontmatter key works more reliably than `paths:`.
 - #21858: `paths:` rules in `~/.claude/rules/` are ignored on Windows.
 - #23478: Path-scoped rules don't load on Write (only Read), which means they can't enforce conventions on newly created files without hook workarounds.
- **AGENTS.md** has emerged as a cross-tool standard used by Cursor, Codex, OpenCode, Zed, and others. Claude Code still reads CLAUDE.md; AGENTS.md portability matters if your team uses multiple agent tools.

### Revised templates

**Single-repo root CLAUDE.md (target: <100 lines, ideally <60):**

```markdown
# Project: [Name]

## Stack
- [Primary tech: language, framework, key dependencies]

## Commands
- `cmd` - what it does and when to use it
- Prefer the specific incantation the agent would otherwise guess wrong

## Where things live
- `dir/` - one-line purpose
- [File naming convention if non-obvious]

## Non-obvious rules
- Rules the agent would not infer from reading the code
- Skip anything a linter already enforces
- Skip anything Claude can read from package.json, tsconfig.json, etc.

## Verification
- How to check work: test command, build command, lint command
```

**What NOT to include** (consolidated from Anthropic docs, HumanLayer, ETH Zurich paper's recommendations):

- Anything a linter/formatter/typechecker enforces deterministically.
- Generic coding advice ("write clean code", "prefer composition over inheritance").
- Architecture overviews that restate what the file tree shows.
- Auto-generated `/init` output without manual review — the ETH Zurich paper identifies this as actively harmful.
- Content already in README.md, package.json, or tsconfig.json — reference with `@path` instead.

### Monorepo pattern

The original memo's monorepo pattern is still sound:

```
monorepo/
├── CLAUDE.md              # Universal only — stack, monorepo tooling
├── packages/
│   ├── frontend/CLAUDE.md # Lazy-loads only when Claude enters frontend/
│   ├── backend/CLAUDE.md
│   └── shared/CLAUDE.md
└── .claude/rules/         # Path-scoped rules that apply across packages
```

One correction: **subdirectory CLAUDE.md files do not re-inject after `/compact`**. Only the project-root CLAUDE.md survives compaction. If you need something to persist after compact, it must live at the root.

---

## 3. Content guidelines — revised

### What's solid

The core principles from the original memo align with consensus:
- Document what the agent would otherwise guess wrong (commands with non-default flags, build/test/lint specifics).
- Code style rules belong in linters, not CLAUDE.md.
- Reference existing files with `@path` instead of duplicating.

### What should be downgraded

- **Emphasis markers like "YOU MUST", "IMPORTANT", "NEVER":** The original memo recommends these, but the HumanLayer analysis and IFScale paper both suggest that as instruction density grows, *all* instructions get de-weighted — shouting doesn't help, and the `<system-reminder>` explicitly tells Claude "this may or may not be relevant." Use emphasis sparingly, and only for rules that would cause real harm if violated.

### New concrete evidence for what works (ETH Zurich)

Gloaguen et al. recommend (and their empirical data supports):

1. **Describe only minimal requirements.** Commands, boundaries, specific tooling that differs from defaults.
2. **Skip architecture narratives.** Models tested (Sonnet 4.5, GPT-5.2, Qwen3-30B) have enough parametric knowledge to navigate common architectures without prose walkthroughs.
3. **Specify at least one security boundary** if there's anything sensitive — the paper reports this as a consistent behavioral lever.
4. **Write by hand.** LLM-generated context files degraded performance in every single model × benchmark cell tested.

### Writing style, updated table

| Do | Don't |
|----|-------|
| Specific commands with flags: `pytest --numprocesses=auto -v` | Generic: "write tests" |
| Boundary rules: "never touch `src/generated/`" | Style rules handled by formatter |
| Non-default tool choices: "we use pnpm, not npm" | Rehashed README content |
| Gotchas the agent will hit and fix: "Firebase v9 getRedirectResult() returns null (not object with null user) when no redirect occurred" | Aspirational guidance: "follow best practices" |

The "Firebase v9 gotcha" style is exactly what the ETH Zurich paper found helpful in developer-written files: specific, empirical, non-inferable from the code.

---

## 4. Reference patterns — revised

### What's solid

- `@path/to/file` syntax works for both relative and absolute paths.
- `@~/path` references home-directory files (useful for personal-preference imports in shared projects).
- Max import depth: 5 hops (confirmed in official Anthropic docs).
- Imports inside code fences are not evaluated (safe to document examples).

### What's nuanced

- **First-time external imports trigger an approval dialog.** If the user declines, imports are silently disabled — no error, just absence. Worth knowing when debugging "why isn't this loading?"
- **Circular imports are detected** (Claude Code handles them gracefully), but the loaded content may be incomplete — avoid them.

### New: Vercel's compression pattern

For cases where you do need a lot of reference information in the root file, Vercel's approach is notable:

```
[Docs Index]|root: ./.next-docs
|IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning
|01-app/01-getting-started:{01-installation.mdx,02-project-structure.mdx,...}
```

A pipe-delimited compressed index pointing to files the agent reads on demand. Vercel compressed 40KB of docs to 8KB while maintaining 100% eval pass rate. This is a real, testable pattern for Next.js projects (`npx @next/codemod@canary agents-md`).

The general principle: **embed an index, not content.** Names + paths so the agent knows where to look; full content stays out of the system prompt.

---

## 5. Context loading behavior — revised

### Confirmed memory hierarchy (from Anthropic's docs and CLI behavior)

1. **Managed policy** (enterprise-controlled, highest precedence)
2. **Managed drop-ins** (`managed-settings.d/`, Claude Code v2.1.83+)
3. **Project memory** (`./CLAUDE.md`, `./.claude/CLAUDE.md`)
4. **Project rules** (`.claude/rules/`)
5. **User memory** (`~/.claude/CLAUDE.md`)
6. **User rules** (`~/.claude/rules/`)
7. **Local project memory** (`./CLAUDE.local.md`)
8. **Auto memory** (lowest precedence, Claude Code v2.1.59+)

### Loading triggers — with new detail

- **Startup:** root and parent CLAUDE.md files, plus all `.claude/rules/` without `paths:` frontmatter.
- **File access:** subdirectory CLAUDE.md loads lazily; `.claude/rules/` with matching `paths:` activate when Claude reads a matching file.
- **`@mention`:** triggers loading of that file.
- **Compaction recovery:** only the project-root CLAUDE.md re-injects after `/compact`. Nested CLAUDE.md files reload only when Claude next reads a file in that subdirectory. If your instruction disappeared after compaction, it either lived in a conversation turn or in a nested file that hasn't reloaded.

### New: auto memory

- Claude Code ≥ v2.1.59 accumulates notes across sessions (`~/.claude/projects/<project>/memory/`).
- Useful but worth monitoring — files over 200 lines reduce adherence, so periodic review is required.
- Can be disabled: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` or in `/memory` toggle.

---

## 6. Anti-patterns — revised and significantly strengthened

### Strongly supported anti-patterns

**1. Running `/init` and shipping the output.** The ETH Zurich paper is the clearest empirical evidence yet that LLM-auto-generated context files *hurt* performance across every tested model. "Treat `/init` as a starting point, then ruthlessly edit" is the practical takeaway. HumanLayer makes the same point from a leverage argument: "a bad line in CLAUDE.md affects every phase of every workflow."

**2. Using CLAUDE.md as a linter.** HumanLayer calls this "never send an LLM to do a linter's job." Deterministic tools (ESLint, Biome, Prettier, mypy) are faster, cheaper, and more reliable. Use a PostToolUse hook to pipe linter errors back to Claude, not prose instructions about formatting.

**3. Over-stuffing.** IFScale (Jaroslawicz et al., 2025) provides the actual data: Claude Sonnet 4 hits 98% accuracy at 50 instructions and drops to ~43% at 500, with a linear decay pattern. Smaller/non-reasoning models degrade much faster (exponentially). The "150–200" figure floating around is from the primacy-effect peak (where models bias most heavily toward early instructions), not a hard cliff. **The principled version: every instruction competes for attention; adding a marginal instruction lowers adherence to all of them.**

**4. Mixing unrelated tasks in one session.** Practitioner consensus + Chroma's context rot research. Use `/clear` between distinct tasks; use `/compact` at 85–90% threshold before auto-compact kicks in at 95%.

### Anti-patterns worth adding

**5. Trusting CLAUDE.md to carry permissions or safety rules.** The system-reminder explicitly tells Claude the content "may or may not be relevant." For hard constraints (e.g., "never force-push," "never commit to main"), use `settings.json` permissions and hooks — they're deterministic. Anthropic's docs on auto mode note that auto mode actively drops broad allow rules like `Bash(*)` to protect against this category of footgun.

**6. Duplicating content across CLAUDE.md files in a hierarchy.** If a subdirectory CLAUDE.md restates what the root already says, you've burned tokens and created a drift risk. Subdirectory files should only contain what differs for that subtree.

**7. Relying on Skills to self-invoke.** Vercel's eval found Skills were not invoked in 56% of relevant test cases. If a Skill is critical to correctness, either (a) invoke it explicitly in a slash command, or (b) inline the essential knowledge in AGENTS.md/CLAUDE.md.

---

## 7. Validation and maintenance

### Verified commands

- `/context` — inspect what's consuming context.
- `/cost` — token usage stats.
- `/compact` — strategic compression (best used at 85–90%, not at auto-trigger).
- `/clear` — fresh session.
- `/memory` — browse auto-memory files.
- **`InstructionsLoaded` hook** (new since original memo) — logs which instruction files Claude loaded and when. Useful for debugging "why isn't my rule firing?"

### Degradation signals

- Claude asks questions already answered in CLAUDE.md.
- Instructions ignored despite emphasis markers.
- Quality drops late in sessions (especially last 20% of window).
- Repeated corrections for the same class of mistake.

### Maintenance cadence

- Add instructions only when you've corrected Claude on the same thing 2+ times.
- Prune quarterly — or whenever auto-memory starts to look cluttered.
- Use the `#` key during sessions to capture repeated corrections into memory.

---

## 8. Platform-specific notes

### Windows 11

- User-level: `%USERPROFILE%\.claude\CLAUDE.md`.
- WSL2 recommended; keep projects in Linux FS (`~/projects/`), not `/mnt/c/`.
- `git config --global core.autocrlf input` to avoid CRLF issues.
- **Known: `~/.claude/rules/` with `paths:` frontmatter is ignored on Windows** (GitHub issue #21858). Use project-level `.claude/rules/` or work around with hooks.

### VS Code extension

- Uses the same discovery logic as the CLI.
- MCP servers must be configured via the CLI first.
- Checkpoints and conversation rewinding are CLI-only.

### Claude Code on the web (newer)

- Runs in isolated VMs on Anthropic infrastructure.
- CLAUDE.md conventions apply identically, but you lose direct filesystem customization (e.g., local hooks).

---

## 9. Revised decision framework

### Use `.claude/rules/` when

- You have cross-cutting concerns that vary by path (e.g., TypeScript rules for `src/`, SQL rules for `migrations/`).
- You need rules to be version-controlled and team-shared.
- You want the rule to only apply when Claude is working on matching files.
- **Verify** the rule is actually loading — the `InstructionsLoaded` hook is your friend, especially given the open bugs around frontmatter parsing.

### Use subdirectory CLAUDE.md when

- You have genuinely distinct subtrees (monorepos with different stacks per package).
- You want progressive disclosure that's always-on when Claude enters that subtree.
- Each subtree has its own team/owner.

### Use Skills when

- The task has a clear explicit trigger (user says "deploy", "migrate", "upgrade").
- You're packaging a capability Claude doesn't have (PDF generation, Playwright, domain-specific tools).
- You accept that passive triggering is unreliable (Vercel 56% non-invocation rate) and will explicitly invoke via slash command or explicit instruction.

### Use AGENTS.md / embed-in-CLAUDE.md when

- The content is critical to every turn (framework-specific APIs outside training data, as in Vercel's Next.js 16 case).
- You've compressed to an index + on-demand file pattern.
- You want tool-agnostic portability (Cursor, Codex, Claude Code all read AGENTS.md).

### Use hooks when

- You want deterministic behavior (attribution, linting, pre-commit checks).
- A rule would otherwise live in CLAUDE.md as "NEVER do X" — use a hook to make it impossible instead.

---

## 10. What the academic literature actually says, in one place

This section summarizes the four pieces of rigorous research that should anchor any future decisions about CLAUDE.md.

### Liu et al. (2024) — "Lost in the Middle"

- **Venue:** TACL (peer-reviewed journal).
- **Methodology:** Controlled position of relevant information in multi-document QA and key-value retrieval tasks.
- **Finding:** U-shaped performance curve — models perform best when info is at the start or end of context, worst in the middle.
- **Applies to:** Long CLAUDE.md files and long imported content.
- **Practical implication:** Put the most important rules at the top or bottom of CLAUDE.md, not buried in the middle.

### Jaroslawicz et al. (2025) — "IFScale" (arXiv:2507.11538)

- **Methodology:** Keyword-inclusion benchmark with 10–500 instructions across 20 models, 5 seeds per density.
- **Limitations (author-flagged):** Keyword-inclusion is a narrow task; business-domain English only; results may not generalize to other instruction types.
- **Finding for Claude:** Sonnet 4 follows a *linear decay* pattern — 98% at 50, 94% at 100, 77% at 250, 43% at 500. Reasoning mode improves slightly at high densities.
- **Primacy effects** peak at 150–200 instructions, then converge toward uniform failure at 300+.
- **Practical implication:** Every instruction has a cost. The shape of the decay is smooth, not a cliff — no magic number, but fewer instructions is reliably better.

### Gloaguen et al. / ETH Zurich (2026) — "Evaluating AGENTS.md" (arXiv:2602.11988)

- **Methodology:** Two benchmarks — SWE-bench Lite (existing, popular repos) and AGENTbench (new, 138 tasks from 12 niche Python repos with developer-written AGENTS.md). Three conditions: no context file, LLM-generated context file, developer-written context file. Four agents/models tested (Sonnet 4.5, GPT-5.2, Qwen3-30B, and one other).
- **Limitations:** Python only; task-success metric only (doesn't capture consistency/style benefits); models tested were state-of-the-art at Feb 2026.
- **Findings:**
 - LLM-generated files: −0.5% on SWE-bench Lite, −2% on AGENTbench (performance **decrease**).
 - Human-written files: +4% average (marginal improvement).
 - Cost: +20% inference cost regardless of whether context file helps.
 - Stronger generation models don't help.
- **Practical implication:** Do not use `/init` output without heavy manual editing. Write by hand. Keep short. Specify commands and non-inferable details; skip architecture narratives.

### Mohsenimofidi et al. (2025) — "Context Engineering for AI Agents in OSS" (arXiv:2510.21413)

- **Methodology:** Descriptive study of 466 open-source projects' AGENTS.md adoption patterns.
- **Finding:** No established content structure; wide variation in style (descriptive, prescriptive, prohibitive, explanatory, conditional).
- **Caveat:** This is descriptive (what people do), not prescriptive (what works). The field is still figuring norms out.

### Anthropic's own published guidance

- **"Effective context engineering for AI agents"** (Sep 2025) — introduces "just-in-time context": lightweight identifiers (file paths, queries, URLs) that agents resolve as needed, vs. pre-loading everything.
- **"Effective harnesses for long-running agents"** — recommends an initializer agent that writes a progress file and feature checklist, plus coding agents that work one feature at a time with git commits.
- Both align with the minimum-viable-CLAUDE.md thesis.

### Vercel (Jan 2026) — "AGENTS.md outperforms skills in our agent evals"

- **Methodology:** Hardened eval suite targeting Next.js 16 APIs outside training data; four configurations tested (baseline, Skill default, Skill with explicit instructions, AGENTS.md index).
- **Limitations:** Next.js only; single framework; Vercel has a commercial interest in AGENTS.md adoption; "hardened eval" methodology is reasonable but not blinded or external.
- **Findings:** Baseline 53%, Skill (default) 53%, Skill (explicit) 79%, AGENTS.md index 100%.
- **Key insight:** Skills weren't invoked in 56% of cases; explicit instructions helped but were fragile to wording.
- **Apparent contradiction with ETH Zurich?** Partially. Vercel's eval tests APIs *outside* training data (Next.js 16), which is exactly the scenario where documentation matters most. ETH Zurich tested general issue resolution on repos where models had parametric knowledge. Both can be true: context files help when the information isn't in training data; they hurt when the information is redundant with training knowledge.

### 2601.20404 — "On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents"

- **Methodology:** 10 repos, 124 PRs; executed agents with and without AGENTS.md; measured wall-clock runtime and token usage.
- **Finding:** 28.64% lower median runtime and 16.58% lower output tokens with AGENTS.md; task completion comparable.
- **How to reconcile with Gloaguen:** Different metrics (runtime + output tokens vs. task success + input cost). Both can be true: context files shorten paths for successful tasks while also making some tasks fail.

---

## 11. Key metrics and heuristics — honestly sourced

| Heuristic | Source quality | Notes |
|---|---|---|
| Root CLAUDE.md < 200 lines | **Strong** — Anthropic's own docs | Explicitly stated. |
| HumanLayer's root is <60 lines | **Anecdotal existence proof** | Not a prescription, just evidence that very short works in practice. |
| Under 300 lines is "absolute ceiling" | **Heuristic** — multiple blog consensus | Plausible but not from any single authoritative source. |
| `/compact` at 85–90% | **Practitioner heuristic** | Reasonable given auto-trigger at 95%. Not research-backed as a specific threshold. |
| "Pre-rot threshold ~75%" | **Weak** — single-source practitioner advice | Keep if useful, but don't present as research. |
| 90% cache-read discount | **Confirmed** — Anthropic pricing docs | [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| ~50 instructions in Claude Code's system prompt | **HumanLayer's analysis** — independently derived via proxy logging | Plausible, not verified by Anthropic. |
| "150–200 total instructions is LLMs' reliable ceiling" | **Overstated.** | The IFScale paper shows smooth decay for Claude Sonnet 4, not a cliff. Smaller models have earlier cliffs. |

---

## 12. Updated decision tree for a new project

1. Can you express the essential context in <60 lines? **Ideal.** Stop.
2. If no: what's in the excess that a linter, formatter, hook, or README could handle? Move it out.
3. What's left should be in one of:
 - Root CLAUDE.md (universal, always-applies).
 - Subdirectory CLAUDE.md (applies to that subtree).
 - `.claude/rules/` with `globs:` (path-scoped). *Verify it actually loads.*
 - A Skill (for explicit triggers). *Don't assume it will auto-invoke.*
 - A hook in `settings.json` (for deterministic enforcement).
4. For anything still in CLAUDE.md, check: would a new senior engineer joining the team need this in every session? If not, move it.
5. After 2 weeks of use, prune. Delete anything that never fired in session, or that Claude ignored anyway.

---

## 13. Summary: what to change if you read the original memo

**Keep:**
- The core principle of keeping CLAUDE.md concise.
- The structural recommendations (root + progressive disclosure).
- The list of things NOT to include.
- The distinction between CLAUDE.md, `.claude/rules/`, and Skills.

**Change:**
- Don't cite the "62% token reduction" or "47,000 to 9,000 words" figures as if they're systematic findings — they're single-author anecdotes.
- Don't treat "150–200 instructions" as a hard ceiling; the decay is smooth, not a cliff, at least for Claude.
- Don't rely on `/init` output; the ETH Zurich paper is the first rigorous evidence it actively hurts.
- Don't rely on Skills to self-invoke; Vercel shows ~56% non-invocation rate.
- Be aware of the `<system-reminder>` — it filters CLAUDE.md content Claude judges irrelevant.
- Be aware that `.claude/rules/` has real bugs right now — verify it loads.

**Add:**
- Prompt caching changes the cost calculus (90% discount on cache reads).
- Context awareness in Claude 4.5+ reduces the need for some manual discipline.
- Auto memory in Claude Code v2.1.59+ is a new category of file to audit.
- AGENTS.md is emerging as a cross-tool standard if you use multiple agent tools.
- Vercel's compressed-index pattern is a specific, reproducible technique for embedding large reference docs.

---

## Bibliography

### Peer-reviewed / academic

1. Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2024). **Lost in the Middle: How Language Models Use Long Contexts.** *Transactions of the Association for Computational Linguistics*, 12, 157–173. [https://aclanthology.org/2024.tacl-1.9/](https://aclanthology.org/2024.tacl-1.9/)

2. Jaroslawicz, D., Whiting, B., Shah, P., & Maamari, K. (2025). **How Many Instructions Can LLMs Follow at Once?** arXiv:2507.11538. [https://arxiv.org/abs/2507.11538](https://arxiv.org/abs/2507.11538)

3. Gloaguen, T., Mündler, N., et al. (2026). **Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?** arXiv:2602.11988 (ETH Zurich SRI Lab / LogicStar.ai). [https://arxiv.org/abs/2602.11988](https://arxiv.org/abs/2602.11988)

4. Mohsenimofidi, S., Galster, M., Treude, C., & Baltes, S. (2025). **Context Engineering for AI Agents in Open-Source Software.** arXiv:2510.21413. [https://arxiv.org/abs/2510.21413](https://arxiv.org/abs/2510.21413)

5. **On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents.** (2026). arXiv:2601.20404. [https://arxiv.org/abs/2601.20404](https://arxiv.org/abs/2601.20404)

### Chroma research (semi-academic technical report)

6. Hong, K., Troynikov, A., & Huber, J. (2025, July). **Context Rot: How Increasing Input Tokens Impacts LLM Performance.** Technical report, Chroma. [https://research.trychroma.com/context-rot](https://research.trychroma.com/context-rot)

### Official Anthropic sources (authoritative for product behavior)

7. Anthropic. **Best Practices for Claude Code.** [https://code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)

8. Anthropic. **How Claude remembers your project.** [https://code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory)

9. Anthropic. **Effective context engineering for AI agents.** Engineering blog, Sep 29, 2025. [https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

10. Anthropic. **Effective harnesses for long-running agents.** Engineering blog. [https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

11. Anthropic. **Extend Claude with skills.** [https://code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)

12. Anthropic. **Skill authoring best practices.** [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

13. Anthropic. **Context windows.** [https://platform.claude.com/docs/en/build-with-claude/context-windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)

14. Anthropic. **Prompt caching.** [https://platform.claude.com/docs/en/build-with-claude/prompt-caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

15. Anthropic. **Pricing.** [https://platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)

16. Anthropic. **How Anthropic teams use Claude Code.** [https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf](https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf)

### Known-bug GitHub issues (Claude Code repo)

17. **GitHub issue #13905** — Invalid YAML syntax in claude/rules frontmatter `paths` property. [https://github.com/anthropics/claude-code/issues/13905](https://github.com/anthropics/claude-code/issues/13905)

18. **GitHub issue #17204** — `.claude/rules/` frontmatter format: `globs:` works, `paths:` with quotes does not. [https://github.com/anthropics/claude-code/issues/17204](https://github.com/anthropics/claude-code/issues/17204)

19. **GitHub issue #21858** — `paths:` frontmatter in user-level rules ignored on Windows. [https://github.com/anthropics/claude-code/issues/21858](https://github.com/anthropics/claude-code/issues/21858)

20. **GitHub issue #23478** — Path-based rules not loaded on Write tool, only Read. [https://github.com/anthropics/claude-code/issues/23478](https://github.com/anthropics/claude-code/issues/23478)

### Authoritative practitioner sources (quality-curated)

21. Horthy, K. (2025, Nov 25). **Writing a good CLAUDE.md.** HumanLayer blog. [https://www.humanlayer.dev/blog/writing-a-good-claude-md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

22. Gao, J. (2026, Jan 27). **AGENTS.md outperforms skills in our agent evals.** Vercel blog. [https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)

23. Parreño García, J. (2026). **How Claude Code rules actually work.** [https://joseparreogarcia.substack.com/p/how-claude-code-rules-actually-work](https://joseparreogarcia.substack.com/p/how-claude-code-rules-actually-work)

24. Op, A. (2026, Jan). **Stop Bloating Your CLAUDE.md: Progressive Disclosure for AI Coding Tools.** alexop.dev. [https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/](https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/)

### Third-party coverage of ETH Zurich paper

25. DAIR.AI Academy (2026, Feb 25). **Does AGENTS.md Actually Help Coding Agents? A New Study Has Answers.** [https://academy.dair.ai/blog/agents-md-evaluation](https://academy.dair.ai/blog/agents-md-evaluation)

26. MarkTechPost (2026, Feb 26). **New ETH Zurich Study Proves Your AI Coding Agents are Failing Because Your AGENTS.md Files are too Detailed.** [https://www.marktechpost.com/2026/02/25/new-eth-zurich-study-proves-your-ai-coding-agents-are-failing-because-your-agents-md-files-are-too-detailed/](https://www.marktechpost.com/2026/02/25/new-eth-zurich-study-proves-your-ai-coding-agents-are-failing-because-your-agents-md-files-are-too-detailed/)

### Sources explicitly flagged as anecdotal (not authoritative)

27. Jpranav (2025, Nov 18). "Stop Wasting Tokens: How to Optimize Claude Code Context by 60%." Medium. — Source of "62% token reduction" figure; single-author self-report.

28. Agent Native (2026, Apr). "Claude Code's Second Brain Cuts Token Usage by 5x." Medium. — Source of "80% reduction" figures; product marketing.

29. Luong NGUYEN (2025, Nov 24). "Claude Code: Memory — Teaching Claude Your Project's DNA." Medium. — Practitioner walkthrough.

### Original memo sources (inherited, for traceability)

30. `2025-12-12-Optimizing-CLAUDEmd-files-research.md` (original source 1 — not independently verified)
31. `2025-11-17-CLAUDEmdIndexing.md` (original source 2 — not independently verified)
32. `2025-12-16-token-efficiency-deep-research.md` (original source 3 — not independently verified)
33. `2026-01-11 Claude-Code-context-management.md` (original source 4 — not independently verified)
