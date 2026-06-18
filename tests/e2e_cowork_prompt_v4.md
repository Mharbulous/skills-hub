# E2E Functional Test v4 — Live `/skills-hub` Commands

Copy everything below the line into a **new** Cowork chat session.

**Prerequisite:** The skills-hub plugin must be freshly installed from the
repository `https://github.com/Mharbulous/skills-hub.git`. If a previous
version was installed, remove it from Customize > Plugins and re-add it.

---

You are running functional tests of the `/skills-hub` skill on behalf of
the skills-hub maintainer (Claude Code). Execute every step yourself. Record
ALL output — do not summarize or truncate.

This protocol tests the live `/skills-hub` commands after deploying two fixes:
1. Install root detection via `.remote-plugins` ancestor walk
2. Git clone fallback when zip download from `codeload.github.com` is blocked

---

## Section 1: Quick Smoke Check

Before running commands, verify the environment is ready.

### 1A. Confirm plugin is loaded

```bash
# Find the plugin script
SCRIPT=$(find / -path "*skills-hub/scripts/manage_cowork_skills.py" -type f 2>/dev/null | head -1)
echo "SCRIPT=$SCRIPT"

# Verify it has the git fallback (search for the new function)
grep -c "fetch_github_repo_git" "$SCRIPT"

# Verify it has the .remote-plugins detection
grep -c "remote-plugins" "$SCRIPT"
```

**Expected:** Script found, both grep counts >= 1. If either is 0, the
deployed code is stale — stop and report to the maintainer.

### 1B. Confirm skills directory

```bash
SKILLS_DIR=$(find / -path "*/.claude/skills" -type d 2>/dev/null | head -1)
echo "SKILLS_DIR=$SKILLS_DIR"
echo "SKILL_COUNT=$(ls "$SKILLS_DIR" 2>/dev/null | wc -l)"
```

---

## Section 2: Bare Command

Send `/skills-hub` with no arguments.

**Expected:** Help text listing these commands:
- `/skills-hub inventory`
- `/skills-hub install <skill>`
- `/skills-hub update`
- `/skills-hub update <skill>`
- `/skills-hub update all`

**FAIL if:** It fetches remote content, runs the script, or asks the tester
to paste anything. The bare command should only display help text.

Record: **PASS** or **FAIL** with the exact output.

---

## Section 3: Inventory (Critical Path)

This is the most important test. It validates both the install root fix AND
the git fallback working together.

### 3A. Run inventory

Send `/skills-hub inventory`.

Record the FULL output. Then answer these questions:

1. Did the script find the install root automatically (without `--install-root`)?
2. How many installed skills were found?
3. How many skills are in the catalog?
4. What statuses appear? (current/missing/stale/modified/diverged/orphan/conflict)
5. Did it use git clone or zip download? (Check stderr or timing — git clone
   takes ~3s; if the command completed in ~3-5s total, it used git)

### 3B. Verify skill count matches

Compare the inventory installed count to the skill count from Section 1B.
They should match (or be very close — inventory excludes `skills-hub` itself).

### 3C. Pick test candidates

From the inventory output, identify:
- One skill with status `missing` → note the name for Section 4
- One skill with status `current` → note the name for Section 6b
- Any skills with status `stale` → note for Section 5

---

## Section 4: Install a Skill

### 4A. Install a missing skill

Send `/skills-hub install <missing-skill-name>` (using the skill identified
in Section 3C).

Record the FULL output. Check:

1. Did it run `inventory` first to confirm the skill is missing?
2. Did it run `fetch-package <skill> --json`?
3. Did a Save-skill card appear (via `mcp__cowork__present_files`)?
4. Was there any error about network, download, or git?

If a Save-skill card appeared, click **Save skill** now.

### 4B. Verify installation

After clicking Save skill, send `/skills-hub inventory` again.

Check: Does the newly installed skill show status `current`?

### 4C. Check lockfile

```bash
find / -name "skills-hub-lock.json" -type f 2>/dev/null
```

