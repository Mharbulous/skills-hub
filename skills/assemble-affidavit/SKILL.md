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
- **Exhibits MUST be `.pdf` format** — no exceptions. If an exhibit
  exists only as XLSX, DOCX, or another format, abort and ask the user
  to convert it to PDF first (e.g., File > Save As PDF / Export in
  Excel or Word). If both a PDF and a non-PDF version of an exhibit
  exist, use the PDF.

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

## Error handling

- If LibreOffice is not installed, install it: `apt-get install -y libreoffice-writer`
- If PyMuPDF is not installed: `pip install PyMuPDF --break-system-packages`
- If scipy is not installed: `pip install scipy --break-system-packages`
- If an exhibit file is missing, report which letter/file is missing and
  ask the user to provide it
- If the FUSE mount causes write failures, all writes go through `/var/tmp/`
  first with `shutil.copy2()` to the final destination

## FUSE mount — critical constraint

The Cowork sandbox mounts the user's workspace via a FUSE chain (virtiofs
+ bindfs). This FUSE layer caches file lookups aggressively — after a
rename, reads from the new path may return the old file's content.

**Rule: never use bash `mv`, `cp`, or `shutil` directly for exhibit file
operations.** Use the `scripts/rename_exhibits.py` script instead. It
handles FUSE cache invalidation deterministically via rename round-trips.

LLM inference cannot reliably remember this constraint across tool calls.
The script exists specifically to prevent this class of error. See
`references/validation.md` section 2f for usage details.

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
