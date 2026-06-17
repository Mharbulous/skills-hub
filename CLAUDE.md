# Skills-hub — Claude guidance

## Build

The only build entry point is `build/build_index.py`. All marketplace JSONs,
plugin.json files, and `public/cowork/` artifacts are generated outputs — do
not edit them directly. Edit the source in `public/skills/<name>/SKILL.md` and
regenerate.

```bash
python build/build_index.py
python -m pytest tests
```

## Plugin Staleness Gotcha

**When `/skills-hub` loads stale content in Cowork after a reinstall, the repo
is almost never the cause.** Both install-path SKILL.md files
(`plugins/skills-hub/skills/skills-hub/SKILL.md` and
`public/cowork/plugins/skills-hub/skills/skills-hub/SKILL.md`) are generated
outputs — confirm they have the correct content before spending time on repo
changes.

The three actual causes are all Cowork client-side:

1. **Saved resolver-wrapper skill takes precedence over the plugin.**
   Any `skills-hub` skill the user previously clicked "Save skill" on overrides
   the plugin-delivered version. See
   `plugins/skills-hub/skills/skills-hub/SKILL.md` lines 137–140. Fix: delete
   the saved skill from Cowork's user-skills list.

2. **URL marketplace instead of Git repository marketplace.**
   If the marketplace was added via a URL (`mharbulous.github.io/skills-hub` or
   `skills-hub.web.app`) rather than via **Add from a repository**, Cowork
   cannot resolve the relative `./plugins/skills-hub` source and falls back to
   whatever it cached. Fix: remove URL marketplace entries; add via
   `https://github.com/Mharbulous/skills-hub.git`.

3. **Cowork caches plugin clones in AppData.**
   Uninstalling via the UI may not purge the clone. Fix: delete the stale
   `skills-hub` clone directory from Cowork's AppData cache manually, then
   reinstall.

Bumping the plugin version does not fix any of these three causes. Do not
commit version bumps as a response to staleness complaints — investigate the
Cowork client state first.
