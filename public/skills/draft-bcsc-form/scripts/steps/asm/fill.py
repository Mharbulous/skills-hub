"""asm.fill -- Fill template with context + assembled body.

Calls fill_plain.py with --context and --body to produce the final
filled document with substance content. The harness runs the script
via calls_script after the subagent confirms readiness.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from steps.shared.paths import workspace_output_dir

HERE = Path(__file__).resolve().parent          # steps/asm/
SCRIPTS = HERE.parent.parent                    # scripts/
SKILL_ROOT = SCRIPTS.parent                     # draft-bcsc-form/

max_retries = 1

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "ready": {"type": "boolean"},
            },
            "required": ["ready"],
        },
    },
    "required": ["kind", "data"],
}


def precondition(ctx: dict) -> tuple[bool, str]:
    if not ctx.get("asm_body_path"):
        return False, "Assembled body must exist before fill"
    body_path = Path(ctx["asm_body_path"])
    if not body_path.exists():
        return False, f"Body file does not exist: {ctx['asm_body_path']}"
    # Need context.json (from gen.fill or asm.locate_inputs)
    ctx_path = ctx.get("asm_context_path") or ctx.get("context_path", "")
    if not ctx_path or not Path(ctx_path).exists():
        return False, "context.json not found. Run Generate form first."
    return True, ""


def build_prompt(ctx: dict) -> str:
    return f"""You are a fill-readiness agent. The assembled body and context are ready.

Confirm that the form is ready to be filled with substance content.

Return:
{{"kind": "step_result", "data": {{"ready": true}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if not result.get("ready"):
        return False, "Fill step must confirm readiness"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    return ctx


def calls_script(ctx: dict) -> None:
    """Run fill_plain.py with --context and --body to produce filled document."""
    from harness import REGISTRY, SKILL_ROOT as HR_SKILL_ROOT

    form_id = ctx.get("form_id", "form-32")
    form_spec = REGISTRY.get(form_id, REGISTRY["form-32"])
    template_path = HR_SKILL_ROOT / form_spec["template"]
    fill_form_arg = form_spec["fill_form_arg"]

    # Resolve paths
    context_path = ctx.get("asm_context_path") or ctx.get("context_path", "")
    body_path = ctx.get("asm_body_path", "")

    scalars = ctx.get("scalars", {})
    matter_path = ctx.get("matter_path", "")
    title = scalars.get("title", form_spec["name"])

    # Build output path
    if matter_path:
        out_path = workspace_output_dir(matter_path) / f"{title}.docx"
    else:
        out_dir = HR_SKILL_ROOT / "sessions" / ctx["session_id"]
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        out_path = out_dir / f"{today} {title}.docx"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Call fill_plain.py with --body
    fill_script = SCRIPTS / form_spec["fill_script"]
    cmd = [
        sys.executable, str(fill_script),
        "--form", fill_form_arg,
        "--template", str(template_path),
        "--context", str(context_path),
        "--body", str(body_path),
        "--out", str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"fill_plain.py failed (exit {result.returncode}):\n"
            f"{result.stderr}")

    ctx["output_path"] = str(out_path)
