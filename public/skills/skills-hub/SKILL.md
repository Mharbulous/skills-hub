---
name: skills-hub
description: >
  Manage Skills-hub skills for Cowork. Use for /skills-hub install,
  /skills-hub update, /skills-hub inventory, /skills-hub assimilate, installing
  Cowork Skills-hub skills, updating stale Myskillium or old Skills-hub wrapper
  skills, fetching verified Cowork .skill packages, or importing a useful
  non-Skills-hub skill into the skills-hub repo.
---

# Skills-hub

Manage Cowork-facing Skills-hub installs from the skills-hub repository.

Use `scripts/manage_cowork_skills.py` relative to the verified `SKILL.md`
directory currently being read. In Cowork, this is normally the
resolver-materialized cache directory printed by `skills-hub-fetch.py`, not the
repo path. Treat the script as the only supported implementation path; do not
zip Cowork packages manually and do not hotpatch AppData runtime folders unless
the user explicitly asks for an emergency patch.

## Modes

### Inventory

Run inventory before install or update:

```bash
python scripts/manage_cowork_skills.py inventory
```

If Cowork's install root is unclear, pass `--install-root <path>` using the
path the user confirms from Cowork. Report current, missing, stale-wrapper,
orphan, and conflict entries with the evidence printed by the script.

### Install

For missing Skills-hub skills, fetch the published verified package:

```bash
python scripts/manage_cowork_skills.py fetch-package <skill>
```

The script downloads `manifest.json`, verifies `manifest.json.sig`, verifies
the `.skill` package's hash and size, and writes the package to the output
folder. Use `--json` when you need the verified package URL, SHA-256, and size.
Present the package path to the user for Cowork import. Do not generate a local
zip as a substitute.

If Cowork's shell network path cannot reach `skills-hub.web.app`, use the
restricted text workflow instead:

```text
https://skills-hub.web.app/cowork/bootstrap/skills-hub-from-text.md
```

That page is the source of truth for fetching text artifacts, running
`decode-package`, and presenting the reconstructed `.skill` package.

### Update

Run inventory, show stale wrappers, and confirm each target with the user. For
each confirmed skill, run `fetch-package <skill>` and present the verified
package for Cowork import. In restricted Cowork, follow the text workflow above
for each confirmed skill and substitute that skill's `.skill.b64.txt` file.
Re-run inventory after import if the user wants a check.

### Assimilate

Use after the user identifies a useful skill that is not yet in Skills-hub.
Confirm the target skill name and source path first, then run:

```bash
python scripts/manage_cowork_skills.py assimilate --source <path> --name <skill-name> --license <license-or-unknown>
```

Assimilation copies the full source skill into `public/skills/<name>` and
records provenance. If the target name already exists, stop for a naming or
merge discussion.

In Cloud Cowork, prefer GitHub PR assimilation:

```bash
python scripts/manage_cowork_skills.py assimilate --source <path> --name <skill-name> --license <license-or-unknown> --github-pr
```

This requires `GITHUB_TOKEN` with contents write and pull requests write access.
If the token is absent or the GitHub API rejects the request, stop and report
the exact error. Do not sign or deploy from Cowork; PR merge triggers the signed
publish workflow.

After assimilation, build and test:

```bash
python build/build_index.py
python -m pytest tests
```

Sign and deploy only as a separate, explicit step, and only when
`SKILLS_HUB_SIGNING_KEY` is available.
