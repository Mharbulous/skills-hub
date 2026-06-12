"""boc.fill -- BOC Step 7: Convert to Word.

Re-reads bill-of-costs-data.js as source of truth (user may have edited
via the HTML form and pasted back). Builds boc_context.json conforming
to fill_boc.py's expected schema, then calls fill_boc.py.
"""
from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

from steps.shared.paths import workspace_output_dir

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent.parent  # scripts/
FILL_BOC = SCRIPTS_DIR / "fill_boc.py"
VERIFY = SCRIPTS_DIR / "verify.py"

max_retries = 2

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "boc_context": {"type": "object"},
            },
        },
    },
    "required": ["kind"],
}

# Disbursement category keys matching fill_boc.py's DISB_CATEGORY_ORDER
DISB_CATEGORIES = [
    "filing_fees", "transcripts", "expert_fees",
    "photocopying", "search_fees", "travel", "other",
]


def precondition(ctx: dict) -> tuple[bool, str]:
    if not ctx.get("boc_summary"):
        return False, "boc.fill requires approved summary from boc.summary"
    return True, ""


def _read_bill_data(ctx: dict) -> dict:
    """Re-read bill-of-costs-data.js as source of truth."""
    js_path = ctx.get("boc_data_js_path", "")
    if not js_path or not Path(js_path).exists():
        return {}
    raw = Path(js_path).read_text(encoding="utf-8")
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}


def _categorize_disbursements(flat_list: list[dict]) -> dict:
    """Group flat disbursement list into categories for fill_boc.py."""
    categorized = {k: [] for k in DISB_CATEGORIES}
    for item in flat_list:
        desc = (item.get("description", "") or "").lower()
        if any(kw in desc for kw in ("filing", "registry", "court fee")):
            categorized["filing_fees"].append(item)
        elif any(kw in desc for kw in ("transcript",)):
            categorized["transcripts"].append(item)
        elif any(kw in desc for kw in ("expert",)):
            categorized["expert_fees"].append(item)
        elif any(kw in desc for kw in ("photocop", "print", "binding")):
            categorized["photocopying"].append(item)
        elif any(kw in desc for kw in ("search", "land title", "ppsa")):
            categorized["search_fees"].append(item)
        elif any(kw in desc for kw in ("travel", "mileage", "parking")):
            categorized["travel"].append(item)
        else:
            categorized["other"].append(item)
    return categorized


