#!/usr/bin/env python3
"""Fetch, verify, and cache a Skills-hub skill from the public HTTP server.

Usage:
    python skills-hub-fetch.py <harness> <skill> [--base-url URL] [--cache-dir DIR]

The resolver verifies manifest.json.sig with the local trust anchor, then
verifies every downloaded file's size and SHA-256 before writing it to cache.
It prints exactly one local SKILL.md path on success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://mharbulous.github.io/skills-hub"
MANIFEST_SCHEMA_VERSION = 3
SIGNING_IDENTITY = "skills-hub-manifest"
SIGNING_NAMESPACE = "skills-hub-manifest"


def fail(message: str) -> None:
    print(f"skills-hub-fetch: {message}", file=sys.stderr)
    raise SystemExit(1)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-hub-fetch/3"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = getattr(resp, "status", None) or 200
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {url}")
        return resp.read()


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"invalid manifest generated_at timestamp: {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_manifest(data: bytes) -> dict:
    try:
        manifest = json.loads(data.decode("utf-8"))
    except Exception as exc:
        fail(f"could not parse manifest JSON: {exc}")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        fail(f"unsupported manifest schema_version {manifest.get('schema_version')!r}")
    generated_at = parse_timestamp(str(manifest.get("generated_at", "")))
    max_age = int(manifest.get("max_age_seconds", 0))
    if max_age <= 0:
        fail("manifest max_age_seconds must be positive")
    age = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds()
    if age > max_age:
        fail("manifest is expired")
    return manifest


def verify_signature(manifest_data: bytes, signature_data: bytes, allowed_signers: Path) -> None:
    if shutil.which("ssh-keygen") is None:
        fail("ssh-keygen is required for manifest verification")
    if not allowed_signers.is_file():
        fail(f"allowed signers file is missing: {allowed_signers}")
    if not allowed_signers.read_text(encoding="utf-8").strip():
        fail(f"allowed signers file is empty: {allowed_signers}")

    with tempfile.TemporaryDirectory(prefix="skills-hub-verify-") as tmp:
        sig_path = Path(tmp) / "manifest.json.sig"
        sig_path.write_bytes(signature_data)
        result = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(allowed_signers),
                "-I",
                SIGNING_IDENTITY,
                "-n",
                SIGNING_NAMESPACE,
                "-s",
                str(sig_path),
            ],
            input=manifest_data,
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(f"manifest signature verification failed: {detail}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bytes(manifest: dict, rel_path: str, data: bytes) -> None:
    entry = manifest.get("files", {}).get(rel_path)
    if not entry:
        fail(f"manifest has no file entry for {rel_path}")
    expected_size = int(entry.get("size", -1))
    if len(data) != expected_size:
        fail(f"size mismatch for {rel_path}: expected {expected_size}, got {len(data)}")
    expected_sha = entry.get("sha256")
    if sha256_bytes(data) != expected_sha:
        fail(f"sha256 mismatch for {rel_path}")


def resolve_skill(manifest: dict, harness: str, skill: str) -> tuple[str, list[str]]:
    for entry in manifest.get("skills", []):
        if entry["name"] == skill:
            h = entry.get("harnesses", {}).get(harness)
            if h is None:
                fail(f"skill {skill!r} has no harness {harness!r} in manifest")
            return h["base"], h["files"]
    fail(f"skill {skill!r} not found in manifest")


def write_context(cache_dir: Path, base_url: str, harness: str, skill: str, allowed_signers: Path) -> None:
    cached_signers = cache_dir / "skills_hub_allowed_signers"
    shutil.copy2(allowed_signers, cached_signers)
    context = {
        "harness": harness,
        "skill": skill,
        "base_url": base_url.rstrip("/"),
        "original_stub_dir": str(Path(__file__).resolve().parent),
        "allowed_signers_path": str(cached_signers),
    }
    (cache_dir / ".skills-hub-context.json").write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")


def materialize(base_url: str, harness: str, skill: str, cache_root: Path, allowed_signers: Path) -> Path:
    base_url = base_url.rstrip("/")
    cache_dir = cache_root / harness / skill

    try:
        manifest_data = fetch_bytes(f"{base_url}/manifest.json")
        signature_data = fetch_bytes(f"{base_url}/manifest.json.sig")
        verify_signature(manifest_data, signature_data, allowed_signers)
        manifest = load_manifest(manifest_data)
        skill_base, files = resolve_skill(manifest, harness, skill)

        for rel_path in files:
            manifest_rel = f"{skill_base}/{rel_path}"
            content = fetch_bytes(f"{base_url}/{manifest_rel}")
            verify_bytes(manifest, manifest_rel, content)
            dest = cache_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        write_context(cache_dir, base_url, harness, skill, allowed_signers)

    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        fail(f"could not fetch verified skill {skill!r}: {exc}")

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
    parser.add_argument(
        "--allowed-signers",
        type=Path,
        default=Path(__file__).resolve().with_name("skills_hub_allowed_signers"),
    )
    args = parser.parse_args()
    skill_md = materialize(args.base_url, args.harness, args.skill, args.cache_dir, args.allowed_signers)
    print(skill_md)


if __name__ == "__main__":
    main()
