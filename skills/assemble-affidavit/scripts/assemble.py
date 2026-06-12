#!/usr/bin/env python3
"""
assemble-affidavit pipeline.

Accepts JSON on stdin, produces a single flat PDF with:
  - BC-format exhibit stamps on first page of each exhibit
  - Affidavit header rewrite (page 1, top-right)
  - Jurat date rewrite (signature page)

Returns JSON validation summary on stdout.

Usage:
    echo '{"affiant_name": "...", ...}' | python3 assemble.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "PyMuPDF not installed. Run: pip install PyMuPDF --break-system-packages"
    }))
    sys.exit(1)


# ---------------------------------------------------------------------------
# LibreOffice wrapper (soffice.py from docx skill)
# ---------------------------------------------------------------------------

_soffice_module = None

def _find_soffice_module():
    """
    Locate and import the docx skill's soffice.py wrapper at runtime.
    Returns the module, or None if not found.
    """
    global _soffice_module
    if _soffice_module is not None:
        return _soffice_module

    import importlib.util

    # Search for soffice.py in the skills tree
    for search_root in ["/sessions", "/tmp"]:
        if not os.path.isdir(search_root):
            continue
        for root, dirs, files in os.walk(search_root):
            if "soffice.py" in files and root.endswith("office"):
                spec = importlib.util.spec_from_file_location(
                    "office.soffice", os.path.join(root, "soffice.py")
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    _soffice_module = mod
                    return mod
            # Prune deep trees
            if root.count(os.sep) > 8:
                dirs.clear()
    return None


def _get_lo_env() -> dict:
    """
    Get environment dict for running LibreOffice.
    Uses the soffice.py wrapper if available (handles AF_UNIX shim),
    otherwise falls back to basic SAL_USE_VCLPLUGIN=svp.
    """
    mod = _find_soffice_module()
    if mod and hasattr(mod, "get_soffice_env"):
        return mod.get_soffice_env()

    # Fallback: basic env without socket shim
    env = os.environ.copy()
    env["SAL_USE_VCLPLUGIN"] = "svp"
    env["HOME"] = get_run_tmpdir()
    return env


def _run_libreoffice(args: list, **kwargs) -> subprocess.CompletedProcess:
    """
    Run LibreOffice with the correct environment.
    Uses soffice.py wrapper if available, otherwise subprocess with _get_lo_env.
    """
    mod = _find_soffice_module()
    if mod and hasattr(mod, "run_soffice"):
        return mod.run_soffice(args, **kwargs)

    env = _get_lo_env()
    return subprocess.run(["soffice"] + args, env=env, **kwargs)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCALE = 1.25
STAMP_W = 211.09  # pt
STAMP_H = 116.05  # pt
STAMP_FS = 13.8   # pt (11.04 * SCALE)
STAMP_ASCENT = 8.83  # pt (11.04 * 0.8)

STAMP_FONT_PATH = "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf"
HEADER_FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
HEADER_FONT_SIZE = 12.0

# Stamp text opacity (0.0 = invisible, 1.0 = fully opaque)
# 0.5 = 50% opaque / 50% transparent — readable but unobtrusive
STAMP_TEXT_OPACITY = 0.5

# Stamp background and border: fully transparent (text only, no box)
STAMP_BG_OPACITY = 0.0
STAMP_BORDER_OPACITY = 0.0

# Stamp margin from page edge (pt)
STAMP_MARGIN = 18.0

# Whitespace stamp placement: grid resolution and content clearance
GRID_CELL = 4.0       # pt — occupancy grid cell size
CONTENT_CLEARANCE = 6.0  # pt — padding around occupied rects


# ---------------------------------------------------------------------------
# Per-run temp directory
# ---------------------------------------------------------------------------

_run_tmpdir = None

def get_run_tmpdir() -> str:
    """Unique per-run temp dir under /var/tmp. Fixed names in /tmp
    collide with stale files left by other sandbox users (PermissionError);
    a fresh mkdtemp per run cannot collide with anything."""
    global _run_tmpdir
    if _run_tmpdir is None:
        base = "/var/tmp" if os.path.isdir("/var/tmp") else None
        _run_tmpdir = tempfile.mkdtemp(prefix="assemble_", dir=base)
    return _run_tmpdir

def cleanup_run_tmpdir() -> None:
    global _run_tmpdir
    if _run_tmpdir and os.path.isdir(_run_tmpdir):
        shutil.rmtree(_run_tmpdir, ignore_errors=True)
    _run_tmpdir = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ordinal(n: int) -> str:
    """Return ordinal string for integer n (e.g. 1 -> '1st', 2 -> '2nd')."""
    s = ["th", "st", "nd", "rd"]
    v = n % 100
    idx = (v - 20) % 10 if (v - 20) % 10 in (1, 2, 3) else (v if v in (1, 2, 3) else 0)
    return str(n) + s[idx]


def month_name(dt_str: str) -> str:
    """Extract month name from YYYY-MM-DD string."""
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    m = int(dt_str.split("-")[1])
    return months[m - 1]


def parse_date(dt_str: str) -> tuple:
    """Parse YYYY-MM-DD into (year, month_num, day)."""
    parts = dt_str.split("-")
    return int(parts[0]), int(parts[1]), int(parts[2])


def copy_to_tmp(src: str, suffix: str = None) -> str:
    """Copy a file to the per-run temp dir for FUSE-safe processing.

    Reads the source file into memory first to bypass FUSE read caching,
    then writes to the temp dir. This avoids PermissionError and stale
    content issues that occur with shutil.copy2 across FUSE boundaries.
    """
    src_path = Path(src)
    if suffix:
        dst = Path(get_run_tmpdir()) / f"assemble_{src_path.stem}{suffix}"
    else:
        dst = Path(get_run_tmpdir()) / f"assemble_{src_path.name}"
    # Read into memory to bypass FUSE cache, then write to temp dir
    with open(str(src_path), 'rb') as f:
        data = f.read()
    with open(str(dst), 'wb') as f:
        f.write(data)
    return str(dst)


def save_pdf(doc, path: str) -> None:
    """Save a PyMuPDF document to path using tobytes() + manual write.

    PyMuPDF's doc.save() internally removes and replaces the target file,
    which fails on FUSE mounts with PermissionError. Writing the bytes
    manually avoids this.
    """
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    with open(path, 'wb') as f:
        f.write(pdf_bytes)



# ---------------------------------------------------------------------------
# Exhibit conversion
# ---------------------------------------------------------------------------

def convert_docx_to_pdf(docx_path: str) -> str:
    """Convert DOCX to PDF via LibreOffice headless (using soffice.py wrapper). Returns PDF path in the run temp dir."""
    tmp_docx = copy_to_tmp(docx_path)
    outdir = get_run_tmpdir()
    result = _run_libreoffice(
        ["--headless", "--convert-to", "pdf", "--outdir", outdir, tmp_docx],
        capture_output=True, text=True, timeout=120,
    )
    pdf_name = Path(tmp_docx).stem + ".pdf"
    pdf_path = os.path.join(outdir, pdf_name)
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"LibreOffice conversion failed for {docx_path}: {result.stderr}")
    return pdf_path


def convert_exhibit(exhibit_path: str) -> str:
    """
    Copy a PDF exhibit into the run temp dir. Exhibits are PDF-only by
    policy; the validation format gate rejects everything else before
    assembly, so reaching the error below means the gate was skipped.
    Raises RuntimeError with 'unsupported_format' for non-PDF files.
    """
    ext = Path(exhibit_path).suffix.lower()
    if ext == ".pdf":
        return copy_to_tmp(exhibit_path)
    raise RuntimeError(f"unsupported_format:{ext}")


# ---------------------------------------------------------------------------
# Stamp placement — whitespace search with bottom-right preference
# ---------------------------------------------------------------------------

import math

def _get_occupied_rects(page) -> list:
    """Collect padded bounding rects for all content on the page.
    Uses per-line granularity for text (blocks merge nearby lines into
    one giant rect, hiding gaps) and block-level for images.

    For scanned PDFs (image-only, no text layer), falls back to
    pixmap-based detection: renders the page at low DPI and scans
    for non-white regions to build occupied rects.
    """
    rects = []
    has_content = False
    flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_IMAGES
    for block in page.get_text("dict", flags=flags)["blocks"]:
        has_content = True
        if block["type"] == 1:
            # Image block — use the whole bbox
            r = fitz.Rect(block["bbox"])
            rects.append(fitz.Rect(
                r.x0 - CONTENT_CLEARANCE, r.y0 - CONTENT_CLEARANCE,
                r.x1 + CONTENT_CLEARANCE, r.y1 + CONTENT_CLEARANCE,
            ))
        else:
            # Text block — iterate lines for per-line granularity
            for line in block.get("lines", []):
                r = fitz.Rect(line["bbox"])
                rects.append(fitz.Rect(
                    r.x0 - CONTENT_CLEARANCE, r.y0 - CONTENT_CLEARANCE,
                    r.x1 + CONTENT_CLEARANCE, r.y1 + CONTENT_CLEARANCE,
                ))
    try:
        for d in page.get_drawings():
            has_content = True
            r = fitz.Rect(d["rect"])
            rects.append(fitz.Rect(
                r.x0 - CONTENT_CLEARANCE, r.y0 - CONTENT_CLEARANCE,
                r.x1 + CONTENT_CLEARANCE, r.y1 + CONTENT_CLEARANCE,
            ))
    except Exception:
        pass  # best-effort for vector drawings

    # Fallback for scanned PDFs: if no text/drawing content was found,
    # render the page to a low-res pixmap and scan for non-white regions.
    if not rects and not has_content:
        rects = _get_occupied_rects_from_pixmap(page)

    return rects


def _get_occupied_rects_from_pixmap(page) -> list:
    """Render page at low DPI and detect non-white regions.

    Divides the rendered image into a grid of cells and marks cells
    as occupied if their average pixel value is below a threshold
    (i.e., not white). Returns occupied rects in page coordinates.
    """
    # Render at 36 DPI (low res, fast) — enough to detect content regions
    RENDER_DPI = 36
    scale = RENDER_DPI / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))

    pw, ph = page.rect.width, page.rect.height
    img_w, img_h = pix.width, pix.height

    # Cell size in image pixels (corresponds to ~GRID_CELL*4 in page space)
    CELL_PX = max(4, int(16 * scale))
    WHITE_THRESHOLD = 240  # pixel value below this = "has content"

    rects = []
    samples = pix.samples  # raw pixel bytes
    n_channels = pix.n  # number of channels (3 for RGB, 4 for RGBA)

    for row_start in range(0, img_h, CELL_PX):
        for col_start in range(0, img_w, CELL_PX):
            row_end = min(row_start + CELL_PX, img_h)
            col_end = min(col_start + CELL_PX, img_w)

            # Sample center pixel of the cell
            cy = (row_start + row_end) // 2
            cx = (col_start + col_end) // 2
            idx = (cy * img_w + cx) * n_channels
            if idx + 2 < len(samples):
                r_val = samples[idx]
                g_val = samples[idx + 1]
                b_val = samples[idx + 2]
                avg = (r_val + g_val + b_val) / 3.0
                if avg < WHITE_THRESHOLD:
                    # Convert image coords back to page coords
                    px0 = col_start / scale
                    py0 = row_start / scale
                    px1 = col_end / scale
                    py1 = row_end / scale
                    rects.append(fitz.Rect(
                        px0 - CONTENT_CLEARANCE, py0 - CONTENT_CLEARANCE,
                        px1 + CONTENT_CLEARANCE, py1 + CONTENT_CLEARANCE,
                    ))

    return rects


def find_best_stamp_position(page) -> tuple:
    """
    Find the best whitespace position for the exhibit stamp.
    Returns ("whitespace", stamp_rect) or (None, None) if no clear
    position exists (caller inserts a blank page).
    """
    if page.rotation:
        return None, None

    pw, ph = page.rect.width, page.rect.height
    m = STAMP_MARGIN

    # Page too small for stamp + margins
    if pw < STAMP_W + 2 * m or ph < STAMP_H + 2 * m:
        return None, None

    # Build occupancy grid
    cols = math.ceil(pw / GRID_CELL)
    rows = math.ceil(ph / GRID_CELL)
    grid = [[0] * (cols + 1) for _ in range(rows + 1)]

    for r in _get_occupied_rects(page):
        c0 = max(0, int(r.x0 / GRID_CELL))
        r0 = max(0, int(r.y0 / GRID_CELL))
        c1 = min(cols, math.ceil(r.x1 / GRID_CELL))
        r1 = min(rows, math.ceil(r.y1 / GRID_CELL))
        for row in range(r0, r1):
            for col in range(c0, c1):
                grid[row][col] = 1

    # 2-D prefix sum
    psum = [[0] * (cols + 1) for _ in range(rows + 1)]
    for r in range(rows):
        for c in range(cols):
            psum[r + 1][c + 1] = grid[r][c] + psum[r][c + 1] + psum[r + 1][c] - psum[r][c]

    # Stamp window size in grid cells
    sw = math.ceil(STAMP_W / GRID_CELL)
    sh = math.ceil(STAMP_H / GRID_CELL)

    # Margin bounds in grid cells
    min_c = math.ceil(m / GRID_CELL)
    min_r = math.ceil(m / GRID_CELL)
    max_c = int((pw - m) / GRID_CELL) - sw
    max_r = int((ph - m) / GRID_CELL) - sh

    if max_c < min_c or max_r < min_r:
        return None, None

    # Bottom-right target for distance scoring
    target_x = pw - m
    target_y = ph - m

    best_dist = float('inf')
    best_pos = None

    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            area = (psum[r + sh][c + sw] - psum[r][c + sw]
                    - psum[r + sh][c] + psum[r][c])
            if area > 0:
                continue
            # Stamp rect bottom-right corner
            br_x = (c + sw) * GRID_CELL
            br_y = (r + sh) * GRID_CELL
            dist = math.hypot(br_x - target_x, br_y - target_y)
            if dist < best_dist or (dist == best_dist and best_pos is not None
                                    and (r > best_pos[0] or (r == best_pos[0] and c > best_pos[1]))):
                best_dist = dist
                best_pos = (r, c)

    if best_pos is None:
        return None, None

    r, c = best_pos
    x0 = c * GRID_CELL
    y0 = r * GRID_CELL
    return "whitespace", fitz.Rect(x0, y0, x0 + STAMP_W, y0 + STAMP_H)


def draw_stamp(page, rect: fitz.Rect, letter: str, affiant_name: str,
               stamp_font) -> None:
    """
    Draw the BC commissioner exhibit stamp on the page at the given rect.

    Format (text only — no background box or border):
        This is Exhibit "A" referred to in the
        Affidavit of {affiant_name} made
        this ____ day of _____________, 20____

        _________________________
        Commissioner for affidavit
    """
    ox, oy = rect.x0, rect.y0  # origin of stamp rect
    line_height = STAMP_FS * 1.25  # 25% leading

    lines = [
        f'This is Exhibit “{letter}” referred to in the',
        f"Affidavit of {affiant_name} made",
        "this ____ day of _____________, 20____",
        "",  # blank line before signature
        "_________________________",
        "Commissioner for affidavit",
    ]

    for i, text in enumerate(lines):
        if not text:
            continue
        x = ox + 1.0 * SCALE
        y = oy + (i * line_height) + STAMP_ASCENT * SCALE

        page.insert_text(
            fitz.Point(x, y),
            text,
            fontfile=STAMP_FONT_PATH,
            fontsize=STAMP_FS,
            fontname="Carlito",
            fill=(0, 0, 0),
            fill_opacity=STAMP_TEXT_OPACITY,
            stroke_opacity=STAMP_TEXT_OPACITY,
        )


# ---------------------------------------------------------------------------
# Header and jurat rewrite
# ---------------------------------------------------------------------------

def rewrite_header(page, bbox: list, affiant_name: str,
                   affidavit_number: int, signing_date: str) -> None:
    """
    Redact the old header and insert the new one (right-aligned, top-right).
    """
    year, month_num, day = parse_date(signing_date)
    mn = month_name(signing_date)
    ord_num = ordinal(affidavit_number)

    # Validate: check that some text exists in the bbox region
    words = page.get_text("words")
    header_words = [w for w in words
                    if w[0] >= bbox[0] - 20 and w[1] >= bbox[1] - 10
                    and w[2] <= bbox[2] + 20 and w[3] <= bbox[3] + 10]

    if not header_words:
        raise RuntimeError(
            f"bbox_validation_failed:header — no text found in region "
            f"({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}). "
            "Re-examine the PDF text layer and provide corrected coordinates."
        )

    # Redact
    redact_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
    page.add_redact_annot(redact_rect, fill=(1, 1, 1))
    page.apply_redactions(graphics=2)

    # Insert new header lines (right-aligned)
    RIGHT_EDGE = 540.0
    lines = [
        (bbox[1] + 12.8, f"This is the {ord_num} affidavit"),
        (bbox[1] + 26.6, f"of {affiant_name} in this case"),
        (bbox[1] + 40.4, f"and was made on {mn} {day}, {year}"),
    ]

    font = fitz.Font(fontfile=HEADER_FONT_PATH)
    for y, text in lines:
        text_width = font.text_length(text, fontsize=HEADER_FONT_SIZE)
        x = RIGHT_EDGE - text_width
        page.insert_text(
            fitz.Point(x, y),
            text,
            fontfile=HEADER_FONT_PATH,
            fontsize=HEADER_FONT_SIZE,
            fontname="LiberationSans",
            fill=(0, 0, 0),
        )


def rewrite_jurat(page, bbox: list, jurat_verb: str,
                  signing_date: str) -> None:
    """
    Surgically rewrite only the city name and date in the jurat block.

    Preserves the entire signing structure: "AFFIRMED BEFORE ME at the
    City of", the ")" column, the signature space, the commissioner line,
    and the affiant name.  Only two things change:
      1. The city name (e.g. "Vancouver,") → "_______________,"
      2. The date line (e.g. "this June 9, 2026.") → "this {ord} day of {month}, {year}."
    """
    year, month_num, day = parse_date(signing_date)
    mn = month_name(signing_date)
    ord_day = ordinal(day)

    words = page.get_text("words")

    # --- Locate the AFFIRMED/SWORN line ---
    # Find "AFFIRMED BEFORE ME" or "SWORN BEFORE ME" as a phrase, not just
    # the word in isolation. The old w[1] > 200 threshold was arbitrary and
    # broke on affidavits where the jurat started higher on the page.
    affirmed_word = None
    for w in words:
        if w[4].upper() in ("AFFIRMED", "SWORN"):
            # Verify this is part of "BEFORE ME" (the jurat), not
            # "AFFIRM THAT" (the oath in the body)
            nearby = [w2 for w2 in words
                      if abs(w2[1] - w[1]) < 5 and w2[4].upper() == "BEFORE"]
            if nearby:
                affirmed_word = w
                break

    if affirmed_word is None:
        raise RuntimeError(
            "bbox_validation_failed:jurat — could not find AFFIRMED/SWORN "
            "on the signature page."
        )

    affirmed_y = affirmed_word[1]
    affirmed_y1 = affirmed_word[3]

    # --- Find the city line (first line below AFFIRMED) ---
    # Collect words on the line immediately below AFFIRMED
    city_line_words = []
    for w in words:
        if w[1] > affirmed_y1 - 2 and w[1] < affirmed_y1 + 20 and w[4] != ")":
            city_line_words.append(w)

    # --- Find the date line (line containing "this ... year.") ---
    date_line_words = []
    for w in words:
        if (w[1] > affirmed_y1 + 10 and w[1] < affirmed_y1 + 40
                and w[4] != ")"):
            date_line_words.append(w)

    # --- Redact the entire city line (not the ")" markers) ---
    # Redact "Vancouver, Province of British Columbia," as a whole so we can
    # re-insert it as a single aligned string: "______________, Province of ..."
    if city_line_words:
        city_line_words.sort(key=lambda w: w[0])
        cx0 = city_line_words[0][0] - 1
        cy0 = city_line_words[0][1] - 1
        cx1 = city_line_words[-1][2] + 1
        cy1 = city_line_words[-1][3] + 1
        page.add_redact_annot(fitz.Rect(cx0, cy0, cx1, cy1), fill=(1, 1, 1))

    # --- Redact only the date text (not the ")" markers) ---
    if date_line_words:
        date_line_words.sort(key=lambda w: w[0])
        dx0 = date_line_words[0][0] - 1
        dy0 = date_line_words[0][1] - 1
        dx1 = date_line_words[-1][2] + 1
        dy1 = date_line_words[-1][3] + 1
        page.add_redact_annot(fitz.Rect(dx0, dy0, dx1, dy1), fill=(1, 1, 1))

    page.apply_redactions(graphics=2)

    # --- Insert replacement text at the same positions ---
    x_start = affirmed_word[0]  # align with "AFFIRMED" x position

    if city_line_words:
        city_y = city_line_words[0][3]  # baseline of city line
        page.insert_text(
            fitz.Point(x_start, city_y),
            "______________, Province of British Columbia,",
            fontfile=HEADER_FONT_PATH,
            fontsize=HEADER_FONT_SIZE,
            fontname="LiberationSans",
            fill=(0, 0, 0),
        )

    if date_line_words:
        date_y = date_line_words[0][3]  # baseline of date line
        page.insert_text(
            fitz.Point(x_start, date_y),
            f"this {ord_day} day of {mn}, {year}.",
            fontfile=HEADER_FONT_PATH,
            fontsize=HEADER_FONT_SIZE,
            fontname="LiberationSans",
            fill=(0, 0, 0),
        )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    # Read JSON input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    # Validate required fields
    required = ["affiant_name", "affidavit_number", "jurat_verb", "signing_date",
                "affidavit_pdf", "header_bbox", "jurat_bbox", "exhibits", "output_path"]
    missing = [f for f in required if f not in input_data]
    if missing:
        print(json.dumps({"success": False, "error": f"Missing required fields: {missing}"}))
        sys.exit(1)

    affiant_name = input_data["affiant_name"]
    affidavit_number = input_data["affidavit_number"]
    jurat_verb = input_data["jurat_verb"]
    signing_date = input_data["signing_date"]
    affidavit_pdf = input_data["affidavit_pdf"]
    header_bbox = input_data["header_bbox"]
    jurat_bbox = input_data["jurat_bbox"]
    exhibits = input_data["exhibits"]
    output_path = input_data["output_path"]

    warnings = []
    exhibit_info = []

    try:
        # --- Phase 1: Convert affidavit DOCX to PDF if needed, then open ---
        if affidavit_pdf.lower().endswith(".docx"):
            try:
                affidavit_pdf = convert_docx_to_pdf(affidavit_pdf)
            except RuntimeError as e:
                print(json.dumps({"success": False, "error": f"Affidavit DOCX-to-PDF conversion failed: {e}"}))
                sys.exit(1)

        try:
            aff_doc = fitz.open(affidavit_pdf)
        except Exception as e:
            print(json.dumps({"success": False, "error": f"Cannot open affidavit PDF: {e}"}))
            sys.exit(1)

        # --- Phase 2: Rewrite header (page 0) ---
        try:
            rewrite_header(aff_doc[0], header_bbox, affiant_name,
                           affidavit_number, signing_date)
        except RuntimeError as e:
            print(json.dumps({"success": False, "error": str(e)}))
            sys.exit(1)

        # --- Phase 3: Rewrite jurat (find signature page) ---
        jurat_page_idx = None
        verb_upper = jurat_verb.upper()
        for i in range(len(aff_doc)):
            text = aff_doc[i].get_text()
            # Text may be split across lines; normalize whitespace for matching
            normalized = " ".join(text.split())
            if (f"{verb_upper} BEFORE ME" in normalized
                    or "SWORN BEFORE ME" in normalized
                    or "AFFIRMED BEFORE ME" in normalized
                    or ("BEFORE ME" in normalized and (verb_upper in normalized))):
                jurat_page_idx = i
                break

        if jurat_page_idx is None:
            # Fall back to last page of affidavit
            jurat_page_idx = len(aff_doc) - 1
            warnings.append("Jurat verb not found in text; used last page of affidavit")

        try:
            rewrite_jurat(aff_doc[jurat_page_idx], jurat_bbox, jurat_verb, signing_date)
        except RuntimeError as e:
            print(json.dumps({"success": False, "error": str(e)}))
            sys.exit(1)

        # --- Phase 4: Save processed affidavit ---
        aff_tmp = os.path.join(get_run_tmpdir(), "aff_processed.pdf")
        save_pdf(aff_doc, aff_tmp)
        aff_page_count = len(aff_doc)
        aff_doc.close()

        # --- Phase 5: Process each exhibit individually (memory-efficient) ---
        # For each exhibit: convert to PDF, stamp first page, save individually.
        # Then use qpdf to concatenate everything at the end.
        parts = [aff_tmp]  # list of PDF file paths to concatenate
        current_page = aff_page_count

        for ex in exhibits:
            letter = ex["letter"]
            path = ex["path"]

            if not os.path.exists(path):
                print(json.dumps({
                    "success": False,
                    "error": f"Exhibit {letter} file not found: {path}"
                }))
                sys.exit(1)

            # Convert exhibit to PDF
            try:
                pdf_path = convert_exhibit(path)
            except RuntimeError as e:
                err_str = str(e)
                if err_str.startswith("unsupported_format:"):
                    print(json.dumps({
                        "success": False,
                        "error": "unsupported_format",
                        "exhibit_letter": letter,
                        "exhibit_path": path,
                        "format": err_str.split(":")[1],
                        "hint": "All exhibits must be PDF. Ask the user for a PDF version of this exhibit."
                    }))
                    sys.exit(1)
                else:
                    print(json.dumps({
                        "success": False,
                        "error": f"Exhibit {letter} conversion failed: {e}"
                    }))
                    sys.exit(1)

            # Open exhibit, determine stamp placement, stamp, save
            import gc
            ex_doc = fitz.open(pdf_path)
            ex_page_count = ex_doc.page_count
            first_page = ex_doc[0]

            position, stamp_rect = find_best_stamp_position(first_page)

            if position is not None:
                # Stamp directly on the exhibit's first page
                draw_stamp(first_page, stamp_rect, letter, affiant_name, None)
                stamped_path = os.path.join(get_run_tmpdir(), f"ex_{letter}_stamped.pdf")
                save_pdf(ex_doc, stamped_path)
                ex_doc.close()
                gc.collect()
                parts.append(stamped_path)

                exhibit_info.append({
                    "letter": letter,
                    "pages": f"{current_page + 1}-{current_page + ex_page_count}",
                    "stamp_placement": position,
                })
                current_page += ex_page_count
            else:
                # Need a blank page with stamp before this exhibit
                blank_doc = fitz.open()
                blank_doc.new_page(width=612, height=792)
                blank_page = blank_doc[0]
                cx = (612 - STAMP_W) / 2
                cy = (792 - STAMP_H) / 2
                centered_rect = fitz.Rect(cx, cy, cx + STAMP_W, cy + STAMP_H)
                draw_stamp(blank_page, centered_rect, letter, affiant_name, None)
                blank_path = os.path.join(get_run_tmpdir(), f"ex_{letter}_blank.pdf")
                save_pdf(blank_doc, blank_path)
                blank_doc.close()

                stamped_path = os.path.join(get_run_tmpdir(), f"ex_{letter}_stamped.pdf")
                save_pdf(ex_doc, stamped_path)
                ex_doc.close()
                gc.collect()

                parts.append(blank_path)
                parts.append(stamped_path)

                exhibit_info.append({
                    "letter": letter,
                    "pages": f"{current_page + 2}-{current_page + 1 + ex_page_count}",
                    "stamp_placement": "blank_page_inserted",
                })
                current_page += ex_page_count + 1

        # --- Phase 6: Concatenate all parts using qpdf ---
        tmp_output = os.path.join(get_run_tmpdir(), "assembled_final.pdf")
        qpdf_cmd = ["qpdf", "--empty", "--pages"] + parts + ["--", tmp_output]
        try:
            qpdf_result = subprocess.run(qpdf_cmd, capture_output=True, text=True, timeout=60)
            if qpdf_result.returncode not in (0, 3):  # qpdf returns 3 for warnings
                raise RuntimeError(f"qpdf failed: {qpdf_result.stderr}")
        except subprocess.TimeoutExpired:
            print(json.dumps({"success": False, "error": "qpdf concatenation timed out"}))
            sys.exit(1)

        # --- Phase 7: Copy to final output path ---
        # Use read-into-memory + write pattern to bypass FUSE copy issues
        final_path = output_path
        try:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(tmp_output, 'rb') as f:
                data = f.read()
            with open(output_path, 'wb') as f:
                f.write(data)
        except (PermissionError, OSError):
            from datetime import datetime
            base, ext = os.path.splitext(output_path)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            versioned = f"{base}_{ts}{ext}"
            try:
                with open(tmp_output, 'rb') as f:
                    data = f.read()
                with open(versioned, 'wb') as f:
                    f.write(data)
                final_path = versioned
            except Exception:
                rescue = os.path.join(get_run_tmpdir(), f"assembled_rescue_{os.getpid()}.pdf")
                shutil.move(tmp_output, rescue)
                final_path = rescue

        # --- Phase 8: Validate ---
        check_doc = fitz.open(final_path)
        page_count = check_doc.page_count
        check_doc.close()

        # Build result
        result = {
            "success": True,
            "output_path": final_path,
            "page_count": page_count,
            "exhibits": exhibit_info,
            "warnings": warnings,
        }

        if final_path != output_path:
            result["note"] = f"Could not write to {output_path}; saved to {final_path} instead"

        print(json.dumps(result, indent=2))

    finally:
        cleanup_run_tmpdir()


if __name__ == "__main__":
    main()
