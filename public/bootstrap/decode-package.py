#!/usr/bin/env python3
"""Decode and verify a text-safe Skills-hub Cowork package."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


PACKAGES_SCHEMA_VERSION = 1
SIGNING_IDENTITY = "skills-hub-manifest"
SIGNING_NAMESPACE = "skills-hub-manifest"


@dataclass
class DecodeResult:
    skill: str
    package_path: str
    sha256: str
    size: int


def fail(message: str) -> None:
    print(f"decode-package: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"invalid packages generated_at timestamp: {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def canonical_json_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def normalized_signature_bytes(path: Path) -> bytes:
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    except OSError as exc:
        fail(f"packages signature is missing: {path}: {exc}")


def verify_signature(packages: dict, signature_path: Path, allowed_signers: Path) -> None:
    if shutil.which("ssh-keygen") is None:
        fail("ssh-keygen is required for package index verification")
    if not signature_path.is_file():
        fail(f"packages signature is missing: {signature_path}")
    if not allowed_signers.is_file():
        fail(f"allowed signers file is missing: {allowed_signers}")
    if not allowed_signers.read_text(encoding="utf-8").strip():
        fail(f"allowed signers file is empty: {allowed_signers}")
    with tempfile.TemporaryDirectory(prefix="skills-hub-packages-sig-") as tmp:
        normalized_sig = Path(tmp) / "packages.json.sig"
        normalized_sig.write_bytes(normalized_signature_bytes(signature_path))
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
                str(normalized_sig),
            ],
            input=canonical_json_bytes(packages),
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(f"packages signature verification failed: {detail}")


def load_packages(path: Path) -> dict:
    try:
        packages = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"could not read packages JSON: {exc}")
    if packages.get("schema_version") != PACKAGES_SCHEMA_VERSION:
        fail(f"unsupported packages schema_version {packages.get('schema_version')!r}")
    generated_at = parse_timestamp(str(packages.get("generated_at", "")))
    max_age = int(packages.get("max_age_seconds", 0))
    if max_age <= 0:
        fail("packages max_age_seconds must be positive")
    age = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds()
    if age > max_age:
        fail("packages index is expired")
    return packages


def package_entry(packages: dict, skill: str) -> dict:
    for entry in packages.get("packages", []):
        if entry.get("name") == skill:
            return entry
    fail(f"skill {skill!r} not found in packages index")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_base64(path: Path) -> bytes:
    try:
        return base64.b64decode(path.read_text(encoding="ascii").encode("ascii"), validate=False)
    except (OSError, UnicodeDecodeError, binascii.Error) as exc:
        fail(f"could not decode base64 package text: {exc}")


def decode_package(skill: str, packages_path: Path, signature_path: Path, allowed_signers: Path, b64_path: Path, output_dir: Path) -> DecodeResult:
    packages = load_packages(packages_path)
    verify_signature(packages, signature_path, allowed_signers)
    entry = package_entry(packages, skill)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"{skill}.skill"
    data = decode_base64(b64_path)
    try:
        package_path.write_bytes(data)
        expected_size = int(entry.get("size", -1))
        if len(data) != expected_size:
            fail(f"size mismatch for {skill}.skill: expected {expected_size}, got {len(data)}")
        expected_sha = str(entry.get("sha256", ""))
        actual_sha = sha256_bytes(data)
        if actual_sha != expected_sha:
            fail(f"sha256 mismatch for {skill}.skill")
    except SystemExit:
        try:
            package_path.unlink()
        except OSError:
            pass
        raise
    return DecodeResult(skill=skill, package_path=str(package_path), sha256=str(entry["sha256"]), size=int(entry["size"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--allowed-signers", type=Path, required=True)
    parser.add_argument("--b64", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = decode_package(args.skill, args.packages, args.signature, args.allowed_signers, args.b64, args.output_dir)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(result.package_path)


if __name__ == "__main__":
    main()
