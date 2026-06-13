#!/usr/bin/env python3
"""Manage Cowork-facing Skills-hub installs and assimilation."""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://skills-hub.web.app"
DEFAULT_GITHUB_REPO = "Mharbulous/skills-hub"
CONTEXT_FILE = ".skills-hub-context.json"
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


@dataclass
class FetchResult:
    skill: str
    package_path: str
    package_url: str
    sha256: str
    size: int


def fail(message: str) -> None:
    print(f"skills-hub manager: {message}", file=sys.stderr)
    raise SystemExit(1)


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def skill_dir() -> Path:
    return script_dir().parent


def read_context() -> dict:
    path = skill_dir() / CONTEXT_FILE
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid resolver context at {path}: {exc}")


def find_repo_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        if (path / "public" / "skills").is_dir() and (path / "build" / "build_index.py").is_file():
            return path
    fail("could not find skills-hub repo root")


def load_verifier():
    verifier = script_dir() / "skills_hub_verify.py"
    if not verifier.is_file():
        fail(f"missing verifier: {verifier}")
    spec = importlib.util.spec_from_file_location("skills_hub_verify", verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_allowed_signers(override: Path | None = None, context: dict | None = None) -> Path:
    if override:
        return override
    context = context or read_context()
    context_path = context.get("allowed_signers_path")
    if context_path:
        return Path(context_path)
    local = skill_dir() / "skills_hub_allowed_signers"
    if local.is_file():
        return local
    fail("could not locate skills_hub_allowed_signers; pass --allowed-signers <path>")


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-hub-manager/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = getattr(resp, "status", None) or 200
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {url}")
        return resp.read()


def verified_remote_manifest(base_url: str, allowed_signers: Path, verifier) -> dict:
    base_url = base_url.rstrip("/")
    try:
        manifest_data = fetch_bytes(f"{base_url}/manifest.json")
        signature_data = fetch_bytes(f"{base_url}/manifest.json.sig")
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        fail(f"could not download signed manifest from {base_url}: {exc}")
    with tempfile.TemporaryDirectory(prefix="skills-hub-manifest-") as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        signature_path = tmp_path / "manifest.json.sig"
        manifest_path.write_bytes(manifest_data)
        signature_path.write_bytes(signature_data)
        try:
            verifier.verify_signature(manifest_path, signature_path, allowed_signers)
            return verifier.load_manifest(manifest_path)
        except verifier.VerificationError as exc:
            fail(str(exc))


def load_catalog(
    *,
    index_path: Path | None = None,
    manifest_path: Path | None = None,
    base_url: str | None = None,
    allowed_signers: Path | None = None,
    verifier=None,
) -> dict:
    if manifest_path:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    if index_path:
        return json.loads(index_path.read_text(encoding="utf-8"))
    if not base_url or not allowed_signers or verifier is None:
        fail("no catalog source; pass --manifest, --index, or run from a verified Skills-hub cache")
    return verified_remote_manifest(base_url, allowed_signers, verifier)


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


def context_install_roots(context: dict) -> list[Path]:
    original = context.get("original_stub_dir")
    if not original:
        return []
    path = Path(original)
    if path.name and path.parent.name == "skills":
        return [path.parent.parent]
    for parent in path.parents:
        if parent.name == "skills":
            return [parent.parent]
    return []


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
    context = read_context()
    base_url = args.base_url or context.get("base_url") or BASE_URL
    verifier = None
    allowed_signers = None
    if not args.index and not args.manifest:
        verifier = load_verifier()
        allowed_signers = resolve_allowed_signers(args.allowed_signers, context)
    catalog = load_catalog(
        index_path=args.index,
        manifest_path=args.manifest,
        base_url=base_url,
        allowed_signers=allowed_signers,
        verifier=verifier,
    )
    roots = [Path(p) for p in args.install_root] if args.install_root else context_install_roots(context)
    if not roots:
        roots = default_install_roots()
    if not roots:
        fail("could not find Cowork install root; rerun with --install-root <path>")
    rows = build_inventory(catalog, discover_installed(roots))
    print_inventory(rows, args.json)


def write_remote_file(base_url: str, relpath: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetch_bytes(f"{base_url.rstrip('/')}/{relpath}"))


def cmd_fetch_package(args) -> None:
    context = read_context()
    verifier = load_verifier()
    base_url = (args.base_url or context.get("base_url") or BASE_URL).rstrip("/")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    allowed_signers = resolve_allowed_signers(args.allowed_signers, context)
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
            verifier.verify_signature(manifest, signature, allowed_signers)
            manifest_doc = verifier.load_manifest(manifest)
            verifier.verify_artifact(manifest_doc, relpath, package)
        except verifier.VerificationError as exc:
            try:
                package.unlink()
            except OSError:
                pass
            fail(str(exc))
    entry = manifest_doc["files"][relpath]
    result = FetchResult(
        skill=args.skill,
        package_path=str(package),
        package_url=f"{base_url}/{relpath}",
        sha256=entry["sha256"],
        size=int(entry["size"]),
    )
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
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


def provenance_text(source: Path, license_value: str) -> str:
    return "\n".join(
        [
            "# Provenance",
            "",
            f"- Source: `{source}`",
            f"- License: {license_value}",
            f"- Assimilated: {datetime.now(timezone.utc).isoformat()}",
            "",
        ]
    )


def write_provenance(dest: Path, source: Path, license_value: str) -> None:
    text = provenance_text(source, license_value)
    (dest / "PROVENANCE.md").write_text(text, encoding="utf-8")


def selected_skill_files(source: Path) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or not should_copy(path, source):
            continue
        files.append((path.relative_to(source).as_posix(), path.read_bytes()))
    return files


def validate_repo(value: str) -> tuple[str, str]:
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        fail("--repo must be in owner/name format")
    return parts[0], parts[1]


def github_request(method: str, path: str, token: str, data: dict | None = None, expected: tuple[int, ...] = (200,)):
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "skills-hub-manager/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = getattr(resp, "status", None) or 200
            response_body = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in expected:
            return exc.code, {}
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"GitHub API {method} {path} failed with HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API {method} {path} failed: {exc}")
    if status not in expected:
        fail(f"GitHub API {method} {path} returned HTTP {status}")
    if not response_body:
        return status, {}
    return status, json.loads(response_body.decode("utf-8"))


