#!/usr/bin/env python3
"""Generate public/index.json, Cowork packages, and signed-manifest inputs.

Reads   public/skills/<name>/SKILL.md            canonical definition
        public/skills/<name>/overrides/<h>.md    optional per-harness override
Writes  public/<harness>/skills/<name>/          override-merged skill dirs
        public/cowork/skill-packages/<name>.skill
        public/index.json
        public/manifest.json
        public/manifest.json.sig                 when SKILLS_HUB_SIGNING_KEY is set
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
SKILLS = PUBLIC / "skills"
BASE_URL = "https://skills-hub.web.app"
HARNESSES = ["claude", "codex", "cowork"]
INDEX_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 3
MANIFEST_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
SIGNING_NAMESPACE = "skills-hub-manifest"
COWORK_TEMPLATE = ROOT / "build" / "cowork_wrapper_template.md"
COWORK_PACKAGE_DIR = PUBLIC / "cowork" / "skill-packages"
MANIFEST = PUBLIC / "manifest.json"
MANIFEST_SIG = PUBLIC / "manifest.json.sig"
IGNORED_PARTS = {"overrides", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def split_frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            frontmatter = yaml.safe_load(text[4:end]) or {}
            body = text[end + 4:].lstrip("\n")
            return frontmatter, body
    return {}, text


def render(frontmatter, body):
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm_text}\n---\n\n{body.strip()}\n"


def merged_frontmatter(skill_dir, harness):
    fm, _ = split_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    fm = dict(fm)
    override = skill_dir / "overrides" / f"{harness}.md"
    if override.exists():
        o_fm, _ = split_frontmatter(override.read_text(encoding="utf-8"))
        fm = {**fm, **o_fm}
    fm["name"] = skill_dir.name
    return fm


def merge_skill(skill_dir, harness):
    fm, body = split_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    fm = dict(fm)
    override = skill_dir / "overrides" / f"{harness}.md"
    if override.exists():
        o_fm, o_body = split_frontmatter(override.read_text(encoding="utf-8"))
        fm = {**fm, **o_fm}
        if o_body.strip():
            body = body.rstrip() + "\n\n" + o_body.strip() + "\n"
    fm["name"] = skill_dir.name
    return render(fm, body)


def is_publishable(rel):
    if any(part in IGNORED_PARTS or part.startswith(".") for part in rel.parts):
        return False
    if rel.suffix in IGNORED_SUFFIXES:
        return False
    return True


def remove_tree(path):
    def clear_readonly(function, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            function(target)
        except OSError:
            raise exc_info[1]

    shutil.rmtree(path, onexc=clear_readonly)


def skill_files(skill_dir):
    result = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if not is_publishable(rel):
            continue
        result.append(rel.as_posix())
    return result


def write_override_dir(skill_dir, harness):
    out_dir = PUBLIC / harness / "skills" / skill_dir.name
    if out_dir.exists():
        remove_tree(out_dir)
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if not is_publishable(rel):
            continue
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
    (out_dir / "SKILL.md").write_text(merge_skill(skill_dir, harness), encoding="utf-8")


def render_cowork_stub(skill_dir):
    template = COWORK_TEMPLATE.read_text(encoding="utf-8")
    body = template.replace("{skill_name}", skill_dir.name)
    return render(merged_frontmatter(skill_dir, "cowork"), body)


def write_cowork_package(skill_dir):
    COWORK_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    package_path = COWORK_PACKAGE_DIR / f"{skill_dir.name}.skill"
    fetcher = PUBLIC / "bootstrap" / "skills-hub-fetch.py"
    allowed_signers = PUBLIC / "bootstrap" / "skills_hub_allowed_signers"

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{skill_dir.name}/SKILL.md", render_cowork_stub(skill_dir))
        zf.write(fetcher, f"{skill_dir.name}/skills-hub-fetch.py")
        if allowed_signers.is_file():
            zf.write(allowed_signers, f"{skill_dir.name}/skills_hub_allowed_signers")
    return package_path


def build_catalog(skill_dirs):
    catalog = []
    for skill_dir in skill_dirs:
        fm, _ = split_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        files = skill_files(skill_dir)
        entry = {
            "name": skill_dir.name,
            "description": fm.get("description", ""),
            "harnesses": {},
        }
        for harness in HARNESSES:
            if (skill_dir / "overrides" / f"{harness}.md").exists():
                write_override_dir(skill_dir, harness)
                base = f"{harness}/skills/{skill_dir.name}"
            else:
                base = f"skills/{skill_dir.name}"
            entry["harnesses"][harness] = {"base": base, "files": files}
        write_cowork_package(skill_dir)
        catalog.append(entry)
    return catalog


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_files():
    for path in sorted(PUBLIC.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(PUBLIC)
        if rel.as_posix() in {"manifest.json", "manifest.json.sig"}:
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.suffix in IGNORED_SUFFIXES:
            continue
        yield rel, path


def build_manifest(catalog, generated_at):
    files = {}
    for rel, path in public_files():
        files[rel.as_posix()] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "max_age_seconds": MANIFEST_MAX_AGE_SECONDS,
        "base_url": BASE_URL,
        "skills": catalog,
        "files": files,
    }


def signing_key_from_env():
    value = os.environ.get("SKILLS_HUB_SIGNING_KEY")
    if not value:
        return None, None
    candidate = Path(value)
    if candidate.exists():
        return candidate, None
    tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
    tmp.write(value)
    if not value.endswith("\n"):
        tmp.write("\n")
    tmp.close()
    path = Path(tmp.name)
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return path, path


def ensure_public_allowed_signers(require_signature):
    public_bootstrap = PUBLIC / "bootstrap"
    public_bootstrap.mkdir(parents=True, exist_ok=True)
    public_allowed = public_bootstrap / "skills_hub_allowed_signers"
    repo_allowed = ROOT / "bootstrap" / "skills_hub_allowed_signers"
    if repo_allowed.is_file():
        if public_allowed.exists():
            try:
                os.chmod(public_allowed, stat.S_IWRITE)
            except OSError:
                pass
        shutil.copy2(repo_allowed, public_allowed)
        return
    if public_allowed.is_file():
        return

    key_path, temp_key = signing_key_from_env()
    try:
        if key_path:
            result = subprocess.run(
                ["ssh-keygen", "-y", "-f", str(key_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            public_allowed.write_text(f"skills-hub {result.stdout.strip()}\n", encoding="utf-8")
            return
    finally:
        if temp_key:
            try:
                temp_key.unlink()
            except OSError:
                pass

    if require_signature:
        sys.exit("skills_hub_allowed_signers or SKILLS_HUB_SIGNING_KEY is required for signed build")


def sign_manifest(require_signature):
    key_path, temp_key = signing_key_from_env()
    if MANIFEST_SIG.exists():
        MANIFEST_SIG.unlink()
    try:
        if not key_path:
            if require_signature:
                sys.exit("SKILLS_HUB_SIGNING_KEY is required to sign manifest.json")
            return False
        public_allowed = PUBLIC / "bootstrap" / "skills_hub_allowed_signers"
        public_key = subprocess.run(
            ["ssh-keygen", "-y", "-f", str(key_path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if public_key not in public_allowed.read_text(encoding="utf-8"):
            sys.exit("SKILLS_HUB_SIGNING_KEY does not match skills_hub_allowed_signers")
        subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "sign",
                "-f",
                str(key_path),
                "-n",
                SIGNING_NAMESPACE,
                str(MANIFEST),
            ],
            check=True,
        )
        generated = MANIFEST.with_name(MANIFEST.name + ".sig")
        if generated != MANIFEST_SIG and generated.exists():
            generated.replace(MANIFEST_SIG)
        if not MANIFEST_SIG.is_file():
            sys.exit("ssh-keygen did not produce manifest.json.sig")
        return True
    finally:
        if temp_key:
            try:
                temp_key.unlink()
            except OSError:
                pass


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-signature", action="store_true")
    args = parser.parse_args(argv)

    if not SKILLS.is_dir():
        sys.exit(f"No skills directory at {SKILLS}")
    if not COWORK_TEMPLATE.is_file():
        sys.exit(f"No Cowork wrapper template at {COWORK_TEMPLATE}")

    if COWORK_PACKAGE_DIR.exists():
        remove_tree(COWORK_PACKAGE_DIR)

    ensure_public_allowed_signers(args.require_signature)
    skill_dirs = sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").is_file())
    catalog = build_catalog(skill_dirs)
    generated_at = datetime.now(timezone.utc).isoformat()
    index = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "generated_at": generated_at,
        "base_url": BASE_URL,
        "skills": catalog,
    }
    (PUBLIC / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    MANIFEST.write_text(
        json.dumps(build_manifest(catalog, generated_at), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    signed = sign_manifest(args.require_signature)
    suffix = "signed" if signed else "unsigned"
    print(f"Built index and {suffix} manifest for {len(skill_dirs)} skills -> {PUBLIC}")


if __name__ == "__main__":
    main()
