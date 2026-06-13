#!/usr/bin/env python3
"""
Non-destructive exhibit file rename script.

Renames exhibit files using a safe two-pass procedure that avoids
name collisions and works around FUSE mount cache bugs. Designed to
be called by the /assemble-affidavit skill after validation detects
mislabeled exhibits.

Why this exists:
    The Cowork sandbox mounts the user's workspace via a FUSE chain.
    This FUSE layer caches file lookups aggressively — after a rename,
    reads from the new path may still return the old file's content.
    LLM inference cannot reliably remember to work around this bug,
    so file operations that must be correct (exhibit renaming) are
    delegated to this deterministic script.

    This script also handles the case where a file needs to be COPIED
    from another location (e.g., a missing exhibit found elsewhere in
    the matter folder). Copies go through /tmp to avoid FUSE read
    caching on the source path.

Usage:
    echo '<json>' | python3 rename_exhibits.py

Input JSON:
    {
        "exhibit_dir": "/path/to/exhibit/folder",
        "renames": [
            {"from": "Exhibit G.pdf", "to": "Exhibit F.pdf"},
            {"from": "Exhibit F.pdf", "to": "Exhibit G.pdf"}
        ],
        "copies": [
            {
                "source": "/path/to/source/file.pdf",
                "target_name": "Exhibit E.pdf"
            }
        ]
    }

    - renames: swap/rename files already in exhibit_dir (two-pass safe)
    - copies: bring in files from other locations (optional)

Output JSON:
    {
        "success": true,
        "renames_completed": [...],
        "copies_completed": [...],
        "errors": [],
        "verification": { "Exhibit A.pdf": {"size": 123, "ok": true}, ... }
    }

Safety guarantees:
    - Never overwrites a file that isn't part of the rename set
    - Two-pass rename: all → temp names first, then temp → final
    - FUSE cache invalidation after every filesystem operation
    - Copies go through /tmp intermediary to bypass FUSE read cache
    - Dry-run validation before any filesystem changes
    - Full rollback on error during pass 1 (temp rename phase)
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def fuse_cache_invalidate(path: str) -> None:
    """
    Invalidate the FUSE lookup cache for a file path.

    The FUSE layer caches lookup results. After a rename or copy,
    the cache may hold a stale entry for the path. A rename
    round-trip (path → tmp → path) forces a fresh lookup on the
    next open().

    This is a no-op if the file doesn't exist (e.g., after a rename
    moved it away).
    """
    if not os.path.exists(path):
        return
    tmp = path + ".__fuse_invalidate__"
    try:
        os.rename(path, tmp)
        os.rename(tmp, path)
    except OSError:
        pass  # best-effort; some paths may not support rename


def verify_file(path: str) -> dict:
    """Read file header and size to verify it's accessible and non-empty."""
    try:
        fuse_cache_invalidate(path)
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            header = f.read(4).hex()
        return {"size": size, "header": header, "ok": size > 0}
    except Exception as e:
        return {"size": 0, "header": "", "ok": False, "error": str(e)}


def do_renames(exhibit_dir: str, renames: list) -> dict:
    """
    Two-pass rename within exhibit_dir.

    Pass 1: rename all source files to temporary names (.tmp_rename)
    Pass 2: rename temporary files to final target names

    If pass 1 fails partway, rolls back completed temp renames.
    """
    result = {
        "renames_completed": [],
        "errors": [],
    }

    if not renames:
        return result

    # Pre-validate: all source files must exist, no target may collide
    # with a file that is NOT also being renamed away.
    sources_moving = {r["from"] for r in renames}
    for r in renames:
        src_path = os.path.join(exhibit_dir, r["from"])
        if not os.path.exists(src_path):
            result["errors"].append(
                f"Source file not found: {r['from']}"
            )

        # Target collision check: target name must either not exist,
        # or be a file that is itself being renamed away.
        tgt_path = os.path.join(exhibit_dir, r["to"])
        if os.path.exists(tgt_path) and r["to"] not in sources_moving:
            result["errors"].append(
                f"Target name '{r['to']}' already exists and is not "
                f"part of the rename set — would overwrite."
            )

    if result["errors"]:
        return result

    # Pass 1: all sources → temp names
    temp_suffix = ".tmp_rename"
    completed_temps = []
    try:
        for r in renames:
            src = os.path.join(exhibit_dir, r["from"])
            tmp = src + temp_suffix
            os.rename(src, tmp)
            fuse_cache_invalidate(tmp)
            completed_temps.append((src, tmp, r))
    except Exception as e:
        # Rollback completed temps
        for orig_src, tmp_path, _ in reversed(completed_temps):
            try:
                os.rename(tmp_path, orig_src)
                fuse_cache_invalidate(orig_src)
            except OSError:
                pass
        result["errors"].append(
            f"Pass 1 failed on '{r['from']}': {e}. "
            f"Rolled back {len(completed_temps)} temp renames."
        )
        return result

    # Pass 2: temp names → final target names
    for orig_src, tmp_path, r in completed_temps:
        tgt = os.path.join(exhibit_dir, r["to"])
        try:
            os.rename(tmp_path, tgt)
            fuse_cache_invalidate(tgt)
            result["renames_completed"].append({
                "from": r["from"],
                "to": r["to"],
            })
        except Exception as e:
            result["errors"].append(
                f"Pass 2 failed: '{r['from']}' → '{r['to']}': {e}. "
                f"File is at temp path: {tmp_path}"
            )

    return result


