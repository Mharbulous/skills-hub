#!/usr/bin/env python3
"""
Commit Ingestion — Phase 1 of Claude Curator Introspect mode.

Reads the repo cursor from the database, runs git log to get commits
after the cursor (up to a limit), and parses the output into structured
JSON with hash, message, files, areas_touched, and trivial classification.

Usage:
    python commit_ingestion.py <db_path> <repo> [--repo-path PATH] [--limit N]
    python commit_ingestion.py --init-cursor <db_path> <repo> [--repo-path PATH]

Arguments:
    db_path         Path to claude-storage.db
    repo            Repository name (for cursor lookup in repo_cursors table)
    --repo-path     Path to the git repository (default: current directory)
    --limit         Max commits to ingest (default: 100)
    --init-cursor   Initialize cursor to HEAD~100 (for bootstrap)

Output (JSON to stdout):
    {
        "commits": [
            {
                "hash": "abc123...",
                "msg": "feat: add feature",
                "files": ["src/foo.py", "src/bar.py"],
                "areas_touched": ["src/foo/", "src/bar/"],
                "trivial": false
            }
        ],
        "cursor": {
            "previous": "aaa111...",
            "current": "fff666..."
        },
        "skipped_to": null,
        "stats": {
            "total_commits": 5,
            "trivial_count": 2,
            "non_trivial_count": 3
        }
    }

    If the cursor was > 200 commits behind HEAD, "skipped_to" contains
    the hash that was used instead (HEAD~100). Otherwise null.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys


# Patterns for trivial commit detection.
# Trivial = typos, formatting-only changes. NOT docs, refactors, or fixes.
TRIVIAL_PREFIXES = {"style"}
TRIVIAL_MESSAGE_PATTERNS = [
    re.compile(r"\btypo\b", re.IGNORECASE),
    re.compile(r"\bformatting\b", re.IGNORECASE),
    re.compile(r"\bwhitespace\b", re.IGNORECASE),
]


def is_trivial(msg: str) -> bool:
    """
    Determine if a commit is trivial based on its message.

    Trivial commits: style-only changes, typos, formatting fixes.
    NOT trivial: docs, fix, feat, refactor, chore, build, ci, perf, test.
    """
    # Check conventional commit prefix (text before first colon)
    prefix_match = re.match(r"^(\w+)(?:\(.+?\))?:", msg)
    if prefix_match:
        prefix = prefix_match.group(1).lower()
        if prefix in TRIVIAL_PREFIXES:
            return True

    # Check message content patterns
    for pattern in TRIVIAL_MESSAGE_PATTERNS:
        if pattern.search(msg):
            return True

    return False


def get_areas_touched(files: list[str]) -> list[str]:
    """
    Extract deduplicated parent directories from file paths.

    Uses os.path.dirname to get the immediate parent directory.
    Root-level files produce an empty string as their area.
    Results are sorted for deterministic output.
    """
    areas = set()
    for filepath in files:
        # Normalize to forward slashes for consistency
        normalized = filepath.replace("\\", "/")
        parent = os.path.dirname(normalized)
        if parent:
            # Ensure trailing slash for directories
            areas.add(parent.rstrip("/") + "/")
        else:
            # Root-level file
            areas.add("")
    return sorted(areas)


def count_commits_since(repo_path: str, cursor: str) -> int:
    """Count how many commits exist between cursor and HEAD."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{cursor}..HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=repo_path,
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip())


