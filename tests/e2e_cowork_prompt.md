# Prompt to paste into Cowork

Copy everything below the line into a new Cowork chat.

---

You are running an E2E test of the `/skills-hub` skill. Act as an automated test runner: execute every step you can perform yourself, and stop only when you need me to perform a UI action (like clicking Save skill), grant permission, or confirm observed behaviour.

Track results as you go using this format: **Phase N: PASS/FAIL/SKIP — notes**.

## Preconditions — verify these first

1. Confirm the `skills-hub` plugin is loaded (you should have the `/skills-hub` skill available).
2. Test network access by fetching `https://skills-hub.web.app/manifest.json`. Note if this fails — you'll test degraded mode instead.
3. Confirm `ssh-keygen` is on PATH by running `ssh-keygen -h`.

Report which preconditions passed and which need action. Stop if the plugin isn't installed.

## Phase 1: Bare Command

Run `/skills-hub`. Verify the response shows local help listing these five commands and does NOT fetch any remote data or run the management script:
- `/skills-hub inventory`
- `/skills-hub install <skill>`
- `/skills-hub update`
- `/skills-hub update <skill>`
- `/skills-hub update all`

FAIL if it fetches remote content, runs `manage_cowork_skills.py`, or asks me to paste anything.

Ask me: "Did the help panel appear correctly without any network activity? (PASS/FAIL)"

## Phase 2: Inventory

Run `/skills-hub inventory`. The skill should run `python scripts/manage_cowork_skills.py inventory --json`.

**Normal mode:** Output is a JSON array with rows containing `name`, `status` (`current`/`missing`/`stale-wrapper`/`orphan`/`conflict`), `evidence`, and `path`.

**Degraded mode:** If the manifest can't be verified, output is `{"catalog": {"status": "blocked", "error": "..."}, "installed": [...]}`. This is acceptable — it means degraded mode works.

Present a summary table of each skill's name and status. Note one `missing` skill for Phase 3 and any `stale-wrapper` skills for Phase 4/5.

Ask me: "Does this inventory look correct for your current install state? (PASS/FAIL)"

## Phase 3: Install a Skill

Pick a skill with status `missing` from Phase 2. Tell me which one and wait for my confirmation before proceeding.

Then run `/skills-hub install <skill>`. The skill should:
1. Run inventory first
2. Confirm the skill is missing
3. Run `fetch-package <skill> --json` (downloads manifest, verifies signature/hash/size)
4. Present the `.skill` package via `mcp__cowork__present_files` so a Save-skill card appears

FAIL if fetch-package errors, if the path is printed as text instead of a Save-skill card, or if it asks me to paste anything.

Tell me: "A Save-skill card should be visible. Please click Save skill."

After I confirm, run `/skills-hub inventory` again. The installed skill must now show `current`.

If inventory still shows `missing`, note it as EXPECTED LIMITATION (Cowork may need a new session to detect new skills) and ask me to verify in a new chat.

Ask me: "The skill now shows current. Correct? (PASS/FAIL/EXPECTED LIMITATION)"

## Phase 4: Update a Stale Wrapper

Run only if Phase 2 showed a `stale-wrapper`. Otherwise say "No stale wrappers — skipping Phase 4" and move on.

If applicable: tell me which stale skill you'll update, wait for confirmation, then run `/skills-hub update <skill>`. Same flow as Phase 3 — fetch-package, Save-skill card, verify inventory shows `current` after.

FAIL if it tries to update a skill that isn't `stale-wrapper`.

## Phase 5: Update All

Run only if multiple `stale-wrapper` skills remain after Phase 4. Otherwise skip.

Run `/skills-hub update all`. It should list all stale targets, ask for one confirmation, then fetch-package and present a Save-skill card for each.

Tell me to click Save on each card. Then verify all updated skills show `current` in inventory.

## Phase 6: Negative Cases

### 6a — Run `/skills-hub install this-skill-does-not-exist`. It must error and not present a Save-skill card.

### 6b — Pick a `current` skill and run `/skills-hub update <that-skill>`. It must refuse because the skill is not stale.

### 6c — Blocked catalog (skip if network was already down in Phase 2). Ask me to temporarily disconnect from the network or block `skills-hub.web.app`. Then:
- Run `/skills-hub inventory` — expect blocked-catalog response.
- Run `/skills-hub install <any-skill>` — expect refusal.
- Remind me to restore network access.

Ask me for PASS/FAIL on each sub-phase.

## Phase 7: Cross-Session Persistence

Tell me: "Please start a new Cowork chat and run `/skills-hub inventory`. Report back whether the skills we installed still show as current."

Record PASS/FAIL based on my response.

## Phase 8: Installed Skill Functionality

In the new session from Phase 7, tell me to invoke one of the skills we installed (e.g. if we installed `troubleshooting`, try `/troubleshooting`).

Ask me: "Did the installed skill load and respond correctly? (PASS/FAIL)"

## Final Summary

After all phases, present this table filled in with results:

| Phase | Description | Result | Notes |
|-------|-------------|--------|-------|
| 1 | Bare command | | |
| 2 | Inventory | | |
| 3 | Install a skill | | |
| 4 | Update stale wrapper | | |
| 5 | Update all | | |
| 6a | Install non-existent | | |
| 6b | Update current skill | | |
| 6c | Blocked catalog | | |
| 7 | Cross-session persistence | | |
| 8 | Installed skill works | | |

Ask me if I noticed anything else worth recording.
