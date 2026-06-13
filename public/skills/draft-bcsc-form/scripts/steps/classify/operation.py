"""Tier 3 -- Operation classification.

Classifies: generate | draft | assemble | none (-> full pipeline).
Only reached for regular-mode forms without a dedicated workflow.
"""
from __future__ import annotations

VALID_OPS = {"generate", "draft", "assemble", "none"}

max_retries = 1

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "op_id": {"type": "string",
                          "enum": list(VALID_OPS)},
                "confidence": {"type": "number"},
                "ambiguous": {"type": "boolean"},
            },
            "required": ["op_id", "confidence"],
        },
    },
    "required": ["kind", "data"],
}


def precondition(ctx: dict) -> tuple[bool, str]:
    if ctx.get("mode") != "regular":
        return False, "Tier 3 only reached for regular mode"
    if not ctx.get("form_id"):
        return False, "Form must be identified before operation classification"
    return True, ""


def build_classify_prompt(user_request: str, form_id: str,
                          form_spec: dict) -> str:
    """Build Tier 3 operation classification prompt."""
    return f"""You are an operation classification agent for a BC Supreme Court form drafting system.

The user wants to work with: {form_spec.get('name', form_id)}

Classify their request into exactly one operation:

- **generate**: The user wants a blank form with proceedings info filled but substantive body sections untouched. Keywords: "blank form", "just the header", "generate", "fill out proceedings info".
- **draft**: The user wants substantive content drafted in markdown for review. Keywords: "draft substance", "draft parts", "write the content".
- **assemble**: The user wants to merge previously drafted substance into a form template. Keywords: "assemble", "merge", "combine substance into form".
- **none**: The user wants the full pipeline (generate + draft + assemble). Keywords: no specific operation mentioned, or "draft a [form]" without specifying which phase.

## User Request
{user_request}

## Response Format
Return ONLY a JSON object:
{{"kind": "step_result", "data": {{"op_id": "<generate|draft|assemble|none>", "confidence": <0.0-1.0>, "ambiguous": <true|false>}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""


def build_prompt(ctx: dict) -> str:
    from harness import REGISTRY
    form_spec = REGISTRY.get(ctx.get("form_id", ""), {})
    return build_classify_prompt(ctx["user_request"],
                                 ctx.get("form_id", ""), form_spec)


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    op = result.get("op_id")
    if op not in VALID_OPS:
        return False, f"Invalid op_id '{op}'. Must be one of: {VALID_OPS}"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["operation"] = result["op_id"]
    return ctx
