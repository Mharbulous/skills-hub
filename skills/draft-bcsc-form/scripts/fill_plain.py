"""Fill a bracket-placeholder template with matter profile and body content.

Usage:
    python fill_plain.py --context context.json --body body.txt --out output.docx

Default template:
    .agents/skills/draft-bcsc-form/templates/032-noa.docx
"""
from __future__ import annotations
import argparse
import copy
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent            # scripts/
SKILL_ROOT = HERE.parent                           # draft-bcsc-form/
TEMPLATE = SKILL_ROOT / 'templates' / '032-noa.docx'

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XMLSPACE = '{http://www.w3.org/XML/1998/namespace}space'


def WN(tag: str) -> str:
    return f'{{{W}}}{tag}'


# Placeholders that must survive into the output unchanged.
LEAVE_BLANK = {
    '[mmmm d, yyyy]', '[number]', '[judge-date]',
    # Affidavit interpreter endorsement (Rule 22-2(7)) — filled only when needed
    '[name]', '[address]', '[occupation]', '[language(s)]',
    # Firm details — optional, filled by lawyer in Word if needed
    '[FIRM ADDRESS]', '[FIRM EMAIL]', '[FIRM FAX]',
    # NOCC appendix — optional fields the lawyer fills in Word
    '[CONCISE SUMMARY]', '[OTHER ENACTMENT]',
}

# Per-form markers that identify Part body instruction paragraphs (matched by startswith).
FORM_PART_MARKERS: dict[str, dict[str, str]] = {
    'noa': {
        'part1': '[Using numbered paragraphs, set out the order(s)',
        'part2': '[Using numbered paragraphs, set out a brief summary',
        'part3': '[Using paragraphs numbered sequentially from Part 2',
        'part4': '[Using numbered paragraphs, list the affidavits',
    },
    'nocc': {
        'part1': '[Set out the material facts giving rise to the claim',
        'part2': '[Set out the specific relief claimed',
        'part3': '[Set out the legal basis for the relief claimed',
    },
    'petition': {
        'part1': '[Using numbered paragraphs, set out the order(s)',
        'part2': '[Using numbered paragraphs, set out the material facts',
        'part3': '[Using paragraphs numbered sequentially from Part 2',
    },
    'rtc': {
        'part1': '[Using paragraphs numbered sequentially from Division 1',
        'part2': '[Using paragraphs numbered sequentially from Division 2',
        'part3': '[Using paragraphs numbered sequentially from Part 1',
    },
}

# Marker for the Part 2 citation instruction paragraph (NOA-only, separate,
# unnumbered, pStyle="Citation").  Removed when Part 2 content is inserted.
PART2_CITATION_MARKER = '[Include pinpoint citation'


# ---------------------------------------------------------------------------
# Substitution maps
# ---------------------------------------------------------------------------

def _subs_if_present(ctx: dict, mappings: dict[str, str]) -> dict[str, str]:
    """Build substitution map, only including keys present in ctx."""
    return {placeholder: ctx[key] for placeholder, key in mappings.items()
            if key in ctx and ctx[key]}


# Per-form placeholder → context-key mappings.
# Only placeholders that actually appear in each .dotx template are listed.

_COMMON = {
    '[COURT FILE NUMBER]': 'court_file_number',
    '[REGISTRY]': 'registry',
    '[LAWYER NAME]': 'lawyer_name',
}

_STANDARD_PARTIES = {
    '[PLAINTIFF / PETITIONER NAME(S)]': 'plaintiff_caption',
    '[PLAINTIFF]': 'plaintiff_role',
    '[DEFENDANT / RESPONDENT NAME(S)]': 'defendant_caption',
    '[DEFENDANT]': 'defendant_role',
}

_COURT_ADDRESS = {
    # em-dash U+2014 is the actual character in the template XML
    '[COURT ADDRESS \u2014 e.g. 800 Smithe Street, Vancouver, BC V6Z 2E1]': 'court_location',
}

_FIRM = {
    '[FIRM ADDRESS]': 'firm_address',
    '[FIRM EMAIL]': 'firm_email',
    '[FIRM FAX]': 'firm_fax',
}


