import io
import json
import os
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
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
    path = Path(tempfile.mkdtemp(prefix="myskillium-bootstrap-", dir=parent))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def require_shell_tools():
    missing = [tool for tool in ("curl", "tar", "ssh-keygen") if shutil.which(tool) is None]
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


def write_archive(path, skills):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as tar:
        for skill_name, files in sorted(skills.items()):
            for rel_path, content in sorted(files.items()):
                data = content.encode("utf-8")
                info = tarfile.TarInfo(f"{skill_name}/{rel_path}")
                info.size = len(data)
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                tar.addfile(info, io.BytesIO(data))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_signing_key(temp_root):
    require_shell_tools()
    key_path = temp_root / "signing_key"
    if not key_path.exists():
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "myskillium-test", "-f", str(key_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    allowed_signers = temp_root / "allowed_signers"
    pub = (key_path.with_suffix(".pub")).read_text(encoding="utf-8").strip()
    allowed_signers.write_text(f"myskillium-manifest {pub}\n", encoding="utf-8")
    return key_path, allowed_signers


def write_manifest(base, key_path):
    files = {}
    for path in sorted(p for p in base.rglob("*") if p.is_file() and p.name not in {"manifest.json", "manifest.json.sig"}):
        rel = path.relative_to(base).as_posix()
        files[rel] = {"sha256": sha256(path), "size": path.stat().st_size}
    manifest = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 604800,
        "canonical_base_url": base.resolve().as_uri(),
        "harnesses": ["claude", "codex", "cowork"],
        "skills": [],
        "files": files,
    }
    manifest_path = base / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sig_path = base / "manifest.json.sig"
    if sig_path.exists():
        sig_path.unlink()
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key_path), "-n", "myskillium-manifest", str(manifest_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def make_base(temp_root, harness, stub_skills=None, full_skills=None):
    base = temp_root / "base"
    harness_dir = base / harness
    write_archive(
        harness_dir / "skill-stubs.tar.gz",
        stub_skills or {"alpha": {"SKILL.md": "stub alpha\n"}},
    )
    write_archive(
        harness_dir / "skills.tar.gz",
        full_skills or {"alpha": {"SKILL.md": "full alpha\n", "scripts/tool.sh": "echo full\n"}},
    )
    key_path, allowed_signers = make_signing_key(temp_root)
    write_manifest(base, key_path)
    return base, allowed_signers


def run_setup(script_name, harness, base, allowed_signers, dest, *args, check=True):
    require_shell_tools()
    env = os.environ.copy()
    env["SKILLS_BASE_URL"] = base.resolve().as_uri()
    bash = Path(find_git_bash())
    git_root = bash.parent.parent
    env["PATH"] = os.pathsep.join(
        [
            str(git_root / "usr" / "bin"),
            str(git_root / "bin"),
            env.get("PATH", ""),
        ]
    )
    env["MYSKILLIUM_ALLOWED_SIGNERS"] = bash_path(allowed_signers)
    command = [str(bash), f"bootstrap/{script_name}", *args, bash_arg(dest)]
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=check,
        timeout=15,
    )


@pytest.mark.parametrize(
    ("script_name", "harness"),
    [("claude-setup.sh", "claude"), ("codex-setup.sh", "codex")],
)
def test_fresh_stub_install_writes_marker_for_each_harness(work_tmp, script_name, harness):
    base, allowed_signers = make_base(work_tmp, harness)
    dest = work_tmp / "dest"

    result = run_setup(script_name, harness, base, allowed_signers, dest)

    assert result.returncode == 0
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "full alpha\n"
    assert (dest / "alpha" / "scripts" / "tool.sh").read_text(encoding="utf-8") == "echo full\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_rerun_is_idempotent_and_preserves_user_skill(work_tmp):
    base, allowed_signers = make_base(work_tmp, "claude", full_skills={"alpha": {"SKILL.md": "full alpha\n"}})
    dest = work_tmp / "dest"
    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)
    (dest / "local-only").mkdir()
    (dest / "local-only" / "SKILL.md").write_text("local\n", encoding="utf-8")

    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "full alpha\n"
    assert (dest / "local-only" / "SKILL.md").read_text(encoding="utf-8") == "local\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_pre_marker_full_install_is_replaced_by_stub(work_tmp):
    base, allowed_signers = make_base(work_tmp, "claude", full_skills={"alpha": {"SKILL.md": "new full\n"}})
    dest = work_tmp / "dest"
    (dest / "alpha" / "scripts").mkdir(parents=True)
    (dest / "alpha" / "SKILL.md").write_text("old full\n", encoding="utf-8")
    (dest / "alpha" / "scripts" / "old.sh").write_text("old\n", encoding="utf-8")

    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "new full\n"
    assert not (dest / "alpha" / "scripts").exists()


