"""gen.scalars -- Collect form-specific scalar values.

Asks the lawyer for form-specific fields via ask_user sub-loop.
Fields depend on form_id (from generate-form.md Phase 2).
"""
from __future__ import annotations

import json
from pathlib import Path

max_retries = 2

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["step_result", "ask_user"]},
        "data": {
            "type": "object",
            "properties": {
                "scalars": {"type": "object"},
            },
        },
        "question": {"type": "string"},
        "options": {"type": "array"},
    },
    "required": ["kind"],
}

# Form-specific scalar field definitions
FORM_SCALARS = {
    "form-32": {
        "fields": [
            ("hearing_date", "Hearing date (e.g. 'April 30, 2026', or 'leave as [date]' if TBD)"),
            ("hearing_time", "Hearing time (e.g. '10:00')"),
            ("am_pm", "AM or PM"),
            ("duration_hours", "Duration hours (integer)"),
            ("duration_minutes", "Duration minutes (integer)"),
            ("applicant_names", "Applicant name(s) for this application"),
            ("to_affected_parties", "Names of parties to be served"),
            ("title", "Title of the application (e.g. 'Security for Costs') -- used in output filename"),
        ],
    },
    "form-66": {
        "fields": [
            ("time_estimate", "Time estimate for the hearing (e.g. '2 hours', or leave as '[time estimate]')"),
            ("is_judicial_review", "Is this an application for judicial review? (yes/no)"),
            ("title", "Title of the petition (e.g. 'Partition and Sale') -- used in output filename"),
        ],
    },
    "form-123": {
        "fields": [],  # OTSC: all scalars come from matter profile
    },
    "form-1": {
        "fields": [
            ("title", "Title for the output filename (e.g. 'Notice of Civil Claim')"),
        ],
    },
    "form-4": {
        "fields": [
            ("title", "Title for the output filename (e.g. 'Response to Counterclaim')"),
        ],
    },
    "affidavit": {
        "fields": [
            ("deponent_name", "Full name of deponent"),
            ("deponent_address", "Civic address of deponent"),
            ("deponent_occupation", "Occupation of deponent (leave blank if not stated)"),
            ("swear_or_affirm", "Does the deponent swear or affirm? (swear/affirm)"),
            ("affidavit_date", "Date the affidavit is being made (e.g. 'April 27, 2026')"),
            ("commissioner_city", "City where the commissioner is located"),
            ("commissioner_name", "Name of the commissioner (leave blank if unknown)"),
            ("interpreter_required", "Does the deponent require an interpreter? (yes/no, default: no)"),
        ],
    },
}


def precondition(ctx: dict) -> tuple[bool, str]:
    if not ctx.get("profile_confirmed"):
        return False, "Matter profile must be confirmed before collecting scalars"
    return True, ""


def build_prompt(ctx: dict) -> str:
    form_id = ctx.get("form_id", "form-32")
    form_def = FORM_SCALARS.get(form_id, {"fields": []})
    fields = form_def["fields"]
    answers = ctx.get("step_answers", [])

    # If no fields needed, return immediately
    if not fields:
        existing = ctx.get("scalars", {})
        return f"""You are a scalar collection agent. This form has no additional scalar fields to collect.

Return the existing scalars:
{{"kind": "step_result", "data": {{"scalars": {json.dumps(existing)}}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Check if all fields have been answered
    if len(answers) >= len(fields) and all(a is not None for a in answers[:len(fields)]):
        # All answered -- build final scalars
        scalars = dict(ctx.get("scalars", {}))
        for i, (key, _desc) in enumerate(fields):
            scalars[key] = answers[i]
        # Derive sworn_or_affirmed for affidavit
        if form_id == "affidavit" and "swear_or_affirm" in scalars:
            soa = scalars["swear_or_affirm"].strip().lower()
            scalars["sworn_or_affirmed"] = "SWORN" if soa == "swear" else "AFFIRMED"

        return f"""You are a scalar collection agent. All scalar fields have been collected.

Return the complete scalars:
{{"kind": "step_result", "data": {{"scalars": {json.dumps(scalars)}}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Ask for the next unanswered field
    next_idx = len([a for a in answers if a is not None])
    if next_idx >= len(fields):
        next_idx = 0
    key, desc = fields[next_idx]

    # Build batch question for all remaining fields
    remaining = fields[next_idx:]
    if len(remaining) == 1:
        question = f"Please provide: {desc}"
    else:
        lines = [f"{i+1}. {d}" for i, (_k, d) in enumerate(remaining)]
        question = "Please provide the following form details:\\n" + "\\n".join(lines)

    return f"""You are a scalar collection agent for a BC Supreme Court form.

Ask the lawyer for the following information:

{question}

Return:
{{"kind": "ask_user", "question": "{question}", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if "scalars" in result:
        scalars = result["scalars"]
        if not isinstance(scalars, dict):
            return False, "scalars must be a dict"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    if "scalars" in result:
        ctx["scalars"] = result["scalars"]
    return ctx
