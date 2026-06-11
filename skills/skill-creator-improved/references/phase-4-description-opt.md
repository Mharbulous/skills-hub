# Phase 4: Description Optimization

The description field in SKILL.md frontmatter is the primary mechanism that determines whether Claude invokes a skill. This phase optimizes it for triggering accuracy.

## Step 1: Generate trigger eval queries

Create 20 eval queries — a mix of should-trigger and should-not-trigger. Save as JSON:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

### Query quality matters

Queries must be realistic — what a real user would actually type. Include file paths, personal context, column names, company names, URLs. Mix lengths. Use casual speech, abbreviations, typos.

Bad: `"Format this data"`, `"Extract text from PDF"`, `"Create a chart"`

Good: `"ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column that shows the profit margin as a percentage. The revenue is in column C and costs are in column D i think"`

**Should-trigger queries (8-10):** Different phrasings of the same intent — formal and casual. Include cases where the user doesn't name the skill but clearly needs it. Uncommon use cases and competitive wins (where this skill competes with another but should win).

**Should-not-trigger queries (8-10):** Near-misses that share keywords or concepts but need something different. Adjacent domains, ambiguous phrasing where naive keyword matching would trigger but shouldn't. Don't make them obviously irrelevant — "write a fibonacci function" as a negative for a PDF skill is too easy.

### How skill triggering works

Skills appear in Claude's `available_skills` list with name + description. Claude only consults skills for tasks it can't easily handle alone — simple queries like "read this PDF" may not trigger even with perfect descriptions. Make eval queries substantive enough that Claude would benefit from a skill.

## Step 2: Review with user

Present the eval set using the HTML template:

1. Read `assets/eval_review.html`
2. Replace placeholders:
   - `__EVAL_DATA_PLACEHOLDER__` with the JSON array (no quotes — it's a JS variable assignment)
   - `__SKILL_NAME_PLACEHOLDER__` with the skill's name
   - `__SKILL_DESCRIPTION_PLACEHOLDER__` with the current description
3. Write to a temp file and open it
4. User edits queries, toggles should-trigger, adds/removes entries, clicks "Export Eval Set"
5. File downloads to `~/Downloads/eval_set.json` — check for the most recent version

This step matters — bad eval queries lead to bad descriptions.

## Step 3: Run the optimization loop

Tell the user: "This will take some time — I'll run the optimization loop in the background and check on it periodically."

Save the eval set to the workspace, then run:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Use the model ID from your system prompt so the triggering test matches what the user actually experiences.

This automatically: splits 60/40 train/test, evaluates the current description (3x per query for reliability), proposes improvements based on failures, re-evaluates, iterates up to 5 times, selects best by test score to avoid overfitting. While it runs, periodically tail output to give the user progress updates.

## Step 4: Apply the result

Take `best_description` from the JSON output and update SKILL.md frontmatter. Show the user before/after and report the scores.

Update state.json:

```json
{
  "phase": "package",
  "completed_phases": ["intent", "draft", "eval-loop", "description-opt"]
}
```

## Environment-specific notes

**CI mode**: Skip the HTML review step for eval queries (Step 2). Use the generated eval set directly, or accept a pre-built eval set from `state.json` if one was provided. The optimization loop (Step 3) runs unattended.

**Claude.ai**: Description optimization requires `claude -p` (Claude Code CLI). Skip this phase.

**Cowork**: `run_loop.py` uses `claude -p` via subprocess — should work fine. Save until the skill is finalized and the user agrees it's in good shape.
