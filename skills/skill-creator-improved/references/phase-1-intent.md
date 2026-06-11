# Phase 1: Capture Intent

## Goal

Understand what the user wants the skill to do, when it should trigger, and what success looks like.

## If the conversation already contains intent

The user might say "turn this into a skill" after completing a workflow. If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill gaps, but confirm your understanding before proceeding.

## Questions to answer

1. What should this skill enable Claude to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, creative work) often don't need them. Suggest the appropriate default based on the skill type, but let the user decide.

## Interview and research

Proactively ask about edge cases, input/output formats, example files, success criteria, and dependencies. Don't write test prompts yet — iron out the requirements first.

Check available MCPs — if useful for research (searching docs, finding similar skills, looking up best practices), research in parallel via subagents if available, otherwise inline. Come prepared with context to reduce burden on the user.

## When this phase is done

You have a clear picture of what the skill does, when it triggers, what it produces, and whether evals are needed. Update state.json:

```json
{
  "phase": "draft",
  "notes": "Brief summary of the agreed intent"
}
```

Tell the user: "I've captured the intent. Ready to write the skill draft. If this conversation is already long, you can start a fresh session — I'll pick up from the state file."
