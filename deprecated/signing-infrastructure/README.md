# Deprecated: Signing Infrastructure

These files are from the pre-GitHub-direct delivery model where skills were
distributed as signed stubs that resolved and verified content at runtime.

The current model (`fetch-package` in `manage_cowork_skills.py`) downloads the
full skill content directly from the GitHub repo archive. These files are
preserved for historical reference only and are not used by any active code path.

## Files

- `cowork_wrapper_template.md` — stub SKILL.md template that ran the resolver
- `skills-hub-fetch.py` — runtime resolver that downloaded and hash-verified skills
- `decode-package.py` — base64 package decoder for text-based install flow
- `skills-hub-from-text.md` — instructions for the text-based install path
- `skills_hub_verify.py` — manifest signature verification module

## Superseded by

`manage_cowork_skills.py fetch-package` — builds full-content `.skill` packages
directly from the GitHub repo archive without stubs or signature verification.
