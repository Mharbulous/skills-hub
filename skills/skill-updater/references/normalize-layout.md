# Normalize layout

Two cases require normalization before editing. Both take a skill out of a
dangerous layout and into layout 2 (split: wrapper installed, source in repo).

## Case A: First edit of a custom plugin-only skill (layout 1, custom)

The user wrote the skill but it lives only under `skills-plugin/` — no repo
copy. Git can't rescue an overwrite.

**Trigger: first edit, not discovery.** A never-edited custom skill has only
one version and nothing for git to rescue, so the wrapper layout has no
value yet. The moment the user asks to change the skill, a second version
becomes meaningful — that's the point to normalize. Subsequent edits stay on
the normalized layout (which will now classify as layout 2, not layout 1).

How to recognize a "first edit" in practice: the skill is in layout 1 and
there is no corresponding `Coclerk/.agents/skills/<name>/` directory. If
you're in skill-updater at all, the user has asked for an edit, so the first-
edit trigger has fired. Normalize.

**Procedure:**

1. Read the installed SKILL.md and any sibling files.
2. Copy the full directory into `Coclerk/.agents/skills/<name>/`.
3. Write a wrapper into `Coclerk/.claude/wrappers/<name>/SKILL.md` using the template
   from `architecture.md`. Name and description in the wrapper should match
   the original SKILL.md frontmatter exactly.
4. Package the wrapper (not the full skill) with the skill-creator-improved
   packager, targeting the install location.
5. Verify: installed copy is now a thin wrapper pointing at the repo source;
   `.agents/skills/<name>/` holds the real content.
6. Commit to git (`cd Coclerk && git add -A && git commit -m "Normalize <name>
   into wrapper layout"`) — or tell Brahm to do so. Git history is the whole
   point of this step.
7. Now proceed with the original edit against the repo source.

## Case B: Duplicate install drift (layout 4)

Both an installed copy (full content, not a wrapper) and a repo source exist.
They may or may not be in sync.

**Procedure:**

1. Diff the two:
   ```bash
   diff -r \
     "<installed-dir>" \
     "/sessions/dazzling-nice-noether/mnt/Coclerk/.agents/skills/<name>/"
   ```
2. If identical → easy. Replace the installed copy with a wrapper pointing at
   the repo source. Package and reinstall.
3. If they differ → show the user the diff, ask which side is authoritative
   (or whether to merge). Reconcile into the repo source. Then replace the
   installed copy with a wrapper.
4. Commit to git.
5. Now proceed with the original edit.

## What not to do during normalization

- Don't try to normalize a third-party plugin skill. Third-party skills stay
  in layout 1 forever. Preview-first is their only edit path.
- Don't skip the git commit step. The whole value of normalization is
  git-backed versioning; un-committed changes give the same exposure as layout
  1.
- Don't merge the original edit into normalization. Do normalize first, commit,
  then apply the user's edit as a separate step. This keeps the layout change
  reviewable on its own.

## Telling the user

Normalization is usually a surprise to the user — they asked for an edit, not
a migration. Keep the explanation short:

> "Before I edit this I want to move it into the repo-with-wrapper layout so
> git covers future changes. Two steps, ~1 minute. Then I'll make your edit.
> OK?"

If they say no, fall back to preview-flow for the edit and note that the
skill is still exposed to overwrite risk.
