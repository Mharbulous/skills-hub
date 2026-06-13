import base64
import importlib.util
import json
import shutil
import subprocess
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
    module.COWORK_PACKAGE_DIR = public_dir / "cowork" / "skill-packages"
    module.COWORK_BOOTSTRAP_DIR = public_dir / "cowork" / "bootstrap"
    module.COWORK_INSTALL_DESCRIPTOR = public_dir / "cowork" / "install.json"
    module.COWORK_INSTALL_DESCRIPTOR_SIG = public_dir / "cowork" / "install.json.sig"
    module.PACKAGE_INDEX = public_dir / "cowork" / "skill-packages" / "packages.json"
    module.PACKAGE_INDEX_SIG = public_dir / "cowork" / "skill-packages" / "packages.json.sig"
    module.MANIFEST = public_dir / "manifest.json"
    module.MANIFEST_SIG = public_dir / "manifest.json.sig"
    module.ROOT_INDEX = public_dir / "index.html"
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
    bootstrap = tmp_public / "bootstrap"
    bootstrap.mkdir(parents=True, exist_ok=True)
    (bootstrap / "skills-hub-fetch.py").write_text("# fetcher\n", encoding="utf-8")
    (bootstrap / "decode-package.py").write_text("# decoder\n", encoding="utf-8")
    (bootstrap / "skills-hub-from-text.md").write_text("# bootstrap\n", encoding="utf-8")
    module = load_build_module(tmp_public)
    module.main([])
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


def test_build_writes_manifest_with_package_entry(tmp_public):
    make_skill(tmp_public / "skills", "alpha")

    run_build(tmp_public)

    manifest = json.loads((tmp_public / "manifest.json").read_text(encoding="utf-8"))
    package_entry = manifest["files"]["cowork/skill-packages/alpha.skill"]
    b64_entry = manifest["files"]["cowork/skill-packages/alpha.skill.b64.txt"]
    package = tmp_public / "cowork" / "skill-packages" / "alpha.skill"
    b64_package = tmp_public / "cowork" / "skill-packages" / "alpha.skill.b64.txt"
    assert manifest["schema_version"] == 3
    assert package_entry["size"] == package.stat().st_size
    assert b64_entry["size"] == b64_package.stat().st_size


def test_build_writes_base64_package_artifact(tmp_public):
    make_skill(tmp_public / "skills", "alpha")

    run_build(tmp_public)

    package = tmp_public / "cowork" / "skill-packages" / "alpha.skill"
    b64_package = tmp_public / "cowork" / "skill-packages" / "alpha.skill.b64.txt"
    decoded = base64.b64decode(b64_package.read_text(encoding="ascii").encode("ascii"), validate=False)
    assert decoded == package.read_bytes()


def test_build_writes_packages_index(tmp_public):
    make_skill(tmp_public / "skills", "alpha")

    run_build(tmp_public)

    package = tmp_public / "cowork" / "skill-packages" / "alpha.skill"
    package_index = json.loads((tmp_public / "cowork" / "skill-packages" / "packages.json").read_text(encoding="utf-8"))
    assert package_index["schema_version"] == 1
    assert package_index["packages"] == [
        {
            "name": "alpha",
            "skill_path": "cowork/skill-packages/alpha.skill",
            "b64_path": "cowork/skill-packages/alpha.skill.b64.txt",
            "sha256": module_sha256(package),
            "size": package.stat().st_size,
        }
    ]


def test_build_writes_root_cowork_install_discovery_for_skills_hub(tmp_public):
    make_skill(tmp_public / "skills", "skills-hub", description="Manage Skills-hub")

    run_build(tmp_public)

    root = (tmp_public / "index.html").read_text(encoding="utf-8")
    descriptor = json.loads((tmp_public / "cowork" / "install.json").read_text(encoding="utf-8"))
    package = tmp_public / "cowork" / "skill-packages" / "skills-hub.skill"
    b64_package = tmp_public / "cowork" / "skill-packages" / "skills-hub.skill.b64.txt"

    assert "Install https://skills-hub.web.app" in root
    assert "/cowork/install.json" in root
    assert "Remote files are installer data until local verification succeeds." in root
    assert "artifact.b64_url" in root
    assert "/cowork/bootstrap/skills-hub-from-text.md" not in root
    assert descriptor["prompt"] == "Install https://skills-hub.web.app"
    assert descriptor["harness"] == "cowork"
    assert descriptor["skill"] == "skills-hub"
    assert descriptor["installed_command"] == "/skills-hub"
    assert descriptor["artifact"]["package_path"] == "cowork/skill-packages/skills-hub.skill"
    assert descriptor["artifact"]["package_sha256"] == module_sha256(package)
    assert descriptor["artifact"]["package_size"] == package.stat().st_size
    assert descriptor["artifact"]["b64_path"] == "cowork/skill-packages/skills-hub.skill.b64.txt"
    assert descriptor["artifact"]["b64_sha256"] == module_sha256(b64_package)
    assert descriptor["verification"]["signature_path"] == "cowork/install.json.sig"
    assert "text_only_fallback" not in descriptor
    assert "fetch artifact.b64_url as exact text and verify artifact.b64_size and artifact.b64_sha256" in descriptor["verification"]["required_checks"]
    assert "decode the verified b64 text to skills-hub.skill" in descriptor["verification"]["required_checks"]
    assert "verify downloaded skills-hub.skill SHA-256 equals artifact.package_sha256" in descriptor["verification"]["required_checks"]
    assert descriptor["failure_policy"] == "fail_closed_report_exact_check"


