"""gen.fill -- Fill template with scalars (no body content).

Calls fill_plain.py to produce the blank form. The harness runs the
script via calls_script after the subagent confirms readiness.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from steps.shared.paths import workspace_output_dir

HERE = Path(__file__).resolve().parent          # steps/gen/
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
    if not ctx.get("profile_confirmed"):
        return False, "Profile must be confirmed before fill"
    if not ctx.get("scalars"):
        return False, "Scalars must be collected before fill"
    return True, ""


def build_prompt(ctx: dict) -> str:
    return f"""You are a fill-readiness agent. The matter profile is confirmed and all scalar fields are collected.

Confirm that the form is ready to be filled.

Return:
{{"kind": "step_result", "data": {{"ready": true}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if not result.get("ready"):
        return False, "Fill step must confirm readiness"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    # Prepare output paths -- fill script runs via calls_script
    return ctx


def calls_script(ctx: dict) -> None:
    """Run fill_plain.py to produce the filled document."""
    from harness import REGISTRY, SKILL_ROOT as HR_SKILL_ROOT

    form_id = ctx.get("form_id", "form-32")
    form_spec = REGISTRY.get(form_id, REGISTRY["form-32"])
    template_path = HR_SKILL_ROOT / form_spec["template"]
    fill_form_arg = form_spec["fill_form_arg"]

    scalars = ctx.get("scalars", {})
    matter_path = ctx.get("matter_path", "")
    title = scalars.get("title", form_spec["name"])

    # Build output path
    if matter_path:
        draft_dir = workspace_output_dir(matter_path)
        out_path = draft_dir / f"{title}.docx"
    else:
        draft_dir = HR_SKILL_ROOT / "sessions" / ctx["session_id"]
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        out_path = draft_dir / f"{today} {title}.docx"

    draft_dir.mkdir(parents=True, exist_ok=True)

    # Write context JSON
    context_path = draft_dir / "context.json"
    context_path.write_text(
        json.dumps(scalars, indent=2, ensure_ascii=False), encoding="utf-8")

    # Call fill_plain.py
    fill_script = SCRIPTS / form_spec["fill_script"]
    cmd = [
        sys.executable, str(fill_script),
        "--form", fill_form_arg,
        "--template", str(template_path),
        "--context", str(context_path),
        "--out", str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"fill_plain.py failed (exit {result.returncode}):\n"
            f"{result.stderr}")

    ctx["output_path"] = str(out_path)
    ctx["context_path"] = str(context_path)
    ctx["draft_dir"] = str(draft_dir)
