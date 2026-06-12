---
name: skill-updater
description: >
  Apply a known, user-specified change to an existing skill — the "make this
  edit" path, not the "figure out what to change" path. Use whenever the user
  says "edit this skill", "update the description of X", "fix this line in the
  skill", "change the trigger wording", "tweak this skill", "add/remove a
  reference file", "change how this skill triggers", "rename this skill", or
  any variant where the change is already decided and just needs to be applied.
  Also use when editing SKILL.md files directly, touching wrapper files under
  Coclerk/.claude/wrappers/, or updating any file inside a Coclerk/.agents/skills/
  directory. Handles direct-edit and preview-first paths based on where the
  skill lives (plugin install vs repo source vs split), and migrates custom
  plugin-only skills into the repo+wrapper layout on first edit. NOT for
  drafting new skills, figuring out what to change, or running evals — use
  skill-creator-improved for that work.
---

# Skill Updater

The "apply this change" path for skills. The user has already decided what to
change; this skill's job is to apply it in the safest way given where the skill
lives.

**Not this skill's job:** drafting a new skill, deciding what to change, running
evals to discover improvements, or optimizing the description against a
trigger-eval set. Those all belong to `skill-creator-improved`. If the user is
still figuring out *what* the change should be, route them there.

## The primary axis

**Does the user want to review the revised skill before it replaces the
original?**

- **No review needed** → Direct edit on the target file. Use the `Edit` tool,
  done.
- **Review first** → Preview path. Copy the skill to a temp directory, apply
  the edit there (original untouched), package as a `.skill` file, present to
  the user via `present_files`, copy back on approval.

Evals are an **orthogonal** axis. A user can want preview + evals, preview
only, evals only, or direct + no evals. Don't conflate the two. If evals seem
useful and an eval set exists, *offer* them — never couple them to the review
path.

## Step 1: Classify where the skill lives

Four possible layouts. See `references/classify-location.md` for the detection
procedure (paths to check, heuristics, failure modes).

| # | Layout | What it means |
|---|--------|---------------|
| 1 | **Plugin-installed, no repo source** | Installed under `skills-plugin/…/skills/<name>/`. Nothing in `Coclerk/.agents/skills/`. |
| 2 | **Split: wrapper installed, source in repo** | Installed copy is a thin wrapper (body points at a `Coclerk/.agents/skills/SKILL.md` path). Real source lives in the repo. This is the standard Coclerk pattern — see `Coclerk/.claude/wrappers/ar-follow-up/` as the reference model. |
| 3 | **Repo-only, not yet installed** | `Coclerk/.agents/skills/` exists but no installed copy is active. |
| 4 | **Duplicate install (drift)** | Installed copy is full substantive content (not a wrapper) AND a repo source with the same name exists. Two divergent copies — dangerous. |

## Step 2: Pick the default

| Layout | Default review path | Why |
|--------|-------------------|-----|
| 1. Plugin-only | **Preview-first** (direct-edit offered) | No git backstop, so default to preview. But direct-edit on the installed file works — it's the same `Edit` tool flow as anywhere else, just without a recoverable history. Offer it as a second option, especially for small edits the user clearly wants applied without ceremony. |
| 2. Split (wrapper + repo source) | **Direct edit on the repo source** | Git is the backstop. The wrapper itself rarely needs editing; edit it only if the change touches wrapper-level content (see below). |
| 3. Repo-only | **Direct edit on the repo source** | Git backstop applies. Offer to re-install/package afterward if useful. |
| 4. Duplicate install | **Normalize first, then edit** | Stop. Route to `references/normalize-layout.md` to reconcile and convert installed copy into a wrapper. Don't edit until layout is clean. |

The user's stated preference always overrides the default. "Just edit it"
skips preview on any layout; "show me first" forces preview even on layouts
2 and 3.

## Step 3: Handle wrapper-level edits in the split case

In layout 2, the wrapper's frontmatter — especially the `description` — is
what actually drives triggering. The source's frontmatter is read *after*
triggering and doesn't affect it. When the edit touches trigger-level
content (description, name), **edit both the wrapper and the source** to keep
them in sync, and tell the user you're doing the dual edit.

For body-level edits (instructions, references, scripts), edit only the
repo source. The wrapper doesn't change.

## Step 4: Apply the edit

- **Direct-edit path**: `references/direct-edit-flow.md`.
- **Preview-first path**: `references/preview-flow.md`.
- **Normalization needed**: `references/normalize-layout.md`.

## Step 5 (optional): Offer evals

After the edit is saved, check whether the skill has an `evals/` directory or
an `evals.json` referenced in `state.json` (the skill-creator-improved
workspace). If so, offer to run them. Never required. Running evals is a
skill-creator-improved responsibility — delegate, don't duplicate the logic.

## Architectural rule (for reference)

Custom skills use the wrapper-in-install + source-in-repo pattern (layout 2)
once they start being edited. The repo is authoritative; the wrapper is just
a pointer that gives the installer something to load. This gives git-backed
versioning for free. See `references/architecture.md` for the rationale and
the wrapper template.

**Enforcement trigger: first edit, not creation.** A never-edited custom skill
has only one version — there's nothing for git to rescue yet, and the
simplicity of the "just drop it in the plugin directory" creation flow has
real value. Version-control concerns only begin when a second version exists.

So skill-updater normalizes on **first edit** of a custom plugin-only skill
(layout 1, custom), not on discovery. It also normalizes layout 4 (duplicate
install) on encounter, regardless of whether this is a first edit, because
two divergent copies are a problem independent of edit count. Creation-time
layout is unconstrained — skill-creator-improved does not need to produce the
split layout up front.

## What "custom" means here

"Custom" = a skill the user (Brahm) wrote. "Third-party" = a skill that ships
with an installed plugin from elsewhere (e.g. the anthropic-skills plugin).
Third-party skills should stay preview-first and should not be normalized into
the repo — they're not his to rewrite and git would just archive a fork he
doesn't want.

Heuristic if unsure: if the skill name appears under `Coclerk/.agents/skills/`
or `Coclerk/.claude/wrappers/`, it's custom. Otherwise treat as third-party and
preview-first.

## When to refuse or redirect

If the user wants to *create* a new skill, redirect to `skill-creator-improved`
(or `skill-creator`) — skill-updater only updates what already exists. If
they're still exploring what the change should be, that's also a creator-skill
conversation, specifically Phase 3's eval loop or an informal brainstorm. If
they want to update a third-party plugin skill destructively, preview-first is
non-negotiable; push back by reminding them that a future plugin update will
clobber the edit, and ask whether they want to keep it anyway.

## Reusing existing tooling

Do NOT duplicate the packager. Use the one from skill-creator-improved:

```
python "C:\Users\Brahm\Git\Coclerk\.agents\skills\skill-creator-improved\scripts\package_skill.py" <skill-dir> [output-dir]
```

Same rule for validation (`scripts/quick_validate.py` in the same tree). If
skill-creator-improved ever moves, update the path references in
`references/preview-flow.md` — not here.