def build_subs(ctx: dict) -> dict[str, str]:
    """NOA (Form 32) substitutions."""
    return {
        **_subs_if_present(ctx, {**_COMMON, **_STANDARD_PARTIES, **_COURT_ADDRESS}),
        '[APPLICANT NAME(S)]': ctx['applicant_names'],
        '[TO AFFECTED PARTIES]': ctx['to_affected_parties'],
        '[date]': ctx['hearing_date'],
        '[time]': ctx['hearing_time'],
        '[AM/PM]': ctx['am_pm'],
        '[hour(s)]': ctx['duration_hours'],
        '[minute(s)]': ctx['duration_minutes'],
        '[CLIENT NAME]': ctx.get('client_name', ''),
    }


def build_subs_nocc(ctx: dict) -> dict[str, str]:
    """NOCC (Form 1) substitutions."""
    return _subs_if_present(ctx, {
        **_COMMON, **_COURT_ADDRESS, **_FIRM,
        '[PLAINTIFF NAME(S)]': 'plaintiff_caption',
        '[DEFENDANT NAME(S)]': 'defendant_caption',
    })


def build_subs_rtc(ctx: dict) -> dict[str, str]:
    """Response to Counterclaim (Form 4) substitutions."""
    return _subs_if_present(ctx, {
        **_COMMON, **_STANDARD_PARTIES, **_FIRM,
        '[CLIENT NAME]': 'client_name',
        '[RESPONDING PARTY NAME(S)]': 'defendant_caption',
    })


def build_subs_petition(ctx: dict) -> dict[str, str]:
    """Petition (Form 66) substitutions."""
    return _subs_if_present(ctx, {
        **_COMMON, **_COURT_ADDRESS,
        '[PETITIONER NAME(S)]': 'plaintiff_caption',
        '[PETITIONER]': 'plaintiff_role',
        '[RESPONDENT NAME(S)]': 'defendant_caption',
        '[RESPONDENT]': 'defendant_role',
        '[CLIENT NAME]': 'client_name',
        '[CLIENT ADDRESS]': 'client_address',
        '[CLIENT EMAIL]': 'client_email',
        '[CLIENT FAX]': 'client_fax',
        '[LAWYER DETAILS]': 'lawyer_details',
        '[RESPONDENT NAME AND ADDRESS]': 'respondent_name_and_address',
        '[PROCEEDING BROUGHT BY]': 'proceeding_brought_by',
    })


def build_subs_otsc(ctx: dict) -> dict[str, str]:
    """Offer to Settle Costs (Form 123) substitutions."""
    return _subs_if_present(ctx, {
        **_COMMON, **_STANDARD_PARTIES,
        '[CLIENT NAME]': 'client_name',
        '[PARTY(IES)]': 'parties_description',
    })


def build_subs_affidavit(ctx: dict) -> dict[str, str]:
    return {
        '[COURT FILE NUMBER]':              ctx['court_file_number'],
        '[REGISTRY]':                       ctx['registry'],
        '[PLAINTIFF / PETITIONER NAME(S)]': ctx['plaintiff_caption'],
        '[PLAINTIFF]':                      ctx['plaintiff_role'],
        '[DEFENDANT / RESPONDENT NAME(S)]': ctx['defendant_caption'],
        '[DEFENDANT]':                      ctx['defendant_role'],
        '[DEPONENT NAME]':                  ctx['deponent_name'],
        '[DEPONENT ADDRESS]':               ctx['deponent_address'],
        '[DEPONENT OCCUPATION]':            ctx.get('deponent_occupation', ''),
        '[swear or affirm]':                ctx['swear_or_affirm'],
        '[SWORN OR AFFIRMED]':              ctx['sworn_or_affirmed'],
        '[date]':                           ctx['affidavit_date'],
        '[COMMISSIONER CITY]':              ctx['commissioner_city'],
        '[COMMISSIONER NAME]':              ctx.get('commissioner_name', ''),
    }


# ---------------------------------------------------------------------------
# Phase 1: merge split-run placeholders
# ---------------------------------------------------------------------------

