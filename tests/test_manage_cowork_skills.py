import importlib.util
import json
import sys
import zipfile
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

    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)}
    assert rows["alpha"]["status"] == "current"
