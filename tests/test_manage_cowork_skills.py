import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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


def make_repo_skill(repo_root, name, body="Body\n"):
    skill = repo_root / "public" / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}\n---\n\n{body}",
        encoding="utf-8",
    )
    return skill


def repo_skill_body(name, body="Body\n"):
    return f"---\nname: {name}\ndescription: Test {name}\n---\n\n{body}"


def test_inventory_classifies_missing_stale_orphan_and_current(tmp_path):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    make_installed(tmp_path, "alpha", alpha_body)
    alpha_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    make_installed(tmp_path, "beta", "---\nname: beta\n---\n\nOld content\n")
    make_installed(tmp_path, "orphan", "local skill\n")

    catalog = {
        "skills": [
            {"name": "alpha", "content_hash": alpha_hash},
            {"name": "beta", "content_hash": "different-hash-value"},
            {"name": "gamma"},
        ]
    }

    manager.record_install(tmp_path, "alpha", alpha_hash, "Mharbulous/skills-hub@main")

    rows = {row.name: row for row in manager.build_inventory(catalog, manager.discover_installed([tmp_path]), [tmp_path])}

    assert rows["alpha"].status == "current"
    assert rows["beta"].status == "stale"
    assert rows["gamma"].status == "missing"
    assert rows["orphan"].status == "orphan"


def test_inventory_defaults_to_github_repo_archive(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    install_root = tmp_path / "install"
    make_repo_skill(repo, "alpha")
    make_repo_skill(repo, "beta")
    make_installed(install_root, "alpha", repo_skill_body("alpha"))
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
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
            repo="Mharbulous/skills-hub",
            ref="main",
            output_dir=tmp_path / "out",
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


def test_inventory_autocorrects_skills_dir_root(tmp_path, capsys):
    manager = load_manager()
    skills_dir = tmp_path / ".claude" / "skills"
    alpha_dir = skills_dir / "alpha"
    alpha_dir.mkdir(parents=True)
    alpha_body = repo_skill_body("alpha")
    (alpha_dir / "SKILL.md").write_text(alpha_body, encoding="utf-8")
    alpha_hash = manager.content_hash(alpha_dir)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"skills": [{"name": "alpha", "content_hash": alpha_hash}]}),
        encoding="utf-8",
    )

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(skills_dir)],
            index=None,
            manifest=manifest,
            json=True,
            names=None,
        )
    )

    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert rows["alpha"]["status"] == "current"


def test_inventory_no_root_error_lists_attempts(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(manager, "skill_dir", lambda: tmp_path / "plugins" / "skills-hub")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "nohome"))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"skills": [{"name": "alpha"}]}), encoding="utf-8")

    with pytest.raises(SystemExit):
        manager.cmd_inventory(
            SimpleNamespace(
                install_root=[],
                index=None,
                manifest=manifest,
                json=True,
                names=None,
            )
        )

    assert "--install-root" in capsys.readouterr().err


def test_inventory_command_uses_explicit_manifest(tmp_path, capsys):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    make_installed(tmp_path, "alpha", alpha_body)
    alpha_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"skills": [{"name": "alpha", "content_hash": alpha_hash}]}),
        encoding="utf-8",
    )

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=manifest,
            json=True,
            names=None,
        )
    )

    rows = json.loads(capsys.readouterr().out)
    assert rows == [
        {
            "name": "alpha",
            "status": "current",
            "evidence": "content matches GitHub source",
            "path": str(tmp_path / "plugin" / "session" / "skills" / "alpha" / "SKILL.md"),
        }
    ]


def test_inventory_degrades_when_github_unreachable(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    make_installed(tmp_path, "alpha", "some content\n")

    def blocked_fetch(repo_name, ref, dest):
        raise manager.urllib.error.URLError("network blocked")

    monkeypatch.setattr(manager, "fetch_github_repo", blocked_fetch)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=None,
            json=True,
            names=None,
        )
    )

    output = json.loads(capsys.readouterr().out)
    assert output["catalog"]["status"] == "blocked"
    assert output["installed"][0]["local_status"] == "installed"


def test_inventory_degrades_with_empty_installed_when_github_blocked_and_no_install_root(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(manager, "skill_dir", lambda: tmp_path / "plugins" / "skills-hub")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "nohome"))

    def blocked_fetch(repo_name, ref, dest):
        raise manager.urllib.error.URLError("network blocked")

    monkeypatch.setattr(manager, "fetch_github_repo", blocked_fetch)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[],
            index=None,
            manifest=None,
            json=True,
            names=None,
        )
    )

    output = json.loads(capsys.readouterr().out)
    assert output["catalog"]["status"] == "blocked"
    assert output["installed"] == []


