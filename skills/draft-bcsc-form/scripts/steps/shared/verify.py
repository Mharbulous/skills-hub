"""shared.verify -- Run verify.py on filled output.

Runs the existing verify.py script on the filled document.
The subagent receives the verification output and assesses pass/fail.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent  # scripts/
VERIFY_SCRIPT = SCRIPTS / "verify.py"

max_retries = 0  # verify is deterministic — retry would produce identical output

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "step_result"},
        "data": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "summary": {"type": "string"},
            },
            "required": ["passed", "warnings", "summary"],
        },
    },
    "required": ["kind", "data"],
}


def _run_verify(output_path: str) -> str:
    """Run verify.py and return its stdout."""
    try:
        result = subprocess.run(
            [sys.executable, str(VERIFY_SCRIPT), output_path],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "ERROR: verify.py timed out after 60s"
    except OSError as e:
        return f"ERROR: could not run verify.py: {e}"


def precondition(ctx: dict) -> tuple[bool, str]:
    if not ctx.get("output_path"):
        return False, "No output file to verify"
    p = Path(ctx["output_path"])
    if not p.exists():
        return False, f"Output file does not exist: {ctx['output_path']}"
    return True, ""


def _detect_phase(ctx: dict) -> str:
    """Determine if this verify runs after generate or after assemble."""
    seq = ctx.get("sequence", "")
    idx = ctx.get("step_index", 0)
    from harness import SEQUENCES
    steps = SEQUENCES.get(seq, [])
    if idx > 0 and idx <= len(steps):
        prev_step = steps[idx - 1]
        if prev_step == "asm.fill":
            return "assemble"
    return "generate"


def build_prompt(ctx: dict) -> str:
    output_path = ctx.get("output_path", "")
    verify_output = _run_verify(output_path)
    phase = _detect_phase(ctx)

    phase_rules = ""
    if phase == "generate":
        phase_rules = """
- **This is a GENERATE-phase verification.** Content instruction placeholders (e.g. [CONCISE SUMMARY], [OTHER ENACTMENT], [Select an item...], [Set out...]) are EXPECTED to survive — they will be filled in the draft+assemble phases. Only flag proceedings-level placeholders (party names, court file number, registry, etc.) as failures."""
    else:
        phase_rules = """
- **This is an ASSEMBLE-phase verification.** All placeholders except the known leave-blank set should have been filled."""

    return f"""You are a verification agent for a BC Supreme Court form drafting system.

The filled document has been verified by verify.py. Review the output below and determine whether the document passed verification.

## Verification Output
{verify_output}

## Document Path
{output_path}

## Phase
This verification runs after the **{phase}** phase.

## Rules
- If the output contains only "OK" lines and no "WARN" lines, the document passed.
- If there are WARN lines about residual placeholders, check if they are in the known leave-blank set (like [mmmm d, yyyy], [number], [judge-date], [FIRM ADDRESS], [FIRM EMAIL], [FIRM FAX]). Leave-blank warnings are acceptable.
- If there are WARN lines about actual unfilled placeholders that should have been substituted, the document failed.
- ZWSP warnings are failures.
- mc:Ignorable warnings are failures.{phase_rules}

Return:
{{"kind": "step_result", "data": {{"passed": <true|false>, "warnings": [<list of warning strings>], "summary": "<one sentence summary>"}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools.
- All information you need is provided in this prompt."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if "passed" not in result:
        return False, "Result must include 'passed' boolean"
    if not isinstance(result.get("warnings", []), list):
        return False, "'warnings' must be a list"
    if not result["passed"]:
        return False, f"Verification failed: {result.get('summary', 'no summary')}"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    ctx["verify_passed"] = result["passed"]
    ctx["verify_warnings"] = result.get("warnings", [])
    ctx["verify_summary"] = result.get("summary", "")
    return ctx
