#!/usr/bin/env python3
"""
resolve_paths.py -- Shared path resolution for local case-data utilities.

Cowork operation docs use inline snippets. This module remains for local tests
and manual script runs.
"""

import os
import re

POINTER_FILENAME = "coclerk.json"
CASE_DATA_FOLDER = "0. CASE DATA"
MATTER_ARTIFACTS_REL = "9. AI"
DEFAULT_EVIDENCE_SQL_REL = os.path.join(MATTER_ARTIFACTS_REL, "evidence.sql")
LEGACY_EVIDENCE_SQL_REL = os.path.join("ai", "evidence", "evidence.sql")


def pointer_candidates(matter_root: str):
    return [
        os.path.join(matter_root, POINTER_FILENAME),
        os.path.join(matter_root, MATTER_ARTIFACTS_REL, POINTER_FILENAME),
    ]


def load_pointer(matter_root: str) -> dict:
    import json

    for pointer_path in pointer_candidates(matter_root):
        if os.path.exists(pointer_path):
            with open(pointer_path, encoding="utf-8") as f:
                return json.load(f)
    raise RuntimeError(
        "coclerk.json not found at matter root or under '9. AI'. "
        "Resolve the matter pointer first."
    )


def is_absolute_path(path: str) -> bool:
    return bool(
        os.path.isabs(path)
        or re.match(r"^[A-Za-z]:[\\/]", path)
        or path.startswith("\\\\")
    )


def join_relative(matter_root: str, rel_path: str) -> str:
    parts = [part for part in re.split(r"[\\/]+", rel_path) if part]
    return os.path.normpath(os.path.join(matter_root, *parts))


def resolve_case_data_dir(matter_root: str, stored_path: str) -> str:
    """
    Resolve case_data_dir to an existing directory.

    Absolute Windows paths are canonical. In a Linux sandbox, fall back to a
    sibling-mounted 0. CASE DATA folder with the same final folder name.
    """
    if not stored_path:
        raise RuntimeError("case_data_dir missing from coclerk.json")

    if not is_absolute_path(stored_path):
        candidate = join_relative(matter_root, stored_path)
        if os.path.isdir(candidate):
            return candidate
        raise RuntimeError(f"case_data_dir '{candidate}' does not exist")

    if os.path.isdir(stored_path):
        return stored_path

    case_data_folder = os.path.basename(stored_path.replace("\\", "/").rstrip("/"))
    candidate = os.path.normpath(
        os.path.join(matter_root, "..", CASE_DATA_FOLDER, case_data_folder)
    )
    if os.path.isdir(candidate):
        return candidate

    raise RuntimeError(
        f"Cannot resolve case_data_dir: stored path '{stored_path}' does not exist "
        f"and relative fallback '{candidate}' not found."
    )


def resolve_evidence_sql_path(matter_root: str, pointer: dict) -> str:
    stored_path = pointer.get("evidence_sql_path")
    if not stored_path:
        legacy = join_relative(matter_root, LEGACY_EVIDENCE_SQL_REL)
        if os.path.exists(legacy):
            return legacy
        stored_path = DEFAULT_EVIDENCE_SQL_REL
    if is_absolute_path(stored_path):
        return os.path.normpath(stored_path)
    return join_relative(matter_root, stored_path)


def resolve_db_paths(matter_root: str, stored_path: str) -> dict:
    case_data_dir = resolve_case_data_dir(matter_root, stored_path)
    main_path = os.path.join(case_data_dir, "main.sqlite")
    if not os.path.exists(main_path):
        raise RuntimeError(f"main.sqlite not found in '{case_data_dir}'")

    paths = {"main": main_path}
    for db in ("law", "privileged"):
        path = os.path.join(case_data_dir, f"{db}.sqlite")
        if os.path.exists(path):
            paths[db] = path
    return paths
