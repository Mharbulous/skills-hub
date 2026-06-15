# E2E Test: Skills-hub Skill in Claude Cowork

Guide a human tester through a full end-to-end test of the `/skills-hub` skill
inside Claude Cowork. Execute every step you can perform automatically. Stop
only when you need the human to perform a UI action, grant permission, or
confirm that observed behaviour matches expectations.

## Preconditions

Before starting, verify all of the following. If any fail, stop and report
which precondition is unmet.

1. **Plugin installed.** The `skills-hub` plugin is installed in Cowork from the
   Git repository `https://github.com/Mharbulous/skills-hub.git`. If not
   installed, ask the tester to install it via Customize > Plugins > Add from a
   repository before continuing.
2. **Fresh chat.** This test must run in a new Cowork chat so the skill is
   loaded from scratch.
3. **Network access.** `mharbulous.github.io/skills-hub` is reachable. Test with a quick
   fetch of `https://mharbulous.github.io/skills-hub/manifest.json` — a 200 response
   confirms connectivity. If it fails, note this and plan to test degraded-mode
   inventory (Phase 2b) instead of the normal flow.
4. **ssh-keygen available.** Run `ssh-keygen -h` to confirm it is on PATH.
   Signature verification requires it.

Tell the tester which preconditions passed and which need action.

---

## Phase 1: Bare Command

**Goal:** `/skills-hub` shows local help only — no network calls, no inventory,
no fetching.

### Steps

1. Send `/skills-hub` in the chat.
2. Observe the response.

### Expected

The response must contain all five of these command references:
- `/skills-hub inventory`
- `/skills-hub install <skill>`
- `/skills-hub update`
- `/skills-hub update <skill>`
- `/skills-hub update all`

### Failures

- **FAIL** if the response fetches remote content (manifest, catalog, packages).
- **FAIL** if the response runs `manage_cowork_skills.py` with any subcommand.
- **FAIL** if the response asks the tester to paste a URL, script, or manifest.

### Checkpoint

Ask the tester: *"Did the bare `/skills-hub` command show a help/status panel
listing the five commands above, without fetching any remote data?"*

Record: PASS or FAIL with details.

---

## Phase 2: Inventory

**Goal:** `/skills-hub inventory` runs the management script, contacts
`mharbulous.github.io/skills-hub` for a signed manifest, and reports each cataloged skill
with a status.

### Steps

1. Send `/skills-hub inventory` in the chat.
2. Cowork should run:
   ```
   python scripts/manage_cowork_skills.py inventory --json
   ```
3. Observe the JSON output.

### Expected — Normal Mode

The output is a JSON array. Each element has these fields:
- `name` — skill name (string)
- `status` — one of: `current`, `missing`, `stale-wrapper`, `orphan`, `conflict`
- `evidence` — human-readable explanation (string)
- `path` — filesystem path (string, may be empty for `missing`)

There must be at least one row. Most skills should show `missing` on a fresh
install (before any `/skills-hub install` has been run). If skills were
previously installed, they may show `current` or `stale-wrapper`.

### Expected — Degraded Mode (catalog blocked)

If the manifest is unreachable or fails signature/freshness verification, the
output is a JSON object with:
```json
{
  "catalog": { "status": "blocked", "error": "<reason>" },
  "installed": [ ... ]
}
```

The `installed` array lists locally-found skills with `local_status` values
(`skills-hub-wrapper`, `stale-wrapper-marker`, `unrecognized`). This is
acceptable — it means degraded mode works correctly.

### Checkpoint

Ask the tester: *"Inventory ran. Here is the output summary. Does this look
correct for your current install state?"*

Present a table summarizing each row's name and status. The tester confirms
whether the statuses match their expectations (e.g. if they haven't installed
any skills yet, everything except `skills-hub` itself should be `missing`).

Record: PASS or FAIL with details.

**Important:** Note one skill name with status `missing` — you will use it in
Phase 3. If no skills are `missing`, note one with status `stale-wrapper` for
Phase 4 instead. If all are `current` and none are stale, report this and skip
to Phase 5.

---

## Phase 3: Install a Skill

**Goal:** `/skills-hub install <skill>` fetches a verified `.skill` package,
presents a Save-skill card via `mcp__cowork__present_files`, and the tester
clicks Save.

### Pre-check

Pick the `missing` skill noted in Phase 2. Tell the tester which skill you are
about to install and ask for confirmation before proceeding.

### Steps

1. Send `/skills-hub install <skill>` (substituting the chosen skill name).
2. Cowork should:
   a. Run inventory first (per SKILL.md instructions).
   b. Confirm the skill is `missing` or ask for bounded confirmation if `current`.
   c. Run `python scripts/manage_cowork_skills.py fetch-package <skill> --json`.
   d. Present the returned `package_path` via `mcp__cowork__present_files`.
3. A **Save skill** card should appear in the chat.

### User Action Required

Tell the tester: *"A Save-skill card should now be visible. Please click
**Save skill** to import the package into Cowork."*

Wait for the tester to confirm they clicked Save.

### Verification

After the tester confirms Save:
1. Run `/skills-hub inventory` again.
2. The skill that was just installed must now show `status: "current"`.

### Failures

- **FAIL** if `fetch-package` exits with a non-zero code (signature, hash,
  size, or freshness check failed).
- **FAIL** if no Save-skill card appears (the path was printed as bare text
  instead of presented via `mcp__cowork__present_files`).
- **FAIL** if inventory after Save still shows `missing` for the skill.
  Note: If Cowork requires a session restart to detect new skills, this is
  acceptable — record it as EXPECTED LIMITATION and ask the tester to start a
  new chat and rerun inventory from that chat.

### Checkpoint

Ask the tester: *"The installed skill now shows as `current` in inventory.
Does this match your expectations?"*

