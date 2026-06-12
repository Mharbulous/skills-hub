import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def require_tools():
    if shutil.which("ssh-keygen") is None:
        pytest.skip("missing ssh-keygen")


@pytest.fixture
def work_tmp():
    parent = ROOT / ".test-tmp"
    parent.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="myskillium-resolver-", dir=parent))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def write_archive(path, skill_name="alpha", skill_body="verified alpha\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as tar:
        files = {
            f"{skill_name}/SKILL.md": skill_body,
            f"{skill_name}/reference/note.md": "reference\n",
        }
        for relpath, content in sorted(files.items()):
            data = content.encode("utf-8")
            info = tarfile.TarInfo(relpath)
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
    require_tools()
    key_path = temp_root / "signing_key"
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


def write_manifest(base, key_path, max_age_seconds=604800):
    files = {}
    for path in sorted(p for p in base.rglob("*") if p.is_file() and p.name not in {"manifest.json", "manifest.json.sig"}):
        rel = path.relative_to(base).as_posix()
        files[rel] = {"sha256": sha256(path), "size": path.stat().st_size}
    manifest = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": max_age_seconds,
        "canonical_base_url": base.resolve().as_uri(),
        "harnesses": ["cowork"],
        "skills": [],
        "files": files,
    }
    manifest_path = base / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key_path), "-n", "myskillium-manifest", str(manifest_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def make_base(temp_root):
    base = temp_root / "base"
    write_archive(base / "cowork" / "skills" / "alpha.tar.gz")
    key_path, allowed_signers = make_signing_key(temp_root)
    write_manifest(base, key_path)
    return base, allowed_signers


def run_fetch(base_url, allowed_signers, cache_dir, check=True):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "bootstrap" / "myskillium-fetch.py"),
            "cowork",
            "alpha",
            "--base-url",
            base_url,
            "--allowed-signers",
            str(allowed_signers),
            "--cache-dir",
            str(cache_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
        timeout=20,
    )


def test_resolver_materializes_verified_skill(work_tmp):
    base, allowed_signers = make_base(work_tmp)
    cache = work_tmp / "cache"

    result = run_fetch(base.resolve().as_uri(), allowed_signers, cache)
    skill_md = Path(result.stdout.strip())

    assert skill_md.is_file()
    assert skill_md.read_text(encoding="utf-8") == "verified alpha\n"
    assert (skill_md.parent / "reference" / "note.md").read_text(encoding="utf-8") == "reference\n"


def test_resolver_rejects_tampered_tarball_without_printing_content(work_tmp):
    base, allowed_signers = make_base(work_tmp)
    (base / "cowork" / "skills" / "alpha.tar.gz").write_text("pwned skill content\n", encoding="utf-8")

    result = run_fetch(base.resolve().as_uri(), allowed_signers, work_tmp / "cache", check=False)

    assert result.returncode != 0
    assert "pwned" not in result.stdout
    assert "pwned" not in result.stderr


def test_resolver_uses_fresh_cache_when_manifest_unavailable(work_tmp):
    base, allowed_signers = make_base(work_tmp)
    cache = work_tmp / "cache"
    first = run_fetch(base.resolve().as_uri(), allowed_signers, cache)

    result = run_fetch((work_tmp / "missing-base").resolve().as_uri(), allowed_signers, cache)

    assert result.stdout == first.stdout


def test_resolver_rejects_stale_cache_when_manifest_unavailable(work_tmp):
    base, allowed_signers = make_base(work_tmp)
    cache = work_tmp / "cache"
    first = run_fetch(base.resolve().as_uri(), allowed_signers, cache)
    skill_md = Path(first.stdout.strip())
    meta_path = skill_md.parent.parent / "myskillium-cache.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["generated_at"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    meta["max_age_seconds"] = 1
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    result = run_fetch((work_tmp / "missing-base").resolve().as_uri(), allowed_signers, cache, check=False)

    assert result.returncode != 0
    assert not result.stdout.strip()
