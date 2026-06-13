# Initialize -- Create Case-Data Databases for a Matter

Creates `coclerk.json`, a native `0. CASE DATA\<matter>` database folder, the three empty `.sqlite` databases, and the initial `4. LAWYER BRIEF\CoWork\evidence.sql` dump for a matter.

## Step 0: Resolve or Create the Pointer

Use inline code only in Cowork. Do not call `resolve_pointer.py`.

If `coclerk.json` already exists in the matter root or `9. AI\coclerk.json`, do not overwrite it. Resolve it with the shared pointer-resolution snippet from `SKILL.md`; if it points at existing databases, report the existing paths and stop. Only create a new pointer when no pointer exists.

```python
import json, os, re, sqlite3
from datetime import date

PRACTICE_DB_DEFAULT = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Coclerk", "practice.db")
CASE_DATA_FOLDER = "0. CASE DATA"
MATTER_ARTIFACTS_REL = "9. AI"
DUMP_DIR_REL = os.path.join("4. LAWYER BRIEF", "CoWork")
POINTER_FILENAME = "coclerk.json"

def pointer_candidates(matter_root):
    return [
        os.path.join(matter_root, POINTER_FILENAME),
        os.path.join(matter_root, MATTER_ARTIFACTS_REL, POINTER_FILENAME),
    ]

def sanitize(name):
    return re.sub(r'[:<>"/\\|?*]', "", name).rstrip(". ")[:60]

def case_data_root(matter_root):
    return os.environ.get("COCLERK_CASE_DATA_ROOT") or os.path.join(
        os.path.dirname(os.path.normpath(matter_root)), CASE_DATA_FOLDER
    )

def parse_folder_matter_token(matter_root):
    folder_name = os.path.basename(os.path.normpath(matter_root)).strip()
    match = re.match(r"^(\d+\.[A-Za-z0-9][A-Za-z0-9-]*|\.?[A-Za-z]\d+[A-Za-z0-9-]*)\b", folder_name)
    if not match:
        raise RuntimeError("Matter folder must start with a matter number like L153 or a full identifier like 4165.L153, or provide coclerk.json manually")
    return match.group(1).lstrip(".")

def matter_id_from_parts(client_no, matter_no, file_number):
    if client_no and matter_no:
        return f"{client_no}.{matter_no}"
    return file_number or matter_no

def lookup_matter(practice_db, matter_token, matter_root):
    matt_token = matter_token.split(".", 1)[1] if "." in matter_token else matter_token
    con = sqlite3.connect(practice_db)
    con.row_factory = sqlite3.Row
    row = con.execute("""
        SELECT m.file_number, m.matt_num, m.description, c.client_num, c.name AS client_name
        FROM matters m
        LEFT JOIN clients c ON c.id = m.client_id
        WHERE upper(ltrim(coalesce(m.matt_num, ''), '.')) = upper(?)
           OR upper(coalesce(m.file_number, '')) = upper(?)
           OR upper(coalesce(m.file_number, '')) = upper(?)
    """, (matt_token, matter_token, matt_token)).fetchone()
    con.close()
    if not row:
        raise RuntimeError(f"matter number {matter_token!r} not found in practice database")
    matter_no = (row["matt_num"] or matter_token).lstrip(".")
    client_no = row["client_num"]
    matter_id = matter_id_from_parts(client_no, matter_no, row["file_number"])
    if not matter_id:
        raise RuntimeError(f"Practice database row for {matter_token!r} is missing both client_num and file_number")
    return {
        "matter_id": matter_id,
        "client_no": client_no,
        "matter_no": matter_no,
        "short_name": sanitize(row["description"] or os.path.basename(os.path.normpath(matter_root))),
        "client_name": row["client_name"],
    }

def create_pointer(matter_root, practice_db=PRACTICE_DB_DEFAULT):
    existing = next((p for p in pointer_candidates(matter_root) if os.path.exists(p)), None)
    if existing:
        raise RuntimeError(f"coclerk.json already exists at {existing}; resolve existing pointer instead of initializing")

    metadata = lookup_matter(practice_db, parse_folder_matter_token(matter_root), matter_root)
    case_data_dir = os.path.join(case_data_root(matter_root), f"{metadata['matter_id']} {metadata['short_name']}")
    os.makedirs(case_data_dir, exist_ok=True)
    os.makedirs(os.path.join(matter_root, DUMP_DIR_REL), exist_ok=True)
    pointer = {
        "schema_version": 3,
        "case_data_dir": case_data_dir,
        "evidence_sql_path": os.path.join(DUMP_DIR_REL, "evidence.sql"),
    }
    with open(os.path.join(matter_root, POINTER_FILENAME), "w", encoding="utf-8") as f:
        json.dump(pointer, f, indent=2)
    pointer["matter_metadata"] = {
        **metadata,
        "filing_lawyer_name": None,
        "filing_lawyer_firm": None,
        "created": date.today().isoformat(),
    }
    return pointer

pointer = create_pointer(matter_root)
case_data_dir = pointer["case_data_dir"]
```

