#!/usr/bin/env python3
"""Fetch, verify, and materialize one Skills-hub skill into a local cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


BASE_URL = "https://skills-hub.web.app/hub"
NAMESPACE = "skills-hub-manifest"
SIGNER_IDENTITY = "skills-hub-manifest"


def fail(message: str) -> None:
    print(f"skills-hub-fetch: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "skills-hub-fetch/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        status = getattr(response, "status", 200) or 200
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {url}")
        return response.read()


def verify_signature(manifest_bytes: bytes, sig_bytes: bytes, allowed_signers: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="skills-hub-signature-") as temp_dir:
        temp = Path(temp_dir)
        manifest_path = temp / "manifest.json"
        sig_path = temp / "manifest.json.sig"
        manifest_path.write_bytes(manifest_bytes)
        sig_path.write_bytes(sig_bytes)
        result = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(allowed_signers),
                "-I",
                SIGNER_IDENTITY,
                "-n",
                NAMESPACE,
                "-s",
                str(sig_path),
            ],
            input=manifest_bytes,
            capture_output=True,
        )
    if result.returncode != 0:
        fail("manifest signature invalid")


def validate_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != 3:
        fail(f"unsupported manifest schema_version {manifest.get('schema_version')!r}")
    generated_at = parse_timestamp(str(manifest.get("generated_at", "")))
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    max_age = int(manifest.get("max_age_seconds", 0))
    if max_age <= 0:
        fail("manifest max_age_seconds must be positive")
    age = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds()
    if age > max_age:
        fail("manifest is expired")


def load_verified_manifest(base_url: str, allowed_signers: Path) -> dict:
    manifest_bytes = fetch_bytes(f"{base_url.rstrip('/')}/manifest.json")
    sig_bytes = fetch_bytes(f"{base_url.rstrip('/')}/manifest.json.sig")
    verify_signature(manifest_bytes, sig_bytes, allowed_signers)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    validate_manifest(manifest)
    return manifest


def verify_artifact_bytes(manifest: dict, relpath: str, data: bytes) -> dict:
    entry = manifest.get("files", {}).get(relpath)
    if not entry:
        fail(f"manifest has no entry for {relpath}")
    expected_size = int(entry.get("size", -1))
    if len(data) != expected_size:
        fail(f"size mismatch for {relpath}")
    expected_sha = entry.get("sha256")
    actual_sha = sha256_bytes(data)
    if actual_sha != expected_sha:
        fail(f"sha256 mismatch for {relpath}")
    return entry


def safe_extract_skill(tarball: Path, destination: Path, skill: str) -> None:
    with tarfile.open(tarball, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != skill or ".." in parts or member.name.startswith("/"):
                fail(f"unsafe tar member in {skill} archive")
            if member.issym() or member.islnk():
                fail(f"refusing link in {skill} archive")
        try:
            tar.extractall(destination, members, filter="data")
        except TypeError:
            tar.extractall(destination, members)


def cache_entry_is_fresh(meta_path: Path) -> bool:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        generated_at = parse_timestamp(meta["generated_at"])
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        max_age = int(meta["max_age_seconds"])
        age = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds()
        return age <= max_age
    except Exception:
        return False


def find_offline_cache(cache_root: Path, harness: str, skill: str) -> Path | None:
    root = cache_root / harness / skill
    if not root.is_dir():
        return None
    candidates = []
    for child in root.iterdir():
        skill_md = child / skill / "SKILL.md"
        meta = child / "skills-hub-cache.json"
        if skill_md.is_file() and meta.is_file() and cache_entry_is_fresh(meta):
            candidates.append(skill_md)
    return sorted(candidates)[-1] if candidates else None


def materialize(base_url: str, harness: str, skill: str, allowed_signers: Path, cache_root: Path) -> Path:
    try:
        manifest = load_verified_manifest(base_url, allowed_signers)
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        cached = find_offline_cache(cache_root, harness, skill)
        if cached:
            return cached
        fail(f"could not fetch verified manifest and no fresh cache exists: {exc}")

    relpath = f"{harness}/skills/{skill}.tar.gz"
    entry = manifest.get("files", {}).get(relpath)
    if not entry:
        fail(f"manifest has no entry for {relpath}")

    artifact_sha = entry["sha256"]
    final_dir = cache_root / harness / skill / artifact_sha
    final_skill_md = final_dir / skill / "SKILL.md"
    if final_skill_md.is_file():
        return final_skill_md

    tarball_bytes = fetch_bytes(f"{base_url.rstrip('/')}/{relpath}")
    verify_artifact_bytes(manifest, relpath, tarball_bytes)
    final_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="skills-hub-skill-") as temp_dir:
        temp = Path(temp_dir)
        tarball_path = temp / f"{skill}.tar.gz"
        extract_path = temp / "extract"
        extract_path.mkdir()
        tarball_path.write_bytes(tarball_bytes)
        safe_extract_skill(tarball_path, extract_path, skill)
        if not (extract_path / skill / "SKILL.md").is_file():
            fail(f"verified archive for {skill} did not contain {skill}/SKILL.md")
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.move(str(extract_path), str(final_dir))

    meta = {
        "harness": harness,
        "skill": skill,
        "artifact_path": relpath,
        "artifact_sha256": artifact_sha,
        "generated_at": manifest["generated_at"],
        "max_age_seconds": manifest["max_age_seconds"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    (final_dir / "skills-hub-cache.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return final_skill_md


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("harness", choices=["claude", "codex", "cowork"])
    parser.add_argument("skill")
    parser.add_argument("--base-url", default=os.environ.get("SKILLS_BASE_URL", BASE_URL))
    parser.add_argument("--allowed-signers", type=Path, default=Path(os.environ.get("SKILLS_HUB_ALLOWED_SIGNERS", Path(__file__).with_name("skills_hub_allowed_signers"))))
    parser.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("SKILLS_HUB_CACHE_DIR", Path.home() / ".skills-hub" / "cache")))
    args = parser.parse_args()
    skill_md = materialize(args.base_url, args.harness, args.skill, args.allowed_signers, args.cache_dir)
    print(skill_md)


if __name__ == "__main__":
    main()
