#!/usr/bin/env python3
"""Fetch and cache a Skills-hub skill from the public HTTP server.

Usage:
    python skills-hub-fetch.py <harness> <skill> [--base-url URL] [--cache-dir DIR]

Fetches index.json, resolves the skill's file list, downloads each file, and
prints the local path to SKILL.md. Falls back to the local cache if offline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "https://skills-hub.web.app"


def fail(message: str) -> None:
    print(f"skills-hub-fetch: {message}", file=sys.stderr)
    raise SystemExit(1)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-hub-fetch/2"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = getattr(resp, "status", None) or 200
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {url}")
        return resp.read()


def resolve_skill(index: dict, harness: str, skill: str) -> tuple[str, list[str]]:
    for entry in index.get("skills", []):
        if entry["name"] == skill:
            h = entry.get("harnesses", {}).get(harness)
            if h is None:
                fail(f"skill {skill!r} has no harness {harness!r} in index")
            return h["base"], h["files"]
    fail(f"skill {skill!r} not found in index")


def materialize(base_url: str, harness: str, skill: str, cache_root: Path) -> Path:
    base_url = base_url.rstrip("/")
    cache_dir = cache_root / harness / skill

    try:
        index = json.loads(fetch_bytes(f"{base_url}/index.json").decode("utf-8"))
        skill_base, files = resolve_skill(index, harness, skill)

        for rel_path in files:
            url = f"{base_url}/{skill_base}/{rel_path}"
            content = fetch_bytes(url)
            dest = cache_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)

    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        skill_md = cache_dir / "SKILL.md"
        if skill_md.is_file():
            return skill_md
        fail(f"could not fetch skill {skill!r} and no cache exists: {exc}")

    skill_md = cache_dir / "SKILL.md"
    if not skill_md.is_file():
        fail(f"fetch completed but {skill}/SKILL.md is missing from cache")
    return skill_md


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("harness", choices=["claude", "codex", "cowork"])
    parser.add_argument("skill")
    parser.add_argument("--base-url", default=os.environ.get("SKILLS_BASE_URL", BASE_URL))
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ.get("SKILLS_HUB_CACHE_DIR", Path.home() / ".skills-hub" / "cache")),
    )
    args = parser.parse_args()
    skill_md = materialize(args.base_url, args.harness, args.skill, args.cache_dir)
    print(skill_md)


if __name__ == "__main__":
    main()
