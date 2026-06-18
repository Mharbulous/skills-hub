# E2E Diagnostic Protocol v3 — Git Fallback Integration Test

Copy everything below the line into a **new** Cowork chat session.

---

You are running diagnostics for the skills-hub maintainer (Claude Code).
Execute every step yourself. Record ALL output — do not summarize or truncate.

This protocol tests whether git-based downloads work end-to-end in this
sandbox, simulating the fallback mechanism that will replace the blocked
zip download. It also does a mini-integration test: fetching a real skill
and writing it to the user skills directory.

---

## Section 1: Git Clone Fallback Simulation

The maintainer added a fallback to `fetch_github_repo()` that uses
`git clone --depth=1` when the zip download from `codeload.github.com`
is blocked. This section simulates the exact fallback logic.

### 1A. Verify git is available and clone works

```bash
which git
git --version
```

### 1B. Simulate fetch_github_repo_git()

This replicates the exact function the maintainer added:

```bash
python3 -c "
import subprocess, os, tempfile, time
from pathlib import Path

repo = 'Mharbulous/skills-hub'
ref = 'main'
owner, name = repo.split('/')
clone_url = f'https://github.com/{owner}/{name}.git'

with tempfile.TemporaryDirectory(prefix='skills-hub-git-') as tmp:
    dest = Path(tmp)
    repo_dir = dest / 'repo-git'
    
    print(f'Cloning {clone_url} (--depth=1)...')
    start = time.time()
    result = subprocess.run(
        ['git', 'clone', '--depth=1', '--single-branch', '--branch', ref,
         clone_url, str(repo_dir)],
        capture_output=True,
        text=True,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
    )
    elapsed = time.time() - start
    
    print(f'Exit code: {result.returncode}')
    print(f'Time: {elapsed:.1f}s')
    if result.stderr:
        print(f'stderr: {result.stderr.strip()}')
    
    if result.returncode == 0:
        # Verify the repo has public/skills/
        skills_dir = repo_dir / 'public' / 'skills'
        if skills_dir.is_dir():
            skill_dirs = sorted(p.name for p in skills_dir.iterdir() if (p / 'SKILL.md').is_file())
            print(f'Skills found: {len(skill_dirs)}')
            print(f'First 5: {skill_dirs[:5]}')
            print(f'Last 5: {skill_dirs[-5:]}')
        else:
            print(f'ERROR: {skills_dir} not found')
            print(f'Top-level contents: {sorted(p.name for p in repo_dir.iterdir())}')
    else:
        print('Clone FAILED')
        if result.stdout:
            print(f'stdout: {result.stdout.strip()}')
"
```

**Expected result:** Clone succeeds in ~5-15 seconds, finds 100+ skills
in `public/skills/`.

---

## Section 2: Skill Packaging Simulation

After clone, the manager script builds a `.skill` zip package from the
repo tree. This section simulates that packaging step.

### 2A. Clone, build package, verify contents

```bash
python3 -c "
import subprocess, os, tempfile, zipfile, hashlib, shutil
from pathlib import Path

EXCLUDED_DIRS = {'.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.skill'}
EXCLUDED_NAMES = {'manifest.json', 'manifest.json.sig'}

def should_copy(path, source_root):
    rel = path.relative_to(source_root)
    if any(part in EXCLUDED_DIRS or part.startswith('.') for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True

repo = 'Mharbulous/skills-hub'
ref = 'main'
skill_name = 'ar-follow-up'  # simple skill with a companion file

with tempfile.TemporaryDirectory(prefix='skills-hub-pkg-') as tmp:
    dest = Path(tmp)
    repo_dir = dest / 'repo-git'
    
    print(f'1. Cloning repo...')
    subprocess.run(
        ['git', 'clone', '--depth=1', '--single-branch', '--branch', ref,
         f'https://github.com/{repo}.git', str(repo_dir)],
        check=True, capture_output=True,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
    )
    print('   Clone OK')
    
    # Find skill source
    skill_source = repo_dir / 'public' / 'skills' / skill_name
    if not skill_source.is_dir():
        print(f'ERROR: skill {skill_name} not found at {skill_source}')
        exit(1)
    
    print(f'2. Packaging skill: {skill_name}')
    files = []
    for path in sorted(skill_source.rglob('*')):
        if path.is_file() and should_copy(path, skill_source):
            rel = path.relative_to(skill_source)
            files.append(rel)
            print(f'   {rel}')
    
    # Build zip package
    package_path = dest / f'{skill_name}.skill'
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            src = skill_source / rel
            zf.write(src, f'{skill_name}/{rel}')
    
    pkg_size = package_path.stat().st_size
    print(f'3. Package: {package_path.name} ({pkg_size} bytes)')
    
    # Verify package contents
    with zipfile.ZipFile(package_path) as zf:
        names = sorted(zf.namelist())
        print(f'4. Package contents:')
        for n in names:
            info = zf.getinfo(n)
            print(f'   {n} ({info.file_size} bytes)')
    
    # Verify SKILL.md content
    with zipfile.ZipFile(package_path) as zf:
        skill_md = zf.read(f'{skill_name}/SKILL.md').decode('utf-8')
        print(f'5. SKILL.md first 200 chars:')
        print(f'   {skill_md[:200]}')
    
    print()
    print('PACKAGING TEST: PASS')
"
```

