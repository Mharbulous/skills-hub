# Skills-hub Text Bootstrap for Restricted Cowork

Use this when Cowork can fetch text from `https://skills-hub.web.app` but cannot download binary `.skill` files or reach the host from shell commands.

## Trust Anchor

Fetch this text file and save it locally as `skills_hub_allowed_signers`:

```text
https://skills-hub.web.app/bootstrap/skills_hub_allowed_signers
```

This first trust-anchor fetch is trust-on-first-use. Pin the saved file and reuse it for later checks. After this point, package indexes are verified with the pinned key.

## Fetch Text Artifacts

Fetch each URL as text and save it using the filename shown:

```text
https://skills-hub.web.app/cowork/skill-packages/packages.json
https://skills-hub.web.app/cowork/skill-packages/packages.json.sig
https://skills-hub.web.app/cowork/skill-packages/skills-hub.skill.b64.txt
https://skills-hub.web.app/cowork/bootstrap/decode-package.py
```

## Decode the Package

Run this command in the directory containing the saved files:

```bash
python decode-package.py --skill skills-hub --packages packages.json --signature packages.json.sig --allowed-signers skills_hub_allowed_signers --b64 skills-hub.skill.b64.txt --output-dir outputs --json
```

If verification succeeds, present `outputs/skills-hub.skill` for Cowork import. If verification fails, stop and report the decoder's one-line error.
