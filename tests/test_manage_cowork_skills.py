import importlib.util
import sys
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

    manager.cmd_assimilate(SimpleNamespace(source=source, name="imported-skill", license="internal"))

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
        manager.cmd_assimilate(SimpleNamespace(source=source, name="existing", license="unknown"))
