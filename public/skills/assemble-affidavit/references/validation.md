# Exhibit Validation

Validate that all exhibit files are present, properly named, and match the
descriptions in the affidavit. This step catches mismatches early — before
stamps are applied and pages are merged.

If files are mislabeled (e.g., the file named "Exhibit B" actually contains
the document described as Exhibit C in the affidavit), the validation will
detect this, propose a corrected mapping, and ask for approval to rename.

---

## 2a. Extract exhibit references from the affidavit

Read the affidavit body text (via pandoc for DOCX, or PyMuPDF for PDF).
Parse every exhibit reference. Look for patterns like:

- "attached as Exhibit [A-Z]"
- "attached hereto and marked as Exhibit [A-Z]"
- "is attached as Exhibit [A-Z]"
- "Exhibit [A-Z]" in any other context

For each reference, extract:

| Field | Description |
|-------|-------------|
| `letter` | The exhibit letter (A, B, C, ...) |
| `paragraph` | The paragraph number where the reference appears |
| `description` | The full sentence or clause describing the exhibit |
| `key_terms` | Identifying terms extracted from the description (see below) |

### Extracting key terms

From each exhibit's description, extract these categories:

1. **Dates** — regex: `(January|February|...|December)\s+\d{1,2},?\s+\d{4}`
2. **Dollar amounts** — regex: `\$[\d,]+(\.\d{2})?`
3. **Document type keywords** — "promissory note", "amending agreement",
   "share purchase agreement", "demand", "notice of default", "confirmation",
   "employment agreement", "spreadsheet", "letter", "termination", "invoice"
4. **Proper nouns / entity names** — party names, company names, institutions
5. **Sender/signatory names** — names of individuals associated with the
   exhibit (e.g., "Anthony Li-Lam", "Brahm Dorst"). These are highly
   discriminating for correspondence.

**Key term quality matters.** Prefer specific, discriminating terms (exact
dates, dollar amounts, unique document titles) over generic ones ("demand",
"letter", "interest"). A good key term uniquely identifies one exhibit and
would not match other exhibits in the same set.

### Classifying key terms: identity vs. context

Each key term must be classified as **identity** or **context**:

- **Identity terms** are the exhibit's own defining attributes: its date
  (the date the document was created/signed), its title or document type,
  its signatory name, and its unique dollar amount. These identify what the
  document IS.
- **Context terms** are dates, amounts, or references from other documents
  that the description mentions for background. These describe what the
  document REFERENCES.

Heuristic: the first date in the description is usually the identity date.
Subsequent dates (maturity dates, accrual start dates) are context. Unique
dollar amounts tied to the document itself (e.g., "$243,266.92" in a demand
for that amount) are identity; amounts from the underlying agreement are
context.

### IDF weighting

After extracting all key terms across all exhibits, compute an inverse
document frequency weight for each term:

```
idf_weight = 1.0 / (number of exhibit descriptions containing this term)
```

Terms appearing in ≥ 3 descriptions (e.g., "promissory note", "demand",
"amending agreement") are poor discriminators. They still contribute to
scoring but at reduced weight.

Build as a Python data structure:

```python
expected_exhibits = [
    {
        "letter": "A",
        "paragraph": "4",
        "description": "Promissory Note dated December 1, 2020, $300,000",
        "identity_date": "December 1, 2020",
        "identity_terms": ["promissory note", "December 1, 2020", "$300,000"],
        "context_terms": ["June 1, 2021"],
        "key_terms": ["promissory note", "December 1, 2020", "$300,000", "June 1, 2021"]
    },
    # ... etc
]
```

## 2b. Inventory exhibit files and enforce format gate

### Format gate (must pass before any content extraction)

Before extracting text or scoring, verify all file formats:

- **Affidavit** must be `.docx`. If it's a PDF, abort immediately:
  "The affidavit must be in DOCX format for header/jurat rewriting."
- **Exhibits** must be `.pdf` — no other formats. If any exhibit is
  `.docx`, `.xlsx`, or another format, abort and list which files need
  conversion: "These exhibits must be converted to PDF before assembly:
  Exhibit B.docx, Exhibit J.xlsx"
- **If both a PDF and a non-PDF version of the same exhibit exist in
  the folder** (e.g., `Exhibit J.xlsx` and `Exhibit J.pdf`), use the
  PDF and ignore the other file — that is not a gate failure.

