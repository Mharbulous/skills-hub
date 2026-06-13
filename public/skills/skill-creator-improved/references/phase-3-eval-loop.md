# Phase 3: Eval & Iterate

The main session is a thin dispatcher. It spawns subagents, reads their summaries, updates state, and handles all user interaction. It never reads transcripts, grading.json files, or output artifacts directly.

## Entry Preconditions

Before the first iteration:

1. **skill_context check.** If `state.json` has no `skill_context` (Phase 2 was skipped), infer it from the existing skill and evals: read the skill to determine `skill_type`, check for a baseline snapshot, infer `quality_criteria` from skill content. In interactive mode, confirm with the user.

2. **CI preconditions** (CI mode only). Verify `evals_path` exists, contains at least one eval prompt, and all `files` paths in evals.json resolve to existing files on disk. Fail immediately with a clear error listing any missing items.

3. **Assertion bootstrap** (first iteration only, no assertions in evals.json yet). Draft initial assertions from `evals.json` `expected_output` descriptions and `user_priorities`. Reference `references/skill-writing-guide.md` for assertion quality guidance — assertions should be discriminating (not trivially satisfied) and objectively verifiable. Write assertions to `evals.json`. This must happen BEFORE seeing any outputs to avoid self-fulfilling assertions.

## The Iteration Loop

Results go in `<workspace>/iteration-<N>/`. Each test case gets a directory with a descriptive name.

### Step 1: Spawn Test Runners

For each eval, spawn two subagents — one with the skill, one baseline. Batch in waves of `max_parallel_subagents` (default 5-6).

**With-skill run:**
```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<name>/with_skill/outputs/
- Outputs to save: <what the user cares about>
```

**Baseline run** (same prompt, no skill or old skill snapshot):
- **New skill**: No skill. Save to `without_skill/outputs/`.
- **Improving existing skill**: Snapshot first (`cp -r`), point baseline at snapshot. Save to `old_skill/outputs/`.

Write `eval_metadata.json` per test case (see `references/schemas.md`).

### Step 2: Capture Timing Data

As each runner completes, the completion notification contains `total_tokens` and `duration_ms`. Write `timing.json` immediately to the run directory — this data is not persisted elsewhere.

```json
{"total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3}
```

This is the one artifact the main session writes per runner.

### Step 3: Spawn Graders

After all runners complete, spawn one Grader per run (parallel, batched by `max_parallel_subagents`). Each Grader reads `agents/grader.md`.

**Inputs per Grader:**
- `session_id`: the test runner's session ID (from completion notification)
- `outputs_dir`: path to the run's outputs directory
- `evals_path`: path to evals/evals.json
- `eval_id`: which eval to grade (Grader looks up assertions from evals.json — single source of truth)
- `eval_prompt`: the task that was executed

**Grader writes:** `grading.json` and `run_summary.md` to the run directory.

**Grader returns:** ~100-word summary with pass/fail counts, key failure, and any proposed assertion changes.

### Step 4: Aggregate (Inline)

Run from the skill-creator-improved directory:

```bash
python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
```

This produces `benchmark.json`, `benchmark.md`, and `convergence_vector.json`.

Then generate the static viewer:

```bash
python <skill-creator-improved-path>/eval-viewer/generate_review.py \
  <workspace>/iteration-N \
  --skill-name "<name>" \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --static <workspace>/iteration-N/review.html
```

For iteration 2+, also pass `--previous-workspace <workspace>/iteration-<N-1>`.

Use `--static` exclusively. Never use the server mode.

### Step 5: Spawn Benchmark Analyzer

Spawn a subagent that reads `agents/benchmark-analyzer.md`.

**Inputs:** `benchmark.json` path, iteration directory path, skill path.

**Returns:** Top 3-5 observations (non-discriminating assertions, regressions vs baseline, flaky assertions, time/token tradeoffs).

### Step 6: Branch by Mode

#### Interactive Mode