def merge_split_run_placeholders(para: etree._Element) -> None:
    """Collapse `[` + italic-content + `]` three-run sequences into one run.

    Pattern (confirmed by template inspection):
        <w:r><w:t>[</w:t></w:r>
        <w:r><w:rPr><w:i/></w:rPr><w:t>label</w:t></w:r>
        <w:r><w:t>]</w:t></w:r>

    After merge, the first run carries `[label]` and the other two are removed.
    Mutates para in place; loops until no more merges are possible.
    """
    while True:
        runs = [c for c in para if c.tag == WN('r')]
        merged = False
        for i in range(len(runs) - 2):
            r0, r1, r2 = runs[i], runs[i + 1], runs[i + 2]
            t0 = r0.find(WN('t'))
            t1 = r1.find(WN('t'))
            t2 = r2.find(WN('t'))
            if t0 is None or t1 is None or t2 is None:
                continue
            if t0.text != '[' or t2.text != ']':
                continue
            rpr1 = r1.find(WN('rPr'))
            if rpr1 is None or rpr1.find(WN('i')) is None:
                continue
            # Merge
            t0.text = f'[{t1.text}]'
            para.remove(r1)
            para.remove(r2)
            merged = True
            break  # restart after tree mutation
        if not merged:
            break


# ---------------------------------------------------------------------------
# Phase 2: scalar substitution
# ---------------------------------------------------------------------------

def substitute_text(body: etree._Element, subs: dict[str, str]) -> None:
    """Walk all <w:t> elements; substitute those in subs that are not in LEAVE_BLANK."""
    for t_el in body.iter(WN('t')):
        if not t_el.text:
            continue
        if t_el.text in LEAVE_BLANK:
            continue
        if t_el.text in subs:
            t_el.text = subs[t_el.text]
            if t_el.text != t_el.text.strip():
                t_el.set(XMLSPACE, 'preserve')


# ---------------------------------------------------------------------------
# Phase 3: Part body replacement
# ---------------------------------------------------------------------------

def _para_text(para: etree._Element) -> str:
    return ''.join(t.text or '' for t in para.iter(WN('t')))


def _make_numbered_para(template_para: etree._Element, text: str) -> etree._Element:
    """Clone template_para's <w:pPr> (keeping numPr) and set new text content."""
    new_p = etree.Element(WN('p'))
    ppr = template_para.find(WN('pPr'))
    if ppr is not None:
        new_p.append(copy.deepcopy(ppr))
    run = etree.SubElement(new_p, WN('r'))
    t = etree.SubElement(run, WN('t'))
    t.text = text
    if text != text.strip():
        t.set(XMLSPACE, 'preserve')
    return new_p


def _make_citation_para(citation_template: etree._Element, text: str) -> etree._Element:
    """Create an unnumbered paragraph with pStyle="Citation" for evidence citations.

    Clones the pPr from *citation_template* (the template's citation instruction
    paragraph, which carries pStyle="Citation" and no numPr).
    """
    new_p = etree.Element(WN('p'))
    ppr = citation_template.find(WN('pPr'))
    if ppr is not None:
        new_p.append(copy.deepcopy(ppr))
    run = etree.SubElement(new_p, WN('r'))
    t = etree.SubElement(run, WN('t'))
    t.text = text
    if text != text.strip():
        t.set(XMLSPACE, 'preserve')
    return new_p


def replace_part_bodies(body: etree._Element, parts: dict[str, list[str]],
                        form: str = 'noa') -> None:
    """Replace Part instruction paragraphs with user-supplied content paragraphs.

    For each Part:
    - Locate the instruction paragraph by startswith marker
    - Clone its <w:pPr> (which carries numPr) as the template for new paragraphs
    - Remove instruction paragraph (and for Part 4, also the affidavit template line)
    - Insert one new <w:p> per user-supplied line at the same position

    Parts 2 and 3 both carry numId=2 in the template, so Word numbers them
    sequentially across both parts automatically (BC court requirement).

    Part 2 citation handling (NOA only):
    - The template has a separate citation instruction paragraph (pStyle="Citation")
      after the Part 2 instruction.  When Part 2 content is inserted, the citation
      instruction is removed and its pPr is used as the template for ``> `` prefixed
      citation lines in the body text.
    """
    part_markers = FORM_PART_MARKERS.get(form, {})
    if not part_markers:
        return

    # Pre-scan: find and save the Part 2 citation instruction paragraph (NOA only)
    citation_template_para = None
    if form == 'noa':
        for para in body:
            if _para_text(para).startswith(PART2_CITATION_MARKER):
                citation_template_para = para
                break

    for part_key, marker in part_markers.items():
        content_lines = parts.get(part_key, [])
        # Scan current body children each time (indices shift after mutations)
        body_children = list(body)
        instruction_para = None
        instruction_idx = None
        for i, para in enumerate(body_children):
            if _para_text(para).startswith(marker):
                instruction_para = para
                instruction_idx = i
                break
        if instruction_para is None:
            if content_lines:
                print(
                    f"WARNING: no instruction paragraph found for {part_key} "
                    f"(marker: {marker!r}). User content for this part was NOT inserted.",
                    file=sys.stderr,
                )
            continue

        # For Part 4, the next sibling is the affidavit template line (numId=3).
        # Use that as the numPr template and remove it too.
        affidavit_template = None
        if part_key == 'part4':
            next_siblings = list(body)[instruction_idx + 1:]
            for sib in next_siblings:
                sib_text = _para_text(sib)
                if 'Affidavit #' in sib_text:
                    affidavit_template = sib
                    break

        num_template = affidavit_template if affidavit_template is not None else instruction_para

        # Remove instruction and (for Part 4) affidavit template
        insert_idx = list(body).index(instruction_para)
        body.remove(instruction_para)
        if affidavit_template is not None:
            body.remove(affidavit_template)

        # For Part 2: also remove the citation instruction paragraph
        if part_key == 'part2' and citation_template_para is not None and content_lines:
            try:
                body.remove(citation_template_para)
            except ValueError:
                pass  # already removed or not found

        # Insert user paragraphs
        for j, line in enumerate(content_lines):
            if line.startswith('> ') and citation_template_para is not None:
                new_p = _make_citation_para(citation_template_para, line[2:])
            else:
                new_p = _make_numbered_para(num_template, line)
            body.insert(insert_idx + j, new_p)