If the format gate fails, do NOT proceed to text extraction or scoring.
The user must fix the files first.

### File inventory

Scan the exhibit folder for exhibit files. Accept naming patterns:
`Exhibit {letter}.{ext}`, `Ex {letter}`, `{letter} -`.

Build a file inventory:

| Field | Description |
|-------|-------------|
| `letter` | The letter from the filename |
| `path` | Full file path |
| `ext` | File extension |
| `page_count` | Number of pages (for PDFs) |
| `has_text` | Whether extractable text exists |
| `is_scanned` | True if no text layer (image-only PDF) |

Report missing files (referenced in affidavit but no file found) and
extra files (in folder but not referenced in affidavit).

## 2c. Extract text from exhibit files (first 2 pages only)

For each exhibit file, extract text from **pages 0–1 only**. The first
two pages always identify the document; remaining pages add noise from
cross-references and quoted content that causes false matches. Copy to
a unique subdirectory of `/var/tmp/` first for FUSE safety.

- **PDF**: PyMuPDF (`fitz`) — extract text from pages 0 and 1 only
  (`doc[0].get_text()` + `doc[1].get_text()` if it exists). Replace
  `\xa0` with spaces. Skip pages that contain only commissioner stamp
  text (pattern: `This is Exhibit "[A-Z]" referred to in the Affidavit`)
  — if page 0 is a stamp page, use pages 1–2 instead. Install:
  `pip install PyMuPDF --break-system-packages`
- **Images**: No text extraction possible — mark as UNVERIFIABLE.

Classify each file:

- **TEXT** — has extractable text content (after excluding stamp pages)
- **SCANNED** — PDF with no text layer, or all text is from stamp pages
- **UNVERIFIABLE** — extraction failed, password-protected, or image file

Also check the first page for pre-existing exhibit stamps. If found,
record the stamp letter.

### Multimodal fallback for SCANNED PDFs

For files classified as SCANNED (image-only PDFs with no text layer),
use Cowork's multimodal capability to extract identifying information.
This converts SCANNED files to TEXT_OCR status so they participate in
cross-match scoring instead of being left UNVERIFIED.

**Process (runs after initial classification, before scoring):**

1. For each SCANNED file, extract pages 0–1 as PNG images using PyMuPDF:
   ```python
   doc = fitz.open(pdf_path)
   for page_idx in range(min(2, doc.page_count)):
       page = doc[page_idx]
       pix = page.get_pixmap(dpi=200)  # 200 DPI is sufficient for readability
       img_path = f"/tmp/exhibit_{letter}_page{page_idx}.png"
       pix.save(img_path)
   ```

2. Use the **Read tool** on each PNG file. Claude can see images natively
   and will extract the visible text.

