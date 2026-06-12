---
write_targets:
  - .github/workflows/publish.yml
  - README.md
  - bootstrap/claude-setup.sh
  - bootstrap/codex-setup.sh
  - bootstrap/myskillium-fetch.py
  - bootstrap/myskillium_allowed_signers
  - bootstrap/myskillium_verify.py
  - build/build.py
  - handovers/queued/003_wire-remaining-environments.md
  - tests/
read_only_targets:
  - dist/manifest.json
  - dist/index.json
  - dist/claude/stubs/review-plan/SKILL.md
  - dist/codex/stubs/claude-md-optimizer/SKILL.md
  - dist/cowork/stubs/handover/SKILL.md
---

# Handover: Wire Remaining Environments

## Current Signed-Delivery Result - 2026-06-12

The unsafe "fetch and follow remote SKILL.md" stubs have been replaced by signed-manifest delivery:

| Harness | Skill | Current state | Remaining smoke |
|---------|-------|---------------|-----------------|
| Claude Code desktop | review-plan | Prior POC stub replaced with the verified full local skill from the live bootstrap smoke; old slash command remains disabled so the skill route wins | New Claude Code session should confirm `/review-plan` routes to local skill without remote-fetch refusal |
| Codex | claude-md-optimizer | Prior POC stub-only folder replaced with the verified full local skill; `reference/` and `templates/` are present | New Codex session should confirm the local skill triggers normally |
| Claude Cowork | handover | Wrapper source, `handover.skill`, and 4 AppData runtime copies now use the resolver stub plus `myskillium-fetch.py` and `myskillium_allowed_signers` | Manual Cowork session should confirm wrapper runs resolver and reads the verified cache path |

Implemented/deployed:

- `dist/manifest.json` schema v3 is generated with `generated_at`, `max_age_seconds`, signed skill catalog data, and `sha256`/`size` for every published artifact.
- `dist/manifest.json.sig` is produced with SSH signing key fingerprint `SHA256:U4jMB6DQxO+mJ+9VunaQQNXQFxG8xq2rktwr7HK9c5U`.
- `dist/bootstrap/myskillium_allowed_signers` is published and covered by the manifest.
- Claude/Codex setup scripts now default to verified full installs: manifest signature verification, archive hash/size verification, tar validation, then managed cleanup/extract.
- Cowork stubs now instruct the agent to run `python myskillium-fetch.py cowork <skill>` and read only the verified local `SKILL.md` path it prints.
- Firebase Hosting was redeployed after the signed-delivery changes; live `/hub` content byte-matches local `dist` for the checked representative artifacts.

Verification done:

