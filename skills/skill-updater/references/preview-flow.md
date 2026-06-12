# Preview-first flow

Use when the user wants to review the revised skill before it replaces the
original. Always the path for third-party plugin skills (layout 1, non-custom).
Also available as an override for any layout.

## Shape of the flow

1. Copy the skill directory to a temp workspace (original untouched).
2. Apply the edit in the temp copy.
3. Package the temp copy into a `.skill` file using
   skill-creator-improved's packager.
4. Present the `.skill` file to the user with `present_files`. The file ships
   with a "Save skill" button; we're not asking them to install, we're asking
   them to inspect.
5. On approval → copy the edited files back over the original. On rejection →
   iterate or discard.

## Step 1: Copy to temp

Put the working copy somewhere obviously temporary and separate from the
eventual destination. Use the outputs directory so it's visible to the user if
needed but doesn't pollute the repo.

```bash
WORK_DIR="/sessions/dazzling-nice-noether/mnt/outputs/skill-updater-work/<skill-name>"
mkdir -p "$WORK_DIR"
cp -r "<source-dir>/." "$WORK_DIR/"
```

"Source-dir" is the repo source if one exists (layouts 2, 3, 4), otherwise
the installed dir (layout 1).

## Step 2: Apply the edit in the temp copy

Use `Edit` or `Write` against files inside `$WORK_DIR`. Never touch the
original in this flow.

## Step 3: Package

Reuse skill-creator-improved's packager. Do not duplicate it.

```bash
python "/sessions/dazzling-nice-noether/mnt/Coclerk/.agents/skills/skill-creator-improved/scripts/package_skill.py" \
  "$WORK_DIR" \
  "/sessions/dazzling-nice-noether/mnt/outputs/"
```

The packager zips the directory, names the output `<skill-name>.skill`, and
runs `quick_validate.py` first. If validation fails, fix the temp copy and
retry — do not ship a broken package for review.

## Step 4: Present for review

```
present_files({files: [{file_path: "C:\\Users\\Brahm\\AppData\\Roaming\\Claude\\local-agent-mode-sessions\\...\\outputs\\<skill-name>.skill"}]})
```

Send one line of context alongside: what changed, in a sentence. The user
will open the `.skill` (or extract and read) and respond.

### Known bug: present_files cannot serve session-created files

`present_files` validates file accessibility from the Windows host side. The
workspace is mounted via virtiofs + bindfs (FUSE). Files **created by the
sandbox during the current session** are not visible to Windows through this
mount — the FUSE cache is not invalidated for guest-originated writes. The
`present_files` call will return "not accessible on the user's computer" even
though the file exists and is readable in the sandbox.

Files that existed **before the session started** (created in a prior session)
work fine because Windows already has a directory entry for them.

**Workaround — overwrite a pre-existing `.skill` file in the repo:**

```bash
# Find a .skill file that already exists in the repo root (pre-session)
# and overwrite it with the new package. Windows sees the update because
# the dentry already exists.
cp /sessions/.../mnt/outputs/<skill-name>.skill \
   /sessions/.../mnt/Coclerk/<any-pre-existing-skill>.skill
```

Then call `present_files` with the path to the pre-existing file (using its
original filename — the user will see the right content regardless of the
filename). Tell the user what the file actually contains so they're not
confused by the mismatched name.

If no suitable donor file exists, tell the user the `.skill` file is at
`C:\Users\Brahm\Git\Coclerk\<skill-name>.skill` and ask them to install it
manually (double-click or drag into a Cowork session). This is the fallback
of last resort — it always works.

## Step 5: Copy back on approval

On "yes, looks good":

```bash
# Only the files you actually changed — a clean sync, not a blanket overwrite.
cp "$WORK_DIR/SKILL.md" "<destination>/SKILL.md"
# Copy other changed files as needed.
```

Destination:

- Layout 1 (third-party plugin, override case): the installed dir. Check
  writability first.
- Layout 1 (custom plugin-only — shouldn't happen, see normalize-layout.md):
  don't copy back yet; normalize first.
- Layouts 2/3: the repo source. If the edit changed the wrapper frontmatter,
  also copy the wrapper stub into `Coclerk/.claude/wrappers/<name>/`.
- Layout 4: also shouldn't reach preview-flow without normalization first.

On rejection: delete `$WORK_DIR` or leave it for iteration, the user's call.

## Cleanup

After a successful copy-back, remove `$WORK_DIR`:

```bash
rm -rf "$WORK_DIR"
```

Keeping stale working copies around is a source of confusion later.
