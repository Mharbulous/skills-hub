# Maintain -- Dump, Rebuild, and Verify the Evidence Database

## Dump

Run after every mutation. The committed text dump (`evidence.sql`) is the canonical migration boundary; if the dump is stale, the database cannot be rebuilt. Dump writes `evidence.sql`; it never reads it.

Use inline code only in Cowork. Do not call `dump.py`. Before running this snippet, run the shared pointer-resolution snippet from `SKILL.md` so legacy `9. AI` database binaries migrate to native `0. CASE DATA` storage.

```python
import json, os, re, shutil, sqlite3, tempfile

DBS = ("main", "law", "privileged")

def is_abs(path):
    return bool(os.path.isabs(path) or re.match(r"^[A-Za-z]:[\\/]", path) or path.startswith("\\\\"))

def join_rel(root, rel):
    return os.path.normpath(os.path.join(root, *[p for p in re.split(r"[\\/]+", rel) if p]))

def load_pointer(matter_root):
    for path in (os.path.join(matter_root, "coclerk.json"), os.path.join(matter_root, "9. AI", "coclerk.json")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise RuntimeError("coclerk.json not found")

def resolve_case_data_dir(matter_root, stored_path):
    if is_abs(stored_path) and os.path.isdir(stored_path):
        return stored_path
    if not is_abs(stored_path):
        candidate = join_rel(matter_root, stored_path)
        if os.path.isdir(candidate):
            return candidate
    folder = os.path.basename(stored_path.replace("\\", "/").rstrip("/"))
    candidate = os.path.normpath(os.path.join(matter_root, "..", "0. CASE DATA", folder))
    if os.path.isdir(candidate):
        return candidate
    raise RuntimeError(f"Cannot resolve case_data_dir: {stored_path}")

def resolve_evidence_sql_path(matter_root, pointer):
    stored = pointer.get("evidence_sql_path", os.path.join("4. LAWYER BRIEF", "CoWork", "evidence.sql"))
    return os.path.normpath(stored) if is_abs(stored) else join_rel(matter_root, stored)

pointer = load_pointer(matter_root)
case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
dump_file = resolve_evidence_sql_path(matter_root, pointer)
os.makedirs(os.path.dirname(dump_file), exist_ok=True)

tmpdir = tempfile.mkdtemp(prefix="case-data-dump-")
try:
    tmp_paths = {}
    for db in DBS:
        src = os.path.join(case_data_dir, f"{db}.sqlite")
        if not os.path.exists(src):
            raise RuntimeError(f"{src} not found")
        tmp_paths[db] = os.path.join(tmpdir, f"{db}.sqlite")
        shutil.copy2(src, tmp_paths[db])

    total_lines = 0
    with open(dump_file, "w", encoding="utf-8", newline="\n") as f:
        for db in DBS:
            con = sqlite3.connect(tmp_paths[db])
            jm = con.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
            if jm.lower() != "delete":
                raise RuntimeError(f"{db}.sqlite journal_mode is {jm!r}, expected 'delete'")
            f.write(f"-- ===== v6 BEGIN {db} =====\n")
            for line in con.iterdump():
                f.write(line + "\n")
                total_lines += 1
            f.write(f"-- ===== v6 END {db} =====\n")
            con.close()
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print(f"Done. {total_lines} lines written across 3 sections.")
```

## Rebuild

Rebuild is the only normal operation that reads `evidence.sql`. Before running the snippet, read `evidence.sql` with Claude's Read tool and assign the full text to `EVIDENCE_SQL`. Read `references/triggers.sql` with Claude's Read tool and assign the full text to `TRIGGERS_SQL`. Do not use Python `open()` or shell copy for these text files in Cowork.

