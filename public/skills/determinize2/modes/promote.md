# Promote Mode

## Overview

Promotion is the final step of the hardening lifecycle: it replaces an
original skill with its `-hardened` counterpart, after the user has
reviewed A/B results and favors the hardened version. This mode interviews
the user for explicit confirmation, then delegates the mechanical work to
`scripts/promote-skill.mjs`.

## Prerequisites

Promotion assumes A/B test results already exist and that the user has
reviewed them and favors the hardened version. If no A/B results can be
found for this skill, say:

> "No A/B test results found. Run `/determinize2 -test` first to compare
> the original and hardened versions."

and stop — do not proceed to the interview.

## Path resolution

Given any of these input forms, resolve to the skill's actual parent
directory — do not assume a fixed root like `.claude/skills/`; the
examples below use that path only as an illustration, generalize to
wherever the skill actually lives:

| Input form | Example | Resolves to |
|---|---|---|
| Bare skill name | `foo` | `<skill's parent dir>/foo` and `<skill's parent dir>/foo-hardened` |
| `-hardened` name | `foo-hardened` | same pair as above |
| Full path to skill dir | `.claude/skills/foo` | `.claude/skills/foo` and `.claude/skills/foo-hardened` |
| Path to SKILL.md | `.claude/skills/foo/SKILL.md` | same pair, derived from the file's parent directory |

If the resolved hardened directory does not exist, report the missing path
and exit — do not proceed.

## Phase 1: Mandatory confirmation interview

Ask, via `AskUserQuestion`:

```
Ready to promote the hardened skill.

This will:
1. Replace <skill-root>/<name>/ with <skill-root>/<name>-hardened/
2. Update internal references (frontmatter name, path references)
3. Delete the original skill directory permanently

The hardened version's tests/ folder will be preserved in the promoted skill.
This operation is NOT reversible (except via git).

Options:
1. "Promote" — Replace the original with the hardened version
2. "Cancel" — Exit without changes
```

If the user selects "Cancel": exit cleanly, no changes made.

## Phase 2: Execute the script

If the user selects "Promote":

```bash
node <determinize-path>/scripts/promote-skill.mjs <path-to>/<name>-hardened
```

`<determinize-path>` is the directory containing this mode file — i.e.
this skill's own root directory, resolved from where you are currently
reading, not hardcoded.

Parse the script's JSON output. If `action` is `error`, report the message
to the user and exit — do not proceed to Phase 3.

## Phase 3: Report and commit

On success, report to the user: `filesUpdated`, `filesDeleted`, and the new
location, all taken from the script's JSON output.

Delegate to the git-agent for a commit:
- Title: `feat(skills): promote <name>-hardened to <name>`
- Body: "Replaces original skill with hardened version after A/B testing
  confirmed improvement."
- Include the Co-Authored-By trailer.
- Do NOT push to remote.

Then announce: "Promotion complete. The hardened skill is now at
`skills/<name>/`. The `-hardened` directory has been removed."

## The Iron Rule

```
NO PROMOTION WITHOUT USER APPROVAL
```

## Rationalizations (all wrong)

| Rationalization | Why it's wrong |
|---|---|
| "A/B testing clearly showed B is better" | The user still decides — statistics inform, they don't authorize. |
| "It's reversible via git, so just run it" | Reversibility is not the same as consent. Ask first. |
| "The user already said 'promote' earlier" | The Phase 1 interview IS the formal consent — a prior mention doesn't substitute for it. |
| "Promote now, ask about reverting later" | Wrong order — ask, then act, never the reverse. |
