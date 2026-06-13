import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_build_module(public_dir):
    spec = importlib.util.spec_from_file_location("build_index", ROOT / "build" / "build_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PUBLIC = public_dir
    module.SKILLS = public_dir / "skills"
    return module


def make_skill(skills_dir, name, description="A skill", body="Skill body.\n", overrides=None):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\ndescription: {description}\n---\n\n{body}"
    (skill_dir / "SKILL.md").write_text(fm, encoding="utf-8")
    if overrides:
        (skill_dir / "overrides").mkdir()
        for harness, content in overrides.items():
            (skill_dir / "overrides" / f"{harness}.md").write_text(content, encoding="utf-8")
    return skill_dir


@pytest.fixture
def tmp_public(tmp_path):
    return tmp_path / "public"


def run_build(tmp_public):
    module = load_build_module(tmp_public)
    module.main()
    return module


def test_index_lists_all_skills(tmp_public):
    skills = tmp_public / "skills"
    make_skill(skills, "alpha")
    make_skill(skills, "beta")

    run_build(tmp_public)

    index = json.loads((tmp_public / "index.json").read_bytes().decode("utf-8"))
    assert index["schema_version"] == 1
    names = {s["name"] for s in index["skills"]}
    assert names == {"alpha", "beta"}


def test_canonical_skill_uses_skills_base_for_all_harnesses(tmp_public):
    make_skill(tmp_public / "skills", "alpha")

    run_build(tmp_public)

    index = json.loads((tmp_public / "index.json").read_bytes().decode("utf-8"))
    entry = index["skills"][0]
    for harness in ["claude", "codex", "cowork"]:
        assert entry["harnesses"][harness]["base"] == "skills/alpha"


def test_override_skill_uses_harness_base(tmp_public):
    make_skill(tmp_public / "skills", "gamma", overrides={"cowork": "---\n---\n\nCowork extra.\n"})

    run_build(tmp_public)

    index = json.loads((tmp_public / "index.json").read_bytes().decode("utf-8"))
    entry = index["skills"][0]
    assert entry["harnesses"]["claude"]["base"] == "skills/gamma"
    assert entry["harnesses"]["cowork"]["base"] == "cowork/skills/gamma"
    assert entry["harnesses"]["codex"]["base"] == "skills/gamma"


def test_override_dir_is_written_with_merged_skill_md(tmp_public):
    make_skill(
        tmp_public / "skills",
        "gamma",
        body="Canonical body.\n",
        overrides={"cowork": "---\n---\n\nCowork extra.\n"},
    )

    run_build(tmp_public)

    merged = (tmp_public / "cowork" / "skills" / "gamma" / "SKILL.md").read_text(encoding="utf-8")
    assert "Canonical body." in merged
    assert "Cowork extra." in merged


def test_overrides_dir_not_included_in_files_list(tmp_public):
    make_skill(tmp_public / "skills", "alpha", overrides={"cowork": "---\n---\n\nExtra.\n"})

    run_build(tmp_public)

    index = json.loads((tmp_public / "index.json").read_bytes().decode("utf-8"))
    for harness_entry in index["skills"][0]["harnesses"].values():
        assert not any("overrides" in f for f in harness_entry["files"])


def test_skill_md_in_files_list(tmp_public):
    make_skill(tmp_public / "skills", "alpha")

    run_build(tmp_public)

    index = json.loads((tmp_public / "index.json").read_bytes().decode("utf-8"))
    files = index["skills"][0]["harnesses"]["claude"]["files"]
    assert "SKILL.md" in files


def test_subfiles_included_in_files_list(tmp_public):
    skills = tmp_public / "skills"
    make_skill(skills, "alpha")
    (skills / "alpha" / "scripts").mkdir()
    (skills / "alpha" / "scripts" / "tool.sh").write_text("#!/bin/bash\necho hi\n", encoding="utf-8")

    run_build(tmp_public)

    index = json.loads((tmp_public / "index.json").read_bytes().decode("utf-8"))
    files = index["skills"][0]["harnesses"]["claude"]["files"]
    assert "SKILL.md" in files
    assert "scripts/tool.sh" in files
