"""boc.setup -- BOC Step 1: Set up.

Gathers initial case info (style of cause, file number, costs scale, costs
order), spawns background tariff-checker subagent, creates draft directory,
copies HTML form, writes initial bill-of-costs-data.js, and optionally spawns
disbursement-processor if CSV is available.

Interactive step: uses ask_user sub-loop for the 5 initial questions.
"""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from steps.shared.paths import workspace_output_dir

HERE = Path(__file__).resolve().parent            # steps/boc/
STEPS_DIR = HERE.parent                           # steps/
SCRIPTS_DIR = STEPS_DIR.parent                    # scripts/
SKILL_ROOT = SCRIPTS_DIR.parent                   # draft-bcsc-form/
BOC_FORMS = SKILL_ROOT / "forms" / "boc"
BOC_TEMPLATES = BOC_FORMS / "preview"
BOC_AGENTS = BOC_FORMS / "agents"

SCALE_VALUES = {"A": 60, "B": 110, "C": 170}

max_retries = 2

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["step_result", "ask_user"]},
        "data": {"type": "object"},
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind"],
}


def precondition(ctx: dict) -> tuple[bool, str]:
    if not ctx.get("form_id") == "form-62":
        return False, "boc.setup requires form_id == form-62"
    return True, ""


def build_prompt(ctx: dict) -> str:
    answers = ctx.get("step_answers", [])
    num_answers = sum(1 for a in answers if a is not None)

    if num_answers == 0:
        # First question: style of cause
        return """You are a BOC setup agent for a BC Supreme Court Bill of Costs (Form 62).

Your task is to gather initial information for the bill of costs. Ask the first question.

Ask the user for the style of cause (plaintiff v. defendant names).

Return a JSON object requesting user input:
{"kind": "ask_user", "question": "What is the style of cause? (e.g., Smith v. Jones)", "options": []}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""

    if num_answers == 1:
        return f"""You are a BOC setup agent. The user provided the style of cause: "{answers[0]}"

Ask the user for the court file number.