def do_copies(exhibit_dir: str, copies: list) -> dict:
    """
    Copy files from external locations into exhibit_dir.

    Each copy goes through /tmp to bypass FUSE read caching on
    the source path. The target name must not already exist in
    exhibit_dir (non-destructive).
    """
    result = {
        "copies_completed": [],
        "errors": [],
    }

    if not copies:
        return result

    for c in copies:
        source = c["source"]
        target_name = c["target_name"]
        target_path = os.path.join(exhibit_dir, target_name)

        # Safety: don't overwrite existing files
        if os.path.exists(target_path):
            result["errors"].append(
                f"Target '{target_name}' already exists — "
                f"will not overwrite."
            )
            continue

        # FUSE cache invalidate source
        fuse_cache_invalidate(source)

        if not os.path.exists(source):
            result["errors"].append(f"Source not found: {source}")
            continue

        try:
            # Read source bytes fully into memory (bypass FUSE cache)
            with open(source, "rb") as f:
                data = f.read()

            if len(data) == 0:
                result["errors"].append(
                    f"Source is empty (0 bytes): {source}"
                )
                continue

            # Write to /tmp first, then copy to target
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(target_name)[1]
            ) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            # Copy from /tmp to exhibit_dir (cross-device)
            shutil.copy2(tmp_path, target_path)
            os.unlink(tmp_path)

            # Invalidate FUSE cache on the new file
            fuse_cache_invalidate(target_path)

            # Verify
            v = verify_file(target_path)
            if v["ok"] and v["size"] == len(data):
                result["copies_completed"].append({
                    "source": source,
                    "target_name": target_name,
                    "size": len(data),
                })
            else:
                result["errors"].append(
                    f"Copy verification failed for '{target_name}': "
                    f"expected {len(data)} bytes, got {v}"
                )
        except Exception as e:
            result["errors"].append(
                f"Copy failed for '{target_name}': {e}"
            )

    return result


def main():
    try:
        config = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    exhibit_dir = config.get("exhibit_dir", "")
    renames = config.get("renames", [])
    copies = config.get("copies", [])

    if not exhibit_dir or not os.path.isdir(exhibit_dir):
        print(json.dumps({
            "success": False,
            "error": f"exhibit_dir not found: {exhibit_dir}",
        }))
        sys.exit(1)

    output = {
        "success": True,
        "renames_completed": [],
        "copies_completed": [],
        "errors": [],
        "verification": {},
    }

    # Execute renames first (before copies, in case a rename frees
    # up a name that a copy needs)
    if renames:
        r = do_renames(exhibit_dir, renames)
        output["renames_completed"] = r["renames_completed"]
        output["errors"].extend(r["errors"])

    # Execute copies
    if copies:
        c = do_copies(exhibit_dir, copies)
        output["copies_completed"] = c["copies_completed"]
        output["errors"].extend(c["errors"])

    # Final verification: check all exhibit files in the directory
    for fname in sorted(os.listdir(exhibit_dir)):
        if fname.startswith("Exhibit ") and not fname.endswith(
            (".tmp_rename", ".__fuse_invalidate__", ".osl-tmp")
        ):
            fpath = os.path.join(exhibit_dir, fname)
            if os.path.isfile(fpath):
                output["verification"][fname] = verify_file(fpath)

    if output["errors"]:
        output["success"] = False

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
