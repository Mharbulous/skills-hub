"""gen.matter_profile -- Fetch and confirm matter profile.

Fetches the matter profile from /case-data, checks for gaps,
presents to lawyer for confirmation via ask_user sub-loop.
The subagent formats the profile and returns it. The harness
then emits ask_user so the lawyer confirms.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

max_retries = 2

response_schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["step_result", "ask_user"]},
        "data": {
            "type": "object",
            "properties": {
                "profile_summary": {"type": "string"},
                "context_fields": {"type": "object"},
                "confirmed": {"type": "boolean"},
            },
        },
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind"],
}

CASE_DATA_SCRIPT = (
    Path(__file__).resolve().parents[4]  # .agents/skills/
    / "case-data" / "references" / "scripts" / "get_matter_profile.py"
)


def _fetch_profile(matter_path: str) -> dict | None:
    """Call get_matter_profile.py and return parsed JSON."""
    if not matter_path:
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(CASE_DATA_SCRIPT),
             "--matter-root", matter_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def precondition(ctx: dict) -> tuple[bool, str]:
    return True, ""


def build_prompt(ctx: dict) -> str:
    """Build the matter profile step prompt.

    If profile is not yet fetched, the harness fetches it first and
    stores in ctx.profile. If step_answers contains a confirmation,
    we include it.
    """
    # Extract matter_path from step_answers if not yet set
    if not ctx.get("matter_path"):
        answers = ctx.get("step_answers", [])
        for ans in answers:
            if ans and isinstance(ans, str) and ans.strip().lower() not in (
                "yes", "y", "confirmed", "correct", "looks good",
                "no", "n", "no, i need to make corrections",
            ):
                candidate = ans.strip()
                if Path(candidate).is_dir():
                    ctx["matter_path"] = candidate
                    break

    # Fetch profile if not already in ctx
    if not ctx.get("profile"):
        profile = _fetch_profile(ctx.get("matter_path", ""))
        if profile:
            ctx["profile"] = profile

    profile = ctx.get("profile")
    if not profile:
        # No profile available -- subagent should ask user for matter path
        return """You are a matter profile agent for a BC Supreme Court form drafting system.

The matter profile could not be fetched automatically. Ask the user to provide the matter folder path.

Return:
{"kind": "ask_user", "question": "I could not locate the matter profile. Please provide the path to the matter folder.", "options": []}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Check for gaps
    gaps = profile.get("gaps", [])
    if gaps:
        gap_list = "\n".join(f"  - {g}" for g in gaps)
        return f"""You are a matter profile agent for a BC Supreme Court form drafting system.

The matter profile has gaps that must be filled before proceeding. Report these gaps to the user.

## Gaps Found
{gap_list}

Return:
{{"kind": "ask_user", "question": "The matter profile has gaps that must be filled before I can proceed:\\n{gap_list}\\n\\nPlease run the case-data profile operation to fill these gaps, then try again.", "options": []}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Profile is complete -- format for confirmation
    answers = ctx.get("step_answers", [])
    if answers and answers[-1] and answers[-1].lower() in ("yes", "confirmed", "correct", "looks good", "y"):
        # Already confirmed by user
        proceedings = profile.get("proceedings", [])
        proc = proceedings[0] if proceedings else {}
        parties = proc.get("parties", [])
        plaintiffs = [p for p in parties if p["role"] in ("plaintiff", "petitioner", "applicant")]
        defendants = [p for p in parties if p["role"] in ("defendant", "respondent")]
        plaintiff_caption = "\n".join(p["name"].upper() for p in plaintiffs) if plaintiffs else ""
        plaintiff_role = plaintiffs[0]["role"].upper() if plaintiffs else "PLAINTIFF"
        defendant_caption = "\n".join(p["name"].upper() for p in defendants) if defendants else ""
        defendant_role = defendants[0]["role"].upper() if defendants else "DEFENDANT"

        context_fields = {
            "court_file_number": proc.get("file_number", ""),
            "registry": proc.get("registry", ""),
            "court_location": proc.get("courthouse_address", ""),
            "plaintiff_caption": plaintiff_caption,
            "plaintiff_role": plaintiff_role,
            "defendant_caption": defendant_caption,
            "defendant_role": defendant_role,
            "client_name": profile.get("client_name", ""),
            "lawyer_name": profile.get("filing_lawyer_name", ""),
        }

        return f"""You are a matter profile agent. The lawyer has confirmed the profile is correct.

Return the confirmed profile data:
{{"kind": "step_result", "data": {{"profile_summary": "Profile confirmed.", "context_fields": {json.dumps(context_fields)}, "confirmed": true}}}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""

    # Format profile for display and ask for confirmation
    proceedings = profile.get("proceedings", [])
    proc = proceedings[0] if proceedings else {}
    parties = proc.get("parties", [])

    party_lines = []
    for p in parties:
        party_lines.append(f"  {p['name']} ({p['role']})")

    summary = f"""Matter: {profile.get('short_name', profile.get('matter_id', 'Unknown'))}
Client: {profile.get('client_name', 'Unknown')}
Filing Lawyer: {profile.get('filing_lawyer_name', 'Unknown')}
Court: {proc.get('court', 'Unknown')}
Registry: {proc.get('registry', 'Unknown')}
File Number: {proc.get('file_number', 'Unknown')}
Courthouse: {proc.get('courthouse_address', 'Unknown')}
Parties:
{chr(10).join(party_lines)}"""

    return f"""You are a matter profile agent for a BC Supreme Court form drafting system.

Present the following matter profile to the lawyer for confirmation.

## Matter Profile
{summary}

Ask the lawyer to confirm this is correct. Return:
{{"kind": "ask_user", "question": "Here is the matter profile I will use:\\n\\n{summary}\\n\\nIs this correct?", "options": ["Yes", "No, I need to make corrections"]}}

## Constraints
- Return ONLY the JSON object specified above. Do not call Read, Bash, Grep, Glob, or any file-access tools."""


def validate(result: dict, ctx: dict) -> tuple[bool, str]:
    if result.get("confirmed"):
        if not result.get("context_fields"):
            return False, "Confirmed result must include context_fields"
    return True, ""


def apply(ctx: dict, result: dict) -> dict:
    if result.get("confirmed"):
        ctx["profile_confirmed"] = True
        ctx["scalars"] = ctx.get("scalars") or {}
        ctx["scalars"].update(result["context_fields"])
        # Persist matter_path and profile for downstream steps.
        # build_prompt() sets these in memory but they're lost when
        # ctx reloads from disk — extract from step_answers here.
        if not ctx.get("matter_path"):
            skip = {"yes", "y", "confirmed", "correct", "looks good",
                    "no", "n", "no, i need to make corrections"}
            for ans in ctx.get("step_answers", []):
                if ans and isinstance(ans, str) and ans.strip().lower() not in skip:
                    candidate = ans.strip()
                    if Path(candidate).is_dir():
                        ctx["matter_path"] = candidate
                        break
        if not ctx.get("profile") and ctx.get("matter_path"):
            profile = _fetch_profile(ctx["matter_path"])
            if profile:
                ctx["profile"] = profile
    return ctx