def build_prompt(ctx: dict) -> str:
    # Re-read bill-of-costs-data.js as source of truth
    bill_data = _read_bill_data(ctx)
    profile = ctx.get("profile", {})

    # Extract parties from profile or ctx
    proceedings = []
    if isinstance(profile, dict):
        proceedings = profile.get("proceedings", [])

    originating_party = ""
    originating_role = ""
    responding_party = ""
    responding_role = ""
    registry = ""
    if proceedings:
        proc = proceedings[0]
        registry = proc.get("registry", "")
        parties = proc.get("parties", [])
        for p in parties:
            role = (p.get("role", "") or "").upper()
            if role in ("PLAINTIFF", "PETITIONER", "CLAIMANT"):
                originating_party = p.get("name", "")
                originating_role = role
            elif role in ("DEFENDANT", "RESPONDENT"):
                responding_party = p.get("name", "")
                responding_role = role

    tariff_items = bill_data.get("tariffItems", ctx.get("tariff_items", []))
    disbursements = bill_data.get("disbursements", ctx.get("disbursements", []))

    # Build context JSON for fill_boc.py
    # Format monetary values
    scale = ctx.get("costs_scale", "B")
    unit_value = ctx.get("unit_value", 110)
    total_units = sum(
        float(it.get("unitsClaimed", 0) or 0)
        for it in tariff_items
        if it.get("unitsClaimed")
    )
    fees_sub = total_units * unit_value
    fees_gst = fees_sub * 0.05
    fees_pst = fees_sub * 0.07
    fees_taxes = fees_gst + fees_pst
    fees_total = fees_sub + fees_taxes

    disb_total = 0.0
    for d in disbursements:
        try:
            amt = float(str(d.get("claimed", "0")).replace(",", "").replace("$", ""))
            disb_total += amt
        except ValueError:
            pass

    grand_total = fees_total + disb_total

    context_json = {
        "court_file_number": ctx.get("court_file_number", ""),
        "registry": registry,
        "originating_party": originating_party.upper(),
        "originating_party_role": originating_role,
        "responding_party": responding_party.upper(),
        "responding_party_role": responding_role,
        "party_claiming_costs": ctx.get("style_of_cause", "").split(" v.")[0].strip()
                                if " v." in ctx.get("style_of_cause", "") else "",
        "costs_scale": f"Scale {scale}",
        "unit_value": f"${unit_value:.2f}",
        "costs_order": ctx.get("costs_order", ""),
        "costs_terms": "",
        "tariff_items": [
            {
                "no": it.get("no", ""),
                "description": it.get("description", ""),
                "units_claimed": str(it.get("unitsClaimed", "")),
            }
            for it in tariff_items
            if it.get("no")
        ],
        "total_units": str(total_units),
        "fees_subtotal": f"${fees_sub:,.2f}",
        "fees_gst": f"${fees_gst:,.2f}",
        "fees_pst": f"${fees_pst:,.2f}",
        "fees_taxes": f"${fees_taxes:,.2f}",
        "fees_total": f"${fees_total:,.2f}",
        "disbursements": _categorize_disbursements(disbursements),
        "disb_subtotals": {},  # will be computed below
        "disb_total": f"${disb_total:,.2f}",
        "grand_total": f"${grand_total:,.2f}",
        "notes": "",
        "notes_footer": "",
    }

    # Compute disbursement subtotals per category
    for cat_key, items in context_json["disbursements"].items():
        cat_total = 0.0
        for item in items:
            try:
                amt = float(
                    str(item.get("claimed", "0")).replace(",", "").replace("$", "")
                )
                cat_total += amt
            except ValueError:
                pass
        context_json["disb_subtotals"][cat_key] = (
            f"${cat_total:,.2f}" if cat_total > 0 else ""
        )

    return f"""You are a BOC fill agent. Build the final boc_context.json for fill_boc.py.

The bill-of-costs-data.js has been re-read as the source of truth. Here is
the assembled context JSON. Review it for completeness and return it.

{json.dumps(context_json, indent=2)}

Return:
{{"kind": "step_result", "data": {{"boc_context": <the context JSON above>}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    boc_ctx = result.get("boc_context")
    if not isinstance(boc_ctx, dict):
        return False, "boc_context must be a dict"
    required = ["court_file_number", "tariff_items", "fees_total",
                "grand_total"]
    for key in required:
        if key not in boc_ctx:
            return False, f"boc_context missing required field: {key}"
    if not isinstance(boc_ctx.get("tariff_items"), list):
        return False, "boc_context.tariff_items must be a list"
    if len(boc_ctx["tariff_items"]) == 0:
        return False, "boc_context.tariff_items is empty"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["boc_context"] = result["boc_context"]
    return ctx


def calls_script(ctx: dict) -> None:
    """Write boc_context.json and invoke fill_boc.py, then verify.py."""
    boc_ctx = ctx.get("boc_context", {})
    if not boc_ctx:
        raise RuntimeError("calls_script: boc_context not set in ctx -- validate should have caught this")

    # Determine output paths
    matter_path = ctx.get("matter_path", "")
    today = date.today().strftime("%Y-%m-%d")

    if matter_path:
        draft_dir = workspace_output_dir(matter_path)
    elif ctx.get("session_dir"):
        draft_dir = Path(ctx["session_dir"])
    else:
        raise ValueError("calls_script: neither matter_path nor session_dir is set in ctx")

    draft_dir.mkdir(parents=True, exist_ok=True)

    # Write context JSON
    context_path = draft_dir / "boc_context.json"
    context_path.write_text(
        json.dumps(boc_ctx, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    ctx["boc_context_json_path"] = str(context_path)

    # Derive output filename from style of cause
    style = ctx.get("style_of_cause", "")
    # Extract plaintiff last name + first initial
    plaintiff = style.split(" v.")[0].strip() if " v." in style else style
    parts = plaintiff.split()
    if parts:
        name_slug = parts[-1]  # last name
        if len(parts) > 1:
            name_slug += f" {parts[0][0]}"  # first initial
    else:
        name_slug = "BOC"

    out_path = draft_dir / f"BOC {name_slug}.docx"

    # Call fill_boc.py
    subprocess.run(
        ["python", str(FILL_BOC),
         "--context", str(context_path),
         "--out", str(out_path)],
        check=True,
    )
    ctx["output_path"] = str(out_path)

    # Call verify.py
    subprocess.run(
        ["python", str(VERIFY), str(out_path)],
        check=False,  # verify may warn but should not block
    )
