#!/usr/bin/env python3
"""
get_facts_for_drafting.py -- Return v6.2 facts with posture and citations.

This is a local helper for skills that draft from case data. Cowork operation
docs still use inline snippets; this script is for local runs and downstream
skill harnesses.

Usage:
    python get_facts_for_drafting.py --matter-root <path>

Returns JSON to stdout:
{
  "facts": [
    {
      "fact_id": 1,
      "description": "...",
      "category": "contract",
      "date_of_fact": "2024-06-01",
      "posture": "disputed",
      "citation": "5. COURT FILE/NOCC.pdf#para. 3",
      "origin_citation": "5. COURT FILE/NOCC.pdf#para. 3",
      "evidence_count": 1,
      "evidence_citations": [
        {"source_id": 4, "title": "Affidavit #1", "citation": "...#para. 12", "strength": 2}
      ],
      "position_citations": [
        {"source_id": 2, "title": "Response", "citation": "...#para. 3", "position": "deny"}
      ]
    }
  ]
}
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile

from fuse_safe_io import read_text
from resolve_paths import load_pointer, resolve_case_data_dir

QUERY_MARKERS = (
    "CREATE VIEW IF NOT EXISTS v_current_positions AS",
    "CREATE VIEW IF NOT EXISTS v_fact_status AS",
)


def _citation(file_path, source_locator):
    if not file_path:
        return None
    if source_locator:
        return f"{file_path}#{source_locator}"
    return file_path


def _load_views(conn):
    queries_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "queries.sql"
    )
    if not os.path.exists(queries_path):
        return
    text = read_text(queries_path, required_markers=QUERY_MARKERS)
    view_block = re.split(
        r"-- =+\r?\n-- CANONICAL QUERIES",
        text,
        maxsplit=1,
    )[0]
    conn.executescript(view_block)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matter-root", required=True)
    args = parser.parse_args()

    matter_root = args.matter_root
    try:
        pointer = load_pointer(matter_root)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
    main_src = os.path.join(case_data_dir, "main.sqlite")
    if not os.path.exists(main_src):
        print("error: main.sqlite not found", file=sys.stderr)
        sys.exit(1)

    tmpdir = tempfile.mkdtemp(prefix="coclerk_facts_")
    try:
        main_tmp = os.path.join(tmpdir, "main.sqlite")
        shutil.copy2(main_src, main_tmp)

        conn = sqlite3.connect(main_tmp)
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.row_factory = sqlite3.Row
        _load_views(conn)

        facts_rows = conn.execute(
            """
            SELECT
                f.fact_id,
                f.description,
                f.category,
                f.date_of_fact,
                f.source_id,
                f.source_locator,
                s.title AS origin_title,
                s.file_path AS origin_file_path,
                v.posture
            FROM facts f
            LEFT JOIN sources s ON s.source_id = f.source_id
            LEFT JOIN v_fact_status v ON v.fact_id = f.fact_id
            WHERE f.verified >= 0
            ORDER BY f.category, f.date_of_fact, f.fact_id
            """
        ).fetchall()

        facts = []
        for row in facts_rows:
            fid = row["fact_id"]
            origin_citation = _citation(row["origin_file_path"], row["source_locator"])

            evidence_rows = conn.execute(
                """
                SELECT
                    el.source_id,
                    s.title,
                    s.file_path,
                    el.source_locator,
                    el.strength,
                    el.notes
                FROM evidence_links el
                JOIN sources s ON s.source_id = el.source_id
                WHERE el.fact_id = ?
                  AND el.valid_to IS NULL
                  AND el.verified >= 0
                  AND el.strength > 0
                ORDER BY el.strength DESC, el.evidence_link_id
                """,
                (fid,),
            ).fetchall()

            evidence_citations = [
                {
                    "source_id": er["source_id"],
                    "title": er["title"],
                    "citation": _citation(er["file_path"], er["source_locator"]),
                    "strength": er["strength"],
                    "notes": er["notes"],
                }
                for er in evidence_rows
            ]

            position_rows = conn.execute(
                """
                SELECT
                    p.position,
                    p.qualification,
                    p.source_id,
                    p.source_locator,
                    s.title,
                    s.file_path
                FROM positions p
                LEFT JOIN sources s ON s.source_id = p.source_id
                WHERE p.fact_id = ?
                  AND p.valid_to IS NULL
                  AND p.verified >= 0
                ORDER BY p.position_id
                """,
                (fid,),
            ).fetchall()

            position_citations = [
                {
                    "source_id": pr["source_id"],
                    "title": pr["title"],
                    "citation": _citation(pr["file_path"], pr["source_locator"]),
                    "position": pr["position"],
                    "qualification": pr["qualification"],
                }
                for pr in position_rows
            ]

            primary_citation = (
                evidence_citations[0]["citation"]
                if evidence_citations
                else origin_citation
            )

            facts.append(
                {
                    "fact_id": fid,
                    "description": row["description"],
                    "category": row["category"],
                    "date_of_fact": row["date_of_fact"],
                    "posture": row["posture"] or "unclaimed",
                    "citation": primary_citation,
                    "origin_citation": origin_citation,
                    "evidence_count": len(evidence_citations),
                    "evidence_citations": evidence_citations,
                    "position_citations": position_citations,
                }
            )

        conn.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(json.dumps({"facts": facts}, indent=2))


if __name__ == "__main__":
    main()
