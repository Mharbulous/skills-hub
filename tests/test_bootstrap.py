import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
from contextlib import contextmanager
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
    missing = [tool for tool in ("curl",) if shutil.which(tool) is None]
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
    """Create index.json and skill file tree under base/.

    skills: dict of skill_name -> dict of rel_path -> content
    """
    for skill_name, files in skills.items():
        for rel_path, content in files.items():
            file_path = base / "skills" / skill_name / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    entries = []
    for skill_name, files in skills.items():
        entries.append({
            "name": skill_name,
            "description": f"Test skill {skill_name}",
            "harnesses": {
                harness: {
                    "base": f"skills/{skill_name}",
                    "files": list(files.keys()),
                }
            },
        })

    index = {
        "schema_version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "skills": entries,
    }
    (base / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def run_setup(script_name, harness, base_url, dest, check=True):
    require_shell_tools()
    env = os.environ.copy()
    env["SKILLS_BASE_URL"] = base_url
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
    make_skill_server(base, harness, {"alpha": {"SKILL.md": "alpha content\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        result = run_setup(script_name, harness, base_url, dest)

    assert result.returncode == 0
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha content\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_rerun_is_idempotent_and_preserves_user_skill(work_tmp):
    base = work_tmp / "base"
    make_skill_server(base, "claude", {"alpha": {"SKILL.md": "alpha content\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest)
        (dest / "local-only").mkdir()
        (dest / "local-only" / "SKILL.md").write_text("local\n", encoding="utf-8")
        run_setup("claude-setup.sh", "claude", base_url, dest)

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha content\n"
    assert (dest / "local-only" / "SKILL.md").read_text(encoding="utf-8") == "local\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_old_marker_entries_removed_when_upstream_removes_skill(work_tmp):
    base = work_tmp / "base"
    make_skill_server(base, "claude", {"alpha": {"SKILL.md": "alpha\n"}})
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest)
        make_skill_server(base, "claude", {"beta": {"SKILL.md": "beta\n"}})
        run_setup("claude-setup.sh", "claude", base_url, dest)

    assert not (dest / "alpha").exists()
    assert (dest / "beta" / "SKILL.md").read_text(encoding="utf-8") == "beta\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "beta\n"


def test_fresh_install_writes_all_subfiles(work_tmp):
    base = work_tmp / "base"
    make_skill_server(base, "claude", {
        "alpha": {
            "SKILL.md": "alpha\n",
            "scripts/tool.sh": "echo tool\n",
        }
    })
    dest = work_tmp / "dest"

    with serve_dir(base) as base_url:
        run_setup("claude-setup.sh", "claude", base_url, dest)

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha\n"
    assert (dest / "alpha" / "scripts" / "tool.sh").read_text(encoding="utf-8") == "echo tool\n"
    assert (dest / ".skills-hub-managed-skills").read_text(encoding="utf-8") == "alpha\n"
