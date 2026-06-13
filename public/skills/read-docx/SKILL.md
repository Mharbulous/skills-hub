---
name: read-docx
description: Read .docx files from the mounted workspace in the sandbox. Use whenever you need to open, read, extract text from, or process a .docx file via bash/shell and the file cannot be opened (ENOENT on a file that exists). Also use proactively before any bash-based docx reading to prevent FUSE cache failures. Triggers on shell read errors for docx files, "can't open docx", "ENOENT", or any task requiring docx content extraction in the sandbox.
---

# read-docx

Read .docx files from the mounted workspace folder in the Cowork sandbox.

## The problem this solves

The Cowork sandbox mounts the user's workspace via a FUSE chain (virtiofs + bindfs). A stale lookup cache in this FUSE layer can cause `open()` to return `ENOENT` on files that exist — `stat()` works, the file appears in directory listings, but any attempt to read content fails. This affects files that were created or modified outside the current session (by a previous Cowork session, by the user in Windows, etc.).

## How to read a docx file

Run this Python snippet in bash, substituting the actual file path. It handles the FUSE cache fix, extracts text via pandoc, and prints the content.

```bash
python3 << 'PYEOF'
import os, subprocess, sys

path = "INSERT_FILE_PATH_HERE"

# Step 1: Fix FUSE cache staleness via rename round-trip
try:
    fd = os.open(path, os.O_RDONLY)
    os.close(fd)
except OSError as e:
    if e.errno == 2:  # ENOENT
        tmp = path + ".fuse_fix"
        os.rename(path, tmp)
        os.rename(tmp, path)

# Step 2: Extract text with pandoc
result = subprocess.run(
    ["pandoc", "--track-changes=all", path, "-t", "plain", "--wrap=none"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("pandoc error: " + result.stderr, file=sys.stderr)
    sys.exit(1)

print(result.stdout)
PYEOF
```

## Batch fix: make all workspace files readable

If multiple files are inaccessible, run this once at the start of a session to fix every stale file in the workspace:

```bash
python3 << 'PYEOF'
import os

base = "INSERT_WORKSPACE_ROOT_HERE"
fixed = 0
for root, dirs, files in os.walk(base):
    for f in files:
        path = os.path.join(root, f)
        try:
            fd = os.open(path, os.O_RDONLY)
            os.close(fd)
        except OSError as e:
            if e.errno == 2:
                tmp = path + ".fuse_fix"
                try:
                    os.rename(path, tmp)
                    os.rename(tmp, path)
                    fixed += 1
                except:
                    pass
print("Fixed {} stale files".format(fixed))
PYEOF
```

## Using the docx skill's unpack tool

For deeper inspection (raw XML, editing), combine the FUSE fix with the docx skill's unpack script:

```bash
# Fix the file first
python3 -c "
import os
path = 'INSERT_FILE_PATH_HERE'
try:
    fd = os.open(path, os.O_RDONLY)
    os.close(fd)
except OSError:
    tmp = path + '.fuse_fix'
    os.rename(path, tmp)
    os.rename(tmp, path)
"

# Then unpack
python3 SKILLS_DIR/docx/scripts/office/unpack.py "INSERT_FILE_PATH_HERE" /tmp/unpacked/
```

Replace `SKILLS_DIR` with the actual skills directory path (visible in the shell path mappings).

## When to use this skill vs the docx skill

- **This skill**: When you need to *read* a docx file in the sandbox and it fails with ENOENT, or proactively before any sandbox-based docx reading.
- **The docx skill**: When you need to *create*, *edit*, or *manipulate* docx files (writing new documents, tracked changes, XML editing, etc.).

Both can be used together — fix readability with this skill, then use the docx skill's tools for editing.

## Why the rename fix works

The FUSE layer caches lookup results for file paths. When a file was created or modified outside the current session, the cache may hold a stale entry. `stat()` and directory listing use a different FUSE operation (getattr/readdir) than `open()` (lookup + open), so metadata works while content access fails. A rename round-trip invalidates the stale lookup cache entry, forcing a fresh lookup on the next `open()`. The fix is permanent for the session — files stay readable after the rename round-trip.
