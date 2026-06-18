# E2E v4.1 — Targeted Retest (Fixes 1 & 2 Only)

Copy everything below the line into a **new** Cowork chat session.

**Prerequisite:** The skills-hub plugin must be freshly updated from
`https://github.com/Mharbulous/skills-hub.git`. Remove the old plugin
(Customize > Plugins), then re-add it.

---

You are running targeted retests of `/skills-hub` after deploying two fixes.
Execute every step yourself. Record ALL output — do not summarize or truncate.

---

## Section 1: Smoke Check (confirm fixes are deployed)

```bash
SCRIPT=$(find / -path "*skills-hub/scripts/manage_cowork_skills.py" -type f 2>/dev/null | head -1)
echo "SCRIPT=$SCRIPT"
grep -c "fetch_github_repo_git" "$SCRIPT"
grep -c "remote-plugins" "$SCRIPT"
```

**Expected:** Both grep counts >= 1. If either is 0, STOP — plugin is still
stale. Report to maintainer.

---

## Section 2: Inventory Without `--install-root` (Fix 1)

This is the critical test. Previously returned 1 skill; should now return ~34.

Send `/skills-hub inventory`.

Record the FULL output, then answer:

1. Did it find the install root automatically?
2. How many installed skills were found?
3. How many skills are in the catalog?
4. Were any errors reported (network, download, path)?
5. Approximate elapsed time?

**PASS if:** Installed count matches the user's skill count (~34) without
needing `--install-root`.

**FAIL if:** Only 1 skill found, or error about install root.

---

## Section 3: Catalog Fetch via Git Clone (Fix 2)

Section 2 already exercises the git fallback (the catalog download must
succeed for inventory to show catalog statuses). Confirm:

1. Did the inventory show catalog-aware statuses (`current`, `stale`,
   `missing`, `conflict`, `orphan`) — not just `unrecognized`?
2. Was there any error about `codeload.github.com` or `Tunnel connection
   failed`?

If inventory showed only `unrecognized` statuses, the git fallback did NOT
activate. **FAIL.**

---

## Section 4: Install a Missing Skill (end-to-end)

From the inventory output, pick one skill with status `missing`.

Send `/skills-hub install <missing-skill-name>`.

Record the FULL output. Check:

1. Did `fetch-package` complete without network errors?
2. Did a Save-skill card appear?

If a Save-skill card appeared, click **Save skill**.

---

## Section 5: Verify Installed Skill Works

Invoke the skill installed in Section 4 (e.g., `/prototype`).

**PASS if:** The skill loads and responds with its content.
**FAIL if:** Error, empty output, or `manifest.json.sig` 404 (that would
mean it installed as a resolver wrapper instead of a direct package).

---

## Final Report

| Test | Description | Result | Notes |
|---|---|---|---|
| 1 | Fixes deployed (grep counts) | | |
| 2 | Inventory auto-detect root | | installed count, catalog count |
| 3 | Git clone fallback (catalog statuses) | | statuses seen |
| 4 | Install missing skill | | Save-skill card? |
| 5 | Installed skill works | | |

### Key Metrics

| Metric | Value |
|---|---|
| Inventory time (approx) | |
| Download method | zip / git clone |
| Installed skill count | |
| Catalog skill count | |

### Issues Found

List any errors or unexpected behaviors with full error messages.
