"""nt.inspect_tmpl -- Inspect raw LEAP export.

Examines a raw LEAP-exported .docx to extract its SDT alias inventory
and bracket-placeholder inventory. Presents findings for the user.

IMPORTANT: This file is named inspect_tmpl.py, NOT inspect.py.
inspect.py shadows stdlib inspect, breaking lxml imports.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

max_retries = 2

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["step_result", "ask_user"]},
        "data": {
            "type": "object",
            "properties": {
                "sdt_aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "existing_placeholders": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "form_key": {"type": "string"},
                "raw_docx_path": {"type": "string"},
                "summary": {"type": "string"},
            },
        },
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind"],
}


def _extract_sdt_inventory(docx_path: str) -> tuple[list[str], list[str]]:
    """Extract SDT aliases and bracket placeholders from a .docx.

    Returns (sdt_aliases, existing_placeholders).
    Uses stdlib zipfile + basic XML parsing to avoid lxml dependency
    in the step module (lxml is used by convert.py at runtime).
    """
    import re
    from xml.etree import ElementTree as ET

    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

    aliases = []
    placeholders = []

    try:
        with zipfile.ZipFile(docx_path) as z:
            for name in z.namelist():
                if not name.endswith('.xml'):
                    continue
                if not (name.startswith('word/') and
                        (name.endswith('document.xml') or
                         name.startswith('word/header') or
                         name.startswith('word/footer'))):
                    continue

                root = ET.fromstring(z.read(name))

                # SDT aliases
                for sdt in root.iter(f'{{{W}}}sdt'):
                    pr = sdt.find(f'{{{W}}}sdtPr')
                    if pr is not None:
                        alias = pr.find(f'{{{W}}}alias')
                        if alias is not None:
                            a = alias.get(f'{{{W}}}val')
                            if a:
                                aliases.append(a)
                            else:
                                aliases.append('(no val)')
                        else:
                            aliases.append('(no alias)')

                # Bracket placeholders
                for t in root.iter(f'{{{W}}}t'):
                    if t.text:
                        for m in re.finditer(r'\[[^\]]{1,60}\]', t.text):
                            placeholders.append(m.group())

    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        pass

    return aliases, placeholders


def precondition(ctx: dict) -> tuple[bool, str]:
    return True, ""


def build_prompt(ctx: dict) -> str:
    answers = ctx.get("step_answers", [])
    raw_path = ctx.get("raw_docx_path")

    # State 1: Need the raw .docx path
    if not raw_path:
        user_req = ctx.get("user_request", "")
        # Check answers for a path
        if answers and answers[-1] and answers[-1].strip():
            candidate = answers[-1].strip().strip('"').strip("'")
            if candidate.endswith((".docx", ".dotx")):
                if Path(candidate).exists():
                    raw_path = candidate
                    ctx["raw_docx_path"] = candidate
                else:
                    return f"""You are a template inspection agent.

The path provided does not exist: "{candidate}"

Return:
{{"kind": "ask_user", "question": "The file '{candidate}' was not found. Please provide the correct path to the raw LEAP-exported .docx.", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

        if not raw_path:
            # Try extracting from user_request
            import re
            match = re.search(r'["\']?([^"\']+\.docx)["\']?', user_req)
            if match and Path(match.group(1)).exists():
                raw_path = match.group(1)
                ctx["raw_docx_path"] = raw_path
            else:
                return """You are a template inspection agent for a BC Supreme Court form drafting system.

The user wants to convert a raw LEAP-exported document into a bracket-placeholder template. You need the path to the raw export.

Return:
{"kind": "ask_user", "question": "Please provide the path to the raw LEAP-exported .docx file you want to convert into a template.", "options": []}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # State 2: Have path, extract and present inventory
    aliases, placeholders = _extract_sdt_inventory(raw_path)

    alias_list = "\n".join(f"  - {a}" for a in aliases) if aliases else "  (none)"
    ph_list = "\n".join(f"  - {p}" for p in sorted(set(placeholders))) if placeholders else "  (none)"

    # Also check if we need the form key
    form_key = ctx.get("form_key")
    if not form_key:
        if answers and answers[-1] and answers[-1].strip():
            last = answers[-1].strip().lower()
            # Don't treat file paths as form keys
            if not last.endswith((".docx", ".dotx")):
                ctx["form_key"] = last
                form_key = last

    if not form_key:
        return f"""You are a template inspection agent.

Here is the SDT and placeholder inventory from the raw LEAP export:

## Raw Document
{raw_path}

## SDT Aliases Found ({len(aliases)})
{alias_list}

## Existing Bracket Placeholders ({len(set(placeholders))})
{ph_list}

The user needs to provide a short form key for FORM_CONFIGS (e.g., "noa", "petition", "otsc").

Return:
{{"kind": "ask_user", "question": "I found {len(aliases)} SDT aliases and {len(set(placeholders))} unique bracket placeholders in the raw export.\\n\\nSDT aliases:\\n{alias_list}\\n\\nPlaceholders:\\n{ph_list}\\n\\nWhat short key should I use for this form in FORM_CONFIGS? (e.g., 'noa', 'petition', 'affidavit')", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # State 3: Have everything -- return inspection results
    return f"""You are a template inspection agent.

All inspection data has been collected. Return the results.

## Inspection Results
- Raw document: {raw_path}
- Form key: {form_key}
- SDT aliases: {json.dumps(aliases)}
- Existing placeholders: {json.dumps(sorted(set(placeholders)))}

Return:
{{"kind": "step_result", "data": {{"sdt_aliases": {json.dumps(aliases)}, "existing_placeholders": {json.dumps(sorted(set(placeholders)))}, "form_key": "{form_key}", "raw_docx_path": "{raw_path}", "summary": "Found {len(aliases)} SDT aliases and {len(set(placeholders))} unique placeholders."}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if "sdt_aliases" not in result:
        return False, "Result must include 'sdt_aliases'"
    if "form_key" not in result or not result["form_key"]:
        return False, "Result must include non-empty 'form_key'"
    if "raw_docx_path" not in result or not result["raw_docx_path"]:
        return False, "Result must include 'raw_docx_path'"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["sdt_aliases"] = result["sdt_aliases"]
    ctx["existing_placeholders"] = result.get("existing_placeholders", [])
    ctx["form_key"] = result["form_key"]
    ctx["raw_docx_path"] = result["raw_docx_path"]
    return ctx