def test_inventory_names_filter(tmp_path, capsys):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    make_installed(tmp_path, "alpha", alpha_body)
    alpha_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"skills": [
            {"name": "alpha", "content_hash": alpha_hash},
            {"name": "beta"},
            {"name": "gamma"},
        ]}),
        encoding="utf-8",
    )

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(tmp_path)],
            index=None,
            manifest=manifest,
            json=True,
            names="alpha,gamma",
        )
    )

    rows = json.loads(capsys.readouterr().out)
    names = {r["name"] for r in rows}
    assert names == {"alpha", "gamma"}
    assert "beta" not in names


def test_direct_install_then_inventory_shows_current(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    make_repo_skill(repo, "alpha", body="Canonical alpha content.\n")
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)

    manager.cmd_fetch_package(
        SimpleNamespace(
            skill="alpha",
            repo="Mharbulous/skills-hub",
            ref="main",
            output_dir=tmp_path / "out",
            json=True,
        )
    )
    result = json.loads(capsys.readouterr().out)

    install_root = tmp_path / "cowork"
    with zipfile.ZipFile(result["package_path"]) as zf:
        zf.extractall(install_root / "skills")

    manager.record_install(install_root, "alpha", result["content_hash"], result["source_ref"])
    assert (install_root / manager.LOCKFILE_NAME).is_file()

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            json=True,
            names=None,
        )
    )

    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert rows["alpha"]["status"] == "current"


def test_push_writes_source_and_provenance(tmp_path, monkeypatch):
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

    manager.cmd_push(SimpleNamespace(source=source, name="imported-skill", license="internal", github_pr=False))

    dest = repo / "public" / "skills" / "imported-skill"
    assert (dest / "SKILL.md").is_file()
    assert (dest / "PROVENANCE.md").read_text(encoding="utf-8").count("internal") == 1
    assert not (dest / "__pycache__").exists()


def test_push_blocks_name_conflict(tmp_path, monkeypatch):
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
        manager.cmd_push(SimpleNamespace(source=source, name="existing", license="unknown", github_pr=False))


