#!/usr/bin/env python3
"""
Competitive Placement — Phase 3 of Claude Curator Introspect mode.

Ranks the lines assigned to each managed file by cumulative relevance strength
and fills each file's budget top-down. Each file competes independently —
lines that don't fit at their assigned depth stay in cold storage for that
file (they do not overflow up or down; that would violate tightest-fit).

Usage:
    python competitive_placement.py <db_path> --managed-files <json_path>

Arguments:
    db_path         Path to claude-storage.db
    --managed-files Path to JSON file produced by discover_managed_files.py,
                    augmented with a "by_file" assignment map from
                    depth_placement.py. Shape:
                    {
                      "managed_files": [
                        {"path": "...", "repo": "...", "depth": 0,
                         "managed_budget": 188}, ...
                      ],
                      "by_file": {
                        "<managed-file-path>": [line_id, ...], ...
                      }
                    }

Output (JSON to stdout):
    {
      "files": {
        "<managed-file-path>": {
          "placed": [{"line_id": 1, "content": "...", "section": "...",
                      "score": 42.5, "rank": 1}, ...],
          "cold":   [{"line_id": 8, ...}, ...],
          "promotions": [{"line_id": 3, "action": "promote",
                          "target": "<path>"}],
          "demotions":  [{"line_id": 7, "action": "demote",
                          "target": "<path>"}],
          "stats": {
            "total_lines": 8,
            "placed_count": 5,
            "cold_count": 3,
            "budget_used": 5,
            "budget_available": 188
          }
        }, ...
      }
    }
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone


def compute_score_for_line(conn: sqlite3.Connection, line_id: int, now: datetime) -> dict:
    """
    Compute composite ranking score for a single line across ALL repos.

    Factors (unchanged from prior implementation):
      - observed events: HIGH weight (3x)
      - predicted events: 0.25x
      - recency of most recent event: MEDIUM (2x)
      - path breadth (distinct relevant_paths): LOW (1x)
    Tie-break: older promoted_at wins.
    """
    line = conn.execute(
        "SELECT id, content, section, promoted_at FROM lines WHERE id = ?",
        (line_id,),
    ).fetchone()
    if line is None:
        return None

    observed_count = conn.execute(
        "SELECT COUNT(*) FROM relevance_events WHERE line_id = ? AND event_type = 'observed'",
        (line_id,),
    ).fetchone()[0]

    predicted_count = conn.execute(
        "SELECT COUNT(*) FROM relevance_events WHERE line_id = ? AND event_type = 'predicted'",
        (line_id,),
    ).fetchone()[0]

    most_recent_row = conn.execute(
        "SELECT MAX(created_at) as latest FROM relevance_events WHERE line_id = ?",
        (line_id,),
    ).fetchone()
    most_recent = most_recent_row["latest"] if most_recent_row["latest"] else None

    path_breadth = conn.execute(
        "SELECT COUNT(DISTINCT relevant_paths) FROM relevance_events WHERE line_id = ?",
        (line_id,),
    ).fetchone()[0]

    recency_score = 0.0
    if most_recent:
        try:
            mr = datetime.fromisoformat(most_recent.replace("Z", "+00:00"))
            if mr.tzinfo is None:
                mr = mr.replace(tzinfo=timezone.utc)
            days_ago = (now - mr).total_seconds() / 86400
            recency_score = max(0, 365 - days_ago) / 365
        except (ValueError, TypeError):
            recency_score = 0.0

    effective_events = observed_count + (predicted_count * 0.25)
    composite = (effective_events * 3.0) + (recency_score * 2.0) + (path_breadth * 1.0)

    return {
        "line_id": line["id"],
        "content": line["content"],
        "section": line["section"],
        "promoted_at": line["promoted_at"],
        "observed_count": observed_count,
        "predicted_count": predicted_count,
        "recency_score": recency_score,
        "path_breadth": path_breadth,
        "composite": composite,
    }


def current_placement_map(conn: sqlite3.Connection) -> dict[int, str]:
    """Return {line_id: target} from the most-recent placement per line."""
    rows = conn.execute(
        """
        SELECT p.line_id, p.target
        FROM placements p
        INNER JOIN (
            SELECT line_id, MAX(created_at) AS latest
            FROM placements
            GROUP BY line_id
        ) latest ON p.line_id = latest.line_id AND p.created_at = latest.latest
        WHERE p.action = 'promote'
        """
    ).fetchall()
    return {r["line_id"]: r["target"] for r in rows}


def place_one_file(
    conn: sqlite3.Connection,
    file_spec: dict,
    assigned_line_ids: list[int],
    current: dict[int, str],
    now: datetime,
) -> dict:
    """
    Rank assigned lines by composite score, fill this file's budget top-down.
    Lines not currently placed at this file but placed elsewhere produce a
    demote-from-other-path record; lines moving into this file produce promote.
    """
    path = file_spec["path"]
    budget = file_spec["managed_budget"]

    scored = []
    for line_id in assigned_line_ids:
        s = compute_score_for_line(conn, line_id, now)
        if s is not None:
            scored.append(s)

    scored.sort(key=lambda x: (-x["composite"], x["promoted_at"] or ""))

    placed, cold = [], []
    promotions, demotions = [], []

    for rank, line in enumerate(scored, 1):
        entry = {
            "line_id": line["line_id"],
            "content": line["content"],
            "section": line["section"],
            "score": round(line["composite"], 2),
            "rank": rank,
        }
        if len(placed) < budget:
            placed.append(entry)
            if current.get(line["line_id"]) != path:
                promotions.append(
                    {"line_id": line["line_id"], "action": "promote", "target": path}
                )
        else:
            cold.append(entry)
            if current.get(line["line_id"]) == path:
                demotions.append(
                    {"line_id": line["line_id"], "action": "demote", "target": path}
                )

    return {
        "placed": placed,
        "cold": cold,
        "promotions": promotions,
        "demotions": demotions,
        "stats": {
            "total_lines": len(scored),
            "placed_count": len(placed),
            "cold_count": len(cold),
            "budget_used": len(placed),
            "budget_available": budget,
        },
    }


def competitive_placement(db_path: str, managed_files_path: str) -> dict:
    with open(managed_files_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    files_list = spec.get("managed_files", [])
    by_file = spec.get("by_file", {})

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    current = current_placement_map(conn)
    now = datetime.now(timezone.utc)

    results = {}
    for file_spec in files_list:
        path = file_spec["path"]
        assigned = by_file.get(path, [])
        results[path] = place_one_file(conn, file_spec, assigned, current, now)

    conn.close()
    return {"files": results}


def main():
    parser = argparse.ArgumentParser(
        description="Claude Curator — Competitive Placement (Phase 3, per-file)"
    )
    parser.add_argument("db_path", help="Path to claude-storage.db")
    parser.add_argument(
        "--managed-files",
        required=True,
        help="Path to JSON file with managed_files + by_file map",
    )
    args = parser.parse_args()

    result = competitive_placement(args.db_path, args.managed_files)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
