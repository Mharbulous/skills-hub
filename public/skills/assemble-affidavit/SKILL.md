---
name: assemble-affidavit
description: >
  Assemble a completed affidavit (DOCX) plus its exhibit files (PDF) into
  a single flat PDF with BC-format exhibit stamps, affidavit header rewrite, and
  jurat date rewrite. Two-stage workflow: Stage 1 produces a draft for review
  (without page numbers); Stage 2 adds pagination after user approval. Use whenever the user asks to assemble an affidavit with
  exhibits, stamp exhibits, combine an affidavit into a single PDF, or prepare
  an affidavit package for swearing/affirming. Trigger on: assemble affidavit,
  stamp exhibits, affidavit with exhibits, combine affidavit, affidavit package,
  prepare for swearing, prepare for affirming, exhibit stamps.
---

# assemble-affidavit

Assemble a completed affidavit and its exhibits into a single flat PDF with
BC Supreme Court exhibit stamps, header rewrite, and jurat rewrite.

This skill operates in two phases, loaded progressively:

1. **Validation** — verify exhibit files before any assembly work begins
2. **Assembly** — convert, stamp, and merge into a single PDF

Do NOT proceed to assembly until validation passes.

## Skill directory

When this skill is loaded from Skills-hub in Cowork, the wrapper first runs a
verified resolver and then reads this `SKILL.md` from a local cache directory.
Treat the directory containing this verified `SKILL.md` as `SKILL_DIR`. Resolve
`references/`, `scripts/assemble.py`, and `scripts/rename_exhibits.py` relative
to `SKILL_DIR`; do not search for or trust sibling files beside the wrapper
stub.

## Solicitor Details (Hardcoded)

| Field | Value |
|-------|-------|
| Name | Brahm Dorst |
| Firm | Logica Law |

## Step 1 — Identify the affidavit and gather parameters

Scan the matter workspace for affidavit files. Look in `0. DRAFT/` and its
subfolders for `.docx` files whose name contains "AFF" or "affidavit". If
multiple candidates exist, ask the user to pick one.

### Format requirements (hard constraints)

- **Affidavit MUST be `.docx` format** — required for header/jurat XML
  rewriting. If the affidavit is a PDF, abort and tell the user a DOCX
  version is needed.
- **Exhibits must be `.pdf` format.** If both a PDF and a non-PDF
  version of an exhibit exist, use the PDF. If only a non-PDF version
  exists, convert it to PDF using LibreOffice before proceeding (see
  Non-PDF exhibit handling below). Do NOT pass unconverted files to
  the assembly script.

Infer as many parameters as possible from context:

| Parameter | How to infer |
|-----------|-------------|
| `affiant_name` | From the affidavit filename or body text |
| `affidavit_number` | From the filename (e.g. "AFF#2" → 2) or ask |
| `jurat_verb` | From the affidavit body ("AFFIRMED" or "SWORN"); default "AFFIRMED" |
| `signing_date` | Default to today's date; ask if the user wants a different date |

Present assumptions and confirm with the user via `AskUserQuestion`:

```
question: "I'll assemble this affidavit with the following parameters. Correct?"
options:
  - "Yes, proceed"
  - "Let me adjust"
```

**Fallback if `AskUserQuestion` fails:** Present the inferred parameters as
a markdown summary and ask the user to confirm or correct via chat.

## Step 2 — Validate exhibits

**Read `references/validation.md` now.** It contains the full validation
procedure: extracting exhibit references from the affidavit, verifying file
naming, and verifying each exhibit file's content matches the affidavit's
description of it.

Validation MUST pass before proceeding. If validation surfaces issues,
present them to the user and wait for confirmation before continuing.

## Step 3 — Assemble the affidavit package (Stage 1: Draft for Review)

**Only after validation passes**, read `references/assembly.md`. It contains
the full assembly procedure: DOCX-to-PDF conversion, header/jurat coordinate
discovery, JSON input construction, script invocation, and output delivery.

Assembly produces a **draft for review** — the merged PDF with exhibit stamps,
header rewrite, and jurat rewrite, but **without page numbers**. The output
filename uses the pattern:
`{date} AFF#{n} {LastNameFirstInitial} - DRAFT for Review.pdf`

Present the draft to the user for review. The user may need to remove
unnecessary pages (cover sheets, blank scan backs, duplicates) before
finalizing.

## Step 4 — Pagination (Stage 2: Final with Page Numbers)

After the user confirms the draft is ready, add page numbers to produce
the final document. This step is triggered by the user — do NOT paginate
automatically after assembly.

Output filename:
`{date} AFF#{n} {LastNameFirstInitial} - Complete with Exhibits.pdf`

**Note:** Pagination is not yet implemented in `assemble.py`. When the
user requests pagination, add sequential page numbers (footer, centered)
to the finalized PDF using PyMuPDF. Skip this step until the user
explicitly asks for it.

## No ad-hoc assembly — Critical

Assembly MUST use `scripts/assemble.py`. If the script cannot be located,
read, or executed for any reason (resolver failure, FUSE error, missing
dependencies, network timeout, truncated file, etc.), the skill MUST
**fail loudly and stop**. Specifically:

1. Report the exact error to the user (e.g., "assemble.py could not be
   loaded: [reason]").
2. Do NOT improvise a replacement script, inline assembly code, or any
   ad-hoc alternative — not with reportlab, pypdf, PyMuPDF, or any other
   library.
3. Do NOT partially assemble (e.g., merge without stamps, stamp without
   header rewrite).

**Why:** Ad-hoc assembly bypasses the tested stamp placement, opacity,
header/jurat rewrite, and FUSE-safety logic in `assemble.py`. Prior
incidents have produced opaque white boxes that obscure exhibit content —
a defect that could go unnoticed and be filed with the court. The risk of
silent data damage outweighs the inconvenience of a failed run.

**Recovery path:** Tell the user the skill's assembly script is
unavailable and suggest: (a) retry in a new session, (b) verify the
skill is installed correctly, or (c) run `assemble.py` manually from
the command line.

## Idempotency — Critical

This skill MUST be idempotent. It always works from original source files
(affidavit DOCX/PDF + raw exhibit files), never from a previously
assembled output. Re-running produces a clean result without double-stamps
or double-rewrites.

**Source files are read-only.** Never modify, stamp, or add pages to the
original exhibit files or affidavit DOCX. The assembly pipeline is:

1. Copy affidavit and exhibits to `/var/tmp/` (the script does this automatically)
2. Rewrite header and jurat on the *copy* of the affidavit
3. Merge the affidavit copy and exhibit copies into a single consolidated PDF
4. Apply exhibit stamps to the *consolidated output*, not to individual files

If you find yourself modifying an exhibit file in its source location
(adding a stamp page, converting in place, etc.), STOP — that breaks
idempotency. All modifications happen on temp copies that are merged into
the output PDF.

## Date consistency

After editing the header and jurat dates, scan the full affidavit body for
all date references (regex: `(January|February|...|December)\s+\d{1,2},?\s+\d{4}`).
If any body-text dates reference the affidavit's own date (e.g., "as of the
date of this affidavit, June 22, 2026") and that date differs from the
header/jurat date, flag the discrepancy to the user. Do NOT silently change
body-text dates — they may involve interest calculations or other substantive
content that requires the lawyer's judgment.

## Non-PDF exhibit handling

If exhibit files exist in non-PDF formats (`.xlsx`, `.docx`, `.png`, etc.):

- If both a PDF and non-PDF version exist for the same exhibit letter,
  use the PDF and ignore the other.
- If only a non-PDF version exists, convert it to PDF using LibreOffice
  (`soffice --headless --convert-to pdf`), then proceed. Tell the user
  which files were converted so they can verify the output looks correct.
- Flag `.xlsx` files specifically — they are common for financial
  spreadsheet exhibits and their PDF conversion should be confirmed by
  the user before the assembled package is finalized.

## Previously stamped file detection

The exhibit folder may contain previously stamped versions of exhibits
from prior assembly runs. Detect these by:

- Filename patterns like `*-LLC-VAN-D22P.pdf` or `*_stamped.pdf`
- Files whose first page contains exhibit stamp text ("This is Exhibit"
  + "referred to in the Affidavit")

When both stamped and unstamped versions exist, always use the unstamped
(plain) version. Report detected stamped files in the validation summary
so the user can clean up the folder.

## Error handling

- If LibreOffice is not installed, install it: `apt-get install -y libreoffice-writer`
- If PyMuPDF is not installed: `pip install PyMuPDF --break-system-packages`
- If scipy is not installed: `pip install scipy --break-system-packages`
- If an exhibit file is missing, report which letter/file is missing and
  ask the user to provide it
- If the FUSE mount causes write failures, use the `save_pdf()` helper in
  `assemble.py` (writes via `tobytes()` + manual file write) instead of
  `doc.save()`. For file copies, read into memory first then write, rather
  than using `shutil.copy2()` across FUSE boundaries.

## FUSE mount — critical constraint

The Cowork sandbox mounts the user's workspace via a FUSE chain (virtiofs
+ bindfs). This FUSE layer caches file lookups aggressively — after a
rename, reads from the new path may return the old file's content.

### File rename/copy operations

**Rule: never use bash `mv`, `cp`, or `shutil` directly for exhibit file
operations.** Use the `scripts/rename_exhibits.py` script instead. It
handles FUSE cache invalidation deterministically via rename round-trips.

LLM inference cannot reliably remember this constraint across tool calls.
The script exists specifically to prevent this class of error. See
`references/validation.md` section 2f for usage details.

### PyMuPDF save operations

PyMuPDF's `doc.save(path)` internally removes and replaces the target
file, which fails on FUSE mounts with `PermissionError: Operation not
permitted`. The `assemble.py` script uses `save_pdf(doc, path)` which
calls `doc.tobytes()` + `open(path, 'wb').write(bytes)` instead.

Similarly, `shutil.copy2()` across FUSE boundaries can fail with
`PermissionError`. The script reads source files into memory with
`open(path, 'rb').read()` then writes to the destination, bypassing
the FUSE copy path.

**If you add new file operations to assemble.py, always use:**
- `save_pdf(doc, path)` instead of `doc.save(path)`
- `copy_to_tmp(src)` instead of `shutil.copy2(src, dst)`
- Read-into-memory + write instead of `shutil.copy2()` for final output

### Pre-flight: script integrity

The FUSE mount can serve truncated content for large files even when
`stat` reports the correct size. **Before every invocation** of
`scripts/assemble.py` or `scripts/rename_exhibits.py`, run this check:

```bash
python3 -c "import ast,os,sys; p=sys.argv[1]; b=open(p,'rb').read(); s=os.path.getsize(p); assert len(b)==s, f'SHORT READ {len(b)} != {s}'; ast.parse(b.decode()); assert b.rstrip().endswith(b'main()'), 'TRUNCATED TAIL'; print(f'pre-flight OK: {p} ({s} bytes)')" "$SCRIPT"
```

If the check fails, the FUSE mount served corrupt content. Read the
script with the **Read tool**, **Write** it to `/var/tmp/<script-name>`,
re-run the pre-flight on the copy, then invoke the copy.