3. After reading the images, extract key identifying information from
   what Claude sees:
   - Document date (the date the document was created/signed)
   - Document title or type (e.g., "Promissory Note", "Share Purchase
     Agreement", "Demand Letter")
   - Dollar amounts visible on pages 0–1
   - Party names and signatory names
   - Any other unique identifying text

4. Store the extracted text as `page1_text` on the file inventory entry
   and reclassify the file as **TEXT_OCR**. TEXT_OCR files are treated
   identically to TEXT files for scoring purposes.

**Important:** This creates a two-pass validation flow when scanned
exhibits are present:
- **Pass 1:** Classify all files → extract text from TEXT files → identify
  SCANNED files that need multimodal processing
- **Pass 2:** Extract images from SCANNED files → Read images via Claude →
  extract key terms → reclassify as TEXT_OCR → proceed to scoring

If image extraction or multimodal reading fails for a file, leave it as
SCANNED (equivalent to the old UNVERIFIED behavior — it passes the gate
but without content verification).

### Text storage (single field)

For each TEXT file, store a single **`page1_text`** field containing the
concatenated text from pages 0–1. This captures the document's identity:
letterhead, date line, title block, "Re:" line, signatory.

There is no `body_text` field. Extracting text beyond the first two
pages caused false matches from cross-references in prior testing.

For PDFs, page 0 is `doc[0].get_text()` (after skipping any stamp page
at position 0).

### Document-date extraction

From each file's `page1_text`, extract the file's **own date** — the date
the document was created or signed. **Pattern priority matters** — legal
correspondence references other documents' dates in the body, so the
"Dated" pattern must not run first or it will pick up a referenced date
instead of the document's own date.

Apply these patterns **in order**, stopping at the first match:

1. A date on a line by itself (correspondence date line):
   `^(Month DD, YYYY)\s*$` with MULTILINE flag
2. A date after "Dated" or "dated" (formal instruments):
   `(?:Dated|dated)[:\s]+(Month DD, YYYY)`
3. The first date found on page 1 as fallback:
   `(Month DD, YYYY)` — first occurrence

```python
import re

def extract_own_date(page1_text):
    """Extract the document's own date from page 1 text.
    
    Pattern order is critical: standalone date lines first (catches
    correspondence dates above the body), then 'Dated' prefix (catches
    formal instruments), then general fallback.
    """
    if not page1_text:
        return None
    MONTHS = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    patterns = [
        # 1. Standalone date line (correspondence)
        (rf'^({MONTHS}\s+\d{{1,2}},?\s*\d{{4}})\s*$', re.MULTILINE),
        # 2. "Dated" prefix (formal instruments)
        (rf'(?:Dated|dated)[:\s]+(\w+\s+\d{{1,2}},?\s*\d{{4}})', 0),
        # 3. First date on page (fallback)
        (rf'({MONTHS}\s+\d{{1,2}},?\s*\d{{4}})', 0),
    ]
    for pat, flags in patterns:
        m = re.search(pat, page1_text, flags)
        if m:
            return m.group(1).strip()
    return None
```

**Why this order prevents misattribution:** A Notice of Default letter
has "December 3, 2024" on a line by itself (the letter's date), but also
references "Fifth Amending Agreement dated December 1, 2023" in the body.
If pattern 2 runs first, it matches "dated December 1, 2023" — a
referenced date, not the document's own date. Pattern 1 correctly catches
the standalone date line first.

Store this as `file_own_date` on the inventory entry. This will be used
as a high-weight anchor in cross-matching.

## 2d. Build cross-match matrix

This is the core of the validation. Instead of only checking whether
file X matches description X, score **every file** against **every
exhibit description**. This detects mislabeled files.

### Why legal documents need special handling

Legal documents cross-reference each other heavily. A Notice of Default
quotes the agreement being defaulted on. A demand letter recites the
full chronology of amendments. A naive term-count approach will assign
these documents to the WRONG exhibit because they contain more terms
from the referenced agreement than from their own description.

The solution: **positional weighting** (terms on page 1 score higher),
**document-date anchoring** (the file's own date must match the
description's identity date), and **IDF weighting** (terms appearing in
many descriptions are downweighted).

### Term matching rules

For each key term, check whether it appears in the file's text using
these rules (case-insensitive):

- Dates: match exact string or without comma ("December 1, 2020" ↔
  "December 1 2020").
- Dollar amounts: match with/without cents and commas
- Document type keywords: substring match, case-insensitive
- Proper nouns / sender names: substring match, case-insensitive

### Scoring each file–description pair

For each (file, description) pair, compute a weighted score. All scoring
uses `page1_text` only (pages 0–1). There is no body_text field.

```python
score = 0.0

for term in description['key_terms']:
    idf = 1.0 / count_of_descriptions_containing(term)
    is_identity = term in description['identity_terms']

    if not term_matches(term, file['page1_text']):
        continue  # term not found in pages 0–1

    # Identity terms score higher than context terms
    identity_weight = 1.5 if is_identity else 1.0

    score += identity_weight * idf
```

**Document-date anchor bonus/penalty:**

```python
if file['file_own_date'] and description['identity_date']:
    if dates_match(file['file_own_date'], description['identity_date']):
        score += 5.0   # strong positive signal
    else:
        score -= 3.0   # file's own date doesn't match this description
```

**Same-letter prior:**

```python
if file['letter'] == description['letter']:
    score += 1.5  # filenames are usually correct; require evidence to overturn
```

For SCANNED/UNVERIFIABLE files (those that were not successfully
converted to TEXT_OCR via multimodal processing), the score is 0 against
all descriptions. TEXT_OCR files score identically to TEXT files.

### Find the optimal file-to-exhibit assignment

Use the **Hungarian method** (global optimal assignment) instead of a
greedy algorithm. Greedy assignment cascades errors: one confident wrong
match displaces two correct ones. The Hungarian method maximizes total
score across all assignments simultaneously.

```python
from scipy.optimize import linear_sum_assignment
import numpy as np

# Build cost matrix (Hungarian minimizes, so negate scores)
file_letters = sorted(text_files.keys())  # only TEXT files
exhibit_letters = [e['letter'] for e in expected_exhibits]

n_files = len(file_letters)
n_exhibits = len(exhibit_letters)
size = max(n_files, n_exhibits)

# Pad to square matrix with zeros
cost_matrix = np.zeros((size, size))
for i, fl in enumerate(file_letters):
    for j, el in enumerate(exhibit_letters):
        cost_matrix[i][j] = -scores[fl][el]  # negate for minimization

row_ind, col_ind = linear_sum_assignment(cost_matrix)

# Extract assignments
for i, j in zip(row_ind, col_ind):
    if i < n_files and j < n_exhibits:
        fl = file_letters[i]
        el = exhibit_letters[j]
        actual_score = scores[fl][el]
        if actual_score >= 2.0:
            # Meaningful assignment
            assign(fl, el, actual_score)
        else:
            # Score too low — leave as MISMATCH / unassigned
            pass
```

After Hungarian assignment of TEXT files, assign remaining
SCANNED/UNVERIFIABLE files to remaining unassigned descriptions by
letter order (preserving current naming), marked as UNVERIFIED.

Install scipy if needed: `pip install scipy --break-system-packages`

### Minimum score threshold

Pairs with weighted score < 2.0 should NOT be assigned even if the
Hungarian method picks them (they'd only be selected to fill the matrix).
Leave these as MISMATCH — better to flag a gap than force a bad match.

### Classify each assignment

For the final assignment, classify each exhibit:

| Status | Condition |
|--------|-----------|
| **CONFIRMED** | Assigned file has weighted score ≥ 2.0 AND file letter == exhibit letter |
| **MISLABELED** | Assigned file has weighted score ≥ 2.0 BUT file letter ≠ exhibit letter (rename needed) |
| **WEAK** | Assigned file has weighted score between 1.0 and 2.0 |
| **CONFIRMED (OCR)** | Same as CONFIRMED but content was extracted via multimodal OCR (TEXT_OCR file) |
| **UNVERIFIED** | File is SCANNED or UNVERIFIABLE — could not extract content even with multimodal fallback |
| **MISSING** | No file could be assigned above the threshold |

## 2e. Present verification report

Present the results in two parts.

### Part 1: Assignment summary

```
Exhibit Verification Report
═══════════════════════════════════════════════════════════════════════
✓  Exhibit A  (¶4)  Promissory Note (Dec 1, 2020)
                     → Exhibit A.pdf — CONFIRMED (3/3 terms)

⚠  Exhibit B  (¶6b) 2nd Amending Agreement (Sep 29, 2022)
                     → currently Exhibit D.pdf — MISLABELED (2/2 terms match,
                       but file is named "D" not "B")

?  Exhibit C  (¶6c) 3rd Amending Agreement (Jan 31, 2023)
                     → Exhibit C.pdf — UNVERIFIED (scanned, 5 pages)

✗  Exhibit D  (¶6d) 4th Amending Agreement (Sep 1, 2023)
                     → MISSING — no file matched this description
═══════════════════════════════════════════════════════════════════════
```

### Part 2: Rename mapping (only if MISLABELED files exist)

When any files are mislabeled, present a rename mapping table:

```
Proposed File Renames
─────────────────────────────────────────────────────────────
  Current Name       →  Correct Name       Reason
  Exhibit D.pdf      →  Exhibit B.pdf      Content matches ¶6b (2nd Amending Agreement)
  Exhibit B.pdf      →  Exhibit D.pdf      Content matches ¶6d (4th Amending Agreement)
  Exhibit E.pdf      →  Exhibit C.pdf      Content matches ¶6c (3rd Amending Agreement)
─────────────────────────────────────────────────────────────
  3 files to rename | 5 confirmed | 2 unverified (scanned)
```

For SCANNED/UNVERIFIED files caught in a rename chain (e.g., a scanned
file currently named "Exhibit C" needs to move because a text-verified
file should take that letter), include them in the rename table and flag
that their assignment is based on position, not content verification.

### Part 3: Pre-existing stamps (if any)

If any files have pre-existing exhibit stamps, note them:

```
Pre-existing Stamps (will be overwritten during assembly)
  Exhibit B.pdf has stamp for "Exhibit C"
  Exhibit C.pdf has stamp for "Exhibit D"
```

## 2f. Request approval for renames

If any files need renaming, use `AskUserQuestion`:

```
question: "The validation found X mislabeled exhibit files. Rename them to
           match the affidavit? (See mapping above)"
options:
  - "Yes, rename files"
  - "No, I'll fix manually"
  - "Skip renames, proceed anyway"
```

**If "Yes, rename files":**

Use the `scripts/rename_exhibits.py` script. **Do NOT use bash `mv` or
`cp` commands** — the FUSE mount caches file lookups, and bash commands
will silently serve stale content after renames. The script handles
cache invalidation deterministically.

**Pre-flight: script integrity check** — run before invoking the script:

```bash
SKILL_DIR="/path/to/verified/assemble-affidavit"
RENAME_SCRIPT="$SKILL_DIR/scripts/rename_exhibits.py"
python3 -c "import ast,os,sys; p=sys.argv[1]; b=open(p,'rb').read(); s=os.path.getsize(p); assert len(b)==s, f'SHORT READ {len(b)} != {s}'; ast.parse(b.decode()); assert b.rstrip().endswith(b'main()'), 'TRUNCATED TAIL'; print(f'pre-flight OK: {p} ({s} bytes)')" "$RENAME_SCRIPT"
```

If the check fails, Read the script with the **Read tool**, Write it to
`/var/tmp/rename_exhibits.py`, re-run the pre-flight on the copy, then
invoke the copy.

Build the JSON input and pipe it to the script:

```python
import json, subprocess

SKILL_DIR = "/path/to/verified/assemble-affidavit"
rename_input = {
    "exhibit_dir": "/path/to/exhibit/folder",   # sandbox path
    "renames": [
        {"from": "Exhibit G.pdf", "to": "Exhibit F.pdf"},
        {"from": "Exhibit F.pdf", "to": "Exhibit G.pdf"},
    ],
    "copies": []  # for files from other locations; see below
}

result = subprocess.run(
    ["python3", f"{SKILL_DIR}/scripts/rename_exhibits.py"],
    input=json.dumps(rename_input),
    capture_output=True, text=True
)
output = json.loads(result.stdout)
```

Set `SKILL_DIR` to the directory containing this skill's `SKILL.md`.

The script returns JSON with `success`, `renames_completed`, `errors`,
and a `verification` dict showing each file's size and header bytes.
Check `output["success"]` before proceeding.

**Copying files from other locations:**

If a required exhibit is missing from the folder but exists elsewhere
(e.g., in the discovery folder), add it to the `copies` array:

```python
rename_input["copies"] = [
    {
        "source": "/path/to/source/Duckworth0019.pdf",
        "target_name": "Exhibit E.pdf"
    }
]
```

Copies go through `/tmp` to bypass FUSE read caching on the source.
The script will not overwrite existing files.

**If "No, I'll fix manually":** Stop. Do NOT proceed to assembly.

**If "Skip renames, proceed anyway":** Proceed to assembly with files as
named. Note the mismatch warnings in the output.

**Fallback if `AskUserQuestion` fails:** Present the rename mapping in
markdown and ask in chat. Wait for the user's response before proceeding.

### Why bash must not be used for file operations

The Cowork sandbox mounts the user's workspace via a FUSE chain
(virtiofs + bindfs). This FUSE layer caches file lookups aggressively:

- After `mv A B`, reading B may still return A's content
- After `cp src dst`, dst may appear to contain stale data
- `os.path.getsize()` returns the correct size, but `open().read()`
  returns cached content from before the rename

LLM inference cannot reliably remember to work around this bug on
every file operation. The `rename_exhibits.py` script invalidates the
cache after every rename/copy by performing a rename round-trip
(`path → tmp → path`) that forces a fresh FUSE lookup.

**Rule: all exhibit file renames and copies MUST go through the
script. Never use bash `mv`, `cp`, or `shutil` directly.**

## 2g. Gate decision

After renames (if any) are applied:

- If all exhibits are CONFIRMED, WEAK, or UNVERIFIED → proceed to assembly
- If any exhibits are MISSING → present the issue, ask whether to proceed
  without them or stop

UNVERIFIED (scanned) files pass the gate — they're flagged but not
blocking. The lawyer has been informed they couldn't be content-verified.

Do NOT read `references/assembly.md` until this gate is passed.