---

## Section 3: End-to-End Install Simulation

This simulates what happens when a user runs `/skills-hub install`:
clone → package → extract to user skills directory.

### 3A. Find the user skills directory

```bash
SKILLS_DIR=$(find / -path "*/.claude/skills" -type d 2>/dev/null | head -1)
echo "SKILLS_DIR=$SKILLS_DIR"
echo "SKILL_COUNT=$(ls "$SKILLS_DIR" 2>/dev/null | wc -l)"
```

### 3B. Install a skill via git clone

Pick a skill that is NOT already installed. Use `prototype` as it's
unlikely to be pre-installed.

```bash
python3 -c "
import subprocess, os, tempfile, zipfile, shutil
from pathlib import Path

skills_dir = Path('$SKILLS_DIR')
skill_name = 'prototype'
target = skills_dir / skill_name

# Check if already installed
if target.exists():
    print(f'Skill {skill_name} already installed at {target}')
    print('Picking alternate: scaffold-exercises')
    skill_name = 'scaffold-exercises'
    target = skills_dir / skill_name
    if target.exists():
        print(f'{skill_name} also installed. Skipping install test.')
        exit(0)

print(f'Target: {target}')
print(f'Pre-install: exists={target.exists()}')
print()

with tempfile.TemporaryDirectory(prefix='skills-hub-install-') as tmp:
    dest = Path(tmp)
    repo_dir = dest / 'repo-git'
    
    print('1. Cloning repo...')
    subprocess.run(
        ['git', 'clone', '--depth=1', '--single-branch', '--branch', 'main',
         'https://github.com/Mharbulous/skills-hub.git', str(repo_dir)],
        check=True, capture_output=True,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
    )
    print('   Clone OK')
    
    skill_source = repo_dir / 'public' / 'skills' / skill_name
    if not skill_source.is_dir():
        print(f'ERROR: {skill_name} not in repo')
        exit(1)
    
    print(f'2. Source files:')
    for p in sorted(skill_source.rglob('*')):
        if p.is_file():
            rel = p.relative_to(skill_source)
            print(f'   {rel} ({p.stat().st_size} bytes)')
    
    # Build .skill package
    package = dest / f'{skill_name}.skill'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(skill_source.rglob('*')):
            if p.is_file() and not any(part.startswith('.') for part in p.relative_to(skill_source).parts):
                rel = p.relative_to(skill_source)
                zf.write(p, f'{skill_name}/{rel}')
    
    print(f'3. Package built: {package.stat().st_size} bytes')
    
    # Extract to target
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as zf:
        for member in zf.infolist():
            # Strip skill_name/ prefix
            parts = Path(member.filename).parts
            if len(parts) > 1:
                rel = Path(*parts[1:])
                out = target / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                if not member.is_dir():
                    out.write_bytes(zf.read(member.filename))
    
    print(f'4. Installed to: {target}')
    print(f'5. Installed files:')
    for p in sorted(target.rglob('*')):
        if p.is_file():
            print(f'   {p.relative_to(target)} ({p.stat().st_size} bytes)')
    
    # Verify SKILL.md is readable
    skill_md = (target / 'SKILL.md').read_text(encoding='utf-8')
    print(f'6. SKILL.md readable: {len(skill_md)} chars')
    print(f'   First line: {skill_md.splitlines()[0]}')
    
    print()
    print('INSTALL TEST: PASS')
"
```

### 3C. Verify the installed skill is visible

