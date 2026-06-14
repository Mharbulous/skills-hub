import http.server
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def find_git_bash():
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git" / "bin" / "bash.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Git" / "bin" / "bash.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    bash = shutil.which("bash")
    if bash and "System32" not in bash:
        return bash
    return None


@pytest.fixture
def work_tmp():
    parent = Path(os.environ.get("SKILLS_HUB_TEST_TMP", ROOT / ".test-tmp"))
    parent.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="skills-hub-bootstrap-", dir=parent))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def require_shell_tools():
    missing = [tool for tool in ("curl", "ssh-keygen") if shutil.which(tool) is None]
    if find_git_bash() is None:
        missing.append("git-bash")
    if missing:
        pytest.skip(f"missing shell tools: {', '.join(missing)}")


def bash_path(path):
    value = str(path).replace("\\", "/")
    if len(value) >= 3 and value[1] == ":" and value[2] == "/":
        return f"/{value[0].lower()}{value[2:]}"
    return value


def bash_arg(path):
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return bash_path(path)


@contextmanager
def serve_dir(directory):
    """Start an HTTP server rooted at directory; yield the base URL."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


def make_skill_server(base, harness, skills):
    """Create signed manifest.json and skill file tree under base/.

    skills: dict of skill_name -> dict of rel_path -> content
    """
    base.mkdir(parents=True, exist_ok=True)
    key = base / "signing_key"
    allowed = base / "skills_hub_allowed_signers"
    if not key.is_file():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(key)], check=True)
        allowed.write_text(
            f"skills-hub-manifest {(base / 'signing_key.pub').read_text(encoding='utf-8')}",
            encoding="utf-8",
        )

    for skill_name, files in skills.items():
        for rel_path, content in files.items():
            file_path = base / "skills" / skill_name / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    entries = []
    file_entries = {}
    for skill_name, files in skills.items():
        base_path = f"skills/{skill_name}"
        entries.append({
            "name": skill_name,
            "description": f"Test skill {skill_name}",
            "harnesses": {
                harness: {
                    "base": base_path,
                    "files": list(files.keys()),
                }
            },
        })
        for rel_path in files:
            path = base / base_path / rel_path
            data = path.read_bytes()
            file_entries[f"{base_path}/{rel_path}"] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }

    manifest = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 604800,
        "skills": entries,
        "files": file_entries,
    }
    manifest_path = base / "manifest.json"
    signature_path = base / "manifest.json.sig"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if signature_path.exists():
        signature_path.unlink()
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest_path)], check=True)
    return allowed


def run_setup(script_name, harness, base_url, dest, allowed_signers, check=True):
    require_shell_tools()
    env = os.environ.copy()
    env["SKILLS_BASE_URL"] = base_url
    env["SKILLS_HUB_ALLOWED_SIGNERS"] = bash_arg(allowed_signers)
    bash = Path(find_git_bash())
    git_root = bash.parent.parent
    env["PATH"] = os.pathsep.join([
        str(git_root / "usr" / "bin"),
        str(git_root / "bin"),
        env.get("PATH", ""),
    ])
    command = [str(bash), f"bootstrap/{script_name}", bash_arg(dest)]
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=check,
        timeout=30,
    )


@pytest.mark.parametrize(
    ("script_name", "harness"),
    [("claude-setup.sh", "claude"), ("codex-setup.sh", "codex")],
)
def test_fresh_install_writes_marker_for_each_harness(work_tmp, script_name, harness):
    base = work_tmp / "base"
    allowed = make_skill_server(base, harness, {"alpha": {"SKILL.md": "alpha content\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        result = run_setup(script_name, harness, base_url, dest, allowed)

    assert result.returncode == 0
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha content\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_rerun_is_idempotent_and_preserves_user_skill(work_tmp):
    base = work_tmp / "base"
    allowed = make_skill_server(base, "claude", {"alpha": {"SKILL.md": "alpha content\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest, allowed)
        (dest / "local-only").mkdir()
        (dest / "local-only" / "SKILL.md").write_text("local\n", encoding="utf-8")
        run_setup("claude-setup.sh", "claude", base_url, dest, allowed)

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha content\n"
    assert (dest / "local-only" / "SKILL.md").read_text(encoding="utf-8") == "local\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_old_marker_entries_removed_when_upstream_removes_skill(work_tmp):
    base = work_tmp / "base"
    allowed = make_skill_server(base, "claude", {"alpha": {"SKILL.md": "alpha\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest, allowed)
        make_skill_server(base, "claude", {"beta": {"SKILL.md": "beta\n"}})
        run_setup("claude-setup.sh", "claude", base_url, dest, allowed)

    assert not (dest / "alpha").exists()
    assert (dest / "beta" / "SKILL.md").read_text(encoding="utf-8") == "beta\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "beta\n"


def test_fresh_install_writes_all_subfiles(work_tmp):
    base = work_tmp / "base"
    allowed = make_skill_server(base, "claude", {
        "alpha": {
            "SKILL.md": "alpha\n",
            "scripts/tool.sh": "echo tool\n",
        }
    })
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest, allowed)

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha\n"
    assert (dest / "alpha" / "scripts" / "tool.sh").read_text(encoding="utf-8") == "echo tool\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_artifact_verification_failure_leaves_existing_install_unchanged(work_tmp):
    base = work_tmp / "base"
    allowed = make_skill_server(base, "claude", {"alpha": {"SKILL.md": "old\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest, allowed)
        make_skill_server(base, "claude", {"alpha": {"SKILL.md": "new\n"}})
        (base / "skills" / "alpha" / "SKILL.md").write_text("tampered\n", encoding="utf-8")

        result = run_setup("claude-setup.sh", "claude", base_url, dest, allowed, check=False)

    assert result.returncode != 0
    assert "Verification failed" in result.stderr
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "old\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"
