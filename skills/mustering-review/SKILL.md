---
name: mustering-review
description: "Interactive page inspection workflow. Use when the user wants to review, inspect, or walk through a UI page — asking questions about what they see and issuing small correction orders. Triggers on: 'let me inspect', 'review this page', 'walk me through', 'muster', 'what does this do', or any pattern where the user is looking at a running app and asking questions about its components while requesting small fixes. Do NOT use code-review, simplify, or other skills during a muster — use only muster-polisher and muster-secretary subagents."
---

# Mustering Review

An admiral's inspection: the user walks through a UI page, asks questions about what they see, and issues orders for small corrections. You explore the code, answer questions, record findings, and dispatch fixes.

## Critical Rule: Dispatch, Never Do

Your role during a muster is **investigator and dispatcher**. You read code to answer questions and identify relevant files, then dispatch subagents for all recording and fixing.

**NEVER:**
- Fix or edit code yourself — always dispatch the `muster-polisher` agent
- Invoke other skills (`/simplify`, `/commit`, `/code-review`, etc.)
- Invoke other agents (`code-simplifier`, `superpowers:code-reviewer`, `superpowers:requesting-code-review`, etc.)
- Use `subagent_type: "general-purpose"` — always use `muster-polisher` or `muster-secretary`
- Investigate a fix request deeply before dispatching — identify the file(s), then dispatch

**If you catch yourself about to do any of the above, STOP.** Dispatch the correct subagent instead.

## Setup

When the user identifies a page to inspect:

1. Determine the page name from the URL or user description (e.g., `tool-tab` from `/admin/workbench#tools`)
2. Create the muster report at `docs/muster-reports/YYYY-MM-DD_MR_{page_name}.md` (relative to the repo root)
3. Seed it with a header:

```markdown
# Muster Report: {Page Name}

**Date:** {YYYY-MM-DD}
**URL:** {page URL if known}

## Findings
```

4. Read the relevant source files for the page so you're prepared to answer questions

## Handling Questions

When the user asks a question about what they see:

1. Explore the codebase (Read, Grep, Glob) to find the answer
2. Answer the user directly and concisely
3. Dispatch `muster-secretary` in the background to record the Q&A:

```
Agent tool call:
  subagent_type: "muster-secretary"
  run_in_background: true
  prompt: |
    Report: {report file path}
    Question: {the question}
    Answer: {concise answer}
    File: {source file path if applicable}
    Status: Informational
```

## Handling Fix Instructions

When the user issues a correction order ("fix this", "change X", "add a tooltip", etc.):

1. Identify the relevant file path(s) using Read/Grep/Glob — just enough to know WHICH files, not to solve the problem
2. Dispatch `muster-polisher` in the background:

```
Agent tool call:
  subagent_type: "muster-polisher"
  run_in_background: true
  prompt: |
    Instruction: {what to fix}
    Files: {file path(s)}
    Context: {any relevant code patterns or conventions}
```

3. Also dispatch `muster-secretary` to record the fix order in the report

**Do NOT investigate the root cause yourself.** Identify the files, dispatch, move on.

## What Counts as Polisher-Appropriate

The polisher handles any change touching 1-2 files — frontend or backend:

- Add/edit tooltips, labels, placeholder text
- CSS tweaks (spacing, color, cursor, sizing)
- Toggle behaviors (click to select/deselect)
- Add/remove a class or attribute
- Small template restructuring
- Backend field path fixes, fallback logic, string formatting
- Config value changes, mapping corrections

The polisher will escalate to a handover if the change requires 3+ files, new components/composables, new state management, or new dependencies.

## Subagent Reference

| Agent | `subagent_type` | Purpose |
|-------|-----------------|---------|
| Polisher | `muster-polisher` | Makes focused code changes |
| Secretary | `muster-secretary` | Records Q&A into muster report |

Always spawn both as **background** agents (`run_in_background: true`).
