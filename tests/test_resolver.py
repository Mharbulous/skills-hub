import hashlib
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "public" / "bootstrap" / "skills-hub-fetch.py"


@pytest.fixture
def work_tmp():
    parent = ROOT / ".test-tmp"
    parent.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="skills-hub-resolver-", dir=parent))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def require_ssh_keygen():
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available")


@contextmanager
def serve_dir(directory):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def make_signing_material(base_dir):
    require_ssh_keygen()
    key = base_dir / "signing_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(key)], check=True)
    allowed = base_dir / "skills_hub_allowed_signers"
    allowed.write_text(
        f"skills-hub-manifest {(base_dir / 'signing_key.pub').read_text(encoding='utf-8')}",
        encoding="utf-8",
    )
    return key, allowed


def make_skill_server(base_dir, key, skill_name="alpha", files=None):
    if files is None:
        files = {"SKILL.md": f"# {skill_name}\nContent.\n", "ref/note.md": "reference\n"}

    file_entries = {}
    skill_dir = base_dir / "skills" / skill_name
    for rel, content in files.items():
        dest = skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        dest.write_bytes(data)
        file_entries[f"skills/{skill_name}/{rel}"] = {"sha256": sha256_bytes(data), "size": len(data)}

    file_list = list(files.keys())
    manifest = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 3600,
        "base_url": base_dir.resolve().as_uri(),
        "skills": [
            {
                "name": skill_name,
                "description": "test skill",
                "harnesses": {
                    h: {"base": f"skills/{skill_name}", "files": file_list}
                    for h in ["claude", "codex", "cowork"]
                },
            }
        ],
        "files": file_entries,
    }
    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest_path)], check=True)
    return base_dir


def run_fetch(base_url, cache_dir, allowed_signers, harness, skill, check=True):
    return subprocess.run(
        [
            sys.executable,
            str(RESOLVER),
            harness,
            skill,
            "--base-url",
            base_url,
            "--cache-dir",
            str(cache_dir),
            "--allowed-signers",
            str(allowed_signers),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
        timeout=20,
    )


def test_resolver_downloads_verified_skill_files(work_tmp):
    key, allowed = make_signing_material(work_tmp)
    base = make_skill_server(work_tmp / "base", key)
    cache = work_tmp / "cache"

    with serve_dir(base) as base_url:
        result = run_fetch(base_url, cache, allowed, "cowork", "alpha")
    skill_md = Path(result.stdout.strip())

    assert skill_md.is_file()
    assert "Content." in skill_md.read_text(encoding="utf-8")
    assert (skill_md.parent / "ref" / "note.md").read_text(encoding="utf-8") == "reference\n"


def test_resolver_fails_for_unknown_skill(work_tmp):
    key, allowed = make_signing_material(work_tmp)
    base = make_skill_server(work_tmp / "base", key)
    cache = work_tmp / "cache"

    with serve_dir(base) as base_url:
        result = run_fetch(base_url, cache, allowed, "cowork", "nosuchskill", check=False)

    assert result.returncode != 0
    assert not result.stdout.strip()


def test_resolver_rejects_hash_mismatch(work_tmp):
    key, allowed = make_signing_material(work_tmp)
    base = make_skill_server(work_tmp / "base", key)
    (base / "skills" / "alpha" / "SKILL.md").write_text("tampered\n", encoding="utf-8")
    cache = work_tmp / "cache"

    with serve_dir(base) as base_url:
        result = run_fetch(base_url, cache, allowed, "cowork", "alpha", check=False)

    assert result.returncode != 0
    assert "mismatch" in result.stderr
