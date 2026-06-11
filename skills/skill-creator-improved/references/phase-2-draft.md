# Phase 2: Draft the Skill

## Goal

Write the initial SKILL.md and define test cases.

## Writing the SKILL.md

Read `references/skill-writing-guide.md` for detailed guidance on skill anatomy, progressive disclosure, and writing patterns.

Fill in these components:

- **name**: Skill identifier (kebab-case)
- **description**: When to trigger and what it does. This is the primary triggering mechanism — include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here, not in the body. Claude tends to "undertrigger" skills, so make descriptions a bit pushy. Example: instead of "Build dashboards" write "Build dashboards. Use whenever the user mentions dashboards, data visualization, internal metrics, or wants to display data, even if they don't say 'dashboard.'"
- **compatibility**: Required tools/dependencies (optional, rarely needed)
- **Body**: The actual skill instructions

## Test cases

After writing the draft, create 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user: "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?"

Save test cases to `evals/evals.json`. Don't write assertions yet — you'll draft those in Phase 3 while test runs are in progress.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `references/schemas.md` for the full schema (including the `assertions` field, added in Phase 3).

## Updating an existing skill

If the user is updating an existing skill rather than creating one:

- **Preserve the original name.** Note the skill's directory name and `name` frontmatter field — use them unchanged.
- **Copy to a writeable location before editing.** The installed skill path may be read-only. Copy to a temp directory, edit there.
- **If packaging manually, stage in a temp directory first** — direct writes to the installed path may fail.

## When this phase is done

You have a SKILL.md on disk and test cases defined. Update state.json:

```json
{
  "phase": "eval-loop",
  "iteration": 0,
  "skill_path": "/path/to/skill",
  "evals_path": "/path/to/evals/evals.json",
  "skill_context": {
    "skill_type": "subjective_writing|deterministic_transform|mixed",
    "baseline_type": "no_skill|old_skill",
    "baseline_snapshot_path": null,
    "quality_criteria": "What the user cares about most",
    "known_limitations": "What the skill explicitly does not handle"
  }
}
```

Populate `skill_context` based on the Phase 1/2 conversation: infer `skill_type` from the skill's purpose, set `baseline_type` based on whether this is a new skill or an improvement, capture `quality_criteria` from the user's stated priorities, and note any `known_limitations` discussed. This context is passed to subagents in Phase 3 that don't have access to the conversation history.

Tell the user: "Draft is written and test cases are ready. Moving to evaluation. If the conversation is getting long, starting a fresh session here is ideal — Phase 3 is the most intensive part and benefits most from a clean context window."
