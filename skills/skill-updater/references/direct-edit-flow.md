# Direct-edit flow

Use when the user has chosen not to review the revised skill before save.
Available on all layouts. Layouts 2 and 3 default to this (git is the
backstop); layout 1 reaches this path when the user says "just edit it" or
the edit is small enough that the preview ceremony isn't worth it.

## Layouts 2 and 3 (repo source exists)

1. Confirm the target file path. For layout 2 this is the repo source, not
   the installed wrapper. For layout 3 it's the repo source directly.
2. Use the `Read` tool first, then `Edit` to make the change. Small edits →
   one `Edit`. Larger restructuring → multiple `Edit`s or a `Write` rewrite
   after showing the plan.
3. After the edit, tell the user:
   - What was changed (in a sentence, not a diff dump — they can read the
     diff themselves).
   - That git covers them: `git diff` shows the change, `git restore
     <file>` reverts.
4. **Skip** re-packaging unless the edit also changed wrapper-level content
   (name or description). If it did, see "Wrapper resync" below.

## Layout 1 (plugin-only)

Direct-edit on the installed SKILL.md works the same as anywhere else. Use
`Read` then `Edit`. No pre-flight writability check — if the filesystem
rejects the edit, the tool will tell you, and that's rare enough not to
probe for proactively.

1. `Read` the installed file.
2. `Edit` the change.
3. After save, tell the user what changed in one sentence. Do **not** warn
   about plugin-update clobbering — accepted trade-off per memory
   `feedback_installed_skill_edits.md`.
4. Note once, briefly, that there's no git backstop for this file, so if
   they want a second pass to undo something, it's on them to recall the
   prior text. (No need to repeat this every time — the user has seen it.)

If this is the **first edit** of a custom plugin-only skill, don't just
direct-edit. Route to `normalize-layout.md` first — first edit is the
trigger to move the skill into the wrapper+repo-source layout, so git can
cover all future changes. Apply the requested edit *after* normalization.

## Wrapper resync (layout 2 only, when the edit touches triggering)

Triggering is driven by the wrapper's frontmatter — the `description` and
`name` fields. If the edit changed either of those:

1. Edit the repo source (already done).
2. Also edit the wrapper at `Coclerk/.claude/wrappers/<name>/SKILL.md` to match the
   new frontmatter. Body of the wrapper doesn't change.
3. Repackage and reinstall the wrapper if the user wants the new description
   active immediately — otherwise note that the old description will trigger
   until the next install cycle.

For body-level edits (instructions, references, scripts), the wrapper needs
nothing — it just points at the source, which now reads differently.

## What not to do

- Don't dump a diff into chat unless asked. The user can read the file.
- Don't summarize the change at length. One sentence is enough.
- Don't kick off evals automatically. Offer them as a separate step if
  relevant; otherwise stop.
