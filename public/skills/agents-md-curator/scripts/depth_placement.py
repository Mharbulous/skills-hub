#!/usr/bin/env python3
"""
Depth Placement — Phase 5 of Claude Curator Introspect mode.

Routes each permanent line to the deepest managed file whose directory
is an ancestor of the line's observed relevant_paths. Replaces the older
repo-count-only tier classifier.

Algorithm per line:
    1. Collect all distinct paths from relevance_events.relevant_paths
       (observed events only).
    2. Partition by repo. If ≥2 repos contain observed events → target is
       the home-global managed file (the one with depth = -1).
    3. Otherwise single repo: take the longest common directory prefix
       of the paths observed in that repo. Find the deepest managed file
       whose directory equals or contains that prefix. That is the target.
    4. Compare with the most-recent placement for the line; emit promote
       (if target changed or line never placed) or demote (if line was
       previously placed elsewhere and is now unplaced — not produced by
       this script because every line gets a target).

The script also emits a `by_file` map consumed by competitive_placement.py:
    {"<managed-file-path>": [line_id, ...], ...}

Usage:
    python depth_placement.py <db_path>

Arguments:
    db_path     Path to claude-storage.db. Requires managed_files populated
                (run scripts/discover_managed_files.py first).

Output (JSON to stdout):
    {
      "assignments": [
        {"line_id": 1, "target": "<path>", "repos": ["..."], "prefix": "..."}
      ],
      "by_file": {"<path>": [line_id, ...]},
      "promotions": [{"line_id": 1, "action": "promote", "target": "<path>"}],
      "unplaced": [{"line_id": 3, "reason": "no managed file covers prefix"}],
      "stats": {
        "total_lines": 10,
        "assigned": 9,
        "unplaced": 1,
        "promotions": 4
      }
    }
"""

import argparse
import json
import os
import posixpath
import sqlite3
import sys
from collections import defaultdict


def _normalize(path: str) -> str:
    """Normalize a path for prefix comparison: forward slashes, no trailing slash."""
    if path is None:
        return ""
    p = path.replace("\\", "/").strip()
    while p.endswith("/"):
        p = p[:-1]
    return p


def _split_paths(raw: str | None) -> list[str]:
    """relevant_paths is stored as comma-separated strings; split and normalize."""
    if not raw:
        return []
    return [_normalize(x) for x in raw.split(",") if x.strip()]


def longest_common_dir_prefix(paths: list[str]) -> str:
    """
    Longest common directory prefix of a list of file paths.

    Splits each path on '/', takes the common leading segments, rejoins.
    If only one path, returns its directory. Empty list → "".
    """
    if not paths:
        return ""
    if len(paths) == 1:
        return posixpath.dirname(paths[0])
    split = [p.split("/") for p in paths]
    common: list[str] = []
    for segments in zip(*split):
        if all(s == segments[0] for s in segments):
            common.append(segments[0])
        else:
            break
    # If common prefix ends in a filename (last seg matches but is a file),
    # strip it — we want a directory prefix.
    if common and len(common) == min(len(s) for s in split):
        common = common[:-1]
    return "/".join(common)


def load_managed_files(conn: sqlite3.Connection) -> list[dict]:
    """
    Return managed files sorted from deepest to shallowest within each repo.

    Each row gets a `rel_dir` field: directory relative to the repo root.
    The repo root is derived by walking up `depth` segments from the file's
    directory — consistent across all files of the same repo regardless of
    which one is present.
    """
    rows = conn.execute(
        "SELECT path, repo, depth FROM managed_files"
    ).fetchall()
    files = []
    for row in rows:
        abs_dir = _normalize(os.path.dirname(row["path"]))
        depth = row["depth"]
        if depth < 0:
            rel_dir = ""
        else:
            segments = abs_dir.split("/") if abs_dir else []
            rel_dir = "/".join(segments[len(segments) - depth:]) if depth > 0 else ""
        files.append(
            {
                "path": row["path"],
                "repo": row["repo"],
                "depth": depth,
                "dir": abs_dir,
                "rel_dir": rel_dir,
            }
        )
    files.sort(key=lambda f: (-f["depth"], f["path"]))
    return files


def find_home_file(managed: list[dict]) -> dict | None:
    for f in managed:
        if f["depth"] == -1:
            return f
    return None


def find_deepest_covering(
    managed: list[dict], repo: str, prefix: str
) -> dict | None:
    """
    Find the deepest managed file in `repo` whose repo-relative directory is an
    ancestor of `prefix` (or equal to it). Both prefix and rel_dir are
    repo-relative paths. `managed` is pre-sorted deepest-first.
    """
    prefix_n = _normalize(prefix)
    candidates = [f for f in managed if f["repo"] == repo]
    for f in candidates:
        d = f["rel_dir"]
        if d == "" or d == prefix_n or prefix_n.startswith(d + "/"):
            return f
    return None


def collect_events(conn: sqlite3.Connection, line_id: int) -> dict[str, list[str]]:
    """Return {repo: [path, ...]} of observed paths for a line."""
    rows = conn.execute(
        """
        SELECT repo, relevant_paths
        FROM relevance_events
        WHERE line_id = ? AND event_type = 'observed'
        """,
        (line_id,),
    ).fetchall()
    by_repo: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for p in _split_paths(row["relevant_paths"]):
            by_repo[row["repo"]].append(p)
    return by_repo


def most_recent_placement(conn: sqlite3.Connection, line_id: int) -> str | None:
    row = conn.execute(
        """
        SELECT target FROM placements
        WHERE line_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (line_id,),
    ).fetchone()
    return row["target"] if row else None


def depth_placement(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    managed = load_managed_files(conn)
    home = find_home_file(managed)

    assignments = []
    unplaced = []
    by_file: dict[str, list[int]] = defaultdict(list)
    promotions = []

    lines = conn.execute("SELECT id FROM lines").fetchall()

    for line in lines:
        line_id = line["id"]
        by_repo = collect_events(conn, line_id)

        if not by_repo:
            unplaced.append(
                {"line_id": line_id, "reason": "no observed relevance events"}
            )
            continue

        repos = sorted(by_repo.keys())
        target_file: dict | None = None
        prefix = ""

        if len(repos) >= 2:
            if home is None:
                unplaced.append(
                    {
                        "line_id": line_id,
                        "reason": "cross-repo line but no home managed file",
                    }
                )
                continue
            target_file = home
        else:
            repo = repos[0]
            paths = by_repo[repo]
            prefix = longest_common_dir_prefix(paths)
            target_file = find_deepest_covering(managed, repo, prefix)
            if target_file is None:
                unplaced.append(
                    {
                        "line_id": line_id,
                        "reason": f"no managed file in repo '{repo}' covers prefix '{prefix}'",
                    }
                )
                continue

        target_path = target_file["path"]
        assignments.append(
            {
                "line_id": line_id,
                "target": target_path,
                "repos": repos,
                "prefix": prefix,
            }
        )
        by_file[target_path].append(line_id)

        current_target = most_recent_placement(conn, line_id)
        if current_target != target_path:
            promotions.append(
                {"line_id": line_id, "action": "promote", "target": target_path}
            )

    conn.close()

    return {
        "assignments": assignments,
        "by_file": dict(by_file),
        "promotions": promotions,
        "unplaced": unplaced,
        "stats": {
            "total_lines": len(lines),
            "assigned": len(assignments),
            "unplaced": len(unplaced),
            "promotions": len(promotions),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Claude Curator — Depth Placement (Phase 5)"
    )
    parser.add_argument("db_path", help="Path to claude-storage.db")
    args = parser.parse_args()

    result = depth_placement(args.db_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
