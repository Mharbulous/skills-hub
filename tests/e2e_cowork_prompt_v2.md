# E2E Diagnostic Protocol v2

Copy everything below the line into a **new** Cowork chat session.

---

You are running diagnostics for the skills-hub maintainer (Claude Code).
Execute every step yourself. Record ALL output — do not summarize or truncate.

This protocol has three sections:
- **Section 1**: Verify install root fix logic against the live sandbox
- **Section 2**: Probe which GitHub CDN hosts the sandbox proxy allows
- **Section 3**: Test a full skill download via any working host

Run all three sections, then present the final report.

---

## Section 1: Install Root Fix Verification

The maintainer wrote a fix for install root detection but hasn't deployed it
yet. This section runs the fix logic as standalone Python to verify it would
work in this sandbox.

### 1A. Gather paths

```bash
# Find the plugin script
SCRIPT=$(find / -path "*skills-hub/scripts/manage_cowork_skills.py" -type f 2>/dev/null | head -1)
echo "SCRIPT=$SCRIPT"

# Find user skills
SKILLS_DIR=$(find / -path "*/.claude/skills" -type d 2>/dev/null | head -1)
echo "SKILLS_DIR=$SKILLS_DIR"
echo "SKILL_COUNT=$(ls "$SKILLS_DIR" 2>/dev/null | wc -l)"
```

### 1B. Simulate the fix

The fix walks ancestors from the script directory looking for
`.remote-plugins`. When found, it checks if `.claude/skills/` exists as a
sibling under the same parent (the mount point).

Run this simulation — it replicates the exact logic from the pending fix:

```python
python3 -c "
from pathlib import Path
import os

# Replicate skill_dir() and script_dir()
script_path = Path('$SCRIPT').resolve()
scripts_dir = script_path.parent        # .../scripts/
skill_dir = scripts_dir.parent          # .../skills-hub/
parent = skill_dir.parent               # .../skills/

print(f'script_path: {script_path}')
print(f'skill_dir:   {skill_dir}')
print(f'parent:      {parent}')
print(f'parent.name: {parent.name}')
print()

if parent.name == 'skills' and parent.parent.exists():
    plugin_level = parent.parent
    print(f'plugin_level: {plugin_level}')
    print(f'Walking ancestors from plugin_level...')
    for ancestor in plugin_level.parents:
        print(f'  checking: {ancestor} (name={ancestor.name})')
        if ancestor.name == 'skills-plugin':
            print(f'  -> MATCH: skills-plugin at {ancestor}')
            print(f'  -> RESULT: [{ancestor}]')
            break
        if ancestor.name == '.remote-plugins':
            print(f'  -> MATCH: .remote-plugins at {ancestor}')
            claude_dir = ancestor.parent / '.claude'
            skills_sub = claude_dir / 'skills'
            print(f'  -> claude_dir: {claude_dir}')
            print(f'  -> claude_dir/skills exists: {skills_sub.is_dir()}')
            if skills_sub.is_dir():
                skill_count = len(list(skills_sub.iterdir()))
                print(f'  -> skill count: {skill_count}')
                print(f'  -> RESULT: [{claude_dir}]')
            else:
                print(f'  -> RESULT: [{plugin_level}] (no .claude/skills sibling)')
            break
    else:
        print(f'  No matching ancestor found.')
        print(f'  -> RESULT: [{plugin_level}]')
else:
    print(f'parent.name is not skills or parent.parent missing')
    print(f'  -> RESULT: []')

# Also test HOME-based fallback
print()
home = Path.home()
claude_home = home / '.claude'
print(f'Path.home(): {home}')
print(f'HOME/.claude: {claude_home}')
print(f'HOME/.claude/skills exists: {(claude_home / \"skills\").is_dir()}')
# Check mnt variant
mnt_claude = home / 'mnt' / '.claude'
print(f'HOME/mnt/.claude: {mnt_claude}')
print(f'HOME/mnt/.claude/skills exists: {(mnt_claude / \"skills\").is_dir()}')
"
```

**Expected result:** The simulation should find `.remote-plugins` in the
ancestor walk, then locate `.claude/skills` as a sibling under the mount
point, and return the `.claude` directory as the install root. The HOME-based
fallback will likely NOT find `.claude/skills` because HOME points to
`/sessions/.../` not `/sessions/.../mnt/`.

Record exactly what the simulation prints.

---

## Section 2: GitHub Host Reachability

The script currently downloads from `codeload.github.com`, which is blocked
in the sandbox. Test every alternative GitHub host that could serve file
content:

```bash
python3 -c "
import urllib.request

tests = [
    ('github.com',               'https://github.com/Mharbulous/skills-hub'),
    ('codeload (zip)',           'https://codeload.github.com/Mharbulous/skills-hub/zip/main'),
    ('codeload (tar.gz)',        'https://codeload.github.com/Mharbulous/skills-hub/tar.gz/main'),
    ('raw.githubusercontent',    'https://raw.githubusercontent.com/Mharbulous/skills-hub/main/public/manifest.json'),
    ('api.github.com (repo)',    'https://api.github.com/repos/Mharbulous/skills-hub'),
    ('api.github.com (contents)','https://api.github.com/repos/Mharbulous/skills-hub/contents/public/skills?ref=main'),
    ('github.com /archive/',     'https://github.com/Mharbulous/skills-hub/archive/refs/heads/main.zip'),
    ('objects.githubusercontent', 'https://objects.githubusercontent.com'),
]
for label, url in tests:
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'skills-hub-test/1')
        r = urllib.request.urlopen(req, timeout=15)
        data = r.read()
        print(f'OK  {r.status:3d}  {len(data):>8d} bytes  {label:30s}  {url}')
    except Exception as e:
        ename = type(e).__name__
        print(f'FAIL {ename:20s}  {label:30s}  {url}')
        print(f'     {e}')
"
```

