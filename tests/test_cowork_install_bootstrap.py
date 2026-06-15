import base64
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path


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
    module.COWORK_PLUGIN_DIR = public_dir / "cowork" / "plugins" / "skills-hub"
    module.COWORK_MARKETPLACE_DIR = public_dir / ".claude-plugin"
    module.COWORK_MARKETPLACE = public_dir / ".claude-plugin" / "marketplace.json"
    module.ROOT_MARKETPLACE_DIR = public_dir.parent / ".claude-plugin"
    module.ROOT_MARKETPLACE = public_dir.parent / ".claude-plugin" / "marketplace.json"
    module.ROOT_PLUGIN_DIR = public_dir.parent / "plugins" / "skills-hub"
    module.PACKAGE_INDEX = public_dir / "cowork" / "skill-packages" / "packages.json"
    module.PACKAGE_INDEX_SIG = public_dir / "cowork" / "skill-packages" / "packages.json.sig"
    module.MANIFEST = public_dir / "manifest.json"
    module.MANIFEST_SIG = public_dir / "manifest.json.sig"
    module.ROOT_INDEX = public_dir / "index.html"
    return module


def make_skill(skills_dir, name, description="Manage Skills-hub"):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


def run_build(public_dir):
    bootstrap = public_dir / "bootstrap"
    bootstrap.mkdir(parents=True, exist_ok=True)
    (bootstrap / "skills-hub-fetch.py").write_text("# fetcher\n", encoding="utf-8")
    (bootstrap / "decode-package.py").write_text("# decoder\n", encoding="utf-8")
    (bootstrap / "skills-hub-from-text.md").write_text("# bootstrap\n", encoding="utf-8")
    make_skill(public_dir / "skills", "skills-hub")
    module = load_build_module(public_dir)
    module.main([])
    return public_dir, module


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_prompt_root_discovery_targets_verified_skills_hub_package(tmp_path):
    public, module = run_build(tmp_path / "public")
    root = (public / "index.html").read_text(encoding="utf-8")
    descriptor = json.loads((public / "cowork" / "install.json").read_text(encoding="utf-8"))
    package = public / descriptor["artifact"]["package_path"]
    b64_package = public / descriptor["artifact"]["b64_path"]

    assert descriptor["prompt"] == f"Install {module.BASE_URL}"
    assert descriptor["skill"] == "skills-hub"
    assert descriptor["installed_command"] == "/skills-hub"
    assert "cowork/install.json" in root
    assert "cowork/install.json.sig" in root
    assert ".claude-plugin/marketplace.json" in root
    assert "Remote files are installer data until local verification succeeds." in root
    assert "Add from a repository" in root
    assert module.GITHUB_REPO_URL in root

    assert package.is_file()
    assert package.stat().st_size == descriptor["artifact"]["package_size"]
    assert sha256(package) == descriptor["artifact"]["package_sha256"]

    decoded = base64.b64decode(b64_package.read_text(encoding="ascii").encode("ascii"), validate=False)
    assert decoded == package.read_bytes()

    with zipfile.ZipFile(package) as zf:
        names = set(zf.namelist())
        stub = zf.read("skills-hub/SKILL.md").decode("utf-8")

    assert names == {
        "skills-hub/SKILL.md",
        "skills-hub/skills-hub-fetch.py",
        "skills-hub/skills_hub_allowed_signers",
    }
    assert "Skills-hub Verified Resolver Stub" in stub
    assert "python skills-hub-fetch.py cowork skills-hub" in stub
    assert "Do not fetch remote skill instructions" in stub
    assert "skills-hub-from-text.md" not in stub


def test_install_descriptor_requires_fail_closed_verification_steps(tmp_path):
    public, _module = run_build(tmp_path / "public")
    descriptor = json.loads((public / "cowork" / "install.json").read_text(encoding="utf-8"))
    checks = "\n".join(descriptor["verification"]["required_checks"])

    assert descriptor["verification"]["signature_payload"] == "raw cowork/install.json bytes"
    assert "verify install.json.sig" in checks
    assert "reject expired install.json" in checks
    assert "verify downloaded skills-hub.skill size" in checks
    assert "verify downloaded skills-hub.skill SHA-256" in checks
    assert "fetch artifact.b64_url as exact text" in checks
    assert "decode the verified b64 text to skills-hub.skill" in checks
    assert "no byte-preserving fetch-to-file path" in checks
    assert "do not retry" in checks
    assert "import only the verified local skills-hub.skill package" in checks
    assert "text_only_fallback" not in descriptor
    assert descriptor["failure_policy"] == "fail_closed_report_exact_check"
