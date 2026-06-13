"""boc.units -- BOC Step 4: Two-pass unit assignment for range items.

Interactive step: iterates over range items (empty unitsClaimed),
presents 3-4 options for each, collects lawyer's choice via ask_user.
After each choice, rewrites bill-of-costs-data.js.
"""
from __future__ import annotations

import json
from pathlib import Path

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
        return False, "boc.units requires tariff_items from boc.map_items"
    if ctx.get("range_items") is None:
        return False, "boc.units requires range_items to be initialized"
    return True, ""


def build_prompt(ctx: dict) -> str:
    answers = ctx.get("step_answers", [])
    range_items = ctx.get("range_items", [])
    num_answered = sum(1 for a in answers if a is not None)

    if num_answered >= len(range_items):
        # All range items assigned -- compute totals
        # Build patched unit totals using both fixed items and step_answers for range items
        unit_value = ctx.get("unit_value", 110)
        all_items = ctx.get("tariff_items", [])
        range_items_list = ctx.get("range_items", [])

        # Map range item nos to their assigned unit counts from step_answers
        range_assignments = {}
        for i, item in enumerate(range_items_list):
            if i < len(answers) and answers[i] is not None:
                ans = str(answers[i])
                for part in ans.split():
                    try:
                        range_assignments[item["no"]] = float(part)
                        break
                    except ValueError:
                        continue

        total_units = 0
        for it in all_items:
            uc = it.get("unitsClaimed", "")
            if uc:
                try:
                    total_units += float(uc)
                except ValueError:
                    pass
            elif it.get("no") in range_assignments:
                total_units += range_assignments[it["no"]]

        subtotal = total_units * unit_value
        gst = subtotal * 0.05
        pst = subtotal * 0.07
        total = subtotal + gst + pst

        return f"""You are a BOC unit assignment agent. All range items have been assigned.

Total units: {total_units}
Unit value (Scale {ctx.get('costs_scale', 'B')}): ${unit_value:.2f}
Tariff fees subtotal: ${subtotal:,.2f}
GST (5%): ${gst:,.2f}
PST (7%): ${pst:,.2f}
Total Part 1 fees: ${total:,.2f}

Return a step_result with the computed totals:
{{"kind": "step_result", "data": {{
    "total_units": {total_units},
    "fees_subtotal": {subtotal},
    "fees_gst": {gst},
    "fees_pst": {pst},
    "fees_total": {total},
    "all_assigned": true
}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Present options for the next range item
    item = range_items[num_answered]
    item_no = item.get("no", "?")
    desc = item.get("description", "")

    return f"""You are a BOC unit assignment agent for a BC Supreme Court Bill of Costs.

## Current Item
Item {item_no} -- {desc}

This is a range item where the lawyer must choose the number of units to claim.
Generate 3-4 concrete options with reasoning, appropriate for this tariff item.
The options should span the item's range from conservative to aggressive.

Return an ask_user request:
{{"kind": "ask_user", "question": "Item {item_no} -- {desc}\\n\\nHow many units should be claimed?", "options": ["<N> units -- <brief reasoning>", "<N> units -- <brief reasoning>", "<N> units -- <brief reasoning>", "Custom number"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if "all_assigned" not in result:
        return False, "Expected all_assigned in result"
    if "total_units" not in result:
        return False, "Missing total_units"
    if "fees_subtotal" not in result:
        return False, "Missing fees_subtotal"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    # Update range items with assigned values from step_answers
    answers = ctx.get("step_answers", [])
    range_items = ctx.get("range_items", [])

    for i, item in enumerate(range_items):
        if i < len(answers) and answers[i] is not None:
            # Parse unit count from answer (e.g., "5 units -- standard work")
            ans = str(answers[i])
            # Extract leading number
            parts = ans.split()
            unit_count = ""
            for part in parts:
                try:
                    unit_count = str(int(part))
                    break
                except ValueError:
                    try:
                        unit_count = str(float(part))
                        break
                    except ValueError:
                        continue
            if unit_count:
                item["unitsClaimed"] = unit_count
                # Update in the main tariff_items list
                for ti in ctx.get("tariff_items", []):
                    if ti["no"] == item["no"]:
                        ti["unitsClaimed"] = unit_count
                        break

    ctx["fees_subtotal"] = result.get("fees_subtotal", 0)
    ctx["fees_gst"] = result.get("fees_gst", 0)
    ctx["fees_pst"] = result.get("fees_pst", 0)
    ctx["fees_total"] = result.get("fees_total", 0)
    ctx["total_units"] = result.get("total_units", 0)
    return ctx


def calls_script(ctx: dict) -> None:
    """Rewrite bill-of-costs-data.js with updated unit counts and tax totals."""
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

    bill_data["tariffItems"] = [
        {
            "no": it["no"],
            "description": it["description"],
            "unitsClaimed": it["unitsClaimed"],
            "unitsAllowed": "",
        }
        for it in ctx.get("tariff_items", [])
    ]

    bill_data["gstAmount"] = f"${ctx.get('fees_gst', 0):,.2f}"
    bill_data["pstAmount"] = f"${ctx.get('fees_pst', 0):,.2f}"

    js_path.write_text(
        f"window.billData = {json.dumps(bill_data, indent=2)};",
        encoding="utf-8",
    )
