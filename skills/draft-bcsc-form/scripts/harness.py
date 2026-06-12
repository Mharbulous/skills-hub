"""draft-bcsc-form v2 — Deterministic harness.

CLI state machine. Each invocation reads ctx.json, does one action,
writes ctx.json, returns JSON to stdout.

Usage:
    python harness.py <command> [<json_arg>]

Commands:
    init, classify, step, list, resume, abandon, reset, rewind, paste
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # scripts/
SKILL_ROOT = HERE.parent                        # draft-bcsc-form/
SESSIONS_DIR = SKILL_ROOT / "sessions"

CONFIDENCE_THRESHOLD = 0.8

# ---------------------------------------------------------------------------
# Form Registry (Section 9 parity)
# ---------------------------------------------------------------------------

REGISTRY = {
    "form-32": {
        "name": "Notice of Application (Form 32)",
        "rule": "Rule 8-1",
        "template": "templates/032-noa.dotx",
        "fill_script": "fill_plain.py",
        "fill_form_arg": "noa",
        "workflow": None,
        "sources_scope": "router_default",
        "generate_only": False,
    },
    "form-62": {
        "name": "Bill of Costs (Form 62)",
        "rule": "Appendix B",
        "template": "templates/062-boc.dotx",
        "fill_script": "fill_boc.py",
        "fill_form_arg": "boc",
        "workflow": "forms/boc/workflow.md",
        "sources_scope": "declared_in_workflow",
        "generate_only": False,
    },
    "form-66": {
        "name": "Petition (Form 66)",
        "rule": "Rule 16-1",
        "template": "templates/066-petition.dotx",
        "fill_script": "fill_plain.py",
        "fill_form_arg": "petition",
        "workflow": None,
        "sources_scope": "router_default",
        "generate_only": False,
    },
    "form-123": {
        "name": "Offer to Settle Costs (Form 123)",
        "rule": "Rule 9-1(6)",
        "template": "templates/123-otsc.dotx",
        "fill_script": "fill_plain.py",
        "fill_form_arg": "otsc",
        "workflow": None,
        "sources_scope": "declared_in_workflow",
        "generate_only": True,
    },
    "form-1": {
        "name": "Notice of Civil Claim (Form 1)",
        "rule": "Rule 3-1",
        "template": "templates/001-nocc.dotx",
        "fill_script": "fill_plain.py",
        "fill_form_arg": "nocc",
        "workflow": None,
        "sources_scope": "router_default",
        "generate_only": False,
    },
    "form-4": {
        "name": "Response to Counterclaim (Form 4)",
        "rule": "Rule 3-4",
        "template": "templates/004-rtc.dotx",
        "fill_script": "fill_plain.py",
        "fill_form_arg": "rtc",
        "workflow": None,
        "sources_scope": "router_default",
        "generate_only": False,
    },
    "affidavit": {
        "name": "Affidavit (Rule 22-2)",
        "rule": "Rule 22-2",
        "template": "templates/affidavit.dotx",
        "fill_script": "fill_plain.py",
        "fill_form_arg": "affidavit",
        "workflow": None,
        "sources_scope": None,
        "generate_only": True,
    },
}

# ---------------------------------------------------------------------------
# Step Sequences (Section 5 / Reference Skeleton)
# ---------------------------------------------------------------------------

SEQUENCES = {
    "generate":     ["gen.matter_profile", "gen.scalars", "gen.fill",
                     "shared.verify"],
    "draft":        ["gen.matter_profile", "draft.part1", "draft.part2",
                     "draft.part3", "draft.part4"],
    "assemble":     ["gen.matter_profile", "asm.locate_inputs",
                     "asm.assemble_body", "asm.fill", "shared.verify"],
    "full":         ["gen.matter_profile", "gen.scalars", "gen.fill",
                     "shared.verify",
                     "draft.part1", "draft.part2", "draft.part3",
                     "draft.part4",
                     "asm.locate_inputs", "asm.assemble_body", "asm.fill",
                     "shared.verify"],
    "amend":        ["amend.identify", "amend.propose", "amend.spec",
                     "amend.run"],
    "new-template": ["nt.inspect_tmpl", "nt.configure", "nt.convert",
                     "nt.validate"],
    "boc":          ["boc.setup", "boc.mcq", "boc.map_items", "boc.units",
                     "boc.disbursements", "boc.summary", "boc.fill",
                     "shared.verify"],
}

# Mode -> sequence mapping for Tier 1 short-circuits
MODE_SEQUENCES = {
    "amend": "amend",
    "new-template": "new-template",
}

# ---------------------------------------------------------------------------
# Step Module Loader
# ---------------------------------------------------------------------------

STEPS: dict[str, dict] = {}


def _load_step_module(step_id: str):
    """Import a step module by dotted step_id and register in STEPS."""
    # step_id like "gen.matter_profile" -> steps/gen/matter_profile.py
    parts = step_id.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid step_id format: {step_id}")
    package, module_name = parts
    module_path = f"steps.{package}.{module_name}"
    import importlib
    mod = importlib.import_module(module_path)
    STEPS[step_id] = {
        "id": step_id,
        "precondition": mod.precondition,
        "build_prompt": mod.build_prompt,
        "response_schema": mod.response_schema,
        "validate": mod.validate,
        "apply": mod.apply,
        "calls_script": getattr(mod, "calls_script", None),
        "max_retries": getattr(mod, "max_retries", 2),
    }


def load_all_steps():
    """Load all step modules referenced by any sequence."""
    loaded = set()
    for seq in SEQUENCES.values():
        for step_id in seq:
            if step_id not in loaded:
                try:
                    _load_step_module(step_id)
                    loaded.add(step_id)
                except (ImportError, ModuleNotFoundError):
                    pass  # Step module not yet implemented


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------

def _make_session_id(matter_id: str, form_id: str, ts: str) -> str:
    return f"{matter_id}__{form_id}__{ts}"


def _session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def _ctx_path(session_id: str) -> Path:
    return _session_dir(session_id) / "ctx.json"


def new_ctx(user_request: str, matter_id: str = "",
            matter_path: str = "") -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    session_id = _make_session_id(matter_id or "unknown", "unclassified", ts)
    return {
        "user_request": user_request,
        "matter_id": matter_id,
        "matter_path": matter_path,
        "form_id": None,
        "mode": None,
        "operation": None,
        "sequence": None,
        "step_index": 0,
        "current_step": None,
        "step_answers": [],
        "profile": None,
        "profile_confirmed": False,
        "scalars": None,
        "output_path": None,
        "stale_outputs": [],
        "session_id": session_id,
        "classify_tier": 1,
        "start_ts": ts,
        "attempts": 0,
    }


def save_ctx(ctx: dict) -> None:
    d = _session_dir(ctx["session_id"])
    d.mkdir(parents=True, exist_ok=True)
    _ctx_path(ctx["session_id"]).write_text(
        json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")


def load_ctx(session_id: str) -> dict:
    p = _ctx_path(session_id)
    return json.loads(p.read_text(encoding="utf-8"))


def find_session_id() -> str | None:
    """Find the most recently modified session."""
    if not SESSIONS_DIR.exists():
        return None
    candidates = []
    for d in SESSIONS_DIR.iterdir():
        ctx_file = d / "ctx.json"
        if ctx_file.exists():
            candidates.append((ctx_file.stat().st_mtime, d.name))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# Snapshot helpers (Section 3.2.3)
# ---------------------------------------------------------------------------

def save_snapshot(ctx: dict, step_id: str) -> None:
    """Save pre-step ctx snapshot for rollback."""
    d = _session_dir(ctx["session_id"])
    snap_path = d / f"ctx_before_{step_id}.json"
    snap_path.write_text(
        json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")


def load_snapshot(session_id: str, step_id: str) -> dict | None:
    d = _session_dir(session_id)
    snap_path = d / f"ctx_before_{step_id}.json"
    if not snap_path.exists():
        return None
    return json.loads(snap_path.read_text(encoding="utf-8"))


def delete_snapshots_from(session_id: str, sequence: list[str],
                          from_index: int) -> None:
    """Delete snapshots for steps at or after from_index."""
    d = _session_dir(session_id)
    for step_id in sequence[from_index:]:
        snap_path = d / f"ctx_before_{step_id}.json"
        if snap_path.exists():
            snap_path.unlink()


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def _emit(action_dict: dict) -> None:
    """Print JSON action to stdout and exit."""
    print(json.dumps(action_dict, ensure_ascii=False))
    sys.exit(0)


def _build_step_action(ctx: dict) -> dict:
    """Build spawn_subagent action for the current step."""
    step_id = ctx["current_step"]
    step = STEPS[step_id]
    ok, msg = step["precondition"](ctx)
    if not ok:
        return {"action": "halt", "reason": "precondition_failed",
                "error": msg, "step_id": step_id}
    prompt = step["build_prompt"](ctx)
    save_ctx(ctx)  # persist any mutations from build_prompt
    return {
        "action": "spawn_subagent",
        "session_id": ctx["session_id"],
        "step_id": step_id,
        "prompt": prompt,
        "schema": step["response_schema"],
        "route_to": "step",
    }


def cmd_init(user_request: str) -> dict:
    """Create session, return Tier 1 classification prompt."""
    ctx = new_ctx(user_request)
    save_ctx(ctx)
    # Build Tier 1 (mode) classification prompt
    from steps.classify.mode import build_classify_prompt, response_schema
    return {
        "action": "spawn_subagent",
        "prompt": build_classify_prompt(user_request),
        "schema": response_schema,
        "session_id": ctx["session_id"],
        "route_to": "classify",
    }


def cmd_classify(session_id: str, result_json: str) -> dict:
    """Validate classification result, advance tier or select sequence."""
    ctx = load_ctx(session_id)
    result = json.loads(result_json)

    # Unwrap envelope if present (subagents return {kind, data} wrappers)
    if result.get("kind") == "step_result" and "data" in result:
        result = result["data"]

    tier = ctx["classify_tier"]

    if tier == 1:
        # Mode classification
        from steps.classify.mode import validate as validate_mode
        ok, err = validate_mode(result, ctx)
        if not ok:
            return {"action": "retry", "error": err,
                    "step_id": "classify.mode", "attempt": ctx["attempts"]}
        mode = result["mode"]
        ctx["mode"] = mode
        # Short-circuit for amend / new-template
        if mode in MODE_SEQUENCES:
            seq_key = MODE_SEQUENCES[mode]
            ctx["sequence"] = seq_key
            ctx["step_index"] = 0
            ctx["current_step"] = SEQUENCES[seq_key][0]
            ctx["classify_tier"] = None
            save_ctx(ctx)
            return _build_step_action(ctx)
        # Regular mode -> Tier 2
        ctx["classify_tier"] = 2
        save_ctx(ctx)
        from steps.classify.form import build_classify_prompt, response_schema
        return {
            "action": "spawn_subagent",
            "prompt": build_classify_prompt(ctx["user_request"]),
            "schema": response_schema,
            "session_id": ctx["session_id"],
            "route_to": "classify",
        }

    elif tier == 2:
        # Form classification
        from steps.classify.form import validate as validate_form
        ok, err = validate_form(result, ctx)
        if not ok:
            return {"action": "retry", "error": err,
                    "step_id": "classify.form", "attempt": ctx["attempts"]}
        form_id = result["form_id"]
        ctx["form_id"] = form_id
        # Rename session directory
        old_sid = ctx["session_id"]
        parts = old_sid.split("__")
        new_sid = f"{parts[0]}__{form_id}__{parts[2]}"
        old_dir = _session_dir(old_sid)
        new_dir = _session_dir(new_sid)
        if old_dir != new_dir and old_dir.exists():
            try:
                old_dir.rename(new_dir)
            except OSError:
                # Collision: append counter
                new_sid = f"{parts[0]}__{form_id}__{parts[2]}_2"
                new_dir = _session_dir(new_sid)
                old_dir.rename(new_dir)
        ctx["session_id"] = new_sid
        # BOC short-circuits to boc sequence
        form_spec = REGISTRY.get(form_id, {})
        if form_spec.get("workflow"):
            ctx["sequence"] = "boc"
            ctx["operation"] = "boc"
            ctx["step_index"] = 0
            ctx["current_step"] = SEQUENCES["boc"][0]
            ctx["classify_tier"] = None
            save_ctx(ctx)
            return _build_step_action(ctx)
        # Generate-only forms skip Tier 3 -> generate sequence
        if form_spec.get("generate_only"):
            ctx["sequence"] = "generate"
            ctx["operation"] = "generate"
            ctx["step_index"] = 0
            ctx["current_step"] = SEQUENCES["generate"][0]
            ctx["classify_tier"] = None
            save_ctx(ctx)
            return _build_step_action(ctx)
        # Other forms -> Tier 3
        ctx["classify_tier"] = 3
        save_ctx(ctx)
        from steps.classify.operation import (build_classify_prompt,
                                              response_schema)
        return {
            "action": "spawn_subagent",
            "prompt": build_classify_prompt(ctx["user_request"],
                                            form_id, form_spec),
            "schema": response_schema,
            "session_id": ctx["session_id"],
            "route_to": "classify",
        }

    elif tier == 3:
        # Operation classification
        from steps.classify.operation import validate as validate_op
        ok, err = validate_op(result, ctx)
        if not ok:
            return {"action": "retry", "error": err,
                    "step_id": "classify.operation",
                    "attempt": ctx["attempts"]}
        op = result["op_id"]
        ctx["operation"] = op
        seq_key = op if op != "none" else "full"
        ctx["sequence"] = seq_key
        ctx["step_index"] = 0
        ctx["current_step"] = SEQUENCES[seq_key][0]
        ctx["classify_tier"] = None
        save_ctx(ctx)
        return _build_step_action(ctx)

    return {"action": "halt", "error": f"Unknown classify tier: {tier}"}


def cmd_step(session_id: str, result_json: str) -> dict:
    """Validate step result, apply, advance or retry."""
    ctx = load_ctx(session_id)
    step_id = ctx["current_step"]
    step = STEPS[step_id]
    result = json.loads(result_json)

    # --- OOW response ---
    if result.get("kind") == "oow_response":
        save_ctx(ctx)
        return {"action": "oow", "session_id": session_id,
                "step_id": step_id,
                "lawyer_question": result.get("lawyer_question", ""),
                "context": result.get("context", "")}

    # --- Subagent requested user input (ask_user sub-loop) ---
    if result.get("kind") == "ask_user" or result.get("needs_input"):
        question = result.get("question", "")
        options = result.get("options", [])
        ctx["step_answers"].append(None)  # placeholder
        save_ctx(ctx)
        return {"action": "ask_user", "session_id": session_id,
                "question": question,
                "options": options, "step_id": step_id}

    # --- User answer routed back ---
    if "user_answer" in result:
        if ctx["step_answers"] and ctx["step_answers"][-1] is None:
            ctx["step_answers"][-1] = result["user_answer"]
        else:
            ctx["step_answers"].append(result["user_answer"])
        save_ctx(ctx)
        prompt = step["build_prompt"](ctx)
        save_ctx(ctx)  # persist any mutations from build_prompt
        return {
            "action": "spawn_subagent",
            "session_id": session_id,
            "step_id": step_id,
            "prompt": prompt,
            "schema": step["response_schema"],
        }

    # --- OOW resolved ---
    if result.get("kind") == "oow_resolved":
        save_ctx(ctx)
        prompt = step["build_prompt"](ctx)
        save_ctx(ctx)  # persist any mutations from build_prompt
        return {
            "action": "spawn_subagent",
            "session_id": session_id,
            "step_id": step_id,
            "prompt": prompt,
            "schema": step["response_schema"],
        }

    # --- Normal step result ---
    # Extract data from envelope if present
    data = result.get("data", result) if result.get("kind") == "step_result" else result

    ok, err = step["validate"](data, ctx)
    if not ok:
        ctx["attempts"] = ctx.get("attempts", 0) + 1
        max_r = step["max_retries"]
        if ctx["attempts"] > max_r:
            save_ctx(ctx)
            return {"action": "halt",
                    "reason": "validation_failure_exhausted",
                    "step_id": step_id, "attempts": ctx["attempts"],
                    "max_retries": max_r, "last_error": err}
        save_ctx(ctx)
        return {"action": "retry", "error": err, "step_id": step_id,
                "attempt": ctx["attempts"],
                "continuation_available": True}

    # Save pre-step snapshot before apply
    save_snapshot(ctx, step_id)

    # Apply
    ctx = step["apply"](ctx, data)
    ctx["step_answers"] = []
    ctx["attempts"] = 0

    # Stay on step if apply() requested it (e.g. pending confirmation)
    if ctx.pop("_stay_on_step", False):
        save_ctx(ctx)
        return _build_step_action(ctx)

    # Run script if defined
    if step["calls_script"]:
        try:
            step["calls_script"](ctx)
        except (RuntimeError, ValueError) as e:
            save_ctx(ctx)
            return {"action": "halt", "reason": "script_failed",
                    "step_id": step_id, "error": str(e)}

    # Advance
    seq = SEQUENCES[ctx["sequence"]]
    ctx["step_index"] += 1
    if ctx["step_index"] >= len(seq):
        ctx["current_step"] = None
        save_ctx(ctx)
        result_action = {"action": "done",
                         "output_path": ctx.get("output_path", ""),
                         "session_id": ctx["session_id"]}
        # Cleanup session on completion (Section 3.1.3)
        cleanup_session(ctx["session_id"])
        return result_action

    ctx["current_step"] = seq[ctx["step_index"]]
    save_ctx(ctx)
    return _build_step_action(ctx)


def cleanup_session(session_id: str) -> None:
    """Delete session directory on completion."""
    d = _session_dir(session_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def cmd_list(matter_filter: str = "") -> dict:
    """Return JSON array of active sessions."""
    if not SESSIONS_DIR.exists():
        return []
    sessions = []
    for d in sorted(SESSIONS_DIR.iterdir()):
        ctx_file = d / "ctx.json"
        if not ctx_file.exists():
            continue
        ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
        if matter_filter and ctx.get("matter_id") != matter_filter:
            continue
        seq = ctx.get("sequence")
        total = len(SEQUENCES.get(seq, [])) if seq else 0
        sessions.append({
            "session_id": ctx["session_id"],
            "matter_id": ctx.get("matter_id", ""),
            "form_id": ctx.get("form_id", ""),
            "current_step": ctx.get("current_step"),
            "step_index": ctx.get("step_index", 0),
            "total_steps": total,
            "started": ctx.get("start_ts", ""),
            "last_modified": datetime.fromtimestamp(
                ctx_file.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        })
    return sessions


def cmd_resume(session_id: str) -> dict:
    """Resume an existing session -- return next action."""
    ctx = load_ctx(session_id)
    if ctx.get("current_step") is None:
        return {"action": "done", "output_path": ctx.get("output_path", ""),
                "session_id": session_id}
    step_id = ctx["current_step"]
    if step_id not in STEPS:
        return {"action": "halt",
                "error": f"Step module not loaded: {step_id}"}
    return _build_step_action(ctx)


def cmd_abandon(session_id: str) -> dict:
    """Delete a session directory."""
    d = _session_dir(session_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    return {"action": "abandoned", "session_id": session_id}


def cmd_reset(session_id: str, new_request: str) -> dict:
    """Re-classify: clear classification, keep session, restart."""
    ctx = load_ctx(session_id)
    # Record stale outputs
    if ctx.get("output_path"):
        ctx["stale_outputs"].append({
            "path": ctx["output_path"],
            "step_id": ctx.get("current_step", ""),
            "produced_at": datetime.now(timezone.utc).isoformat(),
        })
    old_sid = ctx["session_id"]
    # Clear classification and step state
    ctx["user_request"] = new_request
    ctx["form_id"] = None
    ctx["mode"] = None
    ctx["operation"] = None
    ctx["sequence"] = None
    ctx["step_index"] = 0
    ctx["current_step"] = None
    ctx["step_answers"] = []
    ctx["profile"] = None
    ctx["profile_confirmed"] = False
    ctx["scalars"] = None
    ctx["output_path"] = None
    ctx["classify_tier"] = 1
    ctx["attempts"] = 0
    # Rename directory back to unclassified
    parts = old_sid.split("__")
    new_sid = f"{parts[0]}__unclassified__{parts[-1]}"
    old_dir = _session_dir(old_sid)
    new_dir = _session_dir(new_sid)
    if old_dir != new_dir and old_dir.exists():
        try:
            old_dir.rename(new_dir)
        except OSError:
            pass  # keep old name if rename fails
        else:
            ctx["session_id"] = new_sid
    save_ctx(ctx)
    # Return Tier 1 classification prompt
    from steps.classify.mode import build_classify_prompt, response_schema
    return {
        "action": "spawn_subagent",
        "prompt": build_classify_prompt(new_request),
        "schema": response_schema,
        "session_id": ctx["session_id"],
        "reset_from": old_sid,
        "stale_outputs": ctx["stale_outputs"],
    }


def cmd_rewind(session_id: str, target_step_id: str) -> dict:
    """Backtrack to a prior step using snapshot."""
    ctx = load_ctx(session_id)
    seq = SEQUENCES.get(ctx.get("sequence", ""), [])
    if target_step_id not in seq:
        return {"action": "halt", "reason": "rewind_invalid",
                "error": f"Cannot rewind to '{target_step_id}': "
                         f"step not in current sequence"}
    target_idx = seq.index(target_step_id)
    if target_idx >= ctx["step_index"]:
        return {"action": "halt", "reason": "rewind_invalid",
                "error": f"Cannot rewind to '{target_step_id}': "
                         f"step not yet completed"}
    # Restore snapshot
    snap = load_snapshot(session_id, target_step_id)
    if snap is None:
        return {"action": "halt", "reason": "rewind_invalid",
                "error": f"No snapshot found for '{target_step_id}'"}
    # Mark stale outputs from target forward
    # (future: track script outputs per step)
    # Delete snapshots from target forward
    delete_snapshots_from(session_id, seq, target_idx)
    # Restore ctx from snapshot
    ctx = snap
    ctx["step_index"] = target_idx
    ctx["current_step"] = target_step_id
    ctx["step_answers"] = []
    ctx["attempts"] = 0
    save_ctx(ctx)
    return _build_step_action(ctx)


PASTE_VALID_STEPS = {"boc.mcq", "boc.map_items", "boc.units",
                     "boc.disbursements", "boc.summary"}


def cmd_paste(session_id: str, json_str: str) -> dict:
    """Handle BOC paste-back (Section 9.1)."""
    ctx = load_ctx(session_id)
    if ctx.get("sequence") != "boc" or \
       ctx.get("current_step") not in PASTE_VALID_STEPS:
        return {"action": "halt", "reason": "paste_not_allowed",
                "error": f"Paste-back only valid during BOC steps 2-6 "
                         f"(current step: {ctx.get('current_step')})"}
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"action": "halt", "reason": "paste_invalid",
                "error": f"Invalid JSON: {e}"}
    if "tariffItems" not in data and "disbursements" not in data:
        return {"action": "halt", "reason": "paste_invalid",
                "error": "Pasted JSON must contain tariffItems "
                         "or disbursements"}
    # Write bill-of-costs-data.js
    matter_path = ctx.get("matter_path", "")
    if matter_path:
        js_path = Path(matter_path) / "bill-of-costs-data.js"
        js_path.write_text(f"window.billData = {json.dumps(data)};",
                           encoding="utf-8")
    # Update ctx fields
    if "tariffItems" in data:
        ctx["tariff_items"] = data["tariffItems"]
    if "disbursements" in data:
        ctx["disbursements"] = data["disbursements"]
    ctx["step_answers"] = []
    save_ctx(ctx)
    step_id = ctx["current_step"]
    step = STEPS.get(step_id)
    if not step:
        return {"action": "halt",
                "error": f"Step module not loaded: {step_id}"}
    return {
        "action": "spawn_subagent",
        "step_id": step_id,
        "prompt": step["build_prompt"](ctx),
        "schema": step["response_schema"],
        "paste_applied": True,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    # Change working directory to scripts/ so relative imports work
    os.chdir(HERE)
    # Ensure steps/ is importable
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))

    load_all_steps()

    parser = argparse.ArgumentParser(description="v2 harness CLI")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init")
    p_init.add_argument("user_request")

    p_classify = sub.add_parser("classify")
    p_classify.add_argument("session_id")
    p_classify.add_argument("result_json")

    p_step = sub.add_parser("step")
    p_step.add_argument("session_id")
    p_step.add_argument("result_json")

    p_list = sub.add_parser("list")
    p_list.add_argument("--matter", default="")

    p_resume = sub.add_parser("resume")
    p_resume.add_argument("session_id")

    p_abandon = sub.add_parser("abandon")
    p_abandon.add_argument("session_id")

    p_reset = sub.add_parser("reset")
    p_reset.add_argument("session_id")
    p_reset.add_argument("new_request")

    p_rewind = sub.add_parser("rewind")
    p_rewind.add_argument("session_id")
    p_rewind.add_argument("target_step_id")

    p_paste = sub.add_parser("paste")
    p_paste.add_argument("session_id")
    p_paste.add_argument("json_str")

    args = parser.parse_args()

    if args.command == "init":
        _emit(cmd_init(args.user_request))
    elif args.command == "classify":
        _emit(cmd_classify(args.session_id, args.result_json))
    elif args.command == "step":
        _emit(cmd_step(args.session_id, args.result_json))
    elif args.command == "list":
        _emit(cmd_list(args.matter))
    elif args.command == "resume":
        _emit(cmd_resume(args.session_id))
    elif args.command == "abandon":
        _emit(cmd_abandon(args.session_id))
    elif args.command == "reset":
        _emit(cmd_reset(args.session_id, args.new_request))
    elif args.command == "rewind":
        _emit(cmd_rewind(args.session_id, args.target_step_id))
    elif args.command == "paste":
        _emit(cmd_paste(args.session_id, args.json_str))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
