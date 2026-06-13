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

Use `scripts/manage_cowork_skills.py`. Treat this script as the only supported
implementation path; do not zip Cowork packages manually and do not hotpatch
AppData runtime folders unless the user explicitly asks for an emergency patch.

## Modes

### Inventory

Run inventory before install or update:

```bash
python public/skills/skills-hub/scripts/manage_cowork_skills.py inventory
```

If Cowork's install root is unclear, pass `--install-root <path>` using the
path the user confirms from Cowork. Report current, missing, stale-wrapper,
orphan, and conflict entries with the evidence printed by the script.

### Install

For missing Skills-hub skills, fetch the published verified package:

```bash
python public/skills/skills-hub/scripts/manage_cowork_skills.py fetch-package <skill>
```

The script downloads `manifest.json`, verifies `manifest.json.sig`, verifies
the `.skill` package's hash and size, and writes the package to the output
folder. Present the package path to the user for Cowork import. Do not generate
a local zip as a substitute.

### Update

Run inventory, show stale wrappers, and confirm each target with the user. For
each confirmed skill, run `fetch-package <skill>` and present the verified
package for Cowork import. Re-run inventory after import if the user wants a
check.

### Assimilate

Use after the user identifies a useful skill that is not yet in Skills-hub.
Confirm the target skill name and source path first, then run:

```bash
python public/skills/skills-hub/scripts/manage_cowork_skills.py assimilate --source <path> --name <skill-name> --license <license-or-unknown>
```

Assimilation copies the full source skill into `public/skills/<name>` and
records provenance. If the target name already exists, stop for a naming or
merge discussion.

After assimilation, build and test:

```bash
python build/build_index.py
python -m pytest tests
```

Sign and deploy only as a separate, explicit step, and only when
`SKILLS_HUB_SIGNING_KEY` is available.
