#!/usr/bin/env python3
"""Generate public/index.json, plugin trees, and manifest.

Reads   public/skills/<name>/SKILL.md            canonical definition
        public/skills/<name>/overrides/<h>.md    optional per-harness override
Writes  public/<harness>/skills/<name>/          override-merged skill dirs
        public/index.json
        .claude-plugin/marketplace.json
        plugins/skills-hub/
        public/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
SKILLS = PUBLIC / "skills"


def _parse_github_remote():
    gh_repo = os.environ.get("GITHUB_REPOSITORY")
    if gh_repo and "/" in gh_repo:
        owner, repo = gh_repo.split("/", 1)
        return owner, repo
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
            cwd=str(ROOT),
        )
        remote = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None
    match = re.match(
        r"(?:git@github\.com:|https?://(?:[^@]+@)?github\.com/)([^/]+)/([^/]+?)(?:\.git)?$",
        remote,
    )
    if match:
        return match.group(1), match.group(2)
    return None, None


def _resolve_base_url():
    env_url = os.environ.get("SKILLS_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    owner, repo = _parse_github_remote()
    if owner and repo:
        return f"https://{owner.lower()}.github.io/{repo}"
    sys.exit(
        "Could not detect GitHub Pages URL from git remote.\n"
        "Set SKILLS_BASE_URL environment variable."
    )


def _resolve_github_repo_url():
    owner, repo = _parse_github_remote()
    if owner and repo:
        return f"https://github.com/{owner}/{repo}.git"
    return None


BASE_URL = _resolve_base_url()
GITHUB_REPO_URL = _resolve_github_repo_url()
HARNESSES = ["claude", "codex", "cowork"]
INDEX_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 3
MANIFEST_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
COWORK_PLUGIN_DIR = PUBLIC / "cowork" / "plugins" / "skills-hub"
COWORK_MARKETPLACE_DIR = PUBLIC / ".claude-plugin"
COWORK_MARKETPLACE = COWORK_MARKETPLACE_DIR / "marketplace.json"
ROOT_MARKETPLACE_DIR = ROOT / ".claude-plugin"
ROOT_MARKETPLACE = ROOT_MARKETPLACE_DIR / "marketplace.json"
ROOT_PLUGIN_DIR = ROOT / "plugins" / "skills-hub"
MANIFEST = PUBLIC / "manifest.json"
IGNORED_PARTS = {"overrides", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
PLUGIN_VERSION = "0.2.1"
PLUGIN_DESCRIPTION = "Install and manage Skills-hub skills from the public GitHub repo in Claude Cowork."
PLUGIN_KEYWORDS = [
    "skills-hub",
    "skills hub",
    "install skills hub",
    "cowork skills",
    "github skills",
    "public skills repo",
]
PLUGIN_HOMEPAGE = GITHUB_REPO_URL or BASE_URL


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


def write_plugin_tree(plugin_dir, skill_dirs):
    skills_hub = next((skill_dir for skill_dir in skill_dirs if skill_dir.name == "skills-hub"), None)
    if skills_hub is None:
        if plugin_dir.exists():
            remove_tree(plugin_dir)
        return False

    if plugin_dir.exists():
        remove_tree(plugin_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)

    plugin_json = {
        "name": "skills-hub",
        "version": PLUGIN_VERSION,
        "description": PLUGIN_DESCRIPTION,
        "author": {"name": "Skills-hub"},
        "homepage": PLUGIN_HOMEPAGE,
        "keywords": PLUGIN_KEYWORDS,
        "skills": "./skills",
    }
    plugin_meta = plugin_dir / ".claude-plugin"
    plugin_meta.mkdir(parents=True, exist_ok=True)
    (plugin_meta / "plugin.json").write_text(
        json.dumps(plugin_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    plugin_skill = plugin_dir / "skills" / "skills-hub"
    for rel in skill_files(skills_hub):
        src = skills_hub / rel
        dst = plugin_skill / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    (plugin_dir / "README.md").write_text(
        "# Skills-hub Cowork Plugin\n\n"
        "Installs the `/skills-hub` control panel in Claude Cowork. "
        "The control panel builds Cowork packages from the public "
        "Mharbulous/skills-hub GitHub repository for inventory, install, "
        "and update operations.\n",
        encoding="utf-8",
    )
    return True


def write_marketplace(marketplace_path, name, description, source):
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": name,
        "description": description,
        "owner": {"name": "Skills-hub"},
        "plugins": [
            {
                "name": "skills-hub",
                "version": PLUGIN_VERSION,
                "description": PLUGIN_DESCRIPTION,
                "source": source,
                "category": "productivity",
                "homepage": PLUGIN_HOMEPAGE,
                "keywords": PLUGIN_KEYWORDS,
            }
        ],
    }
    marketplace_path.write_text(
        json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_cowork_plugin(skill_dirs):
    return write_plugin_tree(COWORK_PLUGIN_DIR, skill_dirs)


def write_root_plugin(skill_dirs):
    return write_plugin_tree(ROOT_PLUGIN_DIR, skill_dirs)


def write_cowork_marketplace():
    write_marketplace(
        COWORK_MARKETPLACE,
        "skills-hub-marketplace",
        "Claude Cowork URL discovery marketplace for Skills-hub.",
        "./cowork/plugins/skills-hub",
    )


def write_root_marketplace():
    write_marketplace(
        ROOT_MARKETPLACE,
        "skills-hub",
        "Claude Cowork Git repository marketplace for Skills-hub.",
        "./plugins/skills-hub",
    )


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
        if rel.as_posix() == "manifest.json":
            continue
        if any(part.startswith(".") for part in rel.parts) and ".claude-plugin" not in rel.parts:
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


def main(argv=None):
    argparse.ArgumentParser().parse_args(argv)

    if not SKILLS.is_dir():
        sys.exit(f"No skills directory at {SKILLS}")

    skill_dirs = sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").is_file())
    catalog = build_catalog(skill_dirs)
    generated_at = datetime.now(timezone.utc).isoformat()
    has_cowork_plugin = write_cowork_plugin(skill_dirs)
    if has_cowork_plugin:
        write_cowork_marketplace()
    elif COWORK_MARKETPLACE.exists():
        COWORK_MARKETPLACE.unlink()
    has_root_plugin = write_root_plugin(skill_dirs)
    if has_root_plugin:
        write_root_marketplace()
    elif ROOT_MARKETPLACE.exists():
        ROOT_MARKETPLACE.unlink()
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
    print(f"Built index and manifest for {len(skill_dirs)} skills -> {PUBLIC}")


if __name__ == "__main__":
    main()
