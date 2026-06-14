#!/usr/bin/env python3
"""Verify Skills-hub signed manifest entries and downloaded artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_SCHEMA_VERSION = 3
SIGNING_NAMESPACE = "skills-hub-manifest"
SIGNING_IDENTITY = "skills-hub-manifest"


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    print(f"skills-hub verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationError(f"invalid manifest generated_at timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_manifest(path: Path, *, check_freshness: bool = True) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VerificationError(f"could not read manifest JSON: {exc}") from exc

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise VerificationError(f"unsupported manifest schema_version {manifest.get('schema_version')!r}")

    generated_at = parse_timestamp(str(manifest.get("generated_at", "")))
    max_age = int(manifest.get("max_age_seconds", 0))
    if max_age <= 0:
        raise VerificationError("manifest max_age_seconds must be positive")
    if check_freshness:
        age = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds()
        if age > max_age:
            raise VerificationError("manifest is expired")
    return manifest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_signature(
    manifest_path: Path,
    signature_path: Path,
    allowed_signers_path: Path,
    *,
    identity: str = SIGNING_IDENTITY,
    namespace: str = SIGNING_NAMESPACE,
) -> None:
    if shutil.which("ssh-keygen") is None:
        raise VerificationError("ssh-keygen is required for manifest signature verification")
    if not signature_path.is_file():
        raise VerificationError(f"manifest signature is missing: {signature_path}")
    if not allowed_signers_path.is_file():
        raise VerificationError(f"allowed signers file is missing: {allowed_signers_path}")
    if not allowed_signers_path.read_text(encoding="utf-8").strip():
        raise VerificationError(f"allowed signers file is empty: {allowed_signers_path}")

    result = subprocess.run(
        [
            "ssh-keygen",
            "-Y",
            "verify",
            "-f",
            str(allowed_signers_path),
            "-I",
            identity,
            "-n",
            namespace,
            "-s",
            str(signature_path),
        ],
        input=manifest_path.read_bytes(),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise VerificationError(f"manifest signature verification failed: {detail}")


def verify_artifact(manifest: dict, relpath: str, artifact_path: Path) -> None:
    entry = manifest.get("files", {}).get(relpath)
    if not entry:
        raise VerificationError(f"manifest has no entry for {relpath}")
    if not artifact_path.is_file():
        raise VerificationError(f"artifact is missing: {artifact_path}")

    actual_size = artifact_path.stat().st_size
    expected_size = int(entry.get("size", -1))
    if actual_size != expected_size:
        raise VerificationError(f"size mismatch for {relpath}: expected {expected_size}, got {actual_size}")

    actual_sha = sha256_file(artifact_path)
    expected_sha = entry.get("sha256")
    if actual_sha != expected_sha:
        raise VerificationError(f"sha256 mismatch for {relpath}")


def verify_manifest_and_artifact(
    manifest_path: Path,
    signature_path: Path,
    allowed_signers_path: Path,
    relpath: str,
    artifact_path: Path,
    *,
    check_freshness: bool = True,
) -> None:
    verify_signature(manifest_path, signature_path, allowed_signers_path)
    manifest = load_manifest(manifest_path, check_freshness=check_freshness)
    verify_artifact(manifest, relpath, artifact_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("signature", type=Path)
    parser.add_argument("allowed_signers", type=Path)
    parser.add_argument("artifact_path", help="Manifest-relative artifact path")
    parser.add_argument("local_file", type=Path)
    parser.add_argument("--skip-freshness", action="store_true")
    args = parser.parse_args()

    try:
        verify_manifest_and_artifact(
            args.manifest,
            args.signature,
            args.allowed_signers,
            args.artifact_path,
            args.local_file,
            check_freshness=not args.skip_freshness,
        )
    except VerificationError as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
