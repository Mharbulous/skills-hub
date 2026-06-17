# Affidavit Assembly

These instructions cover the mechanical assembly of the affidavit package:
DOCX-to-PDF conversion, header/jurat coordinate discovery, script invocation,
and output delivery. Only proceed here after validation (`references/validation.md`)
has passed.

## DOCX-only requirement — Critical

The affidavit **must** be a DOCX file. Edit it directly (header, jurat,
body text) using `python-docx` **before** converting to PDF. This avoids
lossy PDF redaction, font mismatches, and fragile coordinate-based text
replacement. The PDF conversion happens once, after all DOCX edits are
complete.

If no DOCX is available, **stop and tell the user** — do not fall back to
PDF-based header/jurat rewriting. The risk of silent errors (wrong dates,
missed rewrites) outweighs the convenience of a workaround.

## Exhibit stamp format

The exhibit stamp is **text only** — no background box, no visible border.
Text is rendered at 40% opacity (semi-transparent). The stamp reads:

```
This is Exhibit "A" referred to in the
Affidavit of {affiant_name} made
this ____ day of _____________, 20____

_________________________
Commissioner for affidavit
```

For scanned exhibits (image-only PDFs with no text layer), the script uses
pixmap-based whitespace detection to find stamp placement instead of
relying on `get_text("blocks")` which returns nothing for scanned pages.

## Source files are read-only

**Never modify the original exhibit files or affidavit DOCX.** All
modifications (stamps, header/jurat rewrites, format conversions) happen on
temp copies inside `/var/tmp/`. The `assemble.py` script enforces this — it copies
every input to `/var/tmp/` before processing. Do not pre-stamp, pre-convert, or
otherwise alter source files before passing them to the script. Do not write
any output back to the source folder except the final assembled PDF.

## Step 3 — Pre-pass: convert affidavit and locate coordinates

### 3a. Convert affidavit DOCX to PDF

The affidavit MUST be in DOCX format (enforced by the format gate in
validation). The `assemble.py` script converts the DOCX to PDF internally
using the `soffice.py` wrapper from the docx skill. **Do not manually
convert the affidavit** — pass the DOCX path directly to the script via
`affidavit_pdf` (despite the field name, the script accepts DOCX and
converts it automatically).

The script dynamically locates the `soffice.py` wrapper at runtime, which
handles `SAL_USE_VCLPLUGIN=svp` and the `LD_PRELOAD` socket shim needed
in the Cowork sandbox.

### 3b. Locate header and jurat bounding boxes

Install PyMuPDF if not already available:

```bash
pip install PyMuPDF --break-system-packages 2>/dev/null
```

Use PyMuPDF to read the converted PDF's text layer and locate:

1. **Header region** (page 0): The affidavit header block sits in the
   top-right of the first page (typically three lines: "This is the Nth
   affidavit / of Name in this case / and was made on Date"). Filter
   `page.get_text("words")` for words where `x0 > 300` and `y0 < 150`,
   then compute the enclosing bbox from the min/max coordinates of those
   words. Add a few points of margin on each side.

2. **Jurat region** (signature page): The script locates the jurat
   dynamically by searching for "AFFIRMED" or "SWORN" in the text layer,
   so the `jurat_bbox` value is used only as a fallback. Pass a
   reasonable estimate (e.g. `[72, 325, 340, 370]`).

The bounding boxes are passed to the script, which validates them before
redacting. If the script reports that expected text was not found inside
the supplied bounding boxes, re-examine the PDF and adjust coordinates.

**Important:** The script redacts the **entire** city+province line
(e.g. "Vancouver, Province of British Columbia,") and re-inserts it as a
single string ("______________, Province of British Columbia,") to
maintain alignment. It also redacts and rewrites the date line below it.

### Coordinate discovery technique

```python
import fitz
doc = fitz.open("/var/tmp/affidavit.pdf")

# --- Header bbox (page 0, top-right quadrant) ---
page = doc[0]
words = page.get_text("words")  # list of (x0, y0, x1, y1, word, ...)
header_words = [w for w in words if w[0] > 300 and w[1] < 150]
if header_words:
    hx0 = min(w[0] for w in header_words) - 5
    hy0 = min(w[1] for w in header_words) - 5
    hx1 = max(w[2] for w in header_words) + 5
    hy1 = max(w[3] for w in header_words) + 5
    header_bbox = [hx0, hy0, hx1, hy1]

# --- Jurat page (find "AFFIRMED BEFORE ME" or "SWORN BEFORE ME") ---
jurat_bbox = [72, 325, 340, 370]  # reasonable default
for i in range(len(doc)):
    text = doc[i].get_text()
    if "AFFIRMED BEFORE ME" in text or "SWORN BEFORE ME" in text:
        jurat_page = i
        break
```

Store the discovered coordinates for the JSON input.

## Step 4 — Build JSON input and invoke the script

Construct the JSON input matching this schema:

```json
{
  "affiant_name": "Stan Duckworth",
  "affidavit_number": 2,
  "jurat_verb": "AFFIRMED",
  "signing_date": "2026-06-10",
  "affidavit_pdf": "/var/tmp/affidavit.pdf",
  "header_bbox": [360, 70, 548, 116],
  "jurat_bbox": [72, 338, 330, 370],
  "exhibits": [
    {"letter": "A", "path": "/path/to/exhibit_a.pdf"},
    {"letter": "B", "path": "/path/to/exhibit_b.pdf"}
  ],
  "output_path": "/path/to/output.pdf"
}
```

Path notes:
- `affidavit_pdf`: the pre-converted PDF in `/var/tmp/`
- Exhibit paths: use the original file paths (the script handles FUSE
  workarounds internally by copying to `/var/tmp/` before processing)
- `output_path`: write to `/var/tmp/` first, then copy to the matter workspace

Invoke the script:

```bash
SKILL_DIR="/path/to/verified/assemble-affidavit"
SCRIPT="$SKILL_DIR/scripts/assemble.py"
python3 -c "import ast,os,sys; p=sys.argv[1]; b=open(p,'rb').read(); s=os.path.getsize(p); assert len(b)==s, f'SHORT READ {len(b)} != {s}'; ast.parse(b.decode()); assert b.rstrip().endswith(b'main()'), 'TRUNCATED TAIL'; print(f'pre-flight OK: {p} ({s} bytes)')" "$SCRIPT"
echo '<json_input>' | python3 "$SCRIPT"
```

If the pre-flight fails, Read the script with the **Read tool**, Write
it to `/var/tmp/assemble.py`, re-run the pre-flight on the copy, then
invoke the copy.

Set `SKILL_DIR` to the directory containing this skill's `SKILL.md`.

## Step 5 — Handle script output

The script returns JSON on stdout with a validation summary:

```json
{
  "success": true,
  "output_path": "/var/tmp/output.pdf",
  "page_count": 95,
  "exhibits": [
    {"letter": "A", "pages": "12-15", "stamp_placement": "whitespace"},
    {"letter": "B", "pages": "16-20", "stamp_placement": "blank_page_inserted"}
  ],
  "warnings": []
}
```

If `success` is false, read the `error` field and diagnose:
- **unsupported_format**: a non-PDF exhibit reached the script, which means
  the validation format gate was skipped. Do NOT convert the file yourself.
  Return to the format gate: ask the user for a PDF version of the exhibit,
  then re-run.
- **Bbox validation failed**: the header or jurat text wasn't found at the
  supplied coordinates. Re-examine the PDF text layer and provide corrected
  coordinates.
- **FUSE error**: copy the problematic file to `/var/tmp/` and update the path.

## Step 6 — Deliver the output

Copy the output PDF from `/var/tmp/` to the matter workspace:

```bash
cp /var/tmp/output.pdf "/sessions/.../mnt/MATTER_FOLDER/0. DRAFT/YYYY-MM-DD AFF#N LastNameFirstInitial - DRAFT for Review.pdf"
```

Use the naming convention:
`{date} AFF#{n} {LastNameFirstInitial} - DRAFT for Review.pdf`

This is a **Stage 1 draft** — it does not include page numbers. The user
should review the assembled PDF, remove any unnecessary pages (cover
sheets, blank scan backs, duplicates), and then request pagination
(Stage 2) when ready. See SKILL.md Step 4.

Present the file to the user with `mcp__cowork__present_files` and show
the validation summary (page count, exhibit placement, any warnings).
Remind the user to review before requesting pagination.
