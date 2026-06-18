# Prompt to paste into Cowork

Copy everything below the line into a new Cowork chat.

---

You are running an E2E test of the `/skills-hub` skill on behalf of the
skills-hub maintainer (Claude Code). Act as an automated test runner: execute
every step you can perform yourself, and stop only when you need me to perform a
UI action (like clicking Save skill), grant permission, or confirm observed
behaviour. Track results using **Phase N: PASS/FAIL/SKIP — notes**.

This protocol has two parts. Part A gathers environment diagnostics that Claude
Code needs to debug install-root detection and network issues. Part B tests
the core skill flows. Run Part A fully before starting Part B.

---

## Part A: Environment Diagnostics

The maintainer needs specific data about the Cowork sandbox to verify recent
fixes. Run every diagnostic command and include ALL output — do not summarize
or truncate.

### A1. Sandbox paths

Run each command and record the exact output:

```bash
echo "HOME=$HOME"
echo "PWD=$PWD"
python3 -c "from pathlib import Path; print('Path.home():', Path.home())"
```

### A2. Plugin directory structure

Find where the skills-hub plugin is installed and show the directory tree:

```bash
find / -path "*skills-hub/scripts/manage_cowork_skills.py" -type f 2>/dev/null
```

For the first result, show the directory tree from three levels above the
`skills/` directory containing the script:

```bash
# Replace <path> with the actual parent-of-parent-of-parent of the scripts/ dir
ls -la <path>
ls -la <path>/../
ls -la <path>/../../
```

The maintainer specifically needs to know:
- Does `.remote-plugins/` appear in the path?
- What is the mount point (the common parent of `.remote-plugins/` and
  `.claude/`)?

### A3. User skill directory

```bash
find / -path "*/.claude/skills" -type d 2>/dev/null
find / -path "*/.agents/skills" -type d 2>/dev/null
```

If found, count the skills and show a sample:

```bash
ls <skills-dir>/ | head -10
ls <skills-dir>/ | wc -l
```

### A4. Context file

Check whether the skills-hub context file exists:

```bash
# Run from the skills-hub skill directory (where SKILL.md is)
cat .skills-hub-context.json 2>/dev/null || echo "ABSENT"
```

### A5. Network reachability

Test each host that skills-hub needs. The script downloads from
`codeload.github.com`, but if that is blocked, alternative GitHub CDN hosts
may still be reachable:

```bash
python3 -c "
import urllib.request
hosts = [
    'https://github.com/Mharbulous/skills-hub',
    'https://codeload.github.com/Mharbulous/skills-hub/tar.gz/main',
    'https://raw.githubusercontent.com/Mharbulous/skills-hub/main/public/manifest.json',
    'https://api.github.com/repos/Mharbulous/skills-hub',
]
for url in hosts:
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'skills-hub-test')
        r = urllib.request.urlopen(req, timeout=10)
        print(f'OK {r.status} {len(r.read())} bytes {url}')
    except Exception as e:
        print(f'FAIL {type(e).__name__}: {e} {url}')
"
```

### A6. Install root auto-detection

Run the manager script's install root detection and report what it finds:

```bash
python3 scripts/manage_cowork_skills.py inventory --json 2>&1 | head -5
```

If this returns a blocked-catalog response or an error about install roots,
that is diagnostic data — include it.

Then run with the user skill directory (from A3) explicitly:

```bash
python3 scripts/manage_cowork_skills.py inventory --install-root <A3-path> --json 2>&1 | head -20
```

### A7. Lockfile state

```bash
find / -name "skills-hub-lock.json" -type f 2>/dev/null
find / -name "skills-hub-catalog-cache.json" -type f 2>/dev/null
```

If either exists, show its contents.

### A8. Diagnostic report

Present all findings from A1–A7 in a single table:

| Diagnostic | Value |
|---|---|
| HOME | |
| Path.home() | |
| Plugin script path | |
| `.remote-plugins` in path? | yes/no |
| Mount point | |
| User skills directory | |
| User skill count | |
| Context file | present/absent |
| github.com reachable | yes/no |
| codeload.github.com reachable | yes/no |
| raw.githubusercontent.com reachable | yes/no |
| api.github.com reachable | yes/no |
| Auto-detected install root | (from A6 — what the script found without --install-root) |
| --install-root override works | yes/no |
| Lockfile exists | yes/no |
| Catalog cache exists | yes/no |

Ask the tester: "Here are the diagnostics. Should I proceed to Part B
(functional tests)?"

---

## Part B: Functional Tests

### Preconditions

Before starting, verify:

1. **Plugin installed.** The `skills-hub` plugin is loaded (you have the
   `/skills-hub` skill).
2. **Network access.** `codeload.github.com` is reachable (from A5). If not,
   add `github.com` and `codeload.github.com` to the sandbox network allowlist
   and start a new session. If still blocked after allowlisting, run only the
   phases marked "(offline OK)" and skip the rest.

