#!/usr/bin/env python3
"""Check that v6.2 source file paths and computed citations resolve.

Copies .sqlite files to a temp directory, ATTACHes main and privileged
databases, checks source file paths, and reports broken computed citations
from rows that carry source_id + source_locator.

Exit code: 0 if all refs are valid, 1 if any are broken.
"""
import argparse
import os
import shutil
import sqlite3
import sys
import tempfile

from resolve_paths import load_pointer, resolve_case_data_dir

DBS = ("main", "privileged")


def _citation(file_path, source_locator):
    if not file_path:
        return "[missing file_path]"
    if source_locator:
        return f"{file_path}#{source_locator}"
    return file_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matter-root", required=True, help="Path to the matter root folder")
    args = parser.parse_args()

    matter_root = args.matter_root
    pointer = load_pointer(matter_root)
    case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])

    tmpdir = tempfile.mkdtemp(prefix="case-data-verify-")
    try:
        for db in DBS:
            src = os.path.join(case_data_dir, f"{db}.sqlite")
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmpdir, f"{db}.sqlite"))

        main_tmp = os.path.join(tmpdir, "main.sqlite")
        if not os.path.exists(main_tmp):
            print("error: main.sqlite not found", file=sys.stderr)
            sys.exit(1)

        con = sqlite3.connect(main_tmp)
        attached = ["main"]
        priv_tmp = os.path.join(tmpdir, "privileged.sqlite")
        if os.path.exists(priv_tmp):
            con.execute(f"ATTACH DATABASE '{priv_tmp}' AS privileged")
            attached.append("privileged")

        available = {}
        for db in attached:
            for (table,) in con.execute(
                f"SELECT name FROM {db}.sqlite_master WHERE type='table'"
            ).fetchall():
                available[(db, table)] = {
                    row[1]
                    for row in con.execute(f"PRAGMA {db}.table_info({table})").fetchall()
                }

        source_selects = [
            """
            SELECT 'source' AS kind, source_id AS id, file_path, NULL AS source_locator
            FROM main.sources
            WHERE file_path IS NOT NULL
            """
        ]
        if "file_path" in available.get(("privileged", "privileged_sources"), set()):
            source_selects.append(
                """
                SELECT 'privileged_source' AS kind, source_id AS id, file_path, NULL AS source_locator
                FROM privileged.privileged_sources
                WHERE file_path IS NOT NULL
                """
            )
        source_rows = con.execute(" UNION ALL ".join(source_selects)).fetchall()

        citation_selects = []
        checks = [
            ("main", "facts", "fact", "fact_id", "source_id", "source_locator"),
            ("main", "positions", "position", "position_id", "source_id", "source_locator"),
            ("main", "evidence_links", "evidence_link", "evidence_link_id", "source_id", "source_locator"),
            ("privileged", "fact_provenance", "fact_provenance", "fact_id", "source_id", "source_locator"),
        ]
        for db, table, kind, id_col, source_col, locator_col in checks:
            cols = available.get((db, table), set())
            if source_col not in cols or locator_col not in cols:
                continue
            if db == "main":
                citation_selects.append(
                    f"""
                    SELECT '{kind}' AS kind, t.{id_col} AS id, s.file_path, t.{locator_col} AS source_locator
                    FROM main.{table} t
                    LEFT JOIN main.sources s ON s.source_id = t.{source_col}
                    WHERE t.{locator_col} IS NOT NULL
                    """
                )
            else:
                citation_selects.append(
                    f"""
                    SELECT '{kind}' AS kind, t.{id_col} AS id, s.file_path, t.{locator_col} AS source_locator
                    FROM privileged.{table} t
                    LEFT JOIN privileged.privileged_sources s ON s.source_id = t.{source_col}
                    WHERE t.{locator_col} IS NOT NULL
                    """
                )
        citation_rows = (
            con.execute(" UNION ALL ".join(citation_selects)).fetchall()
            if citation_selects
            else []
        )
        con.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    rows = source_rows + citation_rows
    broken = []
    for kind, row_id, file_path, source_locator in rows:
        display = _citation(file_path, source_locator)
        if not file_path or not os.path.isfile(os.path.join(matter_root, file_path)):
            broken.append((kind, row_id, display))

    print(f"Checked {len(rows)} file/citation refs. OK: {len(rows)-len(broken)}, Broken: {len(broken)}")
    for kind, row_id, ref in broken:
        print(f"  [{kind} #{row_id}] {ref}")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
