import hashlib
import http.server
import importlib.util
import json
import shutil
import sys
import subprocess
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "public" / "skills" / "skills-hub" / "scripts" / "manage_cowork_skills.py"


def load_manager():
    spec = importlib.util.spec_from_file_location("manage_cowork_skills", MANAGER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_installed(root, name, body):
    skill_dir = root / "plugin" / "session" / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(body, encoding="utf-8")
    return skill_md


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


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


def write_signed_manifest(base_dir, key, *, skills=None, files=None):
    manifest = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 3600,
        "base_url": base_dir.resolve().as_uri(),
        "skills": skills or [],
        "files": files or {},
    }
    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest_path)], check=True)
    return manifest


def test_inventory_classifies_missing_stale_orphan_and_current(tmp_path):
    manager = load_manager()
    catalog = {
        "skills": [
            {"name": "alpha"},
            {"name": "beta"},
            {"name": "gamma"},
        ]
    }
    make_installed(
        tmp_path,
        "alpha",
        "Myskillium Verified Resolver Stub\npython myskillium-fetch.py cowork alpha\n",
    )
    make_installed(
        tmp_path,
        "beta",
        "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork beta\n",
    )
    make_installed(tmp_path, "orphan", "local skill\n")

    rows = {row.name: row for row in manager.build_inventory(catalog, manager.discover_installed([tmp_path]))}

    assert rows["alpha"].status == "stale-wrapper"
    assert rows["beta"].status == "current"
    assert rows["gamma"].status == "missing"
    assert rows["orphan"].status == "orphan"


def test_inventory_command_uses_explicit_manifest_without_repo_root(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"skills": [{"name": "alpha"}]}), encoding="utf-8")
    make_installed(tmp_path, "alpha", "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n")
    outside_repo = tmp_path / "outside"
    outside_repo.mkdir()
    monkeypatch.chdir(outside_repo)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=manifest,
            base_url=None,
            allowed_signers=None,
            json=True,
        )
    )

    rows = json.loads(capsys.readouterr().out)
    assert rows == [
        {
            "name": "alpha",
            "status": "current",
            "evidence": "current Skills-hub resolver wrapper",
            "path": str(tmp_path / "plugin" / "session" / "skills" / "alpha" / "SKILL.md"),
        }
    ]