```bash
echo "Post-install skill count: $(ls "$SKILLS_DIR" | wc -l)"
ls -la "$SKILLS_DIR/prototype" 2>/dev/null || ls -la "$SKILLS_DIR/scaffold-exercises" 2>/dev/null
```

### 3D. Clean up (remove the test skill)

```bash
python3 -c "
import shutil
from pathlib import Path
skills_dir = Path('$SKILLS_DIR')
for name in ['prototype', 'scaffold-exercises']:
    target = skills_dir / name
    if target.exists():
        shutil.rmtree(target)
        print(f'Cleaned up: {target}')
"
echo "Post-cleanup skill count: $(ls "$SKILLS_DIR" | wc -l)"
```

---

## Section 4: Catalog Hash Verification

The inventory command computes content hashes from the GitHub repo to
detect stale installs. Verify that the hash computation works against
git-cloned content.

```bash
python3 -c "
import subprocess, os, tempfile, hashlib
from pathlib import Path

EXCLUDED_DIRS = {'.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.skill'}
EXCLUDED_NAMES = {'manifest.json', 'manifest.json.sig'}

def direct_package_files(skill_source):
    files = []
    for path in sorted(skill_source.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_source)
        if any(part in EXCLUDED_DIRS or part == 'overrides' or part.startswith('.') for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(rel)
    return files

def strip_frontmatter(text):
    if text.startswith('---\n'):
        end = text.find('\n---', 4)
        if end != -1:
            return text[end + 4:].lstrip('\n')
    return text

def merged_cowork_skill_text(skill_dir_path):
    text = (skill_dir_path / 'SKILL.md').read_text(encoding='utf-8')
    override = skill_dir_path / 'overrides' / 'cowork.md'
    if override.is_file():
        body = strip_frontmatter(override.read_text(encoding='utf-8')).strip()
        if body:
            text = text.rstrip() + '\n\n' + body + '\n'
    return text

def content_hash(skill_dir_path):
    digest = hashlib.sha256()
    for rel in direct_package_files(skill_dir_path):
        digest.update(rel.as_posix().encode('utf-8'))
        if rel.as_posix() == 'SKILL.md':
            digest.update(merged_cowork_skill_text(skill_dir_path).encode('utf-8'))
        else:
            digest.update((skill_dir_path / rel).read_bytes())
    return digest.hexdigest()

with tempfile.TemporaryDirectory(prefix='skills-hub-hash-') as tmp:
    dest = Path(tmp)
    repo_dir = dest / 'repo-git'
    
    print('Cloning repo for hash test...')
    subprocess.run(
        ['git', 'clone', '--depth=1', '--single-branch', '--branch', 'main',
         'https://github.com/Mharbulous/skills-hub.git', str(repo_dir)],
        check=True, capture_output=True,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
    )
    
    skills_dir = repo_dir / 'public' / 'skills'
    test_skills = ['ar-follow-up', 'billing-summary', 'case-data']
    
    for name in test_skills:
        skill_path = skills_dir / name
        if skill_path.is_dir() and (skill_path / 'SKILL.md').is_file():
            h = content_hash(skill_path)
            files = direct_package_files(skill_path)
            print(f'{name}: hash={h[:16]}... files={len(files)}')
        else:
            print(f'{name}: NOT FOUND')
    
    print()
    print('HASH TEST: PASS')
"
```

---

## Final Report

Present results in this format:

### Git Fallback

| Check | Result |
|---|---|
| git available | yes/no + version |
| Shallow clone succeeds | yes/no + time |
| Skills found in clone | count |
| Package builds correctly | yes/no + file list |

### Install Simulation

| Step | Result | Notes |
|---|---|---|
| Clone repo | | |
| Build package | | |
| Extract to skills dir | | |
| SKILL.md readable | | |
| Skill visible in dir | | |
| Cleanup succeeded | | |

### Content Hash

| Skill | Hash (first 16 chars) | File count |
|---|---|---|
| ar-follow-up | | |
| billing-summary | | |
| case-data | | |

### Recommendations for Maintainer

Based on the results, state:
1. Does the git clone fallback work in this sandbox? (yes/no + evidence)
2. Is the clone fast enough for interactive use? (time + assessment)
3. Does the full install pipeline work end-to-end? (yes/no + evidence)
4. Do content hashes compute correctly from git-cloned content? (yes/no)

Write the full report to:

```
outputs/skills-hub-diagnostic-v3.md
```

Tell the tester the file path so they can share it with Claude Code.
