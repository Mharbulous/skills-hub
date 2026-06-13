# Phase 5: Package & Present

## Packaging

Check whether you have access to the `present_files` tool. If not, skip presentation and tell the user where the skill directory is.

Package the skill:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Present the resulting `.skill` file to the user so they can install it.

### Known bug: present_files cannot serve session-created files

`present_files` validates file accessibility from the Windows host side. The
workspace is mounted via virtiofs + bindfs (FUSE). Files **created by the
sandbox during the current session** are not visible to Windows through this
mount — the FUSE cache is not invalidated for guest-originated writes. The
`present_files` call will return "not accessible on the user's computer" even
though the file exists and is readable in the sandbox.

Files that existed **before the session started** work fine because Windows
already has a directory entry for them.

**Workaround — overwrite a pre-existing `.skill` file in the repo:**

```bash
# Find any .skill file that already exists in C:\Users\Brahm\Git\Coclerk\
# (created in a prior session) and overwrite it with the new package.
# Windows sees the update because the directory entry already exists.
cp /sessions/.../mnt/outputs/<skill-name>.skill \
   /sessions/.../mnt/Coclerk/<any-pre-existing-skill>.skill
```

Then call `present_files` with the pre-existing file's path. Tell the user
what the file actually contains (the new skill) so they're not confused by
the filename mismatch.

If no donor file is available, tell the user the `.skill` is at
`C:\Users\Brahm\Git\Coclerk\<skill-name>.skill` and ask them to install it
manually. This always works.

## Updating an existing skill

If you're updating an existing skill, preserve the original name in the `.skill` filename. For example, `research-helper.skill`, not `research-helper-v2.skill`.

If packaging manually, stage in a temp directory first, then copy to the output directory — direct writes may fail due to permissions.

## Final state

Update state.json:

```json
{
  "phase": "complete",
  "completed_phases": ["intent", "draft", "eval-loop", "description-opt", "package"]
}
```

The skill is done!
