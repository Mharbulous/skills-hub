import base64
import hashlib
import http.server
import importlib.util
import json
import shutil
import sys
import subprocess
import threading
import zipfile
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


def write_signed_packages(base_dir, key, package_data=b"package"):
    package_index = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 3600,
        "base_url": "https://mharbulous.github.io/skills-hub",
        "packages": [
            {
                "name": "alpha",
                "skill_path": "cowork/skill-packages/alpha.skill",
                "b64_path": "cowork/skill-packages/alpha.skill.b64.txt",
                "sha256": sha256_bytes(package_data),
                "size": len(package_data),
            }
        ],
    }
    packages_path = base_dir / "packages.json"
    packages_path.write_text(json.dumps(package_index, indent=2), encoding="utf-8")
    canonical = base_dir / "packages.canonical.json"
    canonical.write_text(
        json.dumps(package_index, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(canonical)], check=True)
    (base_dir / "packages.canonical.json.sig").replace(base_dir / "packages.json.sig")
    canonical.unlink()
    return packages_path, base_dir / "packages.json.sig"


def write_signed_packages_index(base_dir, key, names):
    package_index = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 3600,
        "base_url": "https://mharbulous.github.io/skills-hub",
        "packages": [
            {
                "name": name,
                "skill_path": f"cowork/skill-packages/{name}.skill",
                "b64_path": f"cowork/skill-packages/{name}.skill.b64.txt",
                "sha256": sha256_bytes(name.encode("utf-8")),
                "size": len(name),
            }
            for name in names
        ],
    }
    packages_path = base_dir / "packages.json"
    packages_path.write_text(json.dumps(package_index, indent=2), encoding="utf-8")
    canonical = base_dir / "packages.canonical.json"
    canonical.write_text(
        json.dumps(package_index, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(canonical)], check=True)
    (base_dir / "packages.canonical.json.sig").replace(base_dir / "packages.json.sig")
    canonical.unlink()
    return packages_path, base_dir / "packages.json.sig"


def make_repo_skill(repo_root, name, body="Body\n"):
    skill = repo_root / "public" / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\n{body}",
        encoding="utf-8",
    )
    return skill


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


def test_inventory_defaults_to_github_repo_archive(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    install_root = tmp_path / "install"
    make_repo_skill(repo, "alpha")
    make_repo_skill(repo, "beta")
    make_installed(install_root, "alpha", "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n")
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            signature=None,
            packages=None,
            packages_signature=None,
            base_url=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            allowed_signers=None,
            json=True,
            names=None,
        )
    )

    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert rows["alpha"]["status"] == "current"
    assert rows["beta"]["status"] == "missing"


def test_fetch_package_defaults_to_direct_github_skill_package(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    skill = make_repo_skill(repo, "alpha", body="Canonical alpha\n")
    (skill / "scripts").mkdir()
    (skill / "scripts" / "tool.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)

    manager.cmd_fetch_package(
        SimpleNamespace(
            skill="alpha",
            base_url=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            output_dir=tmp_path / "out",
            allowed_signers=None,
            json=True,
        )
    )

    result = json.loads(capsys.readouterr().out)
    package = Path(result["package_path"])
    assert package.is_file()
    assert result["package_url"] == "https://github.com/Mharbulous/skills-hub/tree/main/public/skills/alpha"
    with zipfile.ZipFile(package) as zf:
        names = set(zf.namelist())
        skill_md = zf.read("alpha/SKILL.md").decode("utf-8")
    assert names == {"alpha/SKILL.md", "alpha/scripts/tool.py"}
    assert "Canonical alpha" in skill_md
    assert "Skills-hub Verified Resolver Stub" not in skill_md


def test_inventory_autocorrects_skills_dir_root(tmp_path, capsys):
    manager = load_manager()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"skills": [{"name": "alpha"}]}), encoding="utf-8")
    skills_dir = tmp_path / ".claude" / "skills"
    alpha = skills_dir / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "SKILL.md").write_text(
        "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n",
        encoding="utf-8",
    )

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(skills_dir)],
            index=None,
            manifest=manifest,
            signature=None,
            base_url=None,
            allowed_signers=None,
            json=True,
        )
    )

    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert rows["alpha"]["status"] == "current"


def test_inventory_no_root_error_lists_attempts(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(manager, "skill_dir", lambda: tmp_path / "plugins" / "skills-hub")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"skills": [{"name": "alpha"}]}), encoding="utf-8")

    with pytest.raises(SystemExit):
        manager.cmd_inventory(
            SimpleNamespace(
                install_root=[],
                index=None,
                manifest=manifest,
                signature=None,
                base_url=None,
                allowed_signers=None,
                json=True,
                names=None,
            )
        )

    assert "--install-root" in capsys.readouterr().err


