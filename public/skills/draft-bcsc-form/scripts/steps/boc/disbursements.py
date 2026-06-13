"""boc.disbursements -- BOC Step 5: Disbursement review.

If CSV was processed: parses disbursement-processor report, resolves
flagged items via ask_user, writes to data file.
If no CSV: builds disbursements through conversation (ask_user sub-loop).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent.parent
SKILL_ROOT = SCRIPTS_DIR.parent
SESSIONS_DIR = SKILL_ROOT / "scripts" / "sessions"

max_retries = 3

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
    handle = ctx.get("disbursement_processor_handle", {})
    if not handle.get("done"):
        return False, ("boc.disbursements requires disbursement-processor "
                       "subagent to complete first (or no CSV to process).")
    return True, ""


def build_prompt(ctx: dict) -> str:
    answers = ctx.get("step_answers", [])
    has_csv = ctx.get("has_csv", False)
    dp_result = ctx.get("disbursement_processor_handle", {}).get("result")

    if has_csv and dp_result:
        # CSV was processed -- resolve flagged items
        disb_data = dp_result.get("disbursements", [])
        flagged = dp_result.get("flagged", [])
        num_answered = sum(1 for a in answers if a is not None)

        # Find next unresolved flagged item
        unresolved_flags = flagged[num_answered:] if num_answered < len(flagged) else []

        if not unresolved_flags:
            # All flags resolved -- return final disbursements
            return f"""You are a BOC disbursement agent. All flagged items have been resolved.

Disbursement data:
{json.dumps(disb_data, indent=2)}

Flagged items and resolutions:
{json.dumps(list(zip(flagged, [a for a in answers if a is not None])), indent=2) if flagged else "None"}

Return a step_result with the finalized disbursements:
{{"kind": "step_result", "data": {{"output_path": "{str(SESSIONS_DIR / ctx.get("session_id", "default"))}/boc.disbursements_output.json"}}}}

Write the output file containing:
{{
    "disbursements": <finalized array with flags resolved>,
    "disb_total": <total amount>
}}

## Constraints
- Return ONLY the JSON after writing the output file. Do not call Read, Bash, Grep, Glob, or any file-access tools other than writing the output file."""

        flag = unresolved_flags[0]
        flag_idx = flag.get("index", 0)
        flag_reason = flag.get("reason", "Unknown reason")
        item = disb_data[flag_idx] if flag_idx < len(disb_data) else {}

        return f"""You are a BOC disbursement agent. A flagged item needs resolution.

Flagged item:
  Description: {item.get('description', 'Unknown')}
  Amount: ${item.get('claimed', '0.00')}
  Reason flagged: {flag_reason}

Return an ask_user request:
{{"kind": "ask_user", "question": "Flagged disbursement: {item.get('description', 'Unknown')} (${item.get('claimed', '0.00')})\\nReason: {flag_reason}\\n\\nWhat would you like to do?", "options": ["Include as-is", "Exclude this item", "Modify the amount"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    else:
        # No CSV -- manual entry via conversation
        num_answered = sum(1 for a in answers if a is not None)

        # Common disbursement prompts
        common_items = [
            "Filing fees (court filing fees, registry fees)",
            "Process server fees",
            "Transcript fees (examination, trial)",
            "Expert report fees",
            "Photocopying / printing",
            "Mediation fees",
            "Court search fees",
            "Sheriff fees",
        ]

        if num_answered == 0:
            return f"""You are a BOC disbursement agent. No disbursement CSV was provided.
Build the disbursement schedule through conversation.

Ask the user about the first common disbursement category.

Return: {{"kind": "ask_user", "question": "Let's build your disbursement schedule. Do you have any filing fees to claim? (court filing fees, registry fees)\\n\\nFor each disbursement, please provide the description and amount.", "options": ["Yes - I have filing fees", "No filing fees"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

        if num_answered < len(common_items):
            current_item = common_items[num_answered]
            return f"""You are a BOC disbursement agent. Gathering disbursements manually.

Prior answers: {json.dumps([a for a in answers if a is not None], indent=2)}

Ask about the next common disbursement category: {current_item}

Return: {{"kind": "ask_user", "question": "Do you have any {current_item} to claim?", "options": ["Yes - I will provide details", "No"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

        # All common categories asked -- finalize
        return f"""You are a BOC disbursement agent. All common categories have been covered.

User responses:
{json.dumps(list(zip(common_items, [a for a in answers if a is not None])), indent=2)}

Build the disbursements array from the user's responses. Parse amounts where provided.

Write output to `{str(SESSIONS_DIR / ctx.get("session_id", "default"))}/boc.disbursements_output.json`:
{{
    "disbursements": [
        {{"description": "Filing fee - Notice of Civil Claim", "claimed": "200.00", "allowed": ""}}
    ],
    "disb_total": "<sum of all claimed amounts>"
}}

Return: {{"kind": "step_result", "data": {{"output_path": "{str(SESSIONS_DIR / ctx.get("session_id", "default"))}/boc.disbursements_output.json"}}}}

## Constraints
- Return ONLY the JSON after writing the output file. Do not call Read, Bash, Grep, Glob, or any file-access tools other than writing the output file."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    # Disk-write step: harness reads file and passes contents as result
    disb = result.get("disbursements")
    if not isinstance(disb, list):
        return False, "disbursements must be a list"
    if result.get("disb_total") is None:
        return False, "disbursements result missing disb_total"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["disbursements"] = result["disbursements"]
    ctx["disb_total"] = result.get("disb_total", "0.00")
    return ctx


def calls_script(ctx: dict) -> None:
    """Write disbursements to bill-of-costs-data.js."""
    js_path = ctx.get("boc_data_js_path")
    if not js_path:
        raise RuntimeError("calls_script: boc_data_js_path not set in ctx")
    js_path = Path(js_path)
    if not js_path.exists():
        raise RuntimeError(f"calls_script: bill-of-costs-data.js not found: {js_path}")

    raw = js_path.read_text(encoding="utf-8")
    start = raw.index("{")
    end = raw.rindex("}") + 1
    bill_data = json.loads(raw[start:end])

    bill_data["disbursements"] = ctx.get("disbursements", [])

    js_path.write_text(
        f"window.billData = {json.dumps(bill_data, indent=2)};",
        encoding="utf-8",
    )
