"""boc.summary -- BOC Step 6: Combined summary.

Presents the complete bill of costs summary (Part 1 tariff fees + Part 2
disbursements) and asks for lawyer approval before proceeding to fill.
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent.parent.parent  # draft-bcsc-form/
SESSIONS_DIR = SKILL_ROOT / "scripts" / "sessions"

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
    if not ctx.get("tariff_items"):
        return False, "boc.summary requires tariff_items"
    if ctx.get("disbursements") is None:
        return False, "boc.summary requires disbursements from boc.disbursements"
    return True, ""


def build_prompt(ctx: dict) -> str:
    answers = ctx.get("step_answers", [])
    num_answered = sum(1 for a in answers if a is not None)

    scale = ctx.get("costs_scale", "B")
    unit_value = ctx.get("unit_value", 110)
    total_units = ctx.get("total_units", 0)
    fees_subtotal = ctx.get("fees_subtotal", 0)
    fees_gst = ctx.get("fees_gst", 0)
    fees_pst = ctx.get("fees_pst", 0)
    fees_total = ctx.get("fees_total", 0)
    disb_total_str = ctx.get("disb_total", "0.00")

    try:
        disb_total = float(str(disb_total_str).replace(",", "").replace("$", ""))
    except ValueError:
        disb_total = 0.0

    grand_total = fees_total + disb_total

    if num_answered == 0:
        # Present summary and ask for approval
        return f"""You are a BOC summary agent. Present the complete bill of costs summary.

BILL OF COSTS SUMMARY
=====================
Style of Cause: {ctx.get('style_of_cause', '')}
Court File No.: {ctx.get('court_file_number', '')}
Scale: {scale} at ${unit_value}/unit

PART 1 -- TARIFF FEES
  Total units:      {total_units}
  Fees subtotal:    ${fees_subtotal:,.2f}
  GST (5%):         ${fees_gst:,.2f}
  PST (7%):         ${fees_pst:,.2f}
  Total Part 1:     ${fees_total:,.2f}

PART 2 -- DISBURSEMENTS
  Total disbursements:  ${disb_total:,.2f}

GRAND TOTAL:  ${grand_total:,.2f}

Ask the user for approval:
{{"kind": "ask_user", "question": "BILL OF COSTS SUMMARY\\n=====================\\nStyle of Cause: {ctx.get('style_of_cause', '')}\\nCourt File No.: {ctx.get('court_file_number', '')}\\nScale: {scale} at ${unit_value}/unit\\n\\nPART 1 -- TARIFF FEES\\n  Total units: {total_units}\\n  Fees subtotal: ${fees_subtotal:,.2f}\\n  GST (5%): ${fees_gst:,.2f}\\n  PST (7%): ${fees_pst:,.2f}\\n  Total Part 1: ${fees_total:,.2f}\\n\\nPART 2 -- DISBURSEMENTS\\n  Total: ${disb_total:,.2f}\\n\\nGRAND TOTAL: ${grand_total:,.2f}\\n\\nDoes this look right? Would you like any adjustments before I convert to Word?", "options": ["Looks good - proceed to Word", "I need to make adjustments"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # User responded to approval
    user_response = answers[0] if answers and answers[0] else ""
    if "adjust" in user_response.lower() or "change" in user_response.lower():
        # User wants adjustments -- tell them to edit the form and paste back
        return f"""The user wants adjustments. Tell them to edit the HTML form and paste back.

Return: {{"kind": "ask_user", "question": "Please open the bill of costs form in your browser, make your adjustments, then click the clipboard button and paste the JSON back here. I will update the data and re-present the summary.", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Approval given -- write summary output
    session_dir = str(SESSIONS_DIR / ctx.get("session_id", "default"))
    output_path = f"{session_dir}/boc.summary_output.json"

    return f"""The user approved the summary. Write the summary output file.

Write to `{output_path}`:
{{
    "approved": true,
    "style_of_cause": "{ctx.get('style_of_cause', '')}",
    "court_file_number": "{ctx.get('court_file_number', '')}",
    "costs_scale": "{scale}",
    "unit_value": {unit_value},
    "total_units": {total_units},
    "fees_subtotal": {fees_subtotal},
    "fees_gst": {fees_gst},
    "fees_pst": {fees_pst},
    "fees_total": {fees_total},
    "disb_total": {disb_total},
    "grand_total": {grand_total}
}}

Return: {{"kind": "step_result", "data": {{"output_path": "{output_path}"}}}}

## Constraints
- Return ONLY the JSON after writing the output file. Do not call Read, Bash, Grep, Glob, or any file-access tools other than writing the output file."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if not result.get("approved"):
        return False, "Summary not approved"
    if "grand_total" not in result:
        return False, "Missing grand_total"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["boc_summary"] = result
    return ctx