### Phase 1: Bare command (offline OK)

Send `/skills-hub` with no arguments.

**Expected:** Help text listing these commands, with NO network calls or script
execution:
- `/skills-hub inventory`
- `/skills-hub install <skill>`
- `/skills-hub update`
- `/skills-hub update <skill>`
- `/skills-hub update all`

**FAIL** if it fetches remote content, runs `manage_cowork_skills.py`, or asks
the tester to paste anything.

Ask: "Did the help panel appear correctly? (PASS/FAIL)"

### Phase 2: Inventory (offline OK in degraded mode)

Send `/skills-hub inventory`.

**Normal mode (network available):** Output is a JSON array with rows containing
`name`, `status` (`current`/`missing`/`stale`/`modified`/`diverged`/`orphan`/
`conflict`), `evidence`, and `path`.

**Degraded mode (network blocked):** Output is
`{"catalog": {"status": "blocked", ...}, "installed": [...]}`.

**Critical check:** Does inventory find the user's skills WITHOUT
`--install-root`? Compare the skill count to A3. If inventory finds 0 or 1
skills but A3 showed many, the install root auto-detection is broken — report
this as **FAIL (install root)** with the exact error or output.

Present a summary table of each skill's name and status. Note one `missing`
skill for Phase 3.

Ask: "Does inventory match your install state? (PASS/FAIL)"

### Phase 3: Install a skill (requires network)

Pick a skill with status `missing` from Phase 2. Tell the tester which one and
wait for confirmation.

Then send `/skills-hub install <skill>`. The skill should:
1. Run inventory first
2. Confirm the skill is missing
3. Run `fetch-package <skill> --json`
4. Present the `.skill` package via `mcp__cowork__present_files`

**FAIL** if fetch-package errors, if the path appears as text instead of a
Save-skill card, or if it asks the tester to paste anything.

Tell the tester: "A Save-skill card should be visible. Please click Save skill."

After confirmation, run `/skills-hub inventory` again. The installed skill
should show `current`.

Also check whether `record-install` was called — run:

```bash
find / -name "skills-hub-lock.json" -type f 2>/dev/null
```

If the lockfile exists, show the entry for the installed skill.

Ask: "The skill now shows current. Correct? (PASS/FAIL/EXPECTED LIMITATION)"

### Phase 4: Update a stale skill (requires network)

Run only if Phase 2 showed a `stale` skill. Otherwise skip.

Send `/skills-hub update <skill>`. Same flow as Phase 3 — fetch-package,
Save-skill card, verify inventory shows `current` after.

**FAIL** if it tries to update a skill that isn't `stale`.

### Phase 5: Update all (requires network)

Run only if multiple `stale` skills remain after Phase 4. Otherwise skip.

Send `/skills-hub update all`. It should list all stale targets, ask for one
confirmation, then present one Save-skill card per target.

### Phase 6: Negative cases

**6a** — Send `/skills-hub install this-skill-does-not-exist`. Must error
cleanly and not present a Save-skill card.

**6b** — Pick a `current` skill and send `/skills-hub update <that-skill>`.
Must refuse because the skill is not stale.

**6c** — Blocked catalog (skip if network was already down). Ask the tester
to temporarily disconnect. Run `/skills-hub inventory` — expect blocked-catalog
JSON. Run `/skills-hub install <any-skill>` — expect refusal. Remind tester to
restore network.

**6d** — Modified status (optional — requires a previously installed skill with
a lockfile entry). Manually edit the installed skill's SKILL.md (add a comment
line). Run `/skills-hub inventory` — expect `modified`. Run
`/skills-hub update <that-skill>` — expect a warning about local edits.

Ask for PASS/FAIL on each sub-phase.

### Phase 7: Cross-session persistence

Tell the tester: "Please start a new Cowork chat and run `/skills-hub
inventory`. Report whether the skills we installed still show as current."

### Phase 8: Installed skill functionality

In the new session from Phase 7, ask the tester to invoke one of the skills
installed in Phase 3.

Ask: "Did the installed skill load and respond correctly? (PASS/FAIL)"

---

## Final Report

After all phases, present this table:

| Phase | Description | Result | Notes |
|-------|-------------|--------|-------|
| A | Environment diagnostics | | |
| 1 | Bare command | | |
| 2 | Inventory | | |
| 3 | Install a skill | | |
| 4 | Update stale skill | | |
| 5 | Update all | | |
| 6a | Install non-existent | | |
| 6b | Update current skill | | |
| 6c | Blocked catalog | | |
| 6d | Modified status | | |
| 7 | Cross-session persistence | | |
| 8 | Installed skill works | | |

Then write the full report (diagnostics table + phase results + any issues
found) to a file in the session outputs directory:

```
outputs/skills-hub-e2e-test-report.md
```

Tell the tester the file path so they can share it with Claude Code.
