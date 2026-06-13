"""amend.run -- Execute amend.py and verify the output.

Calls amend.py with the original document, amendments spec, and output
paths. Then runs verify.py on the result. The subagent confirms readiness;
the actual work happens in calls_script.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from steps.shared.paths import workspace_output_dir

SCRIPTS = Path(__file__).resolve().parent.parent.parent  # scripts/
AMEND_SCRIPT = SCRIPTS / "amend.py"
VERIFY_SCRIPT = SCRIPTS / "verify.py"

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
    if not ctx.get("amendments_spec_path"):
        return False, "Amendments spec must be produced before running amend.py"
    spec_path = Path(ctx["amendments_spec_path"])
    if not spec_path.exists():
        return False, f"Amendments spec not found at {spec_path}"
    if not ctx.get("original_docx_path"):
        return False, "Original .docx path required"
    orig = Path(ctx["original_docx_path"])
    if not orig.exists():
        return False, f"Original document not found at {orig}"
    return True, ""


def build_prompt(ctx: dict) -> str:
    original = ctx.get("original_docx_path", "")
    spec_path = ctx.get("amendments_spec_path", "")

    return f"""You are an amendment execution agent.

The amendment spec has been validated and is ready to run.

- Original document: {original}
- Amendments spec: {spec_path}

Confirm that the amendment should proceed.

Return:
{{"kind": "step_result", "data": {{"ready": true}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if not result.get("ready"):
        return False, "Amend step must confirm readiness"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    return ctx


def calls_script(ctx: dict) -> None:
    """Run amend.py to produce the amended document, then verify."""
    original = Path(ctx["original_docx_path"])
    spec_path = Path(ctx["amendments_spec_path"])
    matter_path = ctx.get("matter_path", "")

    # Build output paths
    today = date.today().strftime("%Y-%m-%d")
    form_name = original.stem  # e.g., "Notice of Civil Claim"

    if matter_path:
        draft_dir = workspace_output_dir(matter_path)
        out_path = draft_dir / f"Amended {form_name}.docx"
        clean_path = draft_dir / f"Amended {form_name} (clean).docx"
    else:
        from harness import SESSIONS_DIR
        session_dir = SESSIONS_DIR / ctx["session_id"]
        out_path = session_dir / f"{today} Amended {form_name}.docx"
        clean_path = session_dir / f"{today} Amended {form_name} (clean).docx"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Run amend.py
    cmd = [
        sys.executable, str(AMEND_SCRIPT),
        "--original", str(original),
        "--amendments", str(spec_path),
        "--out", str(out_path),
        "--clean", str(clean_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(
            f"amend.py failed (exit {result.returncode}):\n"
            f"{result.stderr}\n{result.stdout}")

    ctx["output_path"] = str(out_path)
    ctx["clean_path"] = str(clean_path)

    # Run verify.py on the marked-up version
    verify_result = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), str(out_path)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    ctx["verify_output"] = verify_result.stdout + verify_result.stderr
    ctx["verify_passed"] = verify_result.returncode == 0