# ---------------------------------------------------------------------------
# Body paste parser
# ---------------------------------------------------------------------------

def parse_body(body_text: str) -> dict[str, list[str]]:
    """Parse === PART N: TITLE === paste format into lists of paragraph strings."""
    parts: dict[str, list[str]] = {}
    current_part: str | None = None
    current_lines: list[str] = []

    for raw_line in body_text.splitlines():
        line = raw_line.strip()
        # Normalize smart quotes
        line = (line
                .replace('‘', "'").replace('’', "'")
                .replace('“', '"').replace('”', '"'))

        m = re.match(r'^===\s*PART\s+(\d+)', line, re.IGNORECASE)
        if m:
            if current_part is not None:
                parts[f'part{current_part}'] = current_lines
            current_part = m.group(1)
            current_lines = []
            continue

        if current_part is None or not line:
            continue

        # Part 4: strip "- " list prefix
        if current_part == '4' and line.startswith('- '):
            line = line[2:]

        current_lines.append(line)

    if current_part is not None:
        parts[f'part{current_part}'] = current_lines

    return parts


# ---------------------------------------------------------------------------
# Affidavit-only post-processing
# ---------------------------------------------------------------------------

def _clear_footers(members: dict[str, bytes]) -> None:
    """Remove all runs (text + field codes) from every footer in the document.

    Strips LEAP "Last updated [date]" text and page-number fldChar/instrText
    fields from footer1.xml, footer2.xml, footer3.xml (whichever are present).
    """
    footer_names = [n for n in members if re.match(r'word/footer\d+\.xml$', n)]
    for fname in footer_names:
        try:
            root = etree.fromstring(members[fname])
        except etree.XMLSyntaxError:
            continue
        for para in root.iter(WN('p')):
            for run in list(para.findall(WN('r'))):
                para.remove(run)
        members[fname] = etree.tostring(
            root, xml_declaration=True, encoding='UTF-8', standalone=True)


def _inject_keep_next_before_jurat(body: etree._Element) -> None:
    """Add <w:keepNext/> to the last LEAPBCParaNumL* paragraph before the jurat table.

    Ensures at least one numbered paragraph appears on the signature page when
    the jurat falls near a page break.
    """
    children = list(body)

    # Locate the last <w:tbl> in the body (= the jurat signature block)
    jurat_idx = None
    for i, child in enumerate(children):
        if child.tag == WN('tbl'):
            jurat_idx = i  # keep updating — last table is the jurat

    if jurat_idx is None:
        return

    # Walk backwards from the jurat to find the last numbered paragraph
    target_para = None
    for i in range(jurat_idx - 1, -1, -1):
        child = children[i]
        if child.tag != WN('p'):
            continue
        ppr = child.find(WN('pPr'))
        if ppr is None:
            continue
        pstyle = ppr.find(WN('pStyle'))
        if pstyle is None:
            continue
        if pstyle.get(WN('val'), '').startswith('LEAPBCParaNumL'):
            target_para = child
            break

    if target_para is None:
        return

    ppr = target_para.find(WN('pPr'))
    if ppr is None:
        ppr = etree.Element(WN('pPr'))
        target_para.insert(0, ppr)

    if ppr.find(WN('keepNext')) is None:
        kn = etree.Element(WN('keepNext'))
        pstyle = ppr.find(WN('pStyle'))
        if pstyle is not None:
            pstyle.addnext(kn)
        else:
            ppr.insert(0, kn)