Return: {{"kind": "ask_user", "question": "What is the court file number?", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    if num_answers == 2:
        return f"""You are a BOC setup agent. Gathered so far:
- Style of cause: {answers[0]}
- Court file number: {answers[1]}

Ask the user for the costs scale (A, B, or C). Explain the unit values.

Return: {{"kind": "ask_user", "question": "What is the costs scale? Scale A ($60/unit) for matters of little difficulty, Scale B ($110/unit, default) for ordinary matters, or Scale C ($170/unit) for complex matters. If no scale was fixed by order, the default is Scale B.", "options": ["Scale A ($60/unit)", "Scale B ($110/unit) - default", "Scale C ($170/unit)"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    if num_answers == 3:
        return f"""You are a BOC setup agent. Gathered so far:
- Style of cause: {answers[0]}
- Court file number: {answers[1]}
- Costs scale: {answers[2]}

Ask the user for the costs order details (what the order says, date, and judge's name if known).

Return: {{"kind": "ask_user", "question": "What are the costs order details? Include what the order says, the date, and the judge's name if known. If costs are by agreement rather than order, describe the agreement.", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    if num_answers == 4:
        # Ask about disbursement CSV
        return f"""You are a BOC setup agent. Gathered so far:
- Style of cause: {answers[0]}
- Court file number: {answers[1]}
- Costs scale: {answers[2]}
- Costs order: {answers[3]}

Ask the user if they have a disbursement CSV to upload. Explain that a CSV of disbursements from their accounting system will be automatically processed.

Return: {{"kind": "ask_user", "question": "Do you have a CSV export of disbursements from your accounting system? If so, please upload it. If not, we will enter disbursements manually later.", "options": ["I have a CSV to upload", "No CSV - I will enter disbursements manually"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # All questions answered -- return step_result with gathered data
    # Parse scale from answer
    scale_answer = answers[2] if len(answers) > 2 else "B"
    scale = "B"  # default
    for s in ("A", "B", "C"):
        if f"SCALE {s}" in scale_answer.upper():
            scale = s
            break

    csv_answer = answers[4] or "" if len(answers) > 4 else ""
    has_csv = "csv" in csv_answer.lower() and "no" not in csv_answer.lower()

    return f"""You are a BOC setup agent. All initial questions have been answered:
- Style of cause: {answers[0]}
- Court file number: {answers[1]}
- Costs scale: {scale_answer} (parsed as Scale {scale})
- Costs order: {answers[3]}
- Disbursement CSV: {"Yes" if has_csv else "No"}

Return a step_result confirming the setup data:

{{"kind": "step_result", "data": {{
    "style_of_cause": "{answers[0]}",
    "court_file_number": "{answers[1]}",
    "costs_scale": "{scale}",
    "unit_value": {SCALE_VALUES.get(scale, 110)},
    "costs_order": "{answers[3]}",
    "has_csv": {str(has_csv).lower()}
}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if "style_of_cause" not in result:
        return False, "Missing style_of_cause in setup result"
    if "court_file_number" not in result:
        return False, "Missing court_file_number in setup result"
    if result.get("costs_scale") not in ("A", "B", "C"):
        return False, f"Invalid costs_scale: {result.get('costs_scale')}"
    uv = result.get("unit_value")
    if uv not in (60, 110, 170):
        return False, f"Invalid unit_value: {uv}"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["style_of_cause"] = result["style_of_cause"]
    ctx["court_file_number"] = result["court_file_number"]
    ctx["costs_scale"] = result["costs_scale"]
    ctx["unit_value"] = result["unit_value"]
    ctx["costs_order"] = result.get("costs_order", "")
    ctx["has_csv"] = result.get("has_csv", False)

    # Initialize subagent handles
    ctx["tariff_checker_handle"] = {"done": False, "result": None}
    ctx["disbursement_processor_handle"] = {
        "done": not result.get("has_csv", False),
        "result": None,
    }

    # Initialize BOC-specific ctx fields
    ctx["mcq_answers"] = []
    ctx["tariff_items"] = []
    ctx["range_items"] = []
    ctx["disbursements"] = []
    ctx["boc_summary"] = None

    return ctx


def calls_script(ctx: dict) -> None:
    """Create draft directory, copy HTML form, write initial bill-of-costs-data.js."""
    matter_path = ctx.get("matter_path", "")
    if not matter_path:
        raise RuntimeError("calls_script: matter_path not set in ctx -- BOC requires a matter path for file creation")

    today = date.today().strftime("%Y-%m-%d")
    draft_dir = workspace_output_dir(matter_path)
    draft_dir.mkdir(parents=True, exist_ok=True)

    # Copy HTML form template
    html_src = BOC_TEMPLATES / "bill-of-costs-form.html"
    html_dst = draft_dir / "bill-of-costs-form.html"
    if html_src.exists():
        if not html_dst.exists():
            shutil.copy2(html_src, html_dst)
        ctx["boc_html_path"] = str(html_dst)

    # Write initial bill-of-costs-data.js
    scale_letter = ctx.get("costs_scale", "B")
    bill_data = {
        "styleOfProceeding": ctx.get("style_of_cause", ""),
        "name": "",
        "tariffScale": f"Scale {scale_letter}",
        "unitValue": f"${ctx.get('unit_value', 110):.2f}",
        "date": today,
        "tariffItems": [
            {"no": "", "description": "", "unitsClaimed": "", "unitsAllowed": ""}
        ],
        "disbursements": [
            {"description": "", "claimed": "", "allowed": ""}
        ],
        "gstRate": 0.05,
        "pstRate": 0.07,
        "gstAmount": "$0.00",
        "pstAmount": "$0.00",
    }
    js_path = draft_dir / "bill-of-costs-data.js"
    js_path.write_text(
        f"window.billData = {json.dumps(bill_data, indent=2)};",
        encoding="utf-8",
    )
    ctx["boc_data_js_path"] = str(js_path)