- `python build\build.py` succeeded locally.
- Local manifest signature verified with `ssh-keygen -Y verify`.
- Live `manifest.json`, `manifest.json.sig`, `index.json`, trust anchor, selected stubs, selected full skills, full bundles, and selected per-skill tarballs returned HTTP 200 and byte-matched fresh local `dist`.
- Live-downloaded `claude/skills.tar.gz`, `codex/skills.tar.gz`, and `cowork/skills/handover.tar.gz` verified against the live manifest with `bootstrap\myskillium_verify.py`.
- `python bootstrap\myskillium-fetch.py cowork handover --base-url https://myskillium.web.app/hub ...` materialized a verified local cache path and printed only that path.
- Claude and Codex setup scripts installed verified full bundles from live Firebase into temp destinations; `review-plan` was full local content and `claude-md-optimizer` included `reference/` and `templates/`.
- Replaced real POC-installed unsafe stubs in Claude, Codex, Coclerk, and 4 Cowork runtime paths; backups are in `C:\Users\Brahm\myskillium-poc-backups\signed-delivery-20260612-120405\`.
- Coclerk `handover.skill` zip now has forward-slash entries: `handover/SKILL.md`, `handover/myskillium-fetch.py`, and `handover/myskillium_allowed_signers`; inner `SKILL.md` byte-matches `dist\cowork\stubs\handover\SKILL.md`.

Known follow-ups:

- Configure GitHub secret `MYSKILLIUM_SIGNING_KEY`; future publish workflow deploys are skipped unless both Firebase and signing secrets are available.
- Manual harness sessions are still needed for UI/runtime routing evidence; this Codex thread cannot directly control Claude Code desktop or Claude Cowork sessions.
- The resolver enforces freshness but does not yet persist a last-accepted manifest timestamp to reject rollback regressions across runs.

## Earlier Unsafe-Stub POC Result - 2026-06-12

Three one-skill Myskillium stub installs were attempted:

| Harness | Skill | Install result | Runtime smoke result |
|---------|-------|----------------|----------------------|
| Claude Code desktop | review-plan | Installed stub and disabled old command | Failed: Claude saw the stub but refused to fetch the remote SKILL.md as suspected prompt injection |
| Codex | claude-md-optimizer | Installed clean stub-only folder | Not automated: codex.exe is inaccessible from this environment; tarball materialization verified directly |
| Claude Cowork | handover | Installed wrapper, repackaged .skill, updated 4 runtime copies | Not automated: no Cowork control surface available in this Codex thread |

## POC Changes Made

- Deployed the fresh local `dist/` to Firebase because live `index.json` was stale.
- Backups and rollback notes are in `C:\Users\Brahm\myskillium-poc-backups\`.
- Claude desktop:
  - Backed up `C:\Users\Brahm\.claude\skills\review-plan\SKILL.md`.
  - Replaced it with `dist\claude\stubs\review-plan\SKILL.md`.
  - Renamed `C:\Users\Brahm\.claude\commands\review-plan.md` to `review-plan.md.disabled`.
- Codex:
  - Created `C:\Users\Brahm\.codex\skills\claude-md-optimizer\SKILL.md` from `dist\codex\stubs\claude-md-optimizer\SKILL.md`.
  - No pre-existing `claude-md-optimizer` Codex folder existed.
- Cowork:
  - Created `C:\Users\Brahm\Git\Coclerk\.claude\wrappers\handover\SKILL.md`.
  - Repackaged `C:\Users\Brahm\Git\Coclerk\plugins\utilities\skills\handover.skill` with Python zipfile; archive entry is `handover/SKILL.md`.
  - Updated all 4 discovered AppData runtime `skills\handover\SKILL.md` copies.

## Verification Done

- `python build\build.py` succeeded locally.
- Live Firebase content now byte-matches fresh local `dist` for:
  - `/index.json`
  - `/claude/stubs/review-plan/SKILL.md`
  - `/claude/skills/review-plan/SKILL.md`
  - `/codex/stubs/claude-md-optimizer/SKILL.md`
  - `/codex/skills/claude-md-optimizer/SKILL.md`
  - `/codex/skills/claude-md-optimizer.tar.gz`
  - `/cowork/stubs/handover/SKILL.md`
  - `/cowork/skills/handover/SKILL.md`
  - `/cowork/skills/handover.tar.gz`
- Stub frontmatter equals full harness-merged frontmatter and index descriptions for the three POC skills.
- Codex live tarball extraction to temp included `reference/` and `templates/`.
- Cowork `.skill` zip contains exactly `handover/SKILL.md`; inner bytes match the generated Cowork stub.
- All 4 discovered Cowork runtime copies byte-match the generated Cowork stub.
- `curl.exe` to Myskillium fails inside the sandbox with `SEC_E_NO_CREDENTIALS`, but succeeds outside the sandbox with HTTP 200.

## Important Findings

- Full rollout is no-go until the stub trust model is adjusted for Claude Code desktop. A new Claude Code session registered `review-plan`, read the stub, and refused to fetch `https://myskillium.web.app/hub/claude/skills/review-plan/SKILL.md` as a suspected remote-instruction prompt injection.
- The old `/review-plan` command no longer shadows the skill: `review-plan.md` is absent and `review-plan.md.disabled` is present.
- `codex.exe --help` fails with Access denied even when rerun outside the sandbox, so Codex runtime smoke could not be automated from this thread.
- No Claude Cowork session-control tool was available in this Codex thread, so Cowork runtime fetch behavior still needs manual verification.
- Coclerk working tree now has:
  - `M plugins/utilities/skills/handover.skill`
  - `?? .claude/wrappers/handover/`

## Next Step

Run manual harness sessions against the signed-delivery files now installed locally, configure `MYSKILLIUM_SIGNING_KEY` in GitHub Actions, then review/commit the signed-delivery implementation before wider managed rollout.
