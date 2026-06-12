"""Verify a filled .docx or bracket-placeholder .dotx template.

Usage:
  python verify.py <file.docx|.dotx> [<reference.docx>]

Reference-free checks:
  - residual bracket placeholders (except known leave-blank set)
  - ZWSP occurrences
  - mc:Ignorable prefix declarations (T13)

Reference diff (if reference provided):
  - pandoc-plain text diff
"""
from __future__ import annotations
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PLACEHOLDER_RX = re.compile(r'\[[^\]]{1,40}\]')

# Leave-blank set — union across all forms.  These are template placeholders
# the lawyer fills in Word, not programmatically.  Using the union means
# verify.py works for any form type without a --form flag.
LEAVE_BLANK = {
    '[mmmm d, yyyy]', '[number]', '[judge-date]',
    # Affidavit interpreter endorsement (Rule 22-2(7)) — filled only when needed
    '[name]', '[address]', '[occupation]', '[language(s)]',
    # Petition-specific leave-blanks
    '[date]', '[time estimate]',
    # RTC (Response to Counterclaim) leave-blanks
    '[#]',
    # BOC (Bill of Costs) leave-blanks — table content filled in Word
    # Tariff Items table
    '[ITEM NO.]', '[ITEM DESCRIPTION]', '[UNITS CLAIMED]', '[UNITS ALLOWED]',
    '[TOTAL UNITS CLAIMED]', '[TOTAL UNITS ALLOWED]',
    '[FEES UNITS SUBTOTAL CLAIMED]', '[FEES UNITS SUBTOTAL ALLOWED]',
    '[SCHED1 NO.]', '[SCHED1 DESCRIPTION]', '[SCHED1 CLAIMED]', '[SCHED1 ALLOWED]',
    '[FEES SUBTOTAL CLAIMED]', '[FEES SUBTOTAL ALLOWED]',
    '[FEES TAXES CLAIMED]', '[FEES TAXES ALLOWED]',
    '[FEES TOTAL CLAIMED]', '[FEES TOTAL ALLOWED]',
    # Notes
    '[NOTES]', '[NOTES FOOTER]',
    # Disbursement tables
    '[DISB DATE]', '[DISB DESCRIPTION]', '[DISB AMOUNT]', '[DISB GST]',
    '[DISB CLAIMED]', '[DISB ALLOWED]',
    '[DISB SUBTOTAL CLAIMED]', '[DISB SUBTOTAL ALLOWED]',
    # Summary of Disbursements table
    '[SUMMARY CLAIMED]', '[SUMMARY ALLOWED]',
    '[SUMMARY SUBTOTAL CLAIMED]', '[SUMMARY SUBTOTAL ALLOWED]',
    '[SUMMARY TAXES CLAIMED]', '[SUMMARY TAXES ALLOWED]',
    '[SUMMARY TOTAL CLAIMED]', '[SUMMARY TOTAL ALLOWED]',
    # Total Bill of Costs table
    '[BOC TOTAL CLAIMED]', '[BOC TOTAL ALLOWED]',
}

MC_IGNORABLE_RX = re.compile(rb'mc:Ignorable="([^"]*)"')
XMLNS_RX = re.compile(rb'xmlns:([a-zA-Z0-9]+)=')


def pandoc_plain(docx: Path) -> str:
    """Run pandoc with explicit UTF-8 encoding to avoid Windows cp1252 bug."""
    cmd = ['pandoc', '--track-changes=all', str(docx), '-t', 'plain']
    # pandoc doesn't recognise .dotx — tell it explicitly
    if docx.suffix.lower() == '.dotx':
        cmd.insert(1, '-f')
        cmd.insert(2, 'docx')
    result = subprocess.run(
        cmd, capture_output=True, check=True,
        encoding='utf-8', errors='replace',
    )
    return result.stdout


def check_mc_ignorable(docx_path: Path) -> list[str]:
    warns = []
    with zipfile.ZipFile(docx_path) as z:
        for name in z.namelist():
            if not name.endswith('.xml'):
                continue
            data = z.read(name)
            for m in MC_IGNORABLE_RX.finditer(data):
                lt = data.rfind(b'<', 0, m.start())
                gt = data.find(b'>', m.start())
                if lt < 0 or gt < 0:
                    continue
                elem = data[lt:gt + 1]
                declared = {p.decode() for p in XMLNS_RX.findall(elem)}
                ignorable = m.group(1).decode().split()
                missing = [p for p in ignorable if p not in declared]
                if missing:
                    warns.append(
                        f"{name}: mc:Ignorable references undeclared "
                        f"prefixes {missing} (T13)")
    return warns


def check_filled(text: str) -> list[str]:
    warns = []
    for m in PLACEHOLDER_RX.finditer(text):
        ph = m.group()
        if ph in LEAVE_BLANK:
            continue
        warns.append(f"residual placeholder {ph!r}")
    if '\u200b' in text:
        warns.append("ZWSP present in output")
    return warns


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1])
    reference = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    print(f"=== {target.name} --- structural checks ===")
    structural = check_mc_ignorable(target)
    if structural:
        for w in structural:
            print(f"  WARN: {w}")
    else:
        print("  OK")

    print(f"=== {target.name} --- reference-free checks ===")
    print(f"  leave-blank set: {sorted(LEAVE_BLANK)}")
    ft = pandoc_plain(target)
    warns = check_filled(ft)
    if warns:
        for w in warns:
            print(f"  WARN: {w}")
    else:
        print("  OK")

    if reference:
        rt = pandoc_plain(reference)
        import difflib
        diff = list(difflib.unified_diff(
            rt.splitlines(), ft.splitlines(),
            fromfile=reference.name, tofile=target.name, lineterm=''))
        print(f"\n=== Diff vs {reference.name} ===")
        if diff:
            for line in diff[:200]:
                print(line)
        else:
            print("  identical")
    return 0

if __name__ == '__main__':
    sys.exit(main())
