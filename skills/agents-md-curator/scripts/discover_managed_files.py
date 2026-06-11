#!/usr/bin/env python3
"""
Discover Managed Files — walks a root directory, finds every AGENTS.md
that contains a <CURATED>...</CURATED> block, and emits metadata for each.

A file is "managed" if and only if it contains a <CURATED> block. Content
outside the block is human territory — never read for placement decisions,
never mutated. The count of non-blank, non-heading lines outside the block
is used only to derive the per-file managed budget (200 - manual_units).

Usage:
    python discover_managed_files.py <repo_root> [--db <path>] [--repo <name>]
                                                 [--include-home]

Arguments:
    repo_root       Directory to walk (typically the repository root).
    --db            Path to claude-storage.db. If provided, upserts each
                    discovered file into the managed_files table.
    --repo          Repository name to associate with discovered files.
                    Defaults to the basename of repo_root.
    --include-home  Also scan ~/.claude/AGENTS.md if it has a <CURATED> block.
                    That file's depth is reported as -1.

Output (JSON to stdout):
    {
      "managed_files": [
        {
          "path": "<absolute-or-~-path>",
          "repo": "<repo-name-or-null>",
          "depth": 0,
          "manual_units": 12,
          "managed_budget": 188
        },
        ...
      ]
    }

depth is the number of path segments between the repo root and the file's
directory (0 = repo root, 1 = one subfolder deep, ...). For ~/.claude/AGENTS.md
depth is -1 — it is the user-global tier, outside any single repo.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

FILE_BUDGET = 200
CURATED_TAG_RE = re.compile(r"<CURATED>(.*?)</CURATED>", re.DOTALL)


def extract_curated_block(text: str) -> tuple[str, str, str] | None:
    """Return (before, inside, after) if the file has a CURATED block, else None."""
    m = CURATED_TAG_RE.search(text)
    if not m:
        return None
    return text[: m.start()], m.group(1), text[m.end() :]


def count_manual_units(before: str, after: str) -> int:
    """
    Count atomic units outside the CURATED block.

    Approximation: non-blank lines that are not markdown headings. An exact
    atomic-unit count would require Sonnet-level decomposition; this is only
    used to derive the per-file budget, so approximation is acceptable and
    documented in the plan.
    """
    count = 0
    for chunk in (before, after):
        for line in chunk.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            count += 1
    return count


def compute_depth(path: Path, root: Path) -> int:
    """Depth of file's directory below root. 0 = sits at root."""
    rel = path.parent.resolve().relative_to(root.resolve())
    parts = [p for p in rel.parts if p not in ("", ".")]
    return len(parts)


def discover(root: Path, repo: str | None, include_home: bool) -> list[dict]:
    results: list[dict] = []

    for dirpath, _, filenames in os.walk(root):
        if "AGENTS.md" not in filenames:
            continue
        file_path = Path(dirpath) / "AGENTS.md"
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"warn: could not read {file_path}: {e}", file=sys.stderr)
            continue
        block = extract_curated_block(text)
        if block is None:
            continue
        before, _, after = block
        manual_units = count_manual_units(before, after)
        results.append(
            {
                "path": str(file_path),
                "repo": repo,
                "depth": compute_depth(file_path, root),
                "manual_units": manual_units,
                "managed_budget": max(0, FILE_BUDGET - manual_units),
            }
        )

    if include_home:
        home_claude = Path.home() / ".claude" / "AGENTS.md"
        if home_claude.exists():
            text = home_claude.read_text(encoding="utf-8")
            block = extract_curated_block(text)
            if block is not None:
                before, _, after = block
                manual_units = count_manual_units(before, after)
                results.append(
                    {
                        "path": str(home_claude),
                        "repo": None,
                        "depth": -1,
                        "manual_units": manual_units,
                        "managed_budget": max(0, FILE_BUDGET - manual_units),
                    }
                )

    return results


def upsert_managed_files(db_path: str, rows: list[dict]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for row in rows:
            conn.execute(
                """
                INSERT INTO managed_files (path, repo, depth, last_written_at)
                VALUES (?, ?, ?, NULL)
                ON CONFLICT(path) DO UPDATE SET
                    repo = excluded.repo,
                    depth = excluded.depth
                """,
                (row["path"], row["repo"], row["depth"]),
            )
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Claude Curator — Discover managed AGENTS.md files"
    )
    parser.add_argument("repo_root", help="Root directory to walk")
    parser.add_argument("--db", help="Path to claude-storage.db (optional)")
    parser.add_argument(
        "--repo",
        help="Repository name (defaults to basename of repo_root)",
    )
    parser.add_argument(
        "--include-home",
        action="store_true",
        help="Also include ~/.claude/AGENTS.md if it has a <CURATED> block",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(
            json.dumps({"error": f"not a directory: {args.repo_root}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    repo = args.repo or root.name
    rows = discover(root, repo, args.include_home)

    if args.db:
        upsert_managed_files(args.db, rows)

    print(json.dumps({"managed_files": rows}, indent=2))


if __name__ == "__main__":
    main()