def test_fetch_package_unknown_skill_returns_structured_error(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    base = tmp_path / "base"
    base.mkdir()
    write_signed_manifest(base, key, skills=[{"name": "alpha"}], files={})
    out = tmp_path / "out"

    with serve_dir(base) as base_url:
        with pytest.raises(SystemExit):
            manager.cmd_fetch_package(
                SimpleNamespace(
                    skill="ghost",
                    base_url=base_url,
                    output_dir=out,
                    allowed_signers=allowed,
                    json=True,
                )
            )

    error = json.loads(capsys.readouterr().out)
    assert error == {"error": "skill not found in catalog", "skill": "ghost"}
    assert not (out / "ghost.skill").exists()


def test_fetch_package_unwritable_output_dir_returns_structured_error(tmp_path, capsys):
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
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")

    with serve_dir(base) as base_url:
        with pytest.raises(SystemExit):
            manager.cmd_fetch_package(
                SimpleNamespace(
                    skill="alpha",
                    base_url=base_url,
                    output_dir=blocker / "sub",
                    allowed_signers=allowed,
                    json=True,
                )
            )

    error = json.loads(capsys.readouterr().out)
    assert error["skill"] == "alpha"
    assert "--output-dir" in error["error"]


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
            signature=None,
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
                signature=None,
                base_url=base_url,
                allowed_signers=allowed,
                json=True,
            )
        )

    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["status"] == "current"


def test_inventory_degrades_when_remote_manifest_is_invalid(tmp_path, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    base = tmp_path / "base"
    base.mkdir()
    write_signed_manifest(base, key, skills=[{"name": "alpha"}])
    (base / "manifest.json").write_text(json.dumps({"schema_version": 3, "skills": []}), encoding="utf-8")
    make_installed(tmp_path, "alpha", "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n")

    with serve_dir(base) as base_url:
        manager.cmd_inventory(
            SimpleNamespace(
                install_root=[str(tmp_path)],
                index=None,
                manifest=None,
                signature=None,
                base_url=base_url,
                allowed_signers=allowed,
                json=True,
            )
        )

    output = json.loads(capsys.readouterr().out)
    assert output["catalog"]["status"] == "blocked"
    assert "invalid manifest generated_at timestamp" in output["catalog"]["error"]
    assert output["installed"] == [
        {
            "name": "alpha",
            "local_status": "skills-hub-wrapper",
            "evidence": "local Skills-hub resolver wrapper markers found",
            "path": str(tmp_path / "plugin" / "session" / "skills" / "alpha" / "SKILL.md"),
        }
    ]


def test_inventory_degrades_when_remote_manifest_unreachable(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    _, allowed = make_signing_material(tmp_path)
    make_installed(tmp_path, "alpha", "Myskillium Verified Resolver Stub\npython myskillium-fetch.py cowork alpha\n")

    def blocked_fetch(url):
        raise manager.urllib.error.URLError("network blocked")

    monkeypatch.setattr(manager, "fetch_bytes", blocked_fetch)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=None,
            signature=None,
            base_url="https://skills-hub.example.invalid",
            allowed_signers=allowed,
            json=True,
        )
    )

    output = json.loads(capsys.readouterr().out)
    assert output["catalog"]["status"] == "blocked"
    assert "could not download public manifest" in output["catalog"]["error"]
    assert output["installed"][0]["local_status"] == "stale-wrapper-marker"
    assert {row.get("status") for row in output["installed"]} == {None}


def test_inventory_degrades_with_empty_installed_when_remote_blocked_and_no_install_root(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    _, allowed = make_signing_material(tmp_path)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(manager, "skill_dir", lambda: tmp_path / "plugins" / "skills-hub")

    def blocked_fetch(url):
        raise manager.urllib.error.URLError("network blocked")

    monkeypatch.setattr(manager, "fetch_bytes", blocked_fetch)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[],
            index=None,
            manifest=None,
            signature=None,
            base_url="https://skills-hub.example.invalid",
            allowed_signers=allowed,
            json=True,
            names=None,
        )
    )

    output = json.loads(capsys.readouterr().out)
    assert output["catalog"]["status"] == "blocked"
    assert output["installed"] == []


def test_inventory_command_uses_signed_packages_index_for_text_fallback(tmp_path, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    packages, signature = write_signed_packages_index(tmp_path, key, ["alpha", "beta"])
    make_installed(tmp_path, "alpha", "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n")
    make_installed(tmp_path, "orphan", "local skill\n")

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=None,
            signature=None,
            packages=packages,
            packages_signature=signature,
            base_url=None,
            allowed_signers=allowed,
            json=True,
        )
    )

    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert rows["alpha"]["status"] == "current"
    assert rows["beta"]["status"] == "missing"
    assert rows["orphan"]["status"] == "orphan"


def test_inventory_command_verifies_explicit_manifest_when_signature_supplied(tmp_path, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "max_age_seconds": 3600,
                "skills": [{"name": "alpha"}],
                "files": {},
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest)], check=True)
    make_installed(tmp_path, "alpha", "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n")

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=manifest,
            signature=tmp_path / "manifest.json.sig",
            base_url=None,
            allowed_signers=allowed,
            json=True,
        )
    )

    assert json.loads(capsys.readouterr().out)[0]["status"] == "current"