def _remove_interpreter_endorsement(body: etree._Element) -> None:
    """Remove the interpreter endorsement section after the jurat table.

    Deletes all elements between the last <w:tbl> (jurat) and <w:sectPr>,
    leaving only the jurat and the section properties.
    """
    children = list(body)

    # Find the last <w:tbl>
    jurat_idx = None
    for i, child in enumerate(children):
        if child.tag == WN('tbl'):
            jurat_idx = i

    if jurat_idx is None:
        return

    # Remove everything after the jurat that isn't sectPr
    for child in children[jurat_idx + 1:]:
        if child.tag == WN('sectPr'):
            break
        body.remove(child)


# ---------------------------------------------------------------------------
# Content-type rewrite
# ---------------------------------------------------------------------------

def rewrite_content_types(members: dict[str, bytes]) -> None:
    ct = members['[Content_Types].xml'].decode('utf-8')
    ct = ct.replace(
        'ContentType="application/vnd.openxmlformats-officedocument'
        '.wordprocessingml.template.main+xml"',
        'ContentType="application/vnd.openxmlformats-officedocument'
        '.wordprocessingml.document.main+xml"',
    )
    members['[Content_Types].xml'] = ct.encode('utf-8')


# ---------------------------------------------------------------------------
# Main fill routine
# ---------------------------------------------------------------------------

def fill(template_path: Path, context: dict, body_text: str, out_path: Path,
         form: str = 'noa') -> None:
    with zipfile.ZipFile(template_path) as zin:
        members = {n: zin.read(n) for n in zin.namelist()}

    root = etree.fromstring(members['word/document.xml'])
    body = root.find(WN('body'))

    _SUBS_BUILDERS = {
        'noa':       build_subs,
        'nocc':      build_subs_nocc,
        'rtc':       build_subs_rtc,
        'petition':  build_subs_petition,
        'otsc':      build_subs_otsc,
        'affidavit': build_subs_affidavit,
    }
    subs = _SUBS_BUILDERS[form](context)

    # Phase 1: merge split-run placeholders before text substitution
    for para in body.iter(WN('p')):
        merge_split_run_placeholders(para)

    # Phase 2: substitute scalars
    substitute_text(body, subs)

    # Phase 3: replace Part instruction paragraphs with user content
    # When no body text is provided (Generate form mode), instruction text is preserved.
    if body_text:
        parts = parse_body(body_text)
        replace_part_bodies(body, parts, form=form)

    # Phase 4: affidavit-only post-processing
    if form == 'affidavit':
        _clear_footers(members)
        _inject_keep_next_before_jurat(body)
        interpreter = context.get('interpreter_required', 'no')
        if str(interpreter).strip().lower() not in ('yes', 'true', '1'):
            _remove_interpreter_endorsement(body)

    members['word/document.xml'] = etree.tostring(
        root, xml_declaration=True, encoding='UTF-8', standalone=True)

    rewrite_content_types(members)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in members.items():
            zout.writestr(name, data)

    print(f"Written: {out_path}")


def main() -> int:
    p = argparse.ArgumentParser(description='Fill a bracket-placeholder .dotx with matter data.')
    p.add_argument('--context',  required=True, help='Path to JSON matter context file')
    p.add_argument('--body',     default=None, help='Path to body paste text file (omit to keep instruction text)')
    p.add_argument('--out',      required=True, help='Output .docx path')
    p.add_argument('--template', default=None,
                   help='Path to template (default: templates/032-noa.docx)')
    p.add_argument('--form', default='noa',
                   help='Form type: noa, affidavit, petition, nocc, otsc, rtc (default: noa)')
    args = p.parse_args()

    template_path = Path(args.template) if args.template else TEMPLATE

    with open(args.context, encoding='utf-8') as f:
        context = json.load(f)
    body_text = ''
    if args.body:
        with open(args.body, encoding='utf-8') as f:
            body_text = f.read()

    fill(template_path, context, body_text, Path(args.out), form=args.form)
    return 0


if __name__ == '__main__':
    sys.exit(main())
