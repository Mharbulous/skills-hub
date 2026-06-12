# Extract Facts -- Scan Matter Folders for New or Changed PDFs

Scans selected matter folders for PDFs, classifies each file by hash/path status, dispatches read-only subagents to extract schema-neutral facts, then ingests each document sequentially. Subagents never write files and never touch the database.

## Step 0: Resolve the Matter Pointer

Resolve the matter pointer using the inline pointer-resolution snippet from `SKILL.md`. Store the returned pointer, `case_data_dir`, and `matter_root`. If pointer resolution fails, report the error and halt.

```python
matter_root = '<matter_root>'
pointer = resolve_pointer(matter_root)
case_data_dir = pointer["case_data_dir"]
```

## Step 1: Select Folders

Ask the user which folders to scan. Present the canonical litigation folders as a multi-select:

1. `RAW\`
2. `3. CORRESPONDENCE\`
3. `5. COURT FILE...\` (match by prefix)
4. `7. DISCOVERY\`
5. `6. LAW\` if the user is scanning authorities

The user may also specify a custom folder path. Resolve all paths relative to the matter root. There is no persistent scan config; ask every run.

## Step 2: Discover PDFs

For each selected folder, walk recursively and collect all `.pdf` files case-insensitively. Exclude files starting with `~` or `.`.

```python
from pathlib import Path
import os

def scan_folder(folder: str, matter_root: str) -> list:
    folder_path = Path(matter_root) / folder
    if not folder_path.is_dir():
        print(f"WARNING: {folder_path} is not a directory")
        return []
    results = []
    for root, _dirs, files in os.walk(folder_path):
        for fname in files:
            if fname.lower().endswith(".pdf") and not fname.startswith(("~", ".")):
                results.append(os.path.join(root, fname))
    return sorted(results)

all_pdfs = []
for folder in selected_folders:
    all_pdfs.extend(scan_folder(folder, matter_root))
```

## Step 3: Classify Each PDF

For each discovered file:

1. Compute SHA-256 from raw bytes.
2. Convert the absolute path to a path relative to the matter root.
3. Copy the `.sqlite` files from native `case_data_dir` to a fresh temp directory.
4. Query `main.sources` for path and hash matches.

```python
import hashlib

def compute_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
```

```sql
SELECT source_id, file_hash FROM main.sources WHERE file_path = ?;
SELECT source_id, title, file_path FROM main.sources WHERE file_hash = ?;
```

| Disposition | `file_path` match? | `file_hash` match? | Action |
|---|---|---|---|
| New | No | No | Extract |
| Duplicate | No | Yes | Skip and report existing source |
| Unchanged | Yes | Yes | Skip |
| Changed | Yes | No, or stored hash is NULL | Re-extract |

Collect New and Changed PDFs into the extraction list. Track Duplicate and Unchanged counts for the summary report.

## Step 4: Dispatch Extraction Subagents

Spawn parallel read-only subagents, one per document, `model = "sonnet"`, in batches of at most 10. Send all agents in a batch in one tool-call block, wait for all responses, then start the next batch.

Read `agents/extract-facts.md` for the subagent prompt template. The subagent returns schema-neutral JSON: document metadata, facts, locators, and position semantics. It does not emit SQL-shaped objects.

## Step 5: Ingest Sequentially

After each batch completes, ingest each subagent response one document at a time. All inserts for one document run inside one `BEGIN..COMMIT` on the three-database-attached connection. Move to the next document only after the previous document commits or rolls back.

Main-agent processing:

1. Parse the JSON response.
2. Register or update the `main.sources` row using `category`, `title`, `description`, `date`, `file_path`, `file_hash`, and `verified = 0`.
3. Build the existing locator set for the source:

```sql
SELECT source_locator FROM main.facts WHERE source_id = ? AND source_locator IS NOT NULL;
```

4. For each extracted fact:
   - Skip if `(source_id, source_locator)` already exists.
   - Insert `main.facts(description, category, date_of_fact, source_id, source_locator, verified)`.
   - If the fact carries a party position, insert `main.positions(fact_id, party_id, position, qualification, source_id, source_locator, valid_from, verified, notes)`.
   - If the source is proof for the fact, insert `main.evidence_links(source_id, fact_id, source_locator, strength, verified, notes)`.

5. Report after each document: new facts, new positions, new evidence links, and skipped duplicate locators.

## Step 6: Report Summary

Print a summary showing:

- Folders scanned
- Total PDFs found
- Counts per disposition: New, Changed, Duplicate, Unchanged
- Total sources, facts, positions, and evidence links inserted
- `verified = 0` backlog added

## Step 7: Dump

Run the dump procedure from `operations/maintain.md`. Every mutation must be followed by a dump.