Record: PASS, FAIL, or EXPECTED LIMITATION with details.

---

## Phase 4: Update a Stale Wrapper

**Goal:** `/skills-hub update <skill>` replaces a stale wrapper with the
current verified package.

### Applicability

Run this phase only if Phase 2 inventory showed at least one skill with
`status: "stale-wrapper"`. If none exist, tell the tester: *"No stale
wrappers detected — skipping Phase 4."* and move to Phase 5.

### Steps

1. Pick a `stale-wrapper` skill from inventory.
2. Tell the tester which skill you will update and ask for confirmation.
3. Send `/skills-hub update <skill>`.
4. Cowork should:
   a. Run inventory first.
   b. Confirm the skill is `stale-wrapper`.
   c. Run `fetch-package <skill> --json`.
   d. Present the Save-skill card.

### User Action Required

Tell the tester: *"A Save-skill card should now be visible for the updated
package. Please click **Save skill**."*

### Verification

After Save:
1. Run `/skills-hub inventory`.
2. The updated skill must now show `status: "current"`.

### Failures

Same as Phase 3, plus:
- **FAIL** if Cowork attempts to update a skill that is not `stale-wrapper`.

### Checkpoint

Ask the tester: *"The updated skill now shows `current`. Correct?"*

Record: PASS, FAIL, or EXPECTED LIMITATION.

---

## Phase 5: Update All

**Goal:** `/skills-hub update all` batch-updates every `stale-wrapper` skill.

### Applicability

Run this phase only if inventory shows at least one `stale-wrapper` skill. If
Phase 4 already updated the only stale wrapper (and no others remain), tell the
tester: *"No remaining stale wrappers — skipping Phase 5."* and move to
Phase 6.

### Steps

1. Send `/skills-hub update all`.
2. Cowork should:
   a. Run inventory.
   b. List all `stale-wrapper` targets.
   c. Ask for a single bounded confirmation.
   d. Run `fetch-package` for each.
   e. Present one Save-skill card per target.

### User Action Required

Tell the tester: *"Save-skill cards should appear for each stale wrapper.
Please click **Save skill** on each one."*

### Verification

After all Saves:
1. Run `/skills-hub inventory`.
2. All previously stale skills must now show `current`.

### Checkpoint

Ask the tester: *"All stale wrappers are now current. Correct?"*

Record: PASS, FAIL, or EXPECTED LIMITATION.

---

## Phase 6: Negative Cases

**Goal:** Verify that error paths fail closed and report clear messages.

### 6a: Install a Non-Existent Skill

1. Send `/skills-hub install this-skill-does-not-exist`.
2. `fetch-package` must return structured JSON
   (`{"error": "skill not found in catalog", "skill": "this-skill-does-not-exist"}`)
   and exit non-zero — no raw Python traceback. The install must not proceed.
3. No Save-skill card should appear.

Ask the tester: *"Did the install correctly refuse with an error message?"*

### 6b: Update a Current Skill

1. Pick a skill that shows `status: "current"` in the latest inventory.
2. Send `/skills-hub update <that-skill>`.
3. The response must report that the skill is not `stale-wrapper` and stop.

Ask the tester: *"Did the update correctly refuse because the skill is
current?"*

### 6c: Blocked Catalog Behaviour

This sub-phase tests degraded mode. Skip if network was already down during
Phase 2.

1. If possible, disconnect from the network or ask the tester to temporarily
   block `mharbulous.github.io/skills-hub`.
2. Run `/skills-hub inventory`.
3. Expect a blocked-catalog JSON object with a clear `error` field.
4. Run `/skills-hub install <any-skill>`.
5. Expect the install to refuse because the catalog is blocked.

Ask the tester: *"With the catalog blocked, did inventory show a degraded
response and did install correctly refuse?"*

Remind the tester to restore network access.

### Checkpoint

Record each sub-phase: PASS or FAIL with details.

---

## Phase 7: Cross-Session Persistence

**Goal:** Skills installed via Save-skill persist into new Cowork sessions.

### Steps

1. Ask the tester to start a **new Cowork chat** (not continue this one).
2. In the new chat, the tester should send `/skills-hub inventory`.
3. Skills installed in Phase 3 and Phase 4 should still show `current`.

### User Action Required

Tell the tester: *"Please start a new Cowork chat and run `/skills-hub
inventory`. Report back the statuses of the skills we installed earlier."*

### Checkpoint

Ask the tester: *"Do the previously installed skills still show as `current`
in the new session?"*

Record: PASS or FAIL.

---

## Phase 8: Installed Skill Functionality

**Goal:** A skill installed via `/skills-hub install` actually works when
invoked.

### Steps

1. In the new session from Phase 7, identify one of the skills installed in
   Phase 3.
2. Send the installed skill's slash command (e.g., `/troubleshooting` if
   `troubleshooting` was installed).
3. Observe whether Cowork loads the skill and responds with its expected
   behaviour.

### User Action Required

Tell the tester: *"Try invoking the skill we installed. Does it load and
respond as expected?"*

### Checkpoint

Record: PASS or FAIL with details about what the skill did or didn't do.

---

## Results Summary

After all phases complete, present a summary table:

| Phase | Description               | Result | Notes |
|-------|---------------------------|--------|-------|
| 1     | Bare command              |        |       |
| 2     | Inventory                 |        |       |
| 3     | Install a skill           |        |       |
| 4     | Update stale wrapper      |        |       |
| 5     | Update all                |        |       |
| 6a    | Install non-existent      |        |       |
| 6b    | Update current skill      |        |       |
| 6c    | Blocked catalog           |        |       |
| 7     | Cross-session persistence |        |       |
| 8     | Installed skill works     |        |       |

Ask the tester for any additional observations or edge cases they noticed.
