import json
import shutil
import subprocess
import sys
import tempfile
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


def make_skill_server(base_dir, skill_name, files=None):
    """Create a static file tree mimicking the Firebase public/ layout."""
    if files is None:
        files = {"SKILL.md": f"# {skill_name}\nContent.\n", "ref/note.md": "reference\n"}

    skill_dir = base_dir / "skills" / skill_name
    for rel, content in files.items():
        dest = skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    file_list = list(files.keys())
    index = {
        "schema_version": 1,
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
    }
    (base_dir / "index.json").write_bytes(json.dumps(index).encode("utf-8"))
    return base_dir


def run_fetch(base_url, cache_dir, harness, skill, check=True):
    return subprocess.run(
        [sys.executable, str(RESOLVER), harness, skill, "--base-url", base_url, "--cache-dir", str(cache_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
        timeout=20,
    )


def test_resolver_downloads_skill_files(work_tmp):
    base = make_skill_server(work_tmp / "base", "alpha")
    cache = work_tmp / "cache"

    result = run_fetch(base.resolve().as_uri(), cache, "cowork", "alpha")
    skill_md = Path(result.stdout.strip())

    assert skill_md.is_file()
    assert "Content." in skill_md.read_text(encoding="utf-8")
    assert (skill_md.parent / "ref" / "note.md").read_text(encoding="utf-8") == "reference\n"


def test_resolver_falls_back_to_cache_when_offline(work_tmp):
    base = make_skill_server(work_tmp / "base", "alpha")
    cache = work_tmp / "cache"
    first = run_fetch(base.resolve().as_uri(), cache, "cowork", "alpha")

    result = run_fetch((work_tmp / "nonexistent").resolve().as_uri(), cache, "cowork", "alpha")

    assert result.returncode == 0
    assert result.stdout.strip() == first.stdout.strip()


def test_resolver_fails_when_offline_and_no_cache(work_tmp):
    cache = work_tmp / "cache"

    result = run_fetch((work_tmp / "nonexistent").resolve().as_uri(), cache, "cowork", "alpha", check=False)

    assert result.returncode != 0
    assert not result.stdout.strip()


def test_resolver_fails_for_unknown_skill(work_tmp):
    base = make_skill_server(work_tmp / "base", "alpha")
    cache = work_tmp / "cache"

    result = run_fetch(base.resolve().as_uri(), cache, "cowork", "nosuchskill", check=False)

    assert result.returncode != 0


def test_resolver_overwrites_cache_on_refetch(work_tmp):
    base = make_skill_server(work_tmp / "base", "alpha", {"SKILL.md": "version 1\n"})
    cache = work_tmp / "cache"
    run_fetch(base.resolve().as_uri(), cache, "cowork", "alpha")

    # Update the server content
    (base / "skills" / "alpha" / "SKILL.md").write_text("version 2\n", encoding="utf-8")

    result = run_fetch(base.resolve().as_uri(), cache, "cowork", "alpha")
    skill_md = Path(result.stdout.strip())
    assert skill_md.read_text(encoding="utf-8") == "version 2\n"
