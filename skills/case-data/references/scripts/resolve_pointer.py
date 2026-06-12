#!/usr/bin/env python3
"""
resolve_pointer.py -- Resolve the native case-data path for a matter.

Local/testing utility. In Claude Cowork, use the inline operation snippets
instead of executing this file from the mounted skill tree.
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import date

PRACTICE_DB_DEFAULT = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "Coclerk", "practice.db"
)
POINTER_FILENAME = "coclerk.json"
CASE_DATA_FOLDER = "0. CASE DATA"
MATTER_ARTIFACTS_REL = "9. AI"
EVIDENCE_SQL_REL = r"9. AI\evidence.sql"
ILLEGAL_CHARS = r'[:<>"/\\|?*]'
SCHEMA_VERSION = 3
DBS = ("main", "law", "privileged")
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


def sanitize_name(name: str, max_len: int = 60) -> str:
    name = re.sub(ILLEGAL_CHARS, "", name)
    name = name.rstrip(". ")
    return name[:max_len]


def default_case_data_root() -> str:
    override = os.environ.get("COCLERK_CASE_DATA_ROOT")
    if override:
        return override
    return os.path.join(
        os.path.expanduser("~"),
        "Logica Law",
        "Litigation - Documents",
        CASE_DATA_FOLDER,
    )


def parse_matter_token_from_folder(folder_name: str):
    match = re.match(r"^(\d+\.[A-Za-z0-9][A-Za-z0-9-]*|\.?[A-Za-z]\d+[A-Za-z0-9-]*)\b", folder_name.strip())
    return match.group(1).lstrip(".") if match else None


def lookup_matter(practice_db: str, matter_token: str):
    if not os.path.exists(practice_db):
        return None
    matt_token = matter_token.split(".", 1)[1] if "." in matter_token else matter_token
    conn = sqlite3.connect(practice_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = DELETE")
    row = conn.execute(
        """
        SELECT m.file_number, m.matt_num, m.description, c.client_num, c.name AS client_name
        FROM matters m
        LEFT JOIN clients c ON c.id = m.client_id
        WHERE upper(ltrim(coalesce(m.matt_num, ''), '.')) = upper(?)
           OR upper(coalesce(m.file_number, '')) = upper(?)
           OR upper(coalesce(m.file_number, '')) = upper(?)
        """,
        (matt_token, matter_token, matt_token),
    ).fetchone()
    conn.close()
    return row


def pointer_candidates(matter_root: str):
    return [
        os.path.join(matter_root, POINTER_FILENAME),
        os.path.join(matter_root, MATTER_ARTIFACTS_REL, POINTER_FILENAME),
    ]


def build_case_data_dir(matter_id: str | None, short_name: str) -> str:
    folder_name = f"{matter_id} {sanitize_name(short_name)}" if matter_id else sanitize_name(short_name)
    return os.path.join(default_case_data_root(), folder_name)


def matter_metadata_from_pointer(pointer: dict) -> dict:
    return {key: pointer.get(key) for key in IDENTITY_KEYS}


def pointer_with_metadata(pointer: dict, metadata: dict) -> dict:
    result = dict(pointer)
    if metadata:
        result["matter_metadata"] = metadata
    return result


def slim_pointer(case_data_dir: str, evidence_sql_path: str = EVIDENCE_SQL_REL) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_data_dir": case_data_dir,
        "evidence_sql_path": evidence_sql_path,
    }


def write_pointer(pointer_path: str, pointer: dict):
    os.makedirs(os.path.dirname(pointer_path), exist_ok=True)
    with open(pointer_path, "w", encoding="utf-8") as f:
        json.dump(pointer, f, indent=2)


def matter_id_from_parts(client_no, matter_no, file_number):
    if client_no and matter_no:
        return f"{client_no}.{matter_no}"
    return file_number or matter_no


def create_new_pointer(matter_root: str, row):
    matter_no = (row["matt_num"] or "").lstrip(".")
    client_no = row["client_num"]
    matter_id = matter_id_from_parts(client_no, matter_no, row["file_number"])
    if not matter_id:
        raise RuntimeError("Practice database matter row is missing both client_num and file_number")
    short_name = sanitize_name(row["description"] or os.path.basename(os.path.abspath(matter_root)))
    metadata = {
        "matter_id": matter_id,
        "client_no": client_no,
        "matter_no": matter_no or row["file_number"],
        "short_name": short_name,
        "client_name": row["client_name"],
        "filing_lawyer_name": None,
        "filing_lawyer_firm": None,
        "created": date.today().isoformat(),
    }
    case_data_dir = build_case_data_dir(matter_id, short_name)
    os.makedirs(case_data_dir, exist_ok=True)
    os.makedirs(os.path.join(matter_root, MATTER_ARTIFACTS_REL), exist_ok=True)
    pointer = slim_pointer(case_data_dir)
    write_pointer(os.path.join(matter_root, POINTER_FILENAME), pointer)
    return pointer_with_metadata(pointer, metadata)


def derive_case_data_dir(pointer: dict, matter_root: str, metadata: dict) -> str:
    stored = pointer.get("case_data_dir", "")
    if stored and stored not in (MATTER_ARTIFACTS_REL, f"{MATTER_ARTIFACTS_REL}\\"):
        return stored

    matter_id = metadata.get("matter_id") or parse_matter_token_from_folder(
        os.path.basename(os.path.abspath(matter_root))
    )
    short_name = metadata.get("short_name") or os.path.basename(os.path.abspath(matter_root))
    return build_case_data_dir(str(matter_id) if matter_id else None, str(short_name))


def read_matter_metadata(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='matter_metadata'"
        ).fetchone()
        if not exists:
            return {}
        return {key: value for key, value in conn.execute("SELECT key, value FROM matter_metadata")}
    finally:
        conn.close()


def migrate_9_ai_databases(matter_root: str, case_data_dir: str) -> tuple[str, dict]:
    source_dir = os.path.join(matter_root, MATTER_ARTIFACTS_REL)
    if not os.path.isdir(source_dir):
        return case_data_dir, {}
    os.makedirs(case_data_dir, exist_ok=True)
    for db in DBS:
        src = os.path.join(source_dir, f"{db}.sqlite")
        dst = os.path.join(case_data_dir, f"{db}.sqlite")
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.move(src, dst)
    metadata = read_matter_metadata(os.path.join(case_data_dir, "main.sqlite"))
    if not metadata:
        return case_data_dir, {}

    final_dir = build_case_data_dir(
        metadata.get("matter_id"),
        metadata.get("short_name") or os.path.basename(os.path.abspath(matter_root)),
    )
    if final_dir == case_data_dir or not os.path.exists(os.path.join(case_data_dir, "main.sqlite")):
        return case_data_dir, metadata

    os.makedirs(os.path.dirname(final_dir), exist_ok=True)
    if not os.path.exists(final_dir):
        os.rename(case_data_dir, final_dir)
    else:
        for db in DBS:
            src = os.path.join(case_data_dir, f"{db}.sqlite")
            dst = os.path.join(final_dir, f"{db}.sqlite")
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.move(src, dst)
    return final_dir, metadata


def normalize_pointer(pointer_path: str, pointer: dict, matter_root: str) -> dict:
    metadata = matter_metadata_from_pointer(pointer)
    case_data_dir = derive_case_data_dir(pointer, matter_root, metadata)
    if pointer.get("case_data_dir") in (MATTER_ARTIFACTS_REL, f"{MATTER_ARTIFACTS_REL}\\"):
        case_data_dir, db_metadata = migrate_9_ai_databases(matter_root, case_data_dir)
        metadata = {**metadata, **db_metadata}

    normalized = slim_pointer(
        case_data_dir,
        pointer.get("evidence_sql_path", EVIDENCE_SQL_REL),
    )
    write_pointer(pointer_path, normalized)
    return pointer_with_metadata(normalized, metadata)


def resolve(matter_root: str, practice_db: str = PRACTICE_DB_DEFAULT):
    for pointer_path in pointer_candidates(matter_root):
        if os.path.exists(pointer_path):
            with open(pointer_path, encoding="utf-8") as f:
                pointer = json.load(f)
            return normalize_pointer(pointer_path, pointer, matter_root)

    folder_name = os.path.basename(os.path.abspath(matter_root))
    matter_token = parse_matter_token_from_folder(folder_name)
    if matter_token is None:
        raise RuntimeError(
            f"Cannot derive matter number from folder name '{folder_name}'. "
            "Rename the folder to start with a matter number like 'L153' or "
            "supply a coclerk.json manually."
        )

    row = lookup_matter(practice_db, matter_token)
    if row is None:
        raise RuntimeError(
            f"matter number '{matter_token}' not found in practice.db at '{practice_db}'. "
            "Register the matter in the practice database first, or supply "
            "a coclerk.json manually."
        )

    return create_new_pointer(matter_root, row)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("matter_root")
    ap.add_argument("--practice-db", default=PRACTICE_DB_DEFAULT)
    args = ap.parse_args()
    try:
        result = resolve(args.matter_root, args.practice_db)
        print(json.dumps(result, indent=2))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