If found, show the entry for the installed skill:

```bash
python3 -c "
import json
from pathlib import Path
lockfile = Path('$(find / -name "skills-hub-lock.json" -type f 2>/dev/null | head -1)')
if lockfile.is_file():
    data = json.loads(lockfile.read_text())
    entries = data.get('installed', {})
    print(f'Total lockfile entries: {len(entries)}')
    for name in sorted(entries):
        print(f'  {name}: {entries[name].get(\"catalog_hash\", \"?\")[:16]}...')
else:
    print('No lockfile found')
"
```

**Note:** If the lockfile is absent or the write failed with a read-only
error, that's diagnostic data — record it. The install still works via
Save-skill even without the lockfile.

---

## Section 5: Update (if stale skills exist)

Skip this section if no skills showed `stale` in Section 3A.

### 5A. Update a single stale skill

Send `/skills-hub update <stale-skill-name>`.

Check:
1. Did it confirm the skill is stale?
2. Did a Save-skill card appear?

If a card appeared, click **Save skill**.

### 5B. Update all (if multiple stale)

Skip if only one stale skill existed.

Send `/skills-hub update all`.

Check: Does it list all stale targets and present Save-skill cards?

---

## Section 6: Negative Cases

### 6a. Install non-existent skill

Send `/skills-hub install this-skill-does-not-exist-xyz`.

**Expected:** Clean error message. No Save-skill card. No crash.

### 6b. Update a current skill

Send `/skills-hub update <current-skill-name>` (from Section 3C).

**Expected:** Refusal because the skill is already current. No Save-skill card.

### 6c. Install an already-installed skill

Send `/skills-hub install <the-skill-installed-in-Section-4>`.

**Expected:** Should indicate the skill is already installed / current.

---

## Section 7: Installed Skill Works

Invoke the skill that was installed in Section 4. For example, if you
installed `prototype`, send `/prototype` and verify it loads and responds.

**PASS if:** The skill loads its SKILL.md content and responds appropriately.
**FAIL if:** The skill is not found, shows an error, or produces empty output.

---

## Section 8: Cross-Session Persistence

Tell the tester:

> Please start a **new** Cowork chat session and run these checks:
>
> 1. Send `/skills-hub inventory` — does the skill installed in Section 4
>    still show as `current`?
> 2. Invoke the installed skill — does it still work?
>
> Report the results back to Claude Code.

---

## Final Report

Present results in this format:

### Environment

| Check | Result |
|---|---|
| Plugin script found | yes/no + path |
| Git fallback present in code | yes/no (grep count) |
| .remote-plugins detection present | yes/no (grep count) |
| Skills directory | path + count |

### Functional Tests

| Phase | Description | Result | Notes |
|---|---|---|---|
| 2 | Bare command | | |
| 3A | Inventory (auto-detect root) | | |
| 3B | Skill count matches | | |
| 4A | Install missing skill | | |
| 4B | Verify install (current) | | |
| 4C | Lockfile written | | |
| 5A | Update stale skill | | |
| 5B | Update all | | |
| 6a | Install non-existent | | |
| 6b | Update current | | |
| 6c | Install already-installed | | |
| 7 | Installed skill works | | |
| 8 | Cross-session persistence | | |

### Key Metrics

| Metric | Value |
|---|---|
| Inventory time (approx) | |
| Download method used | zip / git clone |
| Catalog skill count | |
| Installed skill count | |
| Stale skills found | |

### Issues Found

List any errors, unexpected behaviors, or edge cases encountered.
Include full error messages and stack traces if any.

### Recommendations for Maintainer

Based on the results:
1. Does `/skills-hub inventory` work without `--install-root`? (yes/no)
2. Does the git fallback activate and complete successfully? (yes/no)
3. Does the full install flow work end-to-end? (yes/no)
4. Are there any remaining issues to fix before release? (list)

Write the full report to:

```
outputs/skills-hub-e2e-v4.md
```

Tell the tester the file path so they can share it with Claude Code.