## Step 1: Check for Existing Data

If any of `main.sqlite`, `law.sqlite`, or `privileged.sqlite` already exists in `case_data_dir`, halt and report the paths. Do not initialize over existing databases.

If any `.sqlite` binaries exist under `9. AI\`, do not initialize over them. Resolve the pointer with the shared snippet in `SKILL.md` so legacy binaries are moved to native `0. CASE DATA` storage.

## Step 2: Read Schema and Triggers

Read `references/schema.sql` and `references/triggers.sql` with Codex's host-side Read tool. Paste their exact current contents into the build script variables below. Do not read those files with Python or shell commands in Cowork.

## Step 3: Create the Matter Folder Structure

```text
{matter root}\
    coclerk.json
    4. LAWYER BRIEF\
        CoWork\
            evidence.sql

0. CASE DATA\
    <matter>\
        main.sqlite
        law.sqlite
        privileged.sqlite
```

Schema, triggers, queries, scripts, and playbooks are read from this skill's `references\` directory by Codex, not copied into the matter folder.

## Step 4: Build the Databases

```python
import os, re, shutil, sqlite3, tempfile

SCHEMA_SQL = """<paste host-side Read of references/schema.sql here>"""
TRIGGERS_SQL = """<paste host-side Read of references/triggers.sql here>"""
DBS = ("main", "law", "privileged")
metadata = pointer.get("matter_metadata")
if not metadata:
    raise RuntimeError("matter_metadata missing from initialization pointer")

schema_markers = [f"-- ===== v6 {kind} {db} =====" for db in DBS for kind in ("BEGIN", "END")]
missing = [marker for marker in schema_markers if marker not in SCHEMA_SQL]
if missing:
    raise RuntimeError(f"schema.sql missing marker(s): {missing}")
for marker in ("CREATE TEMP TRIGGER trg_criteria_facts_criterion_id_insert", "CREATE TEMP TRIGGER trg_facts_delete_guard"):
    if marker not in TRIGGERS_SQL:
        raise RuntimeError(f"triggers.sql missing marker: {marker}")

sections = {}
for db in DBS:
    match = re.search(rf"-- ===== v6 BEGIN {db} =====\r?\n(.*?)\r?\n-- ===== v6 END {db} =====", SCHEMA_SQL, re.DOTALL)
    if not match:
        raise RuntimeError(f"schema.sql missing {db} section")
    sections[db] = match.group(1).strip()

tmpdir = tempfile.mkdtemp(prefix="case-data-init-")
try:
    tmp_paths = {db: os.path.join(tmpdir, f"{db}.sqlite") for db in DBS}
    for db in DBS:
        con = sqlite3.connect(tmp_paths[db])
        jm = con.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
        if jm.lower() != "delete":
            raise RuntimeError(f"{db}.sqlite journal_mode is {jm!r}, expected 'delete'")
        con.executescript(sections[db])
        if db == "main":
            con.executemany(
                "INSERT INTO matter_metadata (key, value) VALUES (?, ?)",
                [(key, None if metadata.get(key) is None else str(metadata.get(key))) for key in (
                    "matter_id", "client_no", "matter_no", "short_name",
                    "client_name", "filing_lawyer_name", "filing_lawyer_firm", "created"
                )],
            )
        con.commit()
        con.close()

    con = sqlite3.connect(tmp_paths["main"])
    con.execute(f"ATTACH DATABASE '{tmp_paths['law']}' AS law")
    con.execute(f"ATTACH DATABASE '{tmp_paths['privileged']}' AS privileged")
    con.executescript(TRIGGERS_SQL)
    con.close()

    os.makedirs(case_data_dir, exist_ok=True)
    for db in DBS:
        shutil.move(tmp_paths[db], os.path.join(case_data_dir, f"{db}.sqlite"))
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

## Step 5: Generate Initial Dump

Run the dump procedure from `operations/maintain.md`. The dump reads the closed `.sqlite` files from native `case_data_dir`, asserts `journal_mode = DELETE`, and writes `evidence.sql` to `4. LAWYER BRIEF\CoWork\evidence.sql`.

## Step 6: Report

Report the pointer path, native `case_data_dir`, and `evidence.sql` path to the user, then prompt them to seed proceedings metadata with `operations/proceedings-profile.md` or ingest sources with `operations/ingest.md`.