```python
import json, os, re, shutil, sqlite3, tempfile

EVIDENCE_SQL = """<paste host-side Read of evidence.sql here>"""
TRIGGERS_SQL = """<paste host-side Read of references/triggers.sql here>"""
DBS = ("main", "law", "privileged")

required = [f"-- ===== v6 {kind} {db} =====" for db in DBS for kind in ("BEGIN", "END")]
missing = [marker for marker in required if marker not in EVIDENCE_SQL]
if missing:
    raise RuntimeError(f"evidence.sql missing section markers: {missing}")
for marker in ("CREATE TEMP TRIGGER trg_criteria_facts_criterion_id_insert", "CREATE TEMP TRIGGER trg_facts_delete_guard"):
    if marker not in TRIGGERS_SQL:
        raise RuntimeError(f"triggers.sql missing marker: {marker}")

def is_abs(path):
    return bool(os.path.isabs(path) or re.match(r"^[A-Za-z]:[\\/]", path) or path.startswith("\\\\"))

def join_rel(root, rel):
    return os.path.normpath(os.path.join(root, *[p for p in re.split(r"[\\/]+", rel) if p]))

def load_pointer(matter_root):
    for path in (os.path.join(matter_root, "coclerk.json"), os.path.join(matter_root, "9. AI", "coclerk.json")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise RuntimeError("coclerk.json not found")

def resolve_case_data_dir(matter_root, stored_path):
    if is_abs(stored_path) and os.path.isdir(stored_path):
        return stored_path
    if not is_abs(stored_path):
        candidate = join_rel(matter_root, stored_path)
        if os.path.isdir(candidate):
            return candidate
    folder = os.path.basename(stored_path.replace("\\", "/").rstrip("/"))
    candidate = os.path.normpath(os.path.join(matter_root, "..", "0. CASE DATA", folder))
    if os.path.isdir(candidate):
        return candidate
    raise RuntimeError(f"Cannot resolve case_data_dir: {stored_path}")

pointer = load_pointer(matter_root)
case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
sections = {}
for db in DBS:
    match = re.search(rf"-- ===== v6 BEGIN {db} =====\r?\n(.*?)\r?\n-- ===== v6 END {db} =====", EVIDENCE_SQL, re.DOTALL)
    if not match:
        raise RuntimeError(f"evidence.sql missing {db} section")
    sections[db] = match.group(1).strip()

tmpdir = tempfile.mkdtemp(prefix="case-data-rebuild-")
try:
    tmp_paths = {db: os.path.join(tmpdir, f"{db}.sqlite") for db in DBS}
    for db, sql in sections.items():
        con = sqlite3.connect(tmp_paths[db])
        jm = con.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
        if jm.lower() != "delete":
            raise RuntimeError(f"{db}.sqlite journal_mode is {jm!r}, expected 'delete'")
        con.executescript(sql)
        con.commit()
        con.close()

    con = sqlite3.connect(tmp_paths["main"])
    con.execute(f"ATTACH DATABASE '{tmp_paths['law']}' AS law")
    con.execute(f"ATTACH DATABASE '{tmp_paths['privileged']}' AS privileged")
    con.executescript(TRIGGERS_SQL)
    con.close()

    checks = {"main": 14, "law": 4, "privileged": 2}
    for db, minimum in checks.items():
        con = sqlite3.connect(tmp_paths[db])
        count = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        con.close()
        if count < minimum:
            raise RuntimeError(f"{db}.sqlite has {count} tables, expected at least {minimum}")

    os.makedirs(case_data_dir, exist_ok=True)
    for db in DBS:
        shutil.move(tmp_paths[db], os.path.join(case_data_dir, f"{db}.sqlite"))
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

print("Rebuild complete.")
```

## Verify sources

Check that every `main.sources.file_path` points to an existing file in the matter folder, and report computed citations for rows that carry a `source_locator`.

