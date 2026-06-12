#!/usr/bin/env python3
"""Verify Skills-hub signed-manifest artifact entries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def fail(message: str) -> None:
    print(f"skills-hub verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(f"invalid manifest generated_at timestamp: {value!r}")


def load_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact JSON errors vary
        fail(f"could not read manifest JSON: {exc}")

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

    return manifest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(manifest_path: Path, relpath: str, artifact_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    entry = manifest.get("files", {}).get(relpath)
    if not entry:
        fail(f"manifest has no entry for {relpath}")
    if not artifact_path.is_file():
        fail(f"artifact is missing: {artifact_path}")

    actual_size = artifact_path.stat().st_size
    expected_size = int(entry.get("size", -1))
    if actual_size != expected_size:
        fail(f"size mismatch for {relpath}: expected {expected_size}, got {actual_size}")

    actual_sha = sha256_file(artifact_path)
    expected_sha = entry.get("sha256")
    if actual_sha != expected_sha:
        fail(f"sha256 mismatch for {relpath}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("artifact_path")
    parser.add_argument("local_file", type=Path)
    args = parser.parse_args()
    verify_artifact(args.manifest, args.artifact_path, args.local_file)


if __name__ == "__main__":
    main()
