#!/usr/bin/env python3
"""Rebuild three .sqlite files from one evidence.sql with section markers.

Procedure (atomic from case_data_dir's perspective):
  1. Read evidence.sql with fuse_safe_io so stale FUSE st_size cannot truncate it.
  2. Parse into three sections by `-- ===== v6 BEGIN <db> =====` markers.
  3. Build main.sqlite, law.sqlite, privileged.sqlite in /tmp.
  4. ATTACH all three on one connection; load triggers.sql from skill references;
     assert PRAGMA journal_mode='delete' on every database.
  5. Smoke-check table counts.
  6. Atomically move the three files into case_data_dir.
     If any step fails, case_data_dir is untouched.
"""
import argparse, os, re, shutil, sqlite3, sys, tempfile

from fuse_safe_io import read_text
from resolve_paths import load_pointer, resolve_case_data_dir, resolve_evidence_sql_path

DBS = ("main", "law", "privileged")
SECTION_MARKERS = tuple(
    marker
    for db in DBS
    for marker in (f"-- ===== v6 BEGIN {db} =====", f"-- ===== v6 END {db} =====")
)
TRIGGER_MARKERS = (
    "CREATE TEMP TRIGGER trg_criteria_facts_criterion_id_insert",
    "CREATE TEMP TRIGGER trg_facts_delete_guard",
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matter-root", required=True, help="Path to the matter root folder")
    args = parser.parse_args()

    matter_root = args.matter_root
    pointer = load_pointer(matter_root)
    case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
    dump_file = resolve_evidence_sql_path(matter_root, pointer)

    # Triggers live in the skill's references/ dir (one level up from this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    triggers_file = os.path.join(script_dir, "..", "triggers.sql")
    if not os.path.isfile(triggers_file):
        print(f"ERROR: {triggers_file} not found", file=sys.stderr); sys.exit(1)

    if not os.path.isfile(dump_file):
        print(f"ERROR: {dump_file} not found", file=sys.stderr); sys.exit(1)

    full = read_text(dump_file, required_markers=SECTION_MARKERS)

    sections = {m.group(1): m.group(2) for m in re.finditer(
        r"-- ===== v6 BEGIN (\w+) =====\r?\n(.*?)\r?\n-- ===== v6 END \1 =====",
        full,
        re.DOTALL,
    )}
    if set(sections) != set(DBS):
        print(f"ERROR: expected sections {DBS}, found {sorted(sections)}",
              file=sys.stderr); sys.exit(2)

    tmp = tempfile.mkdtemp(prefix="rebuild_")
    tmp_paths = {db: os.path.join(tmp, f"{db}.sqlite") for db in DBS}
    try:
        for db in DBS:
            c = sqlite3.connect(tmp_paths[db])
            c.execute("PRAGMA journal_mode = DELETE")
            c.executescript(sections[db])
            c.commit(); c.close()

        # Open main directly; SQLite reserves the schema name "main".
        con = sqlite3.connect(tmp_paths["main"])
        con.execute(f"ATTACH DATABASE '{tmp_paths['law']}' AS law")
        con.execute(f"ATTACH DATABASE '{tmp_paths['privileged']}' AS privileged")
        for db in DBS:
            jm = con.execute(f"PRAGMA {db}.journal_mode = DELETE").fetchone()[0]
            if jm.lower() != "delete":
                print(f"ERROR: {db} journal_mode={jm!r}, expected 'delete'",
                      file=sys.stderr); sys.exit(3)
        triggers_sql = read_text(triggers_file, required_markers=TRIGGER_MARKERS)
        con.executescript(triggers_sql)
        # Smoke check: each database has expected minimum tables
        for db, expected_min in [("main", 14), ("law", 4), ("privileged", 2)]:
            n = con.execute(
                f"SELECT COUNT(*) FROM {db}.sqlite_master WHERE type='table'").fetchone()[0]
            if n < expected_min:
                print(f"ERROR: {db} has {n} tables, expected >= {expected_min}",
                      file=sys.stderr); sys.exit(4)
        has_metadata = con.execute(
            "SELECT 1 FROM main.sqlite_master "
            "WHERE type='table' AND name='matter_metadata'"
        ).fetchone()
        if not has_metadata:
            print("ERROR: main.matter_metadata missing after rebuild",
                  file=sys.stderr); sys.exit(4)
        con.close()
        print("Integrity checks passed; moving files to case_data_dir.")
        for db in DBS:
            dst = os.path.join(case_data_dir, f"{db}.sqlite")
            if os.path.exists(dst): os.remove(dst)
            shutil.move(tmp_paths[db], dst)
        print("Rebuild complete.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