def get_recent_cursor(repo_path: str, n: int = 100) -> str:
    """Get the commit hash n commits before HEAD.

    Falls back to the earliest commit if the repo has fewer than n commits.
    """
    result = subprocess.run(
        ["git", "rev-list", "-1", f"HEAD~{n}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=repo_path,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    # Fallback: repo has < n commits, use earliest commit
    result = subprocess.run(
        ["git", "rev-list", "--reverse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=repo_path,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")[0]

    return ""


def get_cursor(db_path: str, repo: str) -> str | None:
    """Read the last analyzed commit hash from the database."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT last_commit_hash FROM repo_cursors WHERE repo = ?",
        (repo,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def init_cursor(db_path: str, repo: str, repo_path: str) -> dict:
    """Initialize the repo cursor to HEAD~100 for bootstrap.

    Inserts into repo_cursors. Returns JSON-serializable result.
    """
    cursor_hash = get_recent_cursor(repo_path, 100)
    if not cursor_hash:
        return {"error": "No commits found in repository"}

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO repo_cursors (repo, last_commit_hash) VALUES (?, ?)",
        (repo, cursor_hash),
    )
    conn.commit()
    conn.close()

    return {"cursor": cursor_hash, "repo": repo}


def run_git_log(repo_path: str, after_commit: str | None, limit: int) -> str:
    """
    Run git log and return raw output.

    Uses --reverse to get oldest-first ordering.
    Uses COMMIT:%H|%s format for easy parsing.
    Uses --name-only to get file paths.
    """
    cmd = [
        "git", "log", "--reverse",
        "--format=COMMIT:%H|%s",
        "--name-only",
        f"-n{limit}",
    ]

    if after_commit:
        cmd.append(f"{after_commit}..HEAD")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=repo_path,
    )

    if result.returncode != 0:
        print(json.dumps({
            "error": f"git log failed: {result.stderr.strip()}"
        }), file=sys.stderr)
        sys.exit(1)

    return result.stdout


def parse_git_log(raw_output: str) -> list[dict]:
    """
    Parse git log output into structured commit objects.

    Expected format:
        COMMIT:<hash>|<message>
        <file1>
        <file2>
        (blank line)
        COMMIT:<hash>|<message>
        ...
    """
    commits = []
    current_commit = None

    for line in raw_output.split("\n"):
        line = line.strip()

        if line.startswith("COMMIT:"):
            # Save previous commit
            if current_commit is not None:
                current_commit["areas_touched"] = get_areas_touched(
                    current_commit["files"]
                )
                current_commit["trivial"] = is_trivial(current_commit["msg"])
                commits.append(current_commit)

            # Parse new commit line
            rest = line[len("COMMIT:"):]
            parts = rest.split("|", 1)
            commit_hash = parts[0]
            msg = parts[1] if len(parts) > 1 else ""

            current_commit = {
                "hash": commit_hash,
                "msg": msg,
                "files": [],
            }

        elif line and current_commit is not None:
            # File path line
            current_commit["files"].append(line)

    # Don't forget the last commit
    if current_commit is not None:
        current_commit["areas_touched"] = get_areas_touched(
            current_commit["files"]
        )
        current_commit["trivial"] = is_trivial(current_commit["msg"])
        commits.append(current_commit)

    return commits


def commit_ingestion(db_path: str, repo: str, repo_path: str, limit: int) -> dict:
    """
    Perform commit ingestion: read cursor, run git log, parse into JSON.

    Returns structured ingestion result.
    """
    # Step 1: Read cursor
    previous_cursor = get_cursor(db_path, repo)

    # Step 1.5: Staleness guard — skip forward if cursor is too far behind
    skipped_to = None
    if previous_cursor:
        behind = count_commits_since(repo_path, previous_cursor)
        if behind > 200:
            skipped_to = get_recent_cursor(repo_path, 100)
            previous_cursor = skipped_to

    # Step 2: Run git log
    raw_output = run_git_log(repo_path, previous_cursor, limit)

    # Step 3: Parse
    commits = parse_git_log(raw_output)

    # Determine new cursor (last commit hash)
    current_cursor = commits[-1]["hash"] if commits else previous_cursor

    # Stats
    trivial_count = sum(1 for c in commits if c["trivial"])

    return {
        "commits": commits,
        "cursor": {
            "previous": previous_cursor,
            "current": current_cursor,
        },
        "skipped_to": skipped_to,
        "stats": {
            "total_commits": len(commits),
            "trivial_count": trivial_count,
            "non_trivial_count": len(commits) - trivial_count,
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Claude Curator — Commit Ingestion (Phase 1)"
    )
    parser.add_argument("db_path", help="Path to claude-storage.db")
    parser.add_argument("repo", help="Repository name (for cursor lookup)")
    parser.add_argument(
        "--repo-path", default=".",
        help="Path to the git repository (default: current directory)"
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Max commits to ingest (default: 100)"
    )
    parser.add_argument(
        "--init-cursor", action="store_true",
        help="Initialize cursor to HEAD~100 (for bootstrap)"
    )

    args = parser.parse_args()

    if not os.path.isfile(args.db_path):
        print(json.dumps({
            "error": f"Database not found: {args.db_path}"
        }), file=sys.stderr)
        sys.exit(1)

    if args.init_cursor:
        result = init_cursor(args.db_path, args.repo, args.repo_path)
    else:
        result = commit_ingestion(args.db_path, args.repo, args.repo_path, args.limit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
