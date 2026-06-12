#!/usr/bin/env python3
"""
get_matter_profile.py — Return structured matter profile with gap detection.

Reads main.matter_metadata for matter-level fields and queries main.sqlite for
proceedings, parties, and proceeding_parties. Reports gaps for downstream
consumers that need a complete profile before proceeding.

Usage:
    python get_matter_profile.py --matter-root <path>

Returns JSON to stdout. Exits non-zero on failure.
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile

from resolve_paths import load_pointer, resolve_case_data_dir


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

    tmpdir = tempfile.mkdtemp(prefix="case-data-profile-")
    core_tmp = os.path.join(tmpdir, "main.sqlite")
    shutil.copy2(main_src, core_tmp)

    conn = sqlite3.connect(core_tmp)
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.row_factory = sqlite3.Row

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "matter_metadata" in tables:
        matter_metadata = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM matter_metadata").fetchall()
        }
    else:
        matter_metadata = {
            "matter_id": pointer.get("matter_id"),
            "short_name": pointer.get("short_name"),
            "client_name": pointer.get("client_name"),
            "filing_lawyer_name": pointer.get("filing_lawyer_name"),
            "filing_lawyer_firm": pointer.get("filing_lawyer_firm"),
        }

    # Query proceedings
    proceedings_rows = conn.execute(
        "SELECT proceeding_id, court, registry, file_number, style_of_cause, "
        "courthouse_address, trial_date, status "
        "FROM proceedings ORDER BY proceeding_id"
    ).fetchall()

    proceedings = []
    for p in proceedings_rows:
        pid = p["proceeding_id"]

        # Query parties for this proceeding
        party_rows = conn.execute(
            "SELECT pa.name, pp.role, pa.lawyer_name, pa.lawyer_firm "
            "FROM proceeding_parties pp "
            "JOIN parties pa ON pa.party_id = pp.party_id "
            "WHERE pp.proceeding_id = ? "
            "ORDER BY pp.role, pa.name",
            (pid,),
        ).fetchall()

        parties = []
        for pa in party_rows:
            parties.append({
                "name": pa["name"],
                "role": pa["role"],
                "lawyer_name": pa["lawyer_name"],
                "lawyer_firm": pa["lawyer_firm"],
            })

        proc = {
            "proceeding_id": pid,
            "court": p["court"],
            "registry": p["registry"],
            "file_number": p["file_number"],
            "style_of_cause": p["style_of_cause"],
            "courthouse_address": p["courthouse_address"],
            "trial_date": p["trial_date"],
            "status": p["status"],
            "parties": parties,
        }
        proceedings.append(proc)

    conn.close()
    shutil.rmtree(tmpdir, ignore_errors=True)

    # Build profile
    profile = {
        "matter_id": matter_metadata.get("matter_id"),
        "short_name": matter_metadata.get("short_name"),
        "client_name": matter_metadata.get("client_name"),
        "filing_lawyer_name": matter_metadata.get("filing_lawyer_name"),
        "filing_lawyer_firm": matter_metadata.get("filing_lawyer_firm"),
        "proceedings": proceedings,
        "gaps": [],
    }

    # Gap detection — matter-level
    for field in ("client_name", "filing_lawyer_name", "filing_lawyer_firm"):
        if not profile[field]:
            profile["gaps"].append(f"matter-level: {field} missing")

    # Gap detection — per-proceeding
    for proc in proceedings:
        fn = proc["file_number"] or f"id={proc['proceeding_id']}"
        for field in ("court", "registry", "file_number", "style_of_cause", "courthouse_address"):
            if not proc[field]:
                profile["gaps"].append(f"proceeding {fn}: {field} missing")
        if not proc["parties"]:
            profile["gaps"].append(f"proceeding {fn}: no parties linked")
        # trial_date NULL is informational, not a gap

    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