def test_push_github_pr_uploads_selected_files(tmp_path, monkeypatch, capsys):
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

    manager.cmd_push(
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


def test_push_github_pr_requires_token(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(SystemExit):
        manager.cmd_push(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_push_github_pr_blocks_existing_target(tmp_path, monkeypatch):
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
        manager.cmd_push(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


def test_push_github_pr_surfaces_api_failure(tmp_path, monkeypatch):
    manager = load_manager()
    source = tmp_path / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: source-skill\ndescription: Test\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def fake_github_request(method, path, token, data=None, expected=(200,)):
        raise SystemExit(1)

    monkeypatch.setattr(manager, "github_request", fake_github_request)

    with pytest.raises(SystemExit):
        manager.cmd_push(
            SimpleNamespace(
                source=source,
                name="imported-skill",
                license="internal",
                github_pr=True,
                repo="Mharbulous/skills-hub",
                base="main",
            )
        )


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


def test_skill_dir_install_root_cowork_plugin_cache(tmp_path, monkeypatch):
    manager = load_manager()
    cache_root = tmp_path / "skills-plugin"
    hub_dir = cache_root / "sess-uuid" / "plugin-uuid" / "skills" / "skills-hub"
    hub_dir.mkdir(parents=True)
    monkeypatch.setattr(manager, "skill_dir", lambda: hub_dir)
    roots = manager.skill_dir_install_root()
    assert roots == [cache_root]


def test_skill_dir_install_root_remote_plugins(tmp_path, monkeypatch):
    manager = load_manager()
    mount = tmp_path / "mnt"
    plugin_dir = mount / ".remote-plugins" / "plugin_018abc" / "skills" / "skills-hub"
    scripts_dir = plugin_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    user_skill = mount / ".claude" / "skills" / "vision"
    user_skill.mkdir(parents=True)
    (user_skill / "SKILL.md").write_text("---\nname: vision\n---\n", encoding="utf-8")
    monkeypatch.setattr(manager, "script_dir", lambda: scripts_dir)
    roots = manager.skill_dir_install_root()
    assert roots == [mount / ".claude"]


def test_skill_dir_install_root_remote_plugins_no_claude_dir(tmp_path, monkeypatch):
    manager = load_manager()
    mount = tmp_path / "mnt"
    plugin_dir = mount / ".remote-plugins" / "plugin_018abc" / "skills" / "skills-hub"
    scripts_dir = plugin_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    monkeypatch.setattr(manager, "script_dir", lambda: scripts_dir)
    roots = manager.skill_dir_install_root()
    assert roots == [mount / ".remote-plugins" / "plugin_018abc"]


def test_default_install_roots_home_fallback(tmp_path, monkeypatch):
    manager = load_manager()
    other_dir = tmp_path / "plugins" / "skills-hub"
    other_dir.mkdir(parents=True)
    monkeypatch.setattr(manager, "skill_dir", lambda: other_dir)
    claude_home = tmp_path / "fakehome" / ".claude"
    (claude_home / "skills").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "fakehome"))
    monkeypatch.delenv("APPDATA", raising=False)
    roots = manager.default_install_roots()
    assert claude_home in roots


# --- Lockfile tests ---


def test_read_lockfile_missing_returns_empty(tmp_path):
    manager = load_manager()
    assert manager.read_lockfile(tmp_path) == {}


def test_read_lockfile_corrupt_returns_empty(tmp_path):
    manager = load_manager()
    (tmp_path / manager.LOCKFILE_NAME).write_text("not json {{{", encoding="utf-8")
    assert manager.read_lockfile(tmp_path) == {}


def test_record_install_creates_lockfile(tmp_path):
    manager = load_manager()
    manager.record_install(tmp_path, "alpha", "abc123", "Mharbulous/skills-hub@main")
    lock = manager.read_lockfile(tmp_path)
    assert "alpha" in lock
    assert lock["alpha"]["content_hash"] == "abc123"
    assert lock["alpha"]["source_ref"] == "Mharbulous/skills-hub@main"
    assert "installed_at" in lock["alpha"]


def test_record_install_upserts_existing(tmp_path):
    manager = load_manager()
    manager.record_install(tmp_path, "alpha", "hash1", "repo@v1")
    manager.record_install(tmp_path, "beta", "hash2", "repo@v1")
    lock = manager.read_lockfile(tmp_path)
    assert "alpha" in lock
    assert "beta" in lock

    manager.record_install(tmp_path, "alpha", "hash3", "repo@v2")
    lock = manager.read_lockfile(tmp_path)
    assert lock["alpha"]["content_hash"] == "hash3"
    assert lock["beta"]["content_hash"] == "hash2"


def test_merge_lockfiles_across_roots(tmp_path):
    manager = load_manager()
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    manager.record_install(root_a, "alpha", "hash_a", "repo@v1")
    manager.record_install(root_b, "beta", "hash_b", "repo@v1")
    merged = manager.merge_lockfiles([root_a, root_b])
    assert "alpha" in merged
    assert "beta" in merged

    manager.record_install(root_b, "alpha", "hash_a2", "repo@v2")
    merged = manager.merge_lockfiles([root_a, root_b])
    assert merged["alpha"]["content_hash"] == "hash_a2"


# --- Three-way classification tests ---


def test_classify_current_ignores_lockfile(tmp_path):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    make_installed(tmp_path, "alpha", alpha_body)
    installed_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    installed = manager.discover_installed([tmp_path])
    row = manager.classify_installed("alpha", installed["alpha"], catalog_hash=installed_hash, lock_hash=installed_hash)
    assert row.status == "current"


def test_classify_stale_with_lockfile(tmp_path):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    make_installed(tmp_path, "alpha", alpha_body)
    installed_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    installed = manager.discover_installed([tmp_path])
    row = manager.classify_installed("alpha", installed["alpha"], catalog_hash="new-catalog-hash", lock_hash=installed_hash)
    assert row.status == "stale"
    assert "safe to update" in row.evidence


def test_classify_modified_when_user_edited(tmp_path):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    skill_md = make_installed(tmp_path, "alpha", alpha_body)
    original_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    skill_md.write_text(alpha_body + "\nuser edit\n", encoding="utf-8")
    installed = manager.discover_installed([tmp_path])
    row = manager.classify_installed("alpha", installed["alpha"], catalog_hash=original_hash, lock_hash=original_hash)
    assert row.status == "modified"
    assert "locally edited" in row.evidence


def test_classify_diverged_when_both_changed(tmp_path):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    skill_md = make_installed(tmp_path, "alpha", alpha_body)
    original_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    skill_md.write_text(alpha_body + "\nuser edit\n", encoding="utf-8")
    installed = manager.discover_installed([tmp_path])
    row = manager.classify_installed("alpha", installed["alpha"], catalog_hash="new-catalog-hash", lock_hash=original_hash)
    assert row.status == "diverged"
    assert "local edits and hub updates" in row.evidence


def test_classify_stale_without_lockfile(tmp_path):
    manager = load_manager()
    make_installed(tmp_path, "alpha", "some content\n")
    installed = manager.discover_installed([tmp_path])
    row = manager.classify_installed("alpha", installed["alpha"], catalog_hash="different-hash")
    assert row.status == "stale"
    assert "no install record" in row.evidence


def test_classify_current_when_no_catalog_hash_but_lock_matches(tmp_path):
    manager = load_manager()
    alpha_body = repo_skill_body("alpha")
    make_installed(tmp_path, "alpha", alpha_body)
    installed_hash = manager.content_hash(tmp_path / "plugin" / "session" / "skills" / "alpha")
    installed = manager.discover_installed([tmp_path])
    row = manager.classify_installed("alpha", installed["alpha"], catalog_hash=None, lock_hash=installed_hash)
    assert row.status == "current"
    assert "unchanged since install" in row.evidence


# --- Catalog cache tests ---


def test_cached_catalog_enables_offline_staleness(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    install_root = tmp_path / "install"
    make_repo_skill(repo, "alpha")
    make_installed(install_root, "alpha", repo_skill_body("alpha"))
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            json=True,
            names=None,
        )
    )
    capsys.readouterr()
    assert (install_root / manager.CATALOG_CACHE_NAME).is_file()

    def blocked_fetch(repo_name, ref, dest):
        raise manager.urllib.error.URLError("network blocked")

    monkeypatch.setattr(manager, "fetch_github_repo", blocked_fetch)
    # Also block the SHA check so the fast path doesn't short-circuit to the cache
    # without going through the CatalogUnavailable offline-fallback path.
    monkeypatch.setattr(manager, "github_head_sha", lambda r, ref: None)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            json=True,
            names=None,
        )
    )

    rows = json.loads(capsys.readouterr().out)
    alpha = {r["name"]: r for r in rows}["alpha"]
    assert alpha["status"] == "current"
    assert "offline" in alpha["evidence"]


