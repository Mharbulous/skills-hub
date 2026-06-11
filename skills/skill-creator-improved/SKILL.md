---
name: skill-creator-improved
description: Create new skills. Modify or improve existing skills. Evaluate and optimize skill performance. Token-efficient version that uses phase-based loading and persistent state to keep conversations lean. Use when users want to create a skill from scratch, edit or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy. Also triggers when users mention "skill-creator-improved" or want the improved/token-efficient skill creator.
---

# Skill Creator (Improved)

A token-efficient fork of skill-creator. Same workflow, same scripts, same eval tooling — restructured so each conversation loads only the instructions for the current phase instead of the entire 500-line monolith.

## How it works

The skill-creator workflow has five phases. This version loads a lean router (what you're reading now, ~90 lines) plus only the reference file for the active phase (~50-150 lines). A persistent `state.json` in the workspace tracks progress so phases can span multiple sessions without losing context.

## State management

Each skill being created or improved gets its own workspace directory (`<skill-name>-workspace/` as a sibling to the skill directory). The state file lives inside that workspace at `<skill-name>-workspace/state.json`. This is per-skill — parallel sessions working on different skills use different workspace directories and never collide.

At the start of every invocation:

1. Identify which skill the user wants to work on and find its workspace directory. If the user mentions a skill name or there's an obvious workspace from context, check there for `state.json`.
2. If `state.json` exists, read it to determine the current phase and load the corresponding reference file from the table below.
3. If no `state.json` exists, this is a new session — start at Phase 1.

After completing each phase, update `state.json` and tell the user: "Phase N is complete. I've saved progress — you can continue now or pick this up in a fresh session anytime. If the conversation is getting long, starting fresh keeps things fast; I'll read the state file and know exactly where we left off."

### state.json schema

```json
{
  "skill_name": "my-skill",
  "skill_path": "/path/to/skill",
  "workspace_path": "/path/to/workspace",
  "phase": "intent | draft | eval-loop | description-opt | package",
  "mode": "interactive | ci",
  "iteration": 0,
  "evals_path": "/path/to/evals/evals.json",
  "completed_phases": [],
  "pending_improvements": [],
  "notes": "",
  "ci_config": {
    "max_iterations": 5,
    "target_pass_rate": 0.9,
    "stop_on_no_improvement": true,
    "no_improvement_threshold": 2
  },
  "skill_context": {
    "skill_type": "subjective_writing | deterministic_transform | mixed",
    "baseline_type": "no_skill | old_skill",
    "baseline_snapshot_path": "/path/to/snapshot/",
    "quality_criteria": "User-specified quality priorities",
    "known_limitations": "Known scope or capability limits"
  },
  "user_priorities": [
    "Cumulative user preference signals, updated by main session after each feedback round"
  ],
  "improvement_history": [
    {
      "iteration": 1,
      "changes_summary": "What was changed and why",
      "targeted_failures": ["which failures this iteration addressed"],
      "pass_rate_delta": "+0.15"
    }
  ]
}
```

## Phase routing

| Phase | When | Read this reference file |
|-------|------|--------------------------|
| 1. Capture Intent | New skill, no state.json | `references/phase-1-intent.md` |
| 2. Draft Skill | Intent captured, ready to write | `references/phase-2-draft.md` |
| 3. Eval & Iterate | Skill drafted, testing and improving | `references/phase-3-eval-loop.md` |
| 4. Description Opt | Skill finalized, optimizing triggers | `references/phase-4-description-opt.md` |
| 5. Package | Ready to ship | `references/phase-5-package.md` |

Read ONLY the reference file for the current phase. If you need the skill writing guide (during Phase 2 or Phase 3), also read `references/skill-writing-guide.md`.

**CI mode phase routing:** In CI mode, skip Phases 1 and 2 (interactive prerequisites) and enter directly at Phase 3. The skill and evals must already exist. If `evals_path` is missing or contains no eval prompts, fail immediately with a clear error.

## Skipping phases

The user drives the process. If they say "just vibe with me," skip Phase 3's formal eval process. If they already have a draft, skip to Phase 3. If they want description optimization only, jump to Phase 4. Update state.json accordingly.

## Communication style

Pay attention to the user's technical level. "Evaluation" and "benchmark" are fine for most users. For "JSON" and "assertion," look for cues that the user is comfortable before using them without explanation. When in doubt, briefly define terms.

## Environment detection

Detect your environment early and note it in state.json:

- **Cowork**: Subagents available, no browser display. Use `--static` for the eval viewer.
- **Claude Code**: Full capabilities — subagents, browser, `claude -p` CLI.
- **Claude.ai**: No subagents, limited shell. Run test cases serially, skip baselines and benchmarking.
- **CI mode** (`mode: "ci"` in state.json): Phase 3 loops autonomously without pausing for user review. Precondition: `evals_path` must exist with at least one eval prompt — CI automates the iteration loop, not the setup. Phases 1/2 are interactive prerequisites and are skipped in CI mode.

Each phase reference includes environment-specific notes where they matter.

## Bundled resources

The `agents/` directory has subagent instructions — read them only when spawning the relevant agent:

- `agents/grader.md` — Evaluating assertions against outputs
- `agents/comparator.md` — Blind A/B comparison
- `agents/benchmark-analyzer.md` — Cross-run benchmark patterns and assertion critique
- `agents/comparator-analyzer.md` — Post-hoc blind A/B comparison analysis
- `agents/improver.md` — Improving the skill based on grading results, feedback, and improvement history

The `references/` directory has:

- `references/schemas.md` — JSON structures for evals.json, grading.json, benchmark.json, etc.
- `references/skill-writing-guide.md` — Skill anatomy, progressive disclosure, writing patterns

## The core loop

For reference: capture intent > draft skill > run evals > review with user > improve > repeat > optimize description > package. But you only need the details for whatever phase you're in right now. R