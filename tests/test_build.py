import hashlib
import importlib.util
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from pathlib import PurePosixPath

import pytest


def load_build_module():
    spec = importlib.util.spec_from_file_location("myskillium_build", "build/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_temp_dir(prefix):
    parent = Path(os.environ.get("SKILLS_HUB_TEST_TMP", Path.cwd() / ".test-tmp"))
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))


@pytest.fixture(scope="session")
def built_dist():
    module = load_build_module()
    temp_root = make_temp_dir("myskillium-build-")
    module.DIST = temp_root / "dist"
    try:
        module.main()
        yield module, module.DIST
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def skill_names(module):
    return sorted(path.name for path in module.SKILLS.iterdir() if (path / "SKILL.md").is_file())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(path):
    return path.read_text(encoding="utf-8")


def test_every_skill_has_full_stub_tarball_and_index_entry(built_dist):
    module, dist = built_dist
    names = skill_names(module)
    catalog = json.loads(read_text(dist / "index.json"))
    entries = {entry["name"]: entry for entry in catalog["skills"]}

    assert catalog["schema_version"] == 2
    assert catalog["harnesses"] == module.HARNESSES
    assert set(entries) == set(names)

    for skill_name in names:
        for harness in module.HARNESSES:
            full_path = dist / harness / "skills" / skill_name / "SKILL.md"
            stub_path = dist / harness / "stubs" / skill_name / "SKILL.md"
            tarball_path = dist / harness / "skills" / f"{skill_name}.tar.gz"

            assert full_path.is_file()
            assert stub_path.is_file()
            assert tarball_path.is_file()

            harness_entry = entries[skill_name]["harnesses"][harness]
            assert harness_entry["path"] == f"{harness}/skills/{skill_name}/SKILL.md"
            assert harness_entry["sha256"] == sha256(full_path)
            assert harness_entry["stub_path"] == f"{harness}/stubs/{skill_name}/SKILL.md"
            assert harness_entry["stub_sha256"] == sha256(stub_path)
            assert harness_entry["tarball_path"] == f"{harness}/skills/{skill_name}.tar.gz"
            assert "manifest_path" not in harness_entry
            assert "manifest_sha256" not in harness_entry


def test_manifest_covers_generated_files_and_catalog(built_dist):
    _module, dist = built_dist
    manifest = json.loads(read_text(dist / "manifest.json"))

    assert manifest["schema_version"] == 3
    assert manifest["max_age_seconds"] > 0
    assert manifest["skills"]
    assert "index.json" in manifest["files"]
    assert "bootstrap/myskillium_allowed_signers" in manifest["files"]

    expected_files = {
        path.relative_to(dist).as_posix()
        for path in dist.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "manifest.json.sig"}
    }
    assert set(manifest["files"]) == expected_files

    for relpath, entry in manifest["files"].items():
        path = dist / relpath
        assert entry["sha256"] == sha256(path)
        assert entry["size"] == path.stat().st_size


def test_overrides_are_applied_per_harness(built_dist):
    _module, dist = built_dist

    systematic_codex = read_text(dist / "codex" / "skills" / "systematic-debugging" / "SKILL.md")
    handover_cowork = read_text(dist / "cowork" / "skills" / "handover" / "SKILL.md")
    skill_creator_cowork = read_text(dist / "cowork" / "skills" / "skill-creator-improved" / "SKILL.md")
    zoom_out_claude = read_text(dist / "claude" / "skills" / "zoom-out" / "SKILL.md")
    zoom_out_codex = read_text(dist / "codex" / "skills" / "zoom-out" / "SKILL.md")

    assert "# Systematic Debugging (Codex)" in systematic_codex
    assert "# Cowork Override" in handover_cowork
    assert "## Cowork Environment Note" in skill_creator_cowork
    assert zoom_out_claude == zoom_out_codex


def test_stub_frontmatter_matches_merged_frontmatter_and_urls(built_dist):
    module, dist = built_dist

    full_fm, _ = module.split_frontmatter(read_text(dist / "claude" / "skills" / "fill-PDF" / "SKILL.md"))
    stub_fm, _ = module.split_frontmatter(read_text(dist / "claude" / "stubs" / "fill-PDF" / "SKILL.md"))
    assert full_fm == stub_fm
    assert full_fm["name"] == "fill-PDF"

    handover_stub_fm, handover_stub_body = module.split_frontmatter(
        read_text(dist / "codex" / "stubs" / "handover" / "SKILL.md")
    )
    handover_full_fm, _ = module.split_frontmatter(
        read_text(dist / "codex" / "skills" / "handover" / "SKILL.md")
    )
    assert handover_stub_fm == handover_full_fm
    assert "Do not fetch remote `SKILL.md` files at invocation time" in handover_stub_body
    assert "rerun the verified" in handover_stub_body

    cowork_fm, cowork_body = module.split_frontmatter(
        read_text(dist / "cowork" / "stubs" / "handover" / "SKILL.md")
    )
    cowork_full_fm, _ = module.split_frontmatter(
        read_text(dist / "cowork" / "skills" / "handover" / "SKILL.md")
    )
    assert cowork_fm == cowork_full_fm
    assert "python myskillium-fetch.py cowork handover" in cowork_body
    assert "Do not fetch\nMyskillium URLs directly" in cowork_body
    assert (dist / "cowork" / "stubs" / "handover" / "myskillium-fetch.py").is_file()
    assert (dist / "cowork" / "stubs" / "handover" / "myskillium_allowed_signers").is_file()


def test_stub_bundle_contains_only_stub_skill_files_and_full_bundles_keep_subfiles(built_dist):
    module, dist = built_dist
    names = skill_names(module)
    stub_bundle = dist / "claude" / "skill-stubs.tar.gz"

    assert stub_bundle.stat().st_size < 1_000_000
    with tarfile.open(stub_bundle, "r:gz") as tar:
        members = tar.getnames()

    assert len(members) == len(names)
    assert all(member.endswith("/SKILL.md") and member.count("/") == 1 for member in members)

    with tarfile.open(dist / "cowork" / "skill-stubs.tar.gz", "r:gz") as tar:
        cowork_members = set(tar.getnames())
    for skill_name in names:
        assert f"{skill_name}/SKILL.md" in cowork_members
        assert f"{skill_name}/myskillium-fetch.py" in cowork_members
        assert f"{skill_name}/myskillium_allowed_signers" in cowork_members

    with tarfile.open(dist / "claude" / "skills.tar.gz", "r:gz") as tar:
        full_members = set(tar.getnames())
    assert "commit/scripts/gather-context.sh" in full_members
    assert "commit/scripts/sanitize-commit.sh" in full_members

    with tarfile.open(dist / "codex" / "skills" / "handover.tar.gz", "r:gz") as tar:
        handover_members = set(tar.getnames())
    assert "handover/SKILL.md" in handover_members
    assert "handover/scripts/handover_selector.py" in handover_members


def test_no_dot_prefixed_paths_are_generated(built_dist):
    _module, dist = built_dist

    for path in dist.rglob("*"):
        rel = path.relative_to(dist)
        assert not any(part.startswith(".") for part in rel.parts), rel

    for tarball in dist.rglob("*.tar.gz"):
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar.getnames():
                parts = PurePosixPath(member).parts
                assert not any(part.startswith(".") for part in parts), (tarball, member)