# --- FetchResult fields test ---


def test_fetch_package_includes_content_hash_and_source_ref(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    make_repo_skill(repo, "alpha", body="Test content\n")
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)
    # Block SHA lookup so source_ref falls back to repo@ref format.
    monkeypatch.setattr(manager, "github_head_sha", lambda r, ref: None)

    manager.cmd_fetch_package(
        SimpleNamespace(
            skill="alpha",
            repo="Mharbulous/skills-hub",
            ref="main",
            output_dir=tmp_path / "out",
            json=True,
        )
    )

    result = json.loads(capsys.readouterr().out)
    assert "content_hash" in result
    assert len(result["content_hash"]) == 64
    assert result["source_ref"] == "Mharbulous/skills-hub@main"


# --- End-to-end lockfile test ---


def test_install_then_record_then_inventory_current(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    make_repo_skill(repo, "alpha", body="E2E content\n")
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)

    manager.cmd_fetch_package(
        SimpleNamespace(
            skill="alpha",
            repo="Mharbulous/skills-hub",
            ref="main",
            output_dir=tmp_path / "out",
            json=True,
        )
    )
    result = json.loads(capsys.readouterr().out)

    install_root = tmp_path / "cowork"
    with zipfile.ZipFile(result["package_path"]) as zf:
        zf.extractall(install_root / "skills")

    manager.record_install(install_root, "alpha", result["content_hash"], result["source_ref"])
    lock = manager.read_lockfile(install_root)
    assert lock["alpha"]["content_hash"] == result["content_hash"]

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            json=True,
            names=None,
        )
    )

    inv_rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert inv_rows["alpha"]["status"] == "current"


# --- Git fallback tests ---


