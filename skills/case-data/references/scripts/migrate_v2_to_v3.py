#!/usr/bin/env python3
"""Migrate a v2 matter pointer to v3 matter_metadata storage.

The migration stages main.sqlite in /tmp, writes matter_metadata there, moves
the closed database back into case_data_dir, slims coclerk.json, then refreshes
evidence.sql through dump.py.
"""

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from resolve_paths import (
    CASE_DATA_REL,
    pointer_candidates,
    resolve_case_data_dir,
)

SCHEMA_VERSION = 3
EVIDENCE_SQL_REL = r"9. AI\evidence.sql"
IDENTITY_KEYS = (
    "matter_id",
    "client_no",
    "matter_no",
    "short_name",
    "client_name",
    "filing_lawyer_name",
    "filing_lawyer_firm",
    "created",
)


def find_pointer(matter_root: str):
    for pointer_path in pointer_candidates(matter_root):
        if os.path.exists(pointer_path):
            with open(pointer_path, encoding="utf-8") as f:
                return pointer_path, json.load(f)
    raise RuntimeError("coclerk.json not found at matter root or under '9. AI'")


def slim_pointer(pointer: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_data_dir": pointer.get("case_data_dir", CASE_DATA_REL),
        "evidence_sql_path": pointer.get("evidence_sql_path", EVIDENCE_SQL_REL),
    }


def metadata_rows(pointer: dict):
    rows = []
    for key in IDENTITY_KEYS:
        value = pointer.get(key)
        rows.append((key, None if value is None else str(value)))
    return rows


def migrate_main_sqlite(main_src: str) -> str:
    if not os.path.isdir("/tmp"):
        raise RuntimeError("/tmp staging directory not found")
    try:
        tmpdir = tempfile.mkdtemp(prefix="coclerk_v2_to_v3_", dir="/tmp")
    except OSError as e:
        raise RuntimeError(f"cannot create /tmp staging directory: {e}") from e
    staged = os.path.join(tmpdir, "main.sqlite")
    shutil.copy2(main_src, staged)
    return staged


def seed_metadata(staged_main: str, pointer: dict) -> None:
    conn = sqlite3.connect(staged_main)
    try:
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS matter_metadata (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.executemany(
            "INSERT OR REPLACE INTO matter_metadata (key, value) VALUES (?, ?)",
            metadata_rows(pointer),
        )
        conn.commit()
    finally:
        conn.close()


def run_dump(script_dir: str, matter_root: str) -> None:
    dump_script = os.path.join(script_dir, "dump.py")
    result = subprocess.run(
        [sys.executable, dump_script, "--matter-root", matter_root],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "dump.py failed")
    print(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matter-root", required=True, help="Path to the matter root folder")
    args = parser.parse_args()

    matter_root = args.matter_root
    try:
        pointer_path, pointer = find_pointer(matter_root)
        if pointer.get("schema_version") != 2:
            raise RuntimeError(
                f"expected schema_version 2 pointer, found {pointer.get('schema_version')!r}"
            )

        case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
        main_src = os.path.join(case_data_dir, "main.sqlite")
        if not os.path.isfile(main_src):
            raise RuntimeError(f"main.sqlite not found in '{case_data_dir}'")

        staged_main = migrate_main_sqlite(main_src)
        try:
            seed_metadata(staged_main, pointer)
            os.replace(staged_main, main_src)
        finally:
            shutil.rmtree(os.path.dirname(staged_main), ignore_errors=True)

        with open(pointer_path, "w", encoding="utf-8") as f:
            json.dump(slim_pointer(pointer), f, indent=2)

        run_dump(os.path.dirname(os.path.abspath(__file__)), matter_root)
        print("Migration complete: coclerk.json is v3 and main.sqlite has matter_metadata.")
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