1. **Present the viewer.** Give the user the path to `review.html`. Explain the two tabs: "Outputs" for qualitative review with feedback textboxes, "Benchmark" for quantitative comparison. "When you're done reviewing, come back and let me know."

2. **Collect feedback.** The static viewer's "Submit All Reviews" downloads `feedback.json` to the user's default download folder. Locate the downloaded file and copy it to `<iteration_dir>/feedback.json`. You may need to ask the user where it downloaded.

3. **Present assertion change proposals.** If any Grader summaries include proposed assertion changes, present them to the user separately: "For the next iteration, the grader suggests these assertion changes..." Accept or reject based on user response. Update `evals.json` only if the user approves.

4. **Update user_priorities.** If feedback reveals recurring themes or new priorities, update `user_priorities` in state.json.

5. **Spawn Improver.** See Step 7.

#### CI Mode

1. Assertions are frozen — log Grader-proposed changes to `assertion_proposals.json` in the iteration directory but do not apply them.

2. **Spawn Improver.** See Step 7.

### Step 7: Spawn Improver

Spawn a subagent that reads `agents/improver.md`.

**Inputs:**
- `skill_path`, `iteration_dir`, `evals_path`
- `analyst_notes_path`: path to benchmark-analyzer output
- `mode`: "interactive" or "ci"
- `iteration`: current iteration number
- `pending_improvements`, `improvement_history`, `user_priorities`, `skill_context` from state.json
- `skill_writing_guide_path`: path to `references/skill-writing-guide.md`

In interactive mode, ensure `feedback.json` is in `iteration_dir` before spawning.

**Improver writes:** `improved_SKILL.md` and `improvement_log.json` to the iteration directory.

**Improver returns:** ~200-word summary, `addressed_improvements` array, `new_improvements` array, any concerns.

### Step 8: Update State and Evaluate Convergence

1. **Copy improved skill (with CI rollback).** Compare the current iteration's pass rate (from `convergence_vector.json`) against the previous iteration's. If pass rate dropped (CI mode only), do NOT copy the improved skill — instead restore from the previous iteration's `improved_SKILL.md` (at `<workspace>/iteration-<N-1>/improved_SKILL.md`) and log the regression. In interactive mode, or if pass rate held or improved, copy `iteration_dir/improved_SKILL.md` to `skill_path` normally.

2. **Prune pending_improvements.** Remove items listed in the Improver's `addressed_improvements`.

3. **Add new items.** Append the Improver's `new_improvements` to `pending_improvements`.

4. **Append to improvement_history.** Add an entry with iteration number, the Improver's changes summary, targeted failures, and pass rate delta (computed from current vs previous `convergence_vector.json`). Cap at 10 entries.

5. **Oscillation detection.** Read `convergence_vector.json` from the current iteration directory. Compare the set of failing assertions against previous iterations' `convergence_vector.json` files on disk (at `<workspace>/iteration-<N>/convergence_vector.json`). If the current failing set matches a previous iteration's failing set, flag for review.

6. **Update state.json** with new `iteration`, `pending_improvements`, `improvement_history`, and `user_priorities`.

7. **Convergence check (CI mode):**
   - Pass rate >= `ci_config.target_pass_rate`? Stop.
   - No improvement for `ci_config.no_improvement_threshold` consecutive iterations? Stop.
   - `ci_config.max_iterations` reached? Stop.
   - Lateral oscillation detected (failing set matches a prior iteration)? Stop and flag.
   - On stop, write `ci_report.json` to the workspace (per-iteration pass rates, improvement trajectory, final skill state).
   - Otherwise, loop back to Step 1.

8. **Continue check (interactive mode).** Ask the user: continue iterating or stop? If the conversation is growing, suggest a fresh session — state.json has everything needed to resume.

## Environment Notes

**Cowork**: Use `--static` viewer (mandated above). Batch subagents with `max_parallel_subagents`; reduce batch size if timeouts occur.

**Claude Code**: Full capabilities. Everything works as described.

**Claude.ai**: No subagents. Run test cases yourself one at a time. Skip baselines and benchmarking. Present results inline, collect feedback in conversation.
