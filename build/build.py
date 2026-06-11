#!/usr/bin/env python3
"""Build per-harness skill bundles from canonical skills + overrides.

Reads   skills/<name>/SKILL.md             canonical definition
        skills/<name>/overrides/<h>.md     optional per-harness override
Writes  dist/<h>/skills/<name>/...         merged skill + subfiles
        dist/<h>/skills.tar.gz             bundle (skill folders at archive root)
        dist/index.json                    catalog with descriptions and hashes

Override semantics: frontmatter keys replace canonical keys; a non-empty
override body is appended to the canonical body.
"""

import hashlib
import json
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
DIST = ROOT / "dist"
HARNESSES = ["claude", "codex"]


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


def build_skill(skill_dir, harness):
    frontmatter, body = split_frontmatter((skill_dir / "SKILL.md").read_text())
    override = skill_dir / "overrides" / f"{harness}.md"
    if override.exists():
        o_fm, o_body = split_frontmatter(override.read_text())
        frontmatter = {**frontmatter, **o_fm}
        if o_body.strip():
            body = body.rstrip() + "\n\n" + o_body.strip() + "\n"
    return frontmatter, render(frontmatter, body)


def main():
    if not SKILLS.is_dir():
        sys.exit(f"No skills directory at {SKILLS}")
    if DIST.exists():
        shutil.rmtree(DIST)

    skill_dirs = sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").is_file())

    for harness in HARNESSES:
        out_root = DIST / harness / "skills"
        for skill_dir in skill_dirs:
            _, merged = build_skill(skill_dir, harness)
            out_dir = out_root / skill_dir.name
            shutil.copytree(skill_dir, out_dir, ignore=shutil.ignore_patterns("overrides"))
            (out_dir / "SKILL.md").write_text(merged)
        with tarfile.open(DIST / harness / "skills.tar.gz", "w:gz") as tar:
            for skill_dir in skill_dirs:
                tar.add(out_root / skill_dir.name, arcname=skill_dir.name)

    catalog = []
    for skill_dir in skill_dirs:
        entry = {"name": skill_dir.name, "harnesses": {}}
        for harness in HARNESSES:
            frontmatter, merged = build_skill(skill_dir, harness)
            entry.setdefault("description", frontmatter.get("description", ""))
            entry["harnesses"][harness] = {
                "description": frontmatter.get("description", ""),
                "path": f"{harness}/skills/{skill_dir.name}/SKILL.md",
                "sha256": hashlib.sha256(merged.encode()).hexdigest(),
            }
        catalog.append(entry)

    (DIST / "index.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills": catalog,
    }, indent=2) + "\n")

    print(f"Built {len(skill_dirs)} skill(s) for {', '.join(HARNESSES)} -> {DIST}")


if __name__ == "__main__":
    main()
