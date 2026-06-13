#!/usr/bin/env python3
"""Generate public/index.json and write override-merged skill dirs.

Reads   public/skills/<name>/SKILL.md            canonical definition
        public/skills/<name>/overrides/<h>.md    optional per-harness override
Writes  public/<h>/skills/<name>/                override-merged skill (only for overridden skills)
        public/index.json                        skill catalog with file paths
"""

from __future__ import annotations

import json
import shutil
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
BASE_URL = "https://skills-hub.web.app"
HARNESSES = ["claude", "codex", "cowork"]
SCHEMA_VERSION = 1


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


def skill_files(skill_dir):
    """Return sorted list of relative posix paths for all publishable files."""
    result = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if rel.parts[0] == "overrides" or any(p.startswith(".") for p in rel.parts):
            continue
        result.append(rel.as_posix())
    return result


def write_override_dir(skill_dir, harness):
    """Copy canonical skill to public/<harness>/skills/<name>/ with merged SKILL.md."""
    out_dir = PUBLIC / harness / "skills" / skill_dir.name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if rel.parts[0] == "overrides" or any(p.startswith(".") for p in rel.parts):
            continue
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
    (out_dir / "SKILL.md").write_text(merge_skill(skill_dir, harness), encoding="utf-8")


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


def main():
    if not SKILLS.is_dir():
        sys.exit(f"No skills directory at {SKILLS}")

    skill_dirs = sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").is_file())
    catalog = build_catalog(skill_dirs)
    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "skills": catalog,
    }
    (PUBLIC / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Built index for {len(skill_dirs)} skills -> {PUBLIC / 'index.json'}")


if __name__ == "__main__":
    main()
