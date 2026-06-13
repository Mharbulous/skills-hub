#!/usr/bin/env python3
"""Manage Cowork-facing Skills-hub installs and assimilation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://skills-hub.web.app"
STALE_MARKERS = [
    "Myskillium Verified Resolver Stub",
    "myskillium-fetch.py",
    "myskillium",
    "skills/assemble-affidavit.tar.gz",
    "manifest schema v2",
]
CURRENT_MARKERS = [
    "Skills-hub Verified Resolver Stub",
    "skills-hub-fetch.py",
]
EXCLUDED_DIRS = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".skill"}
EXCLUDED_NAMES = {"manifest.json", "manifest.json.sig"}


@dataclass
class InstalledSkill:
    name: str
    skill_md: str
    root: str
    modified: float


@dataclass
class InventoryRow:
    name: str
    status: str
    evidence: str
    path: str = ""


def fail(message: str) -> None:
    print(f"skills-hub manager: {message}", file=sys.stderr)
    raise SystemExit(1)


def find_repo_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        if (path / "public" / "skills").is_dir() and (path / "build" / "build_index.py").is_file():
            return path
    fail("could not find skills-hub repo root")


def load_verifier(repo_root: Path):
    verifier = repo_root / "bootstrap" / "skills_hub_verify.py"
    if not verifier.is_file():
        fail(f"missing verifier: {verifier}")
    spec = importlib.util.spec_from_file_location("skills_hub_verify", verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-hub-manager/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = getattr(resp, "status", None) or 200
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {url}")
        return resp.read()


def load_catalog(repo_root: Path, index_path: Path | None = None, manifest_path: Path | None = None) -> dict:
    if manifest_path:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    if index_path:
        return json.loads(index_path.read_text(encoding="utf-8"))
    local_manifest = repo_root / "public" / "manifest.json"
    if local_manifest.is_file():
        return json.loads(local_manifest.read_text(encoding="utf-8"))
    local_index = repo_root / "public" / "index.json"
    if local_index.is_file():
        return json.loads(local_index.read_text(encoding="utf-8"))
    fail("no local manifest.json or index.json found")


def catalog_names(catalog: dict) -> set[str]:
    return {entry["name"] for entry in catalog.get("skills", [])}


def default_install_roots() -> list[Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    base = Path(appdata) / "Claude" / "local-agent-mode-sessions" / "skills-plugin"
    if not base.exists():
        return []
    return [base]


def discover_installed(install_roots: list[Path]) -> dict[str, list[InstalledSkill]]:
    installed: dict[str, list[InstalledSkill]] = {}
    for root in install_roots:
        if not root.exists():
            continue
        for skill_md in root.glob("**/skills/*/SKILL.md"):
            skill_root = skill_md.parent
            name = skill_root.name
            installed.setdefault(name, []).append(
                InstalledSkill(
                    name=name,
                    skill_md=str(skill_md),
                    root=str(skill_root),
                    modified=skill_md.stat().st_mtime,
                )
            )
    for rows in installed.values():
        rows.sort(key=lambda row: row.modified, reverse=True)
    return installed


def classify_installed(name: str, installed: list[InstalledSkill]) -> InventoryRow:
    if len(installed) > 1:
        return InventoryRow(
            name=name,
            status="conflict",
            evidence=f"multiple installed copies found ({len(installed)}); newest listed",
            path=installed[0].skill_md,
        )
    item = installed[0]
    text = Path(item.skill_md).read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    if any(marker.lower() in lowered for marker in STALE_MARKERS):
        return InventoryRow(name=name, status="stale-wrapper", evidence="matched stale wrapper marker", path=item.skill_md)
    if all(marker.lower() in lowered for marker in CURRENT_MARKERS) and f"cowork {name}".lower() in lowered:
        return InventoryRow(name=name, status="current", evidence="current Skills-hub resolver wrapper", path=item.skill_md)
    return InventoryRow(name=name, status="conflict", evidence="installed skill is not a recognized Skills-hub wrapper", path=item.skill_md)


def build_inventory(catalog: dict, installed: dict[str, list[InstalledSkill]]) -> list[InventoryRow]:
    names = catalog_names(catalog)
    rows: list[InventoryRow] = []
    for name in sorted(names):
        if name not in installed:
            rows.append(InventoryRow(name=name, status="missing", evidence="present in Skills-hub catalog but not installed"))
        else:
            rows.append(classify_installed(name, installed[name]))
    for name in sorted(set(installed) - names):
        newest = installed[name][0]
        rows.append(InventoryRow(name=name, status="orphan", evidence="installed in Cowork but absent from Skills-hub catalog", path=newest.skill_md))
    return rows


def print_inventory(rows: list[InventoryRow], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(row) for row in rows], indent=2))
        return
    for row in rows:
        suffix = f" ({row.path})" if row.path else ""
        print(f"{row.status}\t{row.name}\t{row.evidence}{suffix}")


def cmd_inventory(args) -> None:
    repo_root = find_repo_root()
    catalog = load_catalog(repo_root, args.index, args.manifest)
    roots = [Path(p) for p in args.install_root] if args.install_root else default_install_roots()
    rows = build_inventory(catalog, discover_installed(roots))
    print_inventory(rows, args.json)


def write_remote_file(base_url: str, relpath: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetch_bytes(f"{base_url.rstrip('/')}/{relpath}"))


def cmd_fetch_package(args) -> None:
    repo_root = find_repo_root()
    verifier = load_verifier(repo_root)
    base_url = args.base_url.rstrip("/")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    allowed_signers = args.allowed_signers or (repo_root / "bootstrap" / "skills_hub_allowed_signers")
    relpath = f"cowork/skill-packages/{args.skill}.skill"

    with tempfile.TemporaryDirectory(prefix="skills-hub-fetch-package-") as tmp:
        tmp_path = Path(tmp)
        manifest = tmp_path / "manifest.json"
        signature = tmp_path / "manifest.json.sig"
        package = output_dir / f"{args.skill}.skill"
        write_remote_file(base_url, "manifest.json", manifest)
        write_remote_file(base_url, "manifest.json.sig", signature)
        write_remote_file(base_url, relpath, package)
        try:
            verifier.verify_manifest_and_artifact(manifest, signature, allowed_signers, relpath, package)
        except verifier.VerificationError as exc:
            try:
                package.unlink()
            except OSError:
                pass
            fail(str(exc))
    print(package)


def should_copy(path: Path, source_root: Path) -> bool:
    rel = path.relative_to(source_root)
    if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def copy_skill_source(source: Path, dest: Path) -> None:
    for path in source.rglob("*"):
        if not path.is_file() or not should_copy(path, source):
            continue
        rel = path.relative_to(source)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def write_provenance(dest: Path, source: Path, license_value: str) -> None:
    text = "\n".join(
        [
            "# Provenance",
            "",
            f"- Source: `{source}`",
            f"- License: {license_value}",
            f"- Assimilated: {datetime.now(timezone.utc).isoformat()}",
            "",
        ]
    )
    (dest / "PROVENANCE.md").write_text(text, encoding="utf-8")


def cmd_assimilate(args) -> None:
    repo_root = find_repo_root()
    source = args.source.resolve()
    if not source.is_dir():
        fail(f"source skill directory not found: {source}")
    name = args.name or source.name
    dest = repo_root / "public" / "skills" / name
    if dest.exists():
        fail(f"target skill already exists: {dest}")
    if not (source / "SKILL.md").is_file():
        fail(f"source has no SKILL.md: {source}")
    dest.mkdir(parents=True)
    copy_skill_source(source, dest)
    write_provenance(dest, source, args.license)
    print(dest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("--install-root", action="append", default=[])
    inventory.add_argument("--index", type=Path)
    inventory.add_argument("--manifest", type=Path)
    inventory.add_argument("--json", action="store_true")
    inventory.set_defaults(func=cmd_inventory)

    fetch_package = sub.add_parser("fetch-package")
    fetch_package.add_argument("skill")
    fetch_package.add_argument("--base-url", default=BASE_URL)
    fetch_package.add_argument("--output-dir", type=Path, default=Path("outputs") / "skills-hub-packages")
    fetch_package.add_argument("--allowed-signers", type=Path)
    fetch_package.set_defaults(func=cmd_fetch_package)

    assimilate = sub.add_parser("assimilate")
    assimilate.add_argument("--source", type=Path, required=True)
    assimilate.add_argument("--name")
    assimilate.add_argument("--license", default="unknown")
    assimilate.set_defaults(func=cmd_assimilate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