def cmd_assimilate_github_pr(args, source: Path, name: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        fail("GITHUB_TOKEN is required for --github-pr with contents:write and pull-requests:write access")
    owner, repo = validate_repo(args.repo)
    repo_path = f"/repos/{owner}/{repo}"
    target_path = f"public/skills/{name}"
    branch = f"skills-hub/assimilate-{name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    github_request("GET", repo_path, token)
    status, _ = github_request(
        "GET",
        f"{repo_path}/contents/{urllib.parse.quote(target_path)}?ref={urllib.parse.quote(args.base, safe='')}",
        token,
        expected=(200, 404),
    )
    if status == 200:
        fail(f"target skill already exists on {args.base}: {target_path}")

    _, base_ref = github_request("GET", f"{repo_path}/git/ref/heads/{urllib.parse.quote(args.base, safe='')}", token)
    github_request("POST", f"{repo_path}/git/refs", token, {"ref": f"refs/heads/{branch}", "sha": base_ref["object"]["sha"]}, expected=(201,))

    files = selected_skill_files(source)
    files.append(("PROVENANCE.md", provenance_text(source, args.license).encode("utf-8")))
    for relpath, content in files:
        upload_path = f"{target_path}/{relpath}"
        github_request(
            "PUT",
            f"{repo_path}/contents/{urllib.parse.quote(upload_path)}",
            token,
            {
                "message": f"Add {name}: {relpath}",
                "content": base64.b64encode(content).decode("ascii"),
                "branch": branch,
            },
            expected=(201,),
        )

    _, pr = github_request(
        "POST",
        f"{repo_path}/pulls",
        token,
        {
            "title": f"Assimilate {name}",
            "head": branch,
            "base": args.base,
            "body": f"Adds `{name}` to Skills-hub.\n\nSource: `{source}`\nLicense: {args.license}\n",
        },
        expected=(201,),
    )
    print(pr.get("html_url", ""))


def cmd_assimilate(args) -> None:
    source = args.source.resolve()
    if not source.is_dir():
        fail(f"source skill directory not found: {source}")
    name = args.name or source.name
    if not (source / "SKILL.md").is_file():
        fail(f"source has no SKILL.md: {source}")
    if getattr(args, "github_pr", False):
        cmd_assimilate_github_pr(args, source, name)
        return

    repo_root = find_repo_root()
    dest = repo_root / "public" / "skills" / name
    if dest.exists():
        fail(f"target skill already exists: {dest}")
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
    inventory.add_argument("--base-url")
    inventory.add_argument("--allowed-signers", type=Path)
    inventory.add_argument("--json", action="store_true")
    inventory.set_defaults(func=cmd_inventory)

    fetch_package = sub.add_parser("fetch-package")
    fetch_package.add_argument("skill")
    fetch_package.add_argument("--base-url")
    fetch_package.add_argument("--output-dir", type=Path, default=Path("outputs") / "skills-hub-packages")
    fetch_package.add_argument("--allowed-signers", type=Path)
    fetch_package.add_argument("--json", action="store_true")
    fetch_package.set_defaults(func=cmd_fetch_package)

    assimilate = sub.add_parser("assimilate")
    assimilate.add_argument("--source", type=Path, required=True)
    assimilate.add_argument("--name")
    assimilate.add_argument("--license", default="unknown")
    assimilate.add_argument("--github-pr", action="store_true")
    assimilate.add_argument("--repo", default=DEFAULT_GITHUB_REPO)
    assimilate.add_argument("--base", default="main")
    assimilate.set_defaults(func=cmd_assimilate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
