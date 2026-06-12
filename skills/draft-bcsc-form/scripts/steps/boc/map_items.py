"""boc.map_items -- BOC Step 3: Map MCQ answers to tariff items.

Precondition: tariff-checker subagent must be done.
Reads tariff-appendix-b.md reference, maps confirmed litigation steps
from MCQ answers to specific tariff items. Disk-write step.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent.parent.parent
TARIFF_REF = SKILL_ROOT / "forms" / "boc" / "references" / "tariff-appendix-b.md"
SESSIONS_DIR = SKILL_ROOT / "scripts" / "sessions"

max_retries = 3  # large structured output; incremental fixes expected

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
            },
        },
    },
    "required": ["kind"],
}


def precondition(ctx: dict) -> tuple[bool, str]:
    handle = ctx.get("tariff_checker_handle", {})
    if not handle.get("done"):
        return False, ("boc.map_items requires tariff-checker subagent to "
                       "complete first. Waiting for tariff verification.")
    if not ctx.get("mcq_answers"):
        return False, "boc.map_items requires mcq_answers from boc.mcq"
    return True, ""


def build_prompt(ctx: dict) -> str:
    # Read tariff reference
    tariff_text = ""
    if TARIFF_REF.exists():
        tariff_text = TARIFF_REF.read_text(encoding="utf-8")

    mcq_json = json.dumps(ctx.get("mcq_answers", []), indent=2)

    # Tariff-checker report
    tc_result = ctx.get("tariff_checker_handle", {}).get("result", {})
    tc_report = json.dumps(tc_result, indent=2) if tc_result else "No report available"

    session_dir = str(SESSIONS_DIR / ctx.get("session_id", "default"))
    output_path = f"{session_dir}/boc.map_items_output.json"

    scale = ctx.get("costs_scale", "B")
    unit_value = ctx.get("unit_value", 110)

    return f"""You are a BOC tariff mapping agent for a BC Supreme Court Bill of Costs.

## Task
Map the MCQ interview answers to specific Appendix B tariff items. For each
confirmed litigation step, identify the corresponding tariff item number,
write the description, and fill in the unit count for flat-rate items. For
range items, leave unitsClaimed empty (the lawyer will assign units in the
next step).

## Costs Scale
Scale {scale} at ${unit_value}/unit

## Tariff-Checker Report
{tc_report}

## MCQ Interview Answers
{mcq_json}

## Tariff Reference (Appendix B)
{tariff_text}

## Rules
- Fill in fixed unit counts for flat-rate items (e.g., Item 4 = 5 units,
  Item 39 = 1 unit, Item 40 = 1 unit).
- For per-day items (e.g., Item 34 = 5 units/day, Item 35 = 10 units/day),
  multiply by the number of days from the MCQ answers.
- For range items (e.g., Item 1 = 1-10 units), leave unitsClaimed as empty
  string "". These will be assigned by the lawyer.
- Only include items that are confirmed by the MCQ answers.
- Include the item number, full description, and unitsClaimed.

## Output
Write your output to `{output_path}` and return only:
{{"kind": "step_result", "data": {{"output_path": "{output_path}"}}}}

The output file should contain:
{{
  "tariff_items": [
    {{"no": "1", "description": "Correspondence, conferences... before proceeding", "unitsClaimed": ""}},
    {{"no": "6", "description": "Commencing and prosecuting a proceeding", "unitsClaimed": ""}},
    {{"no": "39", "description": "Payment into or out of court", "unitsClaimed": "1"}}
  ],
  "fixed_count": <number of items with fixed units>,
  "range_count": <number of items needing user assignment>,
  "summary": "<N tariff items mapped, M with fixed units, K range items to assign>"
}}

## Constraints
- Return ONLY the JSON object specified above after writing the output file.
- Do not call Read, Bash, Grep, Glob, or any file-access tools other than
  writing the output file."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    # For disk-write steps, the harness reads the file.
    # result here is the parsed file contents.
    items = result.get("tariff_items")
    if not isinstance(items, list):
        return False, "tariff_items must be a list"
    if len(items) == 0:
        return False, "tariff_items is empty -- at least one item expected"
    for i, item in enumerate(items):
        if "no" not in item:
            return False, f"tariff_items[{i}] missing 'no'"
        if "description" not in item:
            return False, f"tariff_items[{i}] missing 'description'"
        if "unitsClaimed" not in item:
            return False, f"tariff_items[{i}] missing 'unitsClaimed'"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    items = result["tariff_items"]
    ctx["tariff_items"] = items
    ctx["range_items"] = [it for it in items if it["unitsClaimed"] == ""]
    return ctx


def calls_script(ctx: dict) -> None:
    """Write tariff items to bill-of-costs-data.js."""
    js_path = ctx.get("boc_data_js_path")
    if not js_path:
        raise RuntimeError("calls_script: boc_data_js_path not set in ctx")
    js_path = Path(js_path)
    if not js_path.exists():
        raise RuntimeError(f"calls_script: bill-of-costs-data.js not found: {js_path}")

    # Read existing data
    raw = js_path.read_text(encoding="utf-8")
    # Parse window.billData = {...};
    start = raw.index("{")
    end = raw.rindex("}") + 1
    bill_data = json.loads(raw[start:end])

    # Update tariff items
    bill_data["tariffItems"] = [
        {
            "no": it["no"],
            "description": it["description"],
            "unitsClaimed": it["unitsClaimed"],
            "unitsAllowed": "",
        }
        for it in ctx["tariff_items"]
    ]

    js_path.write_text(
        f"window.billData = {json.dumps(bill_data, indent=2)};",
        encoding="utf-8",
    )