def test_old_marker_entries_removed_when_upstream_removes_skill(work_tmp):
    base, allowed_signers = make_base(work_tmp, "claude", full_skills={"alpha": {"SKILL.md": "alpha\n"}})
    dest = work_tmp / "dest"
    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)

    write_archive(base / "claude" / "skills.tar.gz", {"beta": {"SKILL.md": "beta\n"}})
    write_archive(base / "claude" / "skill-stubs.tar.gz", {"beta": {"SKILL.md": "beta stub\n"}})
    key_path = work_tmp / "signing_key"
    write_manifest(base, key_path)
    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)

    assert not (dest / "alpha").exists()
    assert (dest / "beta" / "SKILL.md").read_text(encoding="utf-8") == "beta\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "beta\n"


def test_invalid_archive_leaves_prior_install_and_marker_untouched(work_tmp):
    base, allowed_signers = make_base(work_tmp, "claude", full_skills={"alpha": {"SKILL.md": "alpha\n"}})
    dest = work_tmp / "dest"
    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)
    (base / "claude" / "skills.tar.gz").write_text("not a tarball\n", encoding="utf-8")
    key_path = work_tmp / "signing_key"
    write_manifest(base, key_path)

    result = run_setup("claude-setup.sh", "claude", base, allowed_signers, dest, check=False)

    assert result.returncode != 0
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_full_mode_installs_full_bundle_with_same_cleanup_semantics(work_tmp):
    base, allowed_signers = make_base(
        work_tmp,
        "codex",
        stub_skills={"alpha": {"SKILL.md": "stub alpha\n"}},
        full_skills={"alpha": {"SKILL.md": "full alpha\n", "scripts/tool.sh": "echo full\n"}},
    )
    dest = work_tmp / "dest"

    run_setup("codex-setup.sh", "codex", base, allowed_signers, dest, "--full")

    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "full alpha\n"
    assert (dest / "alpha" / "scripts" / "tool.sh").read_text(encoding="utf-8") == "echo full\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_tampered_archive_hash_leaves_prior_install_and_marker_untouched(work_tmp):
    base, allowed_signers = make_base(work_tmp, "claude", full_skills={"alpha": {"SKILL.md": "alpha\n"}})
    dest = work_tmp / "dest"
    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)
    (base / "claude" / "skills.tar.gz").write_text("tampered after manifest sign\n", encoding="utf-8")

    result = run_setup("claude-setup.sh", "claude", base, allowed_signers, dest, check=False)

    assert result.returncode != 0
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "alpha\n"


def test_bad_manifest_signature_leaves_prior_install_and_marker_untouched(work_tmp):
    base, allowed_signers = make_base(work_tmp, "claude", full_skills={"alpha": {"SKILL.md": "alpha\n"}})
    dest = work_tmp / "dest"
    run_setup("claude-setup.sh", "claude", base, allowed_signers, dest)
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"]["claude/skills.tar.gz"]["size"] += 1
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_setup("claude-setup.sh", "claude", base, allowed_signers, dest, check=False)

    assert result.returncode != 0
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "alpha\n"
    assert (dest / ".myskillium-managed-skills").read_text(encoding="utf-8") == "alpha\n"