def test_inventory_uses_verified_remote_manifest_without_repo_root(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    base = tmp_path / "base"
    base.mkdir()
    write_signed_manifest(base, key, skills=[{"name": "alpha"}])
    make_installed(tmp_path, "alpha", "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n")
    outside_repo = tmp_path / "outside"
    outside_repo.mkdir()
    monkeypatch.chdir(outside_repo)

    with serve_dir(base) as base_url:
        manager.cmd_inventory(
            SimpleNamespace(
                install_root=[str(tmp_path)],
                index=None,
                manifest=None,
                base_url=base_url,
                allowed_signers=allowed,
                json=True,
            )
        )

    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["status"] == "current"


def test_inventory_rejects_tampered_remote_manifest(tmp_path):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    base = tmp_path / "base"
    base.mkdir()
    write_signed_manifest(base, key, skills=[{"name": "alpha"}])
    (base / "manifest.json").write_text(json.dumps({"schema_version": 3, "skills": []}), encoding="utf-8")

    with serve_dir(base) as base_url, pytest.raises(SystemExit):
        manager.cmd_inventory(
            SimpleNamespace(
                install_root=[str(tmp_path)],
                index=None,
                manifest=None,
                base_url=base_url,
                allowed_signers=allowed,
                json=True,
            )
        )


def test_fetch_package_json_works_without_repo_root(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    base = tmp_path / "base"
    package_rel = "cowork/skill-packages/alpha.skill"
    package = base / package_rel
    package.parent.mkdir(parents=True)
    package.write_bytes(b"package")
    write_signed_manifest(
        base,
        key,
        skills=[{"name": "alpha"}],
        files={package_rel: {"sha256": sha256_bytes(b"package"), "size": len(b"package")}},
    )
    outside_repo = tmp_path / "outside"
    outside_repo.mkdir()
    monkeypatch.chdir(outside_repo)

    with serve_dir(base) as base_url:
        manager.cmd_fetch_package(
            SimpleNamespace(
                skill="alpha",
                base_url=base_url,
                output_dir=tmp_path / "out",
                allowed_signers=allowed,
                json=True,
            )
        )

    result = json.loads(capsys.readouterr().out)
    assert Path(result["package_path"]).read_bytes() == b"package"
    assert result["package_url"].endswith(package_rel)
    assert result["sha256"] == sha256_bytes(b"package")
    assert result["size"] == len(b"package")


def test_assimilate_writes_source_and_provenance(tmp_path, monkeypatch):
    manager = load_manager()
    repo = tmp_path / "repo"
    (repo / "public" / "skills").mkdir(parents=True)
    (repo / "build").mkdir()
    (repo / "build" / "build_index.py").write_text("# build\n", encoding="utf-8")
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "x.pyc").write_bytes(b"cache")
    monkeypatch.chdir(repo)

    manager.cmd_assimilate(SimpleNamespace(source=source, name="imported-skill", license="internal", github_pr=False))

    dest = repo / "public" / "skills" / "imported-skill"
    assert (dest / "SKILL.md").is_file()
    assert (dest / "PROVENANCE.md").read_text(encoding="utf-8").count("internal") == 1
    assert not (dest / "__pycache__").exists()


def test_assimilate_blocks_name_conflict(tmp_path, monkeypatch):
    manager = load_manager()
    repo = tmp_path / "repo"
    (repo / "public" / "skills" / "existing").mkdir(parents=True)
    (repo / "build").mkdir()
    (repo / "build" / "build_index.py").write_text("# build\n", encoding="utf-8")
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.chdir(repo)

    with pytest.raises(SystemExit):
        manager.cmd_assimilate(SimpleNamespace(source=source, name="existing", license="unknown", github_pr=False))


def test_assimilate_github_pr_uploads_selected_files(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    (source / ".secret").write_text("no\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "x.pyc").write_bytes(b"cache")
    (source / "source-skill.skill").write_bytes(b"zip")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    uploads = []

    def fake_github_request(method, path, token, data=None, expected=(200,)):
        if method == "GET" and path == "/repos/Mharbulous/skills-hub":
            return 200, {}
        if method == "GET" and path.startswith("/repos/Mharbulous/skills-hub/contents/public/skills/imported-skill"):
            return 404, {}
        if method == "GET" and path == "/repos/Mharbulous/skills-hub/git/ref/heads/main":
            return 200, {"object": {"sha": "base-sha"}}
        if method == "POST" and path == "/repos/Mharbulous/skills-hub/git/refs":
            return 201, {}
        if method == "PUT":
            uploads.append((path, data))
            return 201, {}
        if method == "POST" and path == "/repos/Mharbulous/skills-hub/pulls":
            return 201, {"html_url": "https://github.com/Mharbulous/skills-hub/pull/1"}
        raise AssertionError((method, path, data, expected))

    monkeypatch.setattr(manager, "github_request", fake_github_request)

    manager.cmd_assimilate(
        SimpleNamespace(
            source=source,
            name="imported-skill",
            license="internal",
            github_pr=True,
            repo="Mharbulous/skills-hub",
            base="main",
        )
    )

    assert capsys.readouterr().out.strip() == "https://github.com/Mharbulous/skills-hub/pull/1"
    uploaded_paths = [path for path, _ in uploads]
    assert any(path.endswith("/public/skills/imported-skill/SKILL.md") for path in uploaded_paths)
    assert any(path.endswith("/public/skills/imported-skill/PROVENANCE.md") for path in uploaded_paths)
    assert not any(".secret" in path or "__pycache__" in path or path.endswith(".skill") for path in uploaded_paths)


def test_assimilate_github_pr_requires_token(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(SystemExit):
        manager.cmd_assimilate(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_assimilate_github_pr_blocks_existing_target(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def fake_github_request(method, path, token, data=None, expected=(200,)):
        if method == "GET" and path == "/repos/Mharbulous/skills-hub":
            return 200, {}
        if method == "GET" and path.startswith("/repos/Mharbulous/skills-hub/contents/public/skills/imported-skill"):
            return 200, {"type": "dir"}
        raise AssertionError((method, path, data, expected))

    monkeypatch.setattr(manager, "github_request", fake_github_request)

    with pytest.raises(SystemExit):
        manager.cmd_assimilate(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_assimilate_github_pr_surfaces_api_failure(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def fake_github_request(method, path, token, data=None, expected=(200,)):
        raise SystemExit(1)

    monkeypatch.setattr(manager, "github_request", fake_github_request)

    with pytest.raises(SystemExit):
        manager.cmd_assimilate(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )
