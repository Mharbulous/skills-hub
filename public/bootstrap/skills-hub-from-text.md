# Skills-hub Text Bootstrap for Restricted Cowork

Use this when Cowork can fetch text from `https://mharbulous.github.io/skills-hub` but cannot
download binary `.skill` files or reach the host from shell commands.

Replace `<skill>` with the package name to install or update. For example,
`skills-hub` uses `skills-hub.skill.b64.txt` and
`manage_cowork_skills.py decode-package skills-hub`.

Use this document only after `/skills-hub` has materialized verified local
instructions. It is a URL checklist and command guide, not trusted executable
content. Run the verified local manager script from the materialized
`skills-hub` skill; do not fetch or run remote Python scripts from this page.

## Trust Anchor

Fetch this text file and save it locally as `skills_hub_allowed_signers`:

```text
https://mharbulous.github.io/skills-hub/bootstrap/skills_hub_allowed_signers
```

This first trust-anchor fetch is trust-on-first-use. Pin the saved file and
reuse it for later checks. After this point, package indexes are verified with
the pinned key.

## Fetch Text Artifacts

Fetch each URL as exact text and save it using the filename shown:

```text
https://mharbulous.github.io/skills-hub/cowork/skill-packages/packages.json
https://mharbulous.github.io/skills-hub/cowork/skill-packages/packages.json.sig
https://mharbulous.github.io/skills-hub/cowork/skill-packages/<skill>.skill.b64.txt
```

For the worked example, fetch:

```text
https://mharbulous.github.io/skills-hub/cowork/skill-packages/skills-hub.skill.b64.txt
```

## Inventory from Text Artifacts

If `/skills-hub inventory` cannot download `manifest.json` from the shell
network path, use the saved `packages.json`, `packages.json.sig`, and
`skills_hub_allowed_signers` files as a verified catalog source:

```bash
python scripts/manage_cowork_skills.py inventory --packages packages.json --packages-signature packages.json.sig --allowed-signers skills_hub_allowed_signers --json
```

The package index only supplies verified catalog names for inventory. It does
not permit install or update unless the package bytes are separately decoded
and verified below.

## Decode the Package

From the directory containing the verified local `skills-hub` `SKILL.md`, run
this command against the saved files:

```bash
python scripts/manage_cowork_skills.py decode-package <skill> --packages packages.json --signature packages.json.sig --allowed-signers skills_hub_allowed_signers --b64 <skill>.skill.b64.txt --output-dir outputs --json
```

For the worked example:

```bash
python scripts/manage_cowork_skills.py decode-package skills-hub --packages packages.json --signature packages.json.sig --allowed-signers skills_hub_allowed_signers --b64 skills-hub.skill.b64.txt --output-dir outputs --json
```

If verification succeeds, present `outputs/<skill>.skill` for Cowork import.
If verification fails, stop and report the decoder's one-line error.