```python
import json, os, re, shutil, sqlite3, tempfile

def is_abs(path):
    return bool(os.path.isabs(path) or re.match(r"^[A-Za-z]:[\\/]", path) or path.startswith("\\\\"))

def join_rel(root, rel):
    return os.path.normpath(os.path.join(root, *[p for p in re.split(r"[\\/]+", rel) if p]))

def load_pointer(matter_root):
    for path in (os.path.join(matter_root, "coclerk.json"), os.path.join(matter_root, "9. AI", "coclerk.json")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise RuntimeError("coclerk.json not found")

def resolve_case_data_dir(matter_root, stored_path):
    if is_abs(stored_path) and os.path.isdir(stored_path):
        return stored_path
    if not is_abs(stored_path):
        candidate = join_rel(matter_root, stored_path)
        if os.path.isdir(candidate):
            return candidate
    folder = os.path.basename(stored_path.replace("\\", "/").rstrip("/"))
    candidate = os.path.normpath(os.path.join(matter_root, "..", "0. CASE DATA", folder))
    if os.path.isdir(candidate):
        return candidate
    raise RuntimeError(f"Cannot resolve case_data_dir: {stored_path}")

pointer = load_pointer(matter_root)
case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
tmpdir = tempfile.mkdtemp(prefix="case-data-verify-")
try:
    main_tmp = os.path.join(tmpdir, "main.sqlite")
    shutil.copy2(os.path.join(case_data_dir, "main.sqlite"), main_tmp)
    con = sqlite3.connect(main_tmp)
    attached = ["main"]
    priv_src = os.path.join(case_data_dir, "privileged.sqlite")
    if os.path.exists(priv_src):
        priv_tmp = os.path.join(tmpdir, "privileged.sqlite")
        shutil.copy2(priv_src, priv_tmp)
        con.execute(f"ATTACH DATABASE '{priv_tmp}' AS privileged")
        attached.append("privileged")

    available = {}
    for db in attached:
        for (table,) in con.execute(f"SELECT name FROM {db}.sqlite_master WHERE type='table'").fetchall():
            cols = {row[1] for row in con.execute(f"PRAGMA {db}.table_info({table})").fetchall()}
            available[(db, table)] = cols

    source_selects = ["""
        SELECT 'source' AS kind, source_id AS id, file_path, NULL AS source_locator
        FROM main.sources
        WHERE file_path IS NOT NULL
    """]
    if "file_path" in available.get(("privileged", "privileged_sources"), set()):
        source_selects.append("""
            SELECT 'privileged_source' AS kind, source_id AS id, file_path, NULL AS source_locator
            FROM privileged.privileged_sources
            WHERE file_path IS NOT NULL
        """)
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
        if source_col in cols and locator_col in cols:
            if db == "main":
                citation_selects.append(f"""
                    SELECT '{kind}' AS kind, t.{id_col} AS id, s.file_path, t.{locator_col} AS source_locator
                    FROM main.{table} t
                    LEFT JOIN main.sources s ON s.source_id = t.{source_col}
                    WHERE t.{locator_col} IS NOT NULL
                """)
            else:
                citation_selects.append(f"""
                    SELECT '{kind}' AS kind, t.{id_col} AS id, s.file_path, t.{locator_col} AS source_locator
                    FROM privileged.{table} t
                    LEFT JOIN privileged.privileged_sources s ON s.source_id = t.{source_col}
                    WHERE t.{locator_col} IS NOT NULL
                """)
    citation_rows = con.execute(" UNION ALL ".join(citation_selects)).fetchall() if citation_selects else []
    con.close()
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

broken = []
for kind, row_id, file_path, source_locator in source_rows + citation_rows:
    if not file_path:
        broken.append((kind, row_id, "[missing file_path]"))
        continue
    display = f"{file_path}#{source_locator}" if source_locator else file_path
    if not os.path.isfile(os.path.join(matter_root, file_path)):
        broken.append((kind, row_id, display))

checked = len(source_rows) + len(citation_rows)
print(f"Checked {checked} file/citation refs. OK: {checked-len(broken)}, Broken: {len(broken)}")
for kind, row_id, ref in broken:
    print(f"  [{kind} #{row_id}] {ref}")
```

## Markdown wins

If the database and markdown disagree, the markdown is correct. Fix the database to match. If the markdown is wrong, fix the markdown first, then the database.

The text dump (`evidence.sql`) and the matter's markdown files are the source of truth. The `.sqlite` binaries are derived artifacts rebuilt from those sources. When a discrepancy is found:

1. Identify whether the markdown content or the database content is authoritative for the specific value in question.
2. If the markdown is correct and the database is wrong, edit `evidence.sql` to match the markdown, then run the rebuild procedure above.
3. If the markdown is wrong, fix the markdown first, confirm the correction with the user, then edit `evidence.sql` to match, then rebuild.
4. Never silently update markdown to match the database. The database serves the markdown, not the other way around.
