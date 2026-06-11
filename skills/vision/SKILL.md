---
name: vision
description: Creates vision & design philosophy doc through collaborative HITL dialogue.
---

This skill outlines a process of a collaborative dialogue about a specific target (app, feature, plugin, skill, etc.) where your goal is to elicit and articulate the users high level design philosohpy and vision for that target.  The output will be a comprehensive vision document using this template: `~/.claude/skills/vision/reference/vision_template.md`

You will not be ready to output the vision document until you understand and can paraphrase these key elements in your own words and that the user agrees with, and can write a concise vision statement in your owner words that the user agrees with completely.

Use collaborative dialoge is to clarify the following aspects of the target:
1. **Platform** — app, feature, plugin, skill, browser extension, something else?
2. **Purpose** — audience, primary user, pain points, value proposition, benefits, killer use case
3. **Theme** — litmus-test, design philosophy, principles
4. **Non-Goals** — deliberately excluded from vision
5. **North Star** - the core metrics or measurement of progress toward the vision
6. **Anti-Patterns** - [optional] observed deviations from the vision that coding models have a tendency to produce, which should be guarded against.  This section should is at the end, as it tends to be more accurate if you wait to identify anti-patterns that emerge while using this vision statement. 

## Phase 1: Discovery
Spawn these 6 background sonnet subagents in parallel while continuing with Phase 2:
agents\architecture.md
agents\dependencies.md
agents\documentation.md
agents\intent.md
agents\structure.md
agents\symbols.md


## Phase 2
While waiting for the 6 parallel sonnet subagents to report back, ask closed questions (pick from list if possible) to clarify the following aspects of the project: 
1. Platform
2. Audience
3. Pain Points
4. Non-Goals 


## Phase 2.5
If the 6 parallel sonnet subagents have not yet reported back, ask additional closed questions (pick from list if possible) until all parallel subagents have responded:
7. Similar products or inspiration
8. What market gap does this target fill?
9. Scale target
10. Secondary users or audiences
11. Design philosophy polarities, such as:
  a. simplicity vs configurability
  b. performance vs accuracy
  c. generality vs specialization
  d. fail loudly vs degrade gracefully
  e. user control vs automation
  f. open source vs closed source
  g. opinionated vs flexible
Continue asking improvised closed questions until all parallel subagents have reported back, and then move on to Phase 3.  Try to make the questions insightful and revealing.

## Phase 3: Hypothesis-Driven Refinement

Do NOT synthesize or summarize the subagent findings to the user. Simply internalize what the 6 subagents reported and let it inform the hypotheses you form below.

Work through the remaining vision aspects (theme, non-goals, north star, design principles, litmus test, killer use case, etc.) one at a time using this loop:

1. **Hypothesize** — propose your best guess for the aspect based on all evidence so far.
2. **Confirm or correct** — ask the user if the hypothesis matches their vision.
   - If yes: move to the next aspect.
   - If no: ask open-ended questions to understand how their vision differs, then return to step 1 with a revised hypothesis.

**One question per turn.** Each message must contain exactly one hypothesis baked into a single question. Do not list multiple hypotheses and ask the user to evaluate them as a batch. Work the hypothesis into the question naturally so it reads as a conversational proposal, not a formal document fragment.

Bad: "Proposed Principle 3.1 — X. Proposed Principle 3.2 — Y. Do these capture your thinking?"
Good: "It sounds like the core constraint here is that TimeCamp data is read-only — the skill should never write back to the API. Is that right, or is there a scenario where writing back would be acceptable?"

After all aspects are resolved, draft a concise vision statement in your own words. Ask the user if they agree completely. If not, iterate with open-ended questions until the statement fully captures their intent.

## Phase 4

Write up the vision.md document using the template.