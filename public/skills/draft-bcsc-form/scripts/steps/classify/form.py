"""Tier 2 -- Form identification.

Identifies which BC Supreme Court form the user wants.
Only reached for 'regular' mode.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import REGISTRY from harness at runtime to avoid circular imports
HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent
sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None

max_retries = 1

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "form_id": {"type": "string"},
                "confidence": {"type": "number"},
                "ambiguous": {"type": "boolean"},
            },
            "required": ["form_id", "confidence"],
        },
    },
    "required": ["kind", "data"],
}


def _get_registry():
    from harness import REGISTRY
    return REGISTRY


def precondition(ctx: dict) -> tuple[bool, str]:
    if ctx.get("mode") != "regular":
        return False, "Tier 2 only reached for regular mode"
    return True, ""


def build_classify_prompt(user_request: str) -> str:
    """Build Tier 2 form identification prompt."""
    registry = _get_registry()
    registry_text = "\n".join(
        f"- **{fid}**: {spec['name']} ({spec['rule']})"
        for fid, spec in registry.items()
    )
    return f"""You are a form identification agent for a BC Supreme Court form drafting system.

Given the user's request, identify which form they want. Return the form_id from the registry below.

## Form Registry
{registry_text}

## User Request
{user_request}

## Response Format
Return ONLY a JSON object:
{{"kind": "step_result", "data": {{"form_id": "<form-id>", "confidence": <0.0-1.0>, "ambiguous": <true|false>}}}}

If the user mentions "NOA" or "notice of application", return form-32.
If the user mentions "bill of costs", "Form 62", "tariff", "costs assessment", return form-62.
If the user mentions "petition" or "Form 66", return form-66.
If the user mentions "offer to settle costs" or "Form 123", return form-123.
If the user mentions "notice of civil claim", "NOCC", or "Form 1", return form-1.
If the user mentions "response to counterclaim" or "Form 4", return form-4.
If the user mentions "affidavit", return affidavit.

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""


def build_prompt(ctx: dict) -> str:
    return build_classify_prompt(ctx["user_request"])


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    registry = _get_registry()
    form_id = result.get("form_id")
    if form_id not in registry:
        valid_ids = list(registry.keys())
        return False, (f"Invalid form_id '{form_id}'. "
                       f"Must be one of: {valid_ids}")
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["form_id"] = result["form_id"]
    return ctx