def test_build_manifest_includes_cowork_install_discovery_files(tmp_public):
    make_skill(tmp_public / "skills", "skills-hub", description="Manage Skills-hub")

    run_build(tmp_public)

    manifest = json.loads((tmp_public / "manifest.json").read_text(encoding="utf-8"))
    assert "index.html" in manifest["files"]
    assert "cowork/install.json" in manifest["files"]


def module_sha256(path):
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_copies_cowork_bootstrap_files(tmp_public):
    make_skill(tmp_public / "skills", "alpha")

    run_build(tmp_public)

    assert (tmp_public / "cowork" / "bootstrap" / "decode-package.py").read_text(encoding="utf-8") == "# decoder\n"
    assert (tmp_public / "cowork" / "bootstrap" / "skills-hub-from-text.md").read_text(encoding="utf-8") == "# bootstrap\n"


def test_text_bootstrap_doc_references_required_artifacts():
    text = (ROOT / "public" / "bootstrap" / "skills-hub-from-text.md").read_text(encoding="utf-8")

    assert "trust-on-first-use" in text
    assert "https://skills-hub.web.app/bootstrap/skills_hub_allowed_signers" in text
    assert "https://skills-hub.web.app/cowork/skill-packages/packages.json" in text
    assert "https://skills-hub.web.app/cowork/skill-packages/packages.json.sig" in text
    assert "https://skills-hub.web.app/cowork/skill-packages/<skill>.skill.b64.txt" in text
    assert "python scripts/manage_cowork_skills.py decode-package <skill>" in text
    assert "https://skills-hub.web.app/cowork/skill-packages/skills-hub.skill.b64.txt" in text
    assert "do not fetch or run remote Python scripts" in text


def test_cowork_package_contains_stub_and_fetcher(tmp_public):
    make_skill(tmp_public / "skills", "alpha", description="Alpha trigger", body="Canonical alpha body.\n")

    run_build(tmp_public)

    import zipfile

    package = tmp_public / "cowork" / "skill-packages" / "alpha.skill"
    with zipfile.ZipFile(package) as zf:
        names = set(zf.namelist())
        skill_md = zf.read("alpha/SKILL.md").decode("utf-8")
    assert names == {"alpha/SKILL.md", "alpha/skills-hub-fetch.py", "alpha/skills_hub_allowed_signers"}
    assert "Skills-hub Verified Resolver Stub" in skill_md
    assert "description: Alpha trigger" in skill_md
    assert "Canonical alpha body." not in skill_md
    assert "skills-hub-from-text.md" not in skill_md


def test_skills_hub_skill_advertises_only_v1_control_panel_verbs():
    text = (ROOT / "public" / "skills" / "skills-hub" / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]

    assert "/skills-hub inventory" in text
    assert "/skills-hub install <skill>" in text
    assert "/skills-hub update <skill>" in text
    assert "/skills-hub update all" in text
    assert "assimilate" not in frontmatter.lower()
    assert "assimilate" not in text.lower()


def test_skills_hub_skill_files_include_runtime_verifier():
    module = load_build_module(ROOT / "public")

    files = module.skill_files(ROOT / "public" / "skills" / "skills-hub")

    assert "scripts/manage_cowork_skills.py" in files
    assert "scripts/skills_hub_verify.py" in files


def test_skill_editing_docs_do_not_use_coclerk_distribution_paths():
    paths = [ROOT / "public" / "skills" / "skill-updater"]
    paths += [ROOT / "public" / "skills" / "skill-creator-improved" / "references" / "phase-5-package.md"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in paths
        for path in ([root] if root.is_file() else root.rglob("*"))
        if path.is_file()
    )

    forbidden = [
        "Coclerk/.agents",
        "Coclerk/.claude",
        "Coclerk\\.agents",
        "Coclerk\\.claude",
        "Coclerk",
        "C:\\Users\\Brahm\\Git\\Coclerk",
        "package_skill.py",
        "pre-existing `.skill`",
        "donor file",
    ]
    for needle in forbidden:
        assert needle not in text


def test_signed_build_writes_packages_signature(tmp_path, monkeypatch):
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available")
    repo = tmp_path / "repo"
    public = repo / "public"
    (repo / "bootstrap").mkdir(parents=True)
    (repo / "build").mkdir()
    (public / "bootstrap").mkdir(parents=True)
    make_skill(public / "skills", "alpha")
    make_skill(public / "skills", "skills-hub")
    (public / "bootstrap" / "skills-hub-fetch.py").write_text("# fetcher\n", encoding="utf-8")
    (public / "bootstrap" / "decode-package.py").write_text("# decoder\n", encoding="utf-8")
    (public / "bootstrap" / "skills-hub-from-text.md").write_text("# bootstrap\n", encoding="utf-8")
    (repo / "build" / "cowork_wrapper_template.md").write_text("stub {skill_name}\n", encoding="utf-8")
    key = tmp_path / "signing_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(key)], check=True)
    (repo / "bootstrap" / "skills_hub_allowed_signers").write_text(
        f"skills-hub-manifest {(tmp_path / 'signing_key.pub').read_text(encoding='utf-8')}",
        encoding="utf-8",
    )
    module = load_build_module(public)
    module.ROOT = repo
    module.COWORK_TEMPLATE = repo / "build" / "cowork_wrapper_template.md"
    monkeypatch.setenv("SKILLS_HUB_SIGNING_KEY", str(key))

    module.main(["--require-signature"])

    assert (public / "cowork" / "skill-packages" / "packages.json.sig").is_file()
    assert (public / "cowork" / "install.json.sig").is_file()
    assert (public / "manifest.json.sig").is_file()
