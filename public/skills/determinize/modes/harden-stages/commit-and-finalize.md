# Stage 6: Commit and Finalize

## Goal

Record the hardening work with a recoverable commit, report on it, and let
the user decide what happens to the hardened copy.

## Prerequisites

- `green-results.md` from Stage 5, showing all scenarios passing.
- The complete `<skill-name>-hardened/` tree.

## Step 1: Recovery commit

Delegate to the git-agent:

```
Commit these specific files from the hardening session. Stage ONLY files
under the <skill-name>-hardened/ directory (SKILL.md, scripts/, tests/, references/).
Do NOT stage changes to the original skill directory.

Commit message:
- Title: 'feat(skills): harden <skill-name> — extract <script-name> to script'
- Body: brief description of what was extracted and why
- Body MUST include the searchable key: [hardening:<skill-name>:<script-name>]
- Include Co-Authored-By trailer

Do NOT push to remote.
```

The `[hardening:<skill-name>:<script-name>]` key format here must exactly
match the format Stage 2 Step 4 greps for — same brackets, same colons,
same skill/script name spelling.

## Step 2: Summary report

Produce a table covering: what was hardened, what was extracted, why it
matters (determinism value / variance eliminated), files created, and
regression status (from `green-results.md`).

## Step 3: Optional inline A/B test

Ask via `AskUserQuestion`: "Run A/B tests now" (Recommended) vs "Skip A/B
tests".

- **If run:** follow `modes/test.md` with these fixed parameters — Skill A
  = original, Skill B = hardened, prompt = the Stage 3 baseline prompt,
  3 per skill (minimum), model `sonnet`, `general-purpose` subagents with
  `run_in_background: true`, strictly sequential A1, B1, A2, B2, A3, B3,
  then `modes/test.md` Phases 3–5 (analyze, report, decide).
- **If skip:** announce: "Both versions kept on disk. Run
  `/determinize -test` in a new session to compare them later."

## Step 4: Three-way decision

Ask via `AskUserQuestion`: Promote / Keep both / Delete. Mark the option
that matches the decision-matrix outcome from Step 3 (if the A/B test ran)
as "(Recommended)"; if the A/B test was skipped, mark "Keep both" as
"(Recommended)" instead.

### Promote branch

Delegate to:

```bash
node <determinize-path>/scripts/promote-skill.mjs <path-to>/<skill-name>-hardened
```

`<determinize-path>` is the directory containing the mode file you are
currently reading — i.e. this `determinize` skill's own root directory.
Resolve it from where you are, don't hardcode it.

Parse the script's JSON output. If `action` is `error`, report the message
and stop — do not proceed to the commit below.

On success, delegate to the git-agent for a commit:
- Title: `feat(skills): promote hardened <skill-name> — replace original`
- Body: "Hardened version replaces original after passing regression
  tests. Original recoverable from previous commit.\n\n[hardening:<skill-name>:<script-name>]"

Then announce: "Promotion complete. The hardened skill is now at
`<skill-name>/`. The original is recoverable from the git commit prior to
this one."

### Keep branch

Announce: "Both versions retained. Run `/determinize -test` in a new
session to compare them."

### Delete branch

Delegate to the git-agent:
- `git rm -r <skill-name>-hardened/`
- Commit:
  - Title: `revert(skills): remove hardened <skill-name> — original retained`
  - Body: "Hardened version removed per user decision. Recoverable from
    previous commit.\n\n[hardening:<skill-name>:<script-name>]"

Then announce: "Hardened version deleted. The original skill remains at
`<skill-name>/`. The hardened files are recoverable from the git commit
prior to this one."

## Non-negotiables

- Never create a `deprecated/` or `archived/` folder. Git history is the
  only recovery mechanism.
- Never commit the original and hardened directories together in Step 1.
- Every commit produced by this stage (harden, promote, delete) must carry
  the `[hardening:<skill-name>:<script-name>]` key, byte-identical across
  all three.
