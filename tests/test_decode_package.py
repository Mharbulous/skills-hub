import base64
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DECODER = ROOT / "public" / "bootstrap" / "decode-package.py"


def load_decoder():
    spec = importlib.util.spec_from_file_location("decode_package", DECODER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_ssh_keygen():
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def make_signing_material(base_dir):
    require_ssh_keygen()
    key = base_dir / "signing_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test", "-f", str(key)], check=True)
    allowed = base_dir / "skills_hub_allowed_signers"
    allowed.write_text(
        f"skills-hub-manifest {(base_dir / 'signing_key.pub').read_text(encoding='utf-8')}",
        encoding="utf-8",
    )
    return key, allowed


def write_packages(base_dir, key, package_data=b"PK\x03\x04package", *, generated_at=None, max_age_seconds=3600, sha=None, size=None):
    packages = {
        "schema_version": 1,
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "max_age_seconds": max_age_seconds,
        "base_url": "https://skills-hub.web.app",
        "packages": [
            {
                "name": "alpha",
                "skill_path": "cowork/skill-packages/alpha.skill",
                "b64_path": "cowork/skill-packages/alpha.skill.b64.txt",
                "sha256": sha or sha256_bytes(package_data),
                "size": len(package_data) if size is None else size,
            }
        ],
    }
    packages_path = base_dir / "packages.json"
    packages_path.write_text(json.dumps(packages, indent=2), encoding="utf-8")
    canonical = base_dir / "packages.canonical.json"
    canonical.write_text(json.dumps(packages, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "skills-hub-manifest", str(canonical)], check=True)
    (base_dir / "packages.canonical.json.sig").replace(base_dir / "packages.json.sig")
    canonical.unlink()
    return packages_path, base_dir / "packages.json.sig"


def write_b64(path, data):
    encoded = base64.b64encode(data).decode("ascii")
    mangled = "\r\n ".join(encoded[i : i + 76] for i in range(0, len(encoded), 76)).rstrip()
    path.write_text(f" \n{mangled}\n ", encoding="ascii")


def test_decode_package_accepts_valid_whitespace_mangled_base64(tmp_path):
    decoder = load_decoder()
    key, allowed = make_signing_material(tmp_path)
    package_data = b"PK\x03\x04package"
    packages, signature = write_packages(tmp_path, key, package_data)
    packages.write_bytes(packages.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    signature.write_bytes(signature.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    b64 = tmp_path / "alpha.skill.b64.txt"
    write_b64(b64, package_data)

    result = decoder.decode_package("alpha", packages, signature, allowed, b64, tmp_path / "out")

    assert Path(result.package_path).read_bytes() == package_data
    assert result.sha256 == sha256_bytes(package_data)
    assert result.size == len(package_data)


def test_decode_package_rejects_tampered_packages_signature(tmp_path):
    decoder = load_decoder()
    key, allowed = make_signing_material(tmp_path)
    packages, signature = write_packages(tmp_path, key)
    packages.write_text(json.dumps({"schema_version": 1, "packages": []}), encoding="utf-8")
    b64 = tmp_path / "alpha.skill.b64.txt"
    write_b64(b64, b"PK\x03\x04package")

    with pytest.raises(SystemExit):
        decoder.decode_package("alpha", packages, signature, allowed, b64, tmp_path / "out")


def test_decode_package_rejects_expired_index(tmp_path):
    decoder = load_decoder()
    key, allowed = make_signing_material(tmp_path)
    packages, signature = write_packages(
        tmp_path,
        key,
        generated_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        max_age_seconds=1,
    )
    b64 = tmp_path / "alpha.skill.b64.txt"
    write_b64(b64, b"PK\x03\x04package")

    with pytest.raises(SystemExit):
        decoder.decode_package("alpha", packages, signature, allowed, b64, tmp_path / "out")


def test_decode_package_rejects_truncated_base64_and_removes_output(tmp_path):
    decoder = load_decoder()
    key, allowed = make_signing_material(tmp_path)
    package_data = b"PK\x03\x04package"
    packages, signature = write_packages(tmp_path, key, package_data)
    b64 = tmp_path / "alpha.skill.b64.txt"
    b64.write_text(base64.b64encode(package_data[:-2]).decode("ascii"), encoding="ascii")
    output = tmp_path / "out" / "alpha.skill"

    with pytest.raises(SystemExit):
        decoder.decode_package("alpha", packages, signature, allowed, b64, tmp_path / "out")

    assert not output.exists()


def test_decode_package_rejects_hash_mismatch_and_removes_output(tmp_path):
    decoder = load_decoder()
    key, allowed = make_signing_material(tmp_path)
    packages, signature = write_packages(tmp_path, key, b"PK\x03\x04package", sha="0" * 64)
    b64 = tmp_path / "alpha.skill.b64.txt"
    write_b64(b64, b"PK\x03\x04package")
    output = tmp_path / "out" / "alpha.skill"

    with pytest.raises(SystemExit):
        decoder.decode_package("alpha", packages, signature, allowed, b64, tmp_path / "out")

    assert not output.exists()