def test_inventory_command_degrades_when_explicit_manifest_signature_fails(tmp_path, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "max_age_seconds": 3600,
                "skills": [{"name": "alpha"}],
                "files": {},
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest)], check=True)
    manifest.write_text(json.dumps({"schema_version": 3, "skills": []}), encoding="utf-8")
    make_installed(tmp_path, "alpha", "local skill\n")

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=manifest,
            signature=tmp_path / "manifest.json.sig",
            base_url=None,
            allowed_signers=allowed,
            json=True,
        )
    )

    output = json.loads(capsys.readouterr().out)
    assert output["catalog"]["status"] == "blocked"
    assert "manifest signature verification failed" in output["catalog"]["error"]
    assert output["installed"][0]["local_status"] == "unrecognized"


def test_inventory_command_keeps_malformed_manifest_as_hard_error(tmp_path):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("not json", encoding="utf-8")
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest)], check=True)

    with pytest.raises(SystemExit):
        manager.cmd_inventory(
            SimpleNamespace(
                install_root=[str(tmp_path)],
                index=None,
                manifest=manifest,
                signature=tmp_path / "manifest.json.sig",
                base_url=None,
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


def test_decode_package_json_works_from_text_artifacts(tmp_path, capsys):
    manager = load_manager()
    key, allowed = make_signing_material(tmp_path)
    packages, signature = write_signed_packages(tmp_path, key, b"package")
    packages.write_bytes(packages.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    signature.write_bytes(signature.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    b64 = tmp_path / "alpha.skill.b64.txt"
    b64.write_text("\r\n".join(base64.b64encode(b"package").decode("ascii")), encoding="ascii")

    manager.cmd_decode_package(
        SimpleNamespace(
            skill="alpha",
            packages=packages,
            signature=signature,
            output_dir=tmp_path / "out",
            allowed_signers=allowed,
            b64=b64,
            json=True,
        )
    )

    result = json.loads(capsys.readouterr().out)
    assert Path(result["package_path"]).read_bytes() == b"package"
    assert result["package_url"] == "https://mharbulous.github.io/skills-hub/cowork/skill-packages/alpha.skill"
    assert result["b64_url"] == "https://mharbulous.github.io/skills-hub/cowork/skill-packages/alpha.skill.b64.txt"


def test_absorb_writes_source_and_provenance(tmp_path, monkeypatch):
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

    manager.cmd_absorb(SimpleNamespace(source=source, name="imported-skill", license="internal", github_pr=False))

    dest = repo / "public" / "skills" / "imported-skill"
    assert (dest / "SKILL.md").is_file()
    assert (dest / "PROVENANCE.md").read_text(encoding="utf-8").count("internal") == 1
    assert not (dest / "__pycache__").exists()


def test_absorb_blocks_name_conflict(tmp_path, monkeypatch):
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
        manager.cmd_absorb(SimpleNamespace(source=source, name="existing", license="unknown", github_pr=False))


def test_absorb_github_pr_uploads_selected_files(tmp_path, monkeypatch, capsys):
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

    manager.cmd_absorb(
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


def test_absorb_github_pr_requires_token(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(SystemExit):
        manager.cmd_absorb(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_absorb_github_pr_blocks_existing_target(tmp_path, monkeypatch):
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
        manager.cmd_absorb(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_absorb_github_pr_surfaces_api_failure(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def fake_github_request(method, path, token, data=None, expected=(200,)):
        raise SystemExit(1)

    monkeypatch.setattr(manager, "github_request", fake_github_request)

    with pytest.raises(SystemExit):
        manager.cmd_absorb(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_inventory_names_filter(tmp_path, capsys):
    manager = load_manager()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"skills": [{"name": "alpha"}, {"name": "beta"}, {"name": "gamma"}]}),
        encoding="utf-8",
    )
    make_installed(
        tmp_path, "alpha",
        "Skills-hub Verified Resolver Stub\npython skills-hub-fetch.py cowork alpha\n",
    )

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None, manifest=manifest, signature=None,
            base_url=None, allowed_signers=None, json=True,
            names="alpha,gamma",
        )
    )

    rows = json.loads(capsys.readouterr().out)
    names = {r["name"] for r in rows}
    assert names == {"alpha", "gamma"}
    assert "beta" not in names


def test_skill_dir_install_root_fallback(tmp_path, monkeypatch):
    manager = load_manager()
    skills_dir = tmp_path / "skills"
    hub_dir = skills_dir / "skills-hub"
    hub_dir.mkdir(parents=True)
    monkeypatch.setattr(manager, "skill_dir", lambda: hub_dir)
    roots = manager.skill_dir_install_root()
    assert roots == [tmp_path]


def test_skill_dir_install_root_no_match(tmp_path, monkeypatch):
    manager = load_manager()
    other_dir = tmp_path / "plugins" / "skills-hub"
    other_dir.mkdir(parents=True)
    monkeypatch.setattr(manager, "skill_dir", lambda: other_dir)
    roots = manager.skill_dir_install_root()
    assert roots == []
