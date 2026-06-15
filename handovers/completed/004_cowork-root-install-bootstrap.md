---
write_targets:
  - README.md
  - build/build_index.py
  - public/index.html
  - tests/test_build_index.py
  - tests/test_cowork_install_bootstrap.py
read_only_targets:
  - .github/workflows/publish.yml
  - .gitignore
  - bootstrap/skills_hub_allowed_signers
  - build/cowork_wrapper_template.md
  - firebase.json
  - public/skills/skills-hub/SKILL.md
---

# Handover: Cowork Root Install Bootstrap

## Task

Finish the Claude Cowork bootstrap goal: a clean Cowork chat should be able to type `Install https://mharbulous.github.io/skills-hub` and install the canonical `/skills-hub` skill without the user pasting deeper artifact URLs or commands.

## Current State

Implementation is committed and pushed to `main` as `6b5842a Add Cowork root install bootstrap`. A manual acceptance script is committed and pushed as `550111e Add Cowork install acceptance script`. The builder now generates a root `index.html`, a Cowork `install.json` descriptor for `skills-hub`, and a raw-signature hook for `cowork/install.json.sig`. README and tests were updated. `python build\build_index.py` succeeded locally but produced unsigned generated output because `SKILLS_HUB_SIGNING_KEY` is not available in this session.

## Red Herrings

- `public/cowork/install.json` exists locally after build but is ignored by `.gitignore`; do not try to stage it unless the repository policy changes.
- The standalone Claude Cowork desktop window was visible, but this Codex session did not expose a desktop app-control tool even after the user enabled "Any App".

## Failed Approaches

1. Direct live Cowork verification in this session - blocked because `tool_search` did not expose any desktop click/type/app-control tool after the setting change or in the refreshed delegated session.
2. Initial pytest run - failed before assertions with `PermissionError` under `C:\Users\Brahm\AppData\Local\Temp\pytest-of-Brahm`; rerunning with `TMP` and `TEMP` set to repo-local `.test-tmp` passed.
3. Local deployment path - unsafe for this change because local build is unsigned without `SKILLS_HUB_SIGNING_KEY`; use the signed GitHub publish path or a signed local build.
4. GitHub Actions verification - `gh` could not list workflows due missing authentication/404, and direct `curl.exe` checks to `mharbulous.github.io/skills-hub` failed with `SEC_E_NO_CREDENTIALS`. Python `urllib` worked and verified the live deployed artifacts.

## Key Discoveries

- The root Skills-hub URL was not self-describing; adding `public/index.html` is necessary for a bare `Install https://mharbulous.github.io/skills-hub` prompt to discover the Cowork install contract.
- The first-install package is `skills-hub.skill`, which is a resolver stub plus trust anchor, while the canonical skill body remains under `public/skills/skills-hub`.
- The GitHub publish workflow signs generated artifacts and deploys on `main`; direct local Firebase deploy should not be used unless the signing key is present and artifacts are signed.

## Useful URLs

- [Skills-hub root](https://mharbulous.github.io/skills-hub)

## Verification Done

- `python build\build_index.py`
- `$env:TMP='C:\Users\Brahm\Git\skills-hub\.test-tmp'; $env:TEMP='C:\Users\Brahm\Git\skills-hub\.test-tmp'; python -m pytest tests\test_build_index.py tests\test_cowork_install_bootstrap.py`
- `$env:TMP='C:\Users\Brahm\Git\skills-hub\.test-tmp'; $env:TEMP='C:\Users\Brahm\Git\skills-hub\.test-tmp'; python -m pytest tests`
- `git commit -m "Add Cowork root install bootstrap"`
- `git push`
- Live Python/OpenSSL check verified `https://mharbulous.github.io/skills-hub/`, `/cowork/install.json`, `/cowork/install.json.sig`, and `/manifest.json` returned HTTP 200.
- Live Python/OpenSSL verification checked the manifest signature, install descriptor signature, `cowork/install.json` manifest hash/size, `cowork/skill-packages/skills-hub.skill` manifest hash/size, and `skills-hub.skill` descriptor hash/size.
- `$env:TMP='C:\Users\Brahm\Git\skills-hub\.test-tmp'; $env:TEMP='C:\Users\Brahm\Git\skills-hub\.test-tmp'; python -m pytest tests`
- `git commit -m "Add Cowork install acceptance script"`
- `git push`

All 49 tests passed in the full run.
`git push` reported `main -> main`. Live Firebase content was verified after the first commit. The second commit only added the manual acceptance script under `tests/`, so it does not change hosted artifact content.

## New Session Setup Gate

Before continuing implementation or live acceptance, verify that the refreshed Codex session exposes a desktop app-control tool that can inspect, click, and type in the running Claude Cowork window. If no such tool appears after `tool_search`, stop and report that live Cowork verification is still unavailable in that session.

## Next Step

RECOMMENDED WORKFLOW: execute the pending plan

Use a session with desktop app control, or a human operator following `tests/manual_cowork_install_acceptance.md`, to run the live Cowork prompt acceptance test.
