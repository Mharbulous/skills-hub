#!/usr/bin/env python3
"""Dump three-database matter folder into one canonical evidence.sql with section markers.

Reads coclerk.json to locate case_data_dir. Copies the three .sqlite files
from case_data_dir to /tmp for reading under journal_mode=DELETE. Writes a single evidence.sql with
`-- ===== v6 BEGIN <db> =====` markers to the pointer's dump path.
"""
import argparse, os, shutil, sqlite3, sys, tempfile

from resolve_paths import load_pointer, resolve_case_data_dir, resolve_evidence_sql_path

DBS = ("main", "law", "privileged")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matter-root", required=True, help="Path to the matter root folder")
    args = parser.parse_args()

    matter_root = args.matter_root
    pointer = load_pointer(matter_root)
    case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
    dump_file = resolve_evidence_sql_path(matter_root, pointer)
    os.makedirs(os.path.dirname(dump_file), exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="case-data-dump-")
    try:
        tmp_paths = {}
        for db in DBS:
            tmp_paths[db] = os.path.join(tmpdir, f"{db}.sqlite")
            shutil.copy2(os.path.join(case_data_dir, f"{db}.sqlite"), tmp_paths[db])

        total_lines = 0
        with open(dump_file, "w", encoding="utf-8") as f:
            for db in DBS:
                db_file = tmp_paths[db]
                if not os.path.isfile(db_file):
                    print(f"ERROR: {db_file} not found", file=sys.stderr); sys.exit(1)
                c = sqlite3.connect(db_file)
                jm = c.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
                if jm.lower() != "delete":
                    print(f"ERROR: {db}.sqlite journal_mode is {jm!r}, expected 'delete' "
                          f"(v6 atomicity requirement)", file=sys.stderr); sys.exit(2)
                f.write(f"-- ===== v6 BEGIN {db} =====\n")
                for line in c.iterdump():
                    f.write(line + "\n"); total_lines += 1
                f.write(f"-- ===== v6 END {db} =====\n")
                c.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"Done. {total_lines} lines written across 3 sections.")

if __name__ == "__main__":
    main()
