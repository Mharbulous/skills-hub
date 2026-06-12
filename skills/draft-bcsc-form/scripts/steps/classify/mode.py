"""Tier 1 -- Mode classification.

Classifies user request into: amend | new-template | regular.
Amend and new-template short-circuit (skip Tiers 2-3).
"""
from __future__ import annotations

VALID_MODES = {"amend", "new-template", "regular"}

max_retries = 1

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": list(VALID_MODES)},
                "confidence": {"type": "number", "minimum": 0,
                               "maximum": 1},
                "ambiguous": {"type": "boolean"},
            },
            "required": ["mode", "confidence"],
        },
    },
    "required": ["kind", "data"],
}


def precondition(ctx: dict) -> tuple[bool, str]:
    return True, ""


def build_classify_prompt(user_request: str) -> str:
    """Build Tier 1 classification prompt (called by cmd_init)."""
    return f"""You are a classification agent for a BC Supreme Court form drafting system.

Given the user's request below, classify it into exactly one mode:

- **amend**: The user wants to amend a previously filed pleading (mentions amendment, Rule 6-1, amending a filed document).
- **new-template**: The user wants to convert a raw/LEAP-exported template into a bracket-placeholder template (mentions LEAP, raw template, conversion, new form type).
- **regular**: Anything else -- the user wants to draft, generate, or assemble a BC Supreme Court form.

## User Request
{user_request}

## Response Format
Return ONLY a JSON object:
{{"kind": "step_result", "data": {{"mode": "<amend|new-template|regular>", "confidence": <0.0-1.0>, "ambiguous": <true|false>}}}}

If you are uncertain between modes, set ambiguous to true and confidence below 0.8.

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""


def build_prompt(ctx: dict) -> str:
    return build_classify_prompt(ctx["user_request"])


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    mode = result.get("mode")
    if mode not in VALID_MODES:
        return False, f"Invalid mode '{mode}'. Must be one of: {VALID_MODES}"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["mode"] = result["mode"]
    return ctx
