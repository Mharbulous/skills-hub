import hashlib
import importlib.util
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_verifier():
    spec = importlib.util.spec_from_file_location("skills_hub_verify", ROOT / "bootstrap" / "skills_hub_verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_manifest(path, relpath, artifact):
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 3600,
        "files": {
            relpath: {
                "sha256": digest,
                "size": artifact.stat().st_size,
            }
        },
        "skills": [],
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")


def make_signed_manifest(tmp_path, relpath="cowork/skill-packages/alpha.skill"):
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available")
    key = tmp_path / "signing_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(key)], check=True)
    allowed = tmp_path / "allowed_signers"
    public_key = (tmp_path / "signing_key.pub").read_text(encoding="utf-8")
    allowed.write_text(f"skills-hub-manifest {public_key}", encoding="utf-8")
    artifact = tmp_path / "alpha.skill"
    artifact.write_bytes(b"package")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest, relpath, artifact)
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(manifest)], check=True)
    return manifest, tmp_path / "manifest.json.sig", allowed, relpath, artifact


def test_verifier_accepts_signed_matching_artifact(tmp_path):
    verifier = load_verifier()
    manifest, signature, allowed, relpath, artifact = make_signed_manifest(tmp_path)

    verifier.verify_manifest_and_artifact(manifest, signature, allowed, relpath, artifact)


def test_verifier_rejects_hash_mismatch(tmp_path):
    verifier = load_verifier()
    manifest, signature, allowed, relpath, artifact = make_signed_manifest(tmp_path)
    artifact.write_bytes(b"tampered")

    with pytest.raises(verifier.VerificationError):
        verifier.verify_manifest_and_artifact(manifest, signature, allowed, relpath, artifact)
