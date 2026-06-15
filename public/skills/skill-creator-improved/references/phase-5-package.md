# Phase 5: Package & Present

## Skills-hub Packaging

For Skills-hub source changes, packaging is the build pipeline's job. Add or
edit the skill under `public/skills/<name>/`, then run this from the repository
root when generated artifacts are needed:

```bash
python build/build_index.py
```

Cowork `.skill` packages must come from `public/cowork/skill-packages/` after
that build. Do not package Skills-hub skills from a product repository, do not
overwrite unrelated `.skill` files as a presentation workaround, and do not
document runtime cache edits as the delivery path.

If the change needs to be effective on `https://mharbulous.github.io/skills-hub`, use the
signed publish path for the repo instead of a local package handoff.

## Standalone Packaging

Use this only for a non-Skills-hub standalone skill package.

Check whether you have access to the `present_files` tool. If not, skip
presentation and tell the user where the package is.

Package the skill:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Present the resulting `.skill` file to the user so they can install it.

### Known limitation: present_files cannot serve some session-created files

`present_files` validates file accessibility from the Windows host side. The
workspace may be mounted through layers that do not immediately expose files
created during the current session. If `present_files` cannot access the
package, report that exact limitation and leave the generated package path for
the user. Do not work around it by staging files in a product repository.

## Updating an Existing Skill

If you are updating an existing skill, preserve the original name in the
`.skill` filename. For example, `research-helper.skill`, not
`research-helper-v2.skill`.

If packaging manually, stage in a temp directory first, then copy to the output
directory; direct writes may fail due to permissions.

## Final State

Update state.json:

```json
{
  "phase": "complete",
  "completed_phases": ["intent", "draft", "eval-loop", "description-opt", "package"]
}
```

The skill is done.