def test_fetch_github_repo_git_success(tmp_path, monkeypatch):
    manager = load_manager()
    repo_dir = tmp_path / "repo-git" / "public" / "skills" / "alpha"
    repo_dir.mkdir(parents=True)
    (repo_dir / "SKILL.md").write_text("# alpha\n", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = manager.fetch_github_repo_git("Mharbulous/skills-hub", "main", tmp_path)
    assert result == tmp_path / "repo-git"
    assert (result / "public" / "skills" / "alpha" / "SKILL.md").is_file()


def test_fetch_github_repo_git_raises_on_failure(tmp_path, monkeypatch):
    manager = load_manager()

    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(128, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="git clone failed"):
        manager.fetch_github_repo_git("Mharbulous/skills-hub", "main", tmp_path)


def test_fetch_github_repo_falls_back_to_git(tmp_path, monkeypatch):
    manager = load_manager()
    repo_dir = tmp_path / "repo-git" / "public" / "skills" / "alpha"
    repo_dir.mkdir(parents=True)
    (repo_dir / "SKILL.md").write_text("# alpha\n", encoding="utf-8")

    import urllib.error

    def fake_fetch_bytes(url):
        raise urllib.error.URLError("blocked-by-allowlist")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(manager, "fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = manager.fetch_github_repo("Mharbulous/skills-hub", "main", tmp_path)
    assert result == tmp_path / "repo-git"


def test_fetch_github_repo_uses_zip_when_available(tmp_path, monkeypatch):
    manager = load_manager()
    src = tmp_path / "src"
    skill_dir = src / "skills-hub-main" / "public" / "skills" / "alpha"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# alpha\n", encoding="utf-8")

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(skill_dir / "SKILL.md", "skills-hub-main/public/skills/alpha/SKILL.md")

    dest = tmp_path / "dest"
    dest.mkdir()

    def fake_fetch_bytes(url):
        return zip_path.read_bytes()

    git_called = []

    def tracking_run(cmd, **kwargs):
        git_called.append(cmd)

    monkeypatch.setattr(manager, "fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr(subprocess, "run", tracking_run)
    result = manager.fetch_github_repo("Mharbulous/skills-hub", "main", dest)
    assert "skills-hub-main" in result.name
    assert not git_called


# --- github_head_sha tests ---


def test_github_head_sha_returns_none_on_network_failure(monkeypatch):
    manager = load_manager()

    import urllib.error

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("blocked")

    monkeypatch.setattr(manager.urllib.request, "urlopen", fake_urlopen)
    result = manager.github_head_sha("Mharbulous/skills-hub", "main")
    assert result is None


def test_github_head_sha_returns_none_on_bad_json(monkeypatch):
    manager = load_manager()

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return b"not-json-{"

    monkeypatch.setattr(manager.urllib.request, "urlopen", lambda req, timeout=None: FakeResp())
    result = manager.github_head_sha("Mharbulous/skills-hub", "main")
    assert result is None


# --- SHA catalog cache fast-path tests ---


def test_sha_fast_path_skips_archive_download(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    install_root = tmp_path / "install"
    install_root.mkdir()

    test_sha = "abc123def456"
    catalog = {"skills": [{"name": "alpha", "content_hash": "hash1"}]}
    manager.cache_catalog(install_root, catalog, ref_sha=test_sha)

    fetch_called = []

    def fake_fetch(repo_name, ref, dest):
        fetch_called.append(True)
        raise AssertionError("fetch_github_repo should not be called when SHA matches cache")

    monkeypatch.setattr(manager, "fetch_github_repo", fake_fetch)
    monkeypatch.setattr(manager, "github_head_sha", lambda r, ref: test_sha)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            json=True,
            names=None,
        )
    )

    assert not fetch_called
    rows = json.loads(capsys.readouterr().out)
    assert any(r["name"] == "alpha" for r in rows)


def test_sha_mismatch_triggers_archive_download(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    install_root = tmp_path / "install"
    install_root.mkdir()
    repo = tmp_path / "repo"
    make_repo_skill(repo, "alpha")

    old_sha = "old-sha"
    new_sha = "new-sha"
    old_catalog = {"skills": [{"name": "alpha", "content_hash": "old-hash"}]}
    manager.cache_catalog(install_root, old_catalog, ref_sha=old_sha)

    fetch_called = []

    def fake_fetch(repo_name, ref, dest):
        fetch_called.append(True)
        return repo

    monkeypatch.setattr(manager, "fetch_github_repo", fake_fetch)
    monkeypatch.setattr(manager, "github_head_sha", lambda r, ref: new_sha)

    manager.cmd_inventory(
        SimpleNamespace(
            install_root=[str(install_root)],
            index=None,
            manifest=None,
            repo="Mharbulous/skills-hub",
            ref="main",
            json=True,
            names=None,
        )
    )

    assert fetch_called, "fetch_github_repo should be called when SHA changed"


def test_cache_stores_ref_sha(tmp_path):
    manager = load_manager()
    catalog = {"skills": [{"name": "alpha", "content_hash": "h1"}]}
    manager.cache_catalog(tmp_path, catalog, ref_sha="abc123")
    result = manager.read_cached_catalog([tmp_path])
    assert result is not None
    retrieved_catalog, cached_at, ref_sha = result
    assert ref_sha == "abc123"
    assert retrieved_catalog == catalog


def test_cache_ref_sha_none_when_not_stored(tmp_path):
    manager = load_manager()
    catalog = {"skills": [{"name": "alpha", "content_hash": "h1"}]}
    manager.cache_catalog(tmp_path, catalog, ref_sha=None)
    result = manager.read_cached_catalog([tmp_path])
    assert result is not None
    _, _, ref_sha = result
    assert ref_sha is None


def test_fetch_package_source_ref_uses_sha_when_available(tmp_path, monkeypatch, capsys):
    manager = load_manager()
    repo = tmp_path / "repo"
    make_repo_skill(repo, "alpha", body="Test content\n")
    monkeypatch.setattr(manager, "fetch_github_repo", lambda repo_name, ref, dest: repo)
    monkeypatch.setattr(manager, "github_head_sha", lambda r, ref: "abc123def456")

    manager.cmd_fetch_package(
        SimpleNamespace(
            skill="alpha",
            repo="Mharbulous/skills-hub",
            ref="main",
            output_dir=tmp_path / "out",
            json=True,
        )
    )

    result = json.loads(capsys.readouterr().out)
    assert result["source_ref"] == "Mharbulous/skills-hub@abc123def456"


# --- Preamble injection tests ---


def test_preamble_injected_for_non_skills_hub(tmp_path):
    manager = load_manager()
    repo = tmp_path / "repo"
    make_repo_skill(repo, "vision", body="Vision body\n")

    result = manager.write_direct_skill_package(
        repo, "vision", tmp_path / "out", "Mharbulous/skills-hub", "main", True, sha=None
    )

    with zipfile.ZipFile(result.package_path) as zf:
        skill_md = zf.read("vision/SKILL.md").decode("utf-8")

    assert manager._PREAMBLE_START in skill_md
    assert "Freshness check" in skill_md
    assert "Vision body" in skill_md


def test_preamble_not_injected_for_skills_hub(tmp_path):
    manager = load_manager()
    skill_source = tmp_path / "public" / "skills" / "skills-hub"
    skill_source.mkdir(parents=True)
    (skill_source / "SKILL.md").write_text(
        "---\nname: skills-hub\ndescription: Hub\n---\n\nHub body\n",
        encoding="utf-8",
    )

    result = manager.write_direct_skill_package(
        tmp_path, "skills-hub", tmp_path / "out", "Mharbulous/skills-hub", "main", True, sha=None
    )

    with zipfile.ZipFile(result.package_path) as zf:
        skill_md = zf.read("skills-hub/SKILL.md").decode("utf-8")

    assert manager._PREAMBLE_START not in skill_md


def test_content_hash_unaffected_by_preamble(tmp_path):
    manager = load_manager()
    repo = tmp_path / "repo"
    skill_source = make_repo_skill(repo, "vision", body="Vision body\n")

    source_hash = manager.content_hash(skill_source)

    result = manager.write_direct_skill_package(
        repo, "vision", tmp_path / "out", "Mharbulous/skills-hub", "main", False, sha=None
    )

    install_skills = tmp_path / "installed" / "skills"
    with zipfile.ZipFile(result.package_path) as zf:
        zf.extractall(install_skills)

    install_dir = install_skills / "vision"
    installed_skill_md = (install_dir / "SKILL.md").read_text(encoding="utf-8")
    assert manager._PREAMBLE_START in installed_skill_md, "installed SKILL.md should contain preamble"

    installed_hash = manager.content_hash(install_dir)
    assert installed_hash == source_hash, (
        "content_hash should be equal whether computed from source or installed skill"
    )