**Critical question:** Which hosts return OK? If `raw.githubusercontent.com`
or `api.github.com` works, the maintainer can add a fallback download path.

---

## Section 3: Skill Download Simulation

This section only runs if Section 2 found at least one working host besides
`github.com` itself. Pick the first working host from this priority order:

1. `raw.githubusercontent.com`
2. `api.github.com`

### 3A. If raw.githubusercontent.com works

Test fetching an actual skill's content:

```bash
python3 -c "
import urllib.request, json

base = 'https://raw.githubusercontent.com/Mharbulous/skills-hub/main'

# Fetch manifest to get the skill list
manifest_url = f'{base}/public/manifest.json'
req = urllib.request.Request(manifest_url, headers={'User-Agent': 'skills-hub-test/1'})
resp = urllib.request.urlopen(req, timeout=15)
manifest = json.loads(resp.read())
print(f'Manifest: {len(manifest.get(\"skills\", []))} skills')
print(f'First 5: {[s[\"name\"] for s in manifest.get(\"skills\", [])[:5]]}')
print()

# Pick the first skill and fetch its SKILL.md
skill_name = manifest['skills'][0]['name']
skill_md_url = f'{base}/public/skills/{skill_name}/SKILL.md'
req2 = urllib.request.Request(skill_md_url, headers={'User-Agent': 'skills-hub-test/1'})
resp2 = urllib.request.urlopen(req2, timeout=15)
content = resp2.read().decode('utf-8')
print(f'Fetched SKILL.md for \"{skill_name}\": {len(content)} chars')
print(f'First 200 chars:')
print(content[:200])
print()

# Check if scripts/ dir has files
scripts_url = f'{base}/public/skills/{skill_name}/scripts/'
try:
    req3 = urllib.request.Request(scripts_url, headers={'User-Agent': 'skills-hub-test/1'})
    resp3 = urllib.request.urlopen(req3, timeout=15)
    print(f'scripts/ dir: OK {resp3.status}')
except Exception as e:
    print(f'scripts/ dir: {e} (expected — raw.githubusercontent does not list directories)')
    print('Would need api.github.com to list script files, or a manifest that includes file paths.')
"
```

### 3B. If api.github.com works but raw.githubusercontent.com does not

Test fetching the skill list and a skill file via the API:

```bash
python3 -c "
import urllib.request, json, base64

api = 'https://api.github.com/repos/Mharbulous/skills-hub'
headers = {'User-Agent': 'skills-hub-test/1', 'Accept': 'application/vnd.github.v3+json'}

# List skills in public/skills/
url = f'{api}/contents/public/skills?ref=main'
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
entries = json.loads(resp.read())
dirs = [e['name'] for e in entries if e['type'] == 'dir']
print(f'Skills in public/skills/: {len(dirs)}')
print(f'First 5: {dirs[:5]}')
print()

# Fetch one skill's SKILL.md
skill = dirs[0]
url2 = f'{api}/contents/public/skills/{skill}/SKILL.md?ref=main'
req2 = urllib.request.Request(url2, headers=headers)
resp2 = urllib.request.urlopen(req2, timeout=15)
file_info = json.loads(resp2.read())
content = base64.b64decode(file_info['content']).decode('utf-8')
print(f'Fetched SKILL.md for \"{skill}\": {len(content)} chars')
print(f'First 200 chars:')
print(content[:200])
print()

# List files in the skill directory (to know what to download)
url3 = f'{api}/contents/public/skills/{skill}?ref=main'
req3 = urllib.request.Request(url3, headers=headers)
resp3 = urllib.request.urlopen(req3, timeout=15)
files = json.loads(resp3.read())
print(f'Files in {skill}/:')
for f in files:
    print(f'  {f[\"type\"]:4s} {f[\"size\"]:>8d}  {f[\"name\"]}')
"
```

### 3C. If neither alternative host works

Report this and skip to the final report. The maintainer will need to
investigate the sandbox network policy with Anthropic.

---

## Final Report

Present results in this format:

### Install Root Fix Simulation

| Check | Result |
|---|---|
| `.remote-plugins` found in ancestor walk | yes/no |
| Mount point identified | (path) |
| `.claude/skills` found as sibling | yes/no + skill count |
| Fix would return correct install root | yes/no + path |
| HOME fallback would help | yes/no (and why) |

### Network Host Reachability

| Host | Status | Bytes | Notes |
|---|---|---|---|
| github.com | | | |
| codeload.github.com (zip) | | | |
| codeload.github.com (tar.gz) | | | |
| raw.githubusercontent.com | | | |
| api.github.com (repo) | | | |
| api.github.com (contents) | | | |
| github.com /archive/ | | | |
| objects.githubusercontent.com | | | |

### Skill Download Test

| Step | Result | Notes |
|---|---|---|
| Fetch manifest | | |
| Fetch SKILL.md | | |
| List skill files | | |

### Recommendations for Maintainer

Based on the results, state:
1. Is the install root fix correct for this sandbox? (yes/no + evidence)
2. Which download host should the fallback use? (host + evidence)
3. Can a complete skill package be downloaded via the fallback? (yes/no + what's missing)

Write the full report to:

```
outputs/skills-hub-diagnostic-v2.md
```

Tell the tester the file path so they can share it with Claude Code.
