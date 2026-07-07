#!/usr/bin/env python3
"""Manage Cowork-facing Skills-hub installs and absorption."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_GITHUB_REPO = "Mharbulous/skills-hub"
DEFAULT_GITHUB_REF = "main"
CONTEXT_FILE = ".skills-hub-context.json"
LOCKFILE_NAME = "skills-hub-lock.json"
EXCLUDED_DIRS = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".skill"}
EXCLUDED_NAMES = {"manifest.json", "manifest.json.sig"}

_PREAMBLE_START = "<!-- skills-hub-freshness-check: start -->"
_PREAMBLE_END = "<!-- skills-hub-freshness-check: end -->"


class CatalogUnavailable(RuntimeError):
    pass


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
class LocalInventoryRow:
    name: str
    local_status: str
    evidence: str
    path: str = ""


@dataclass
class FetchResult:
    skill: str
    package_path: str
    package_url: str
    sha256: str
    size: int
    content_hash: str
    source_ref: str


def fail(message: str) -> None:
    print(f"skills-hub manager: {message}", file=sys.stderr)
    raise SystemExit(1)


def emit_structured_error(skill: str, message: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"error": message, "skill": skill}, indent=2))
        raise SystemExit(1)
    fail(f"{skill}: {message}")


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
        fail(f"invalid context file at {path}: {exc}")


def find_repo_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        if (path / "public" / "skills").is_dir() and (path / "build" / "build_index.py").is_file():
            return path
    fail("could not find skills-hub repo root")


def validate_repo(value: str) -> tuple[str, str]:
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        fail("--repo must be in owner/name format")
    return parts[0], parts[1]


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-hub-manager/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = getattr(resp, "status", None) or 200
        if status != 200:
            raise RuntimeError(f"HTTP {status} for {url}")
        return resp.read()


def github_head_sha(repo: str, ref: str) -> str | None:
    """Return the HEAD commit SHA for repo@ref via the GitHub API, or None on any failure."""
    owner, name = validate_repo(repo)
    url = (
        f"https://api.github.com/repos/{owner}/{name}/commits/"
        f"{urllib.parse.quote(ref, safe='')}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "skills-hub-manager/1",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["sha"]
    except Exception:
        return None


def fetch_github_repo_git(repo: str, ref: str, dest: Path) -> Path:
    """Clone a GitHub repo via git (fallback when zip download is blocked)."""
    owner, name = validate_repo(repo)
    clone_url = f"https://github.com/{owner}/{name}.git"
    repo_dir = dest / "repo-git"
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", "--single-branch", "--branch", ref,
             clone_url, str(repo_dir)],
            check=True,
            capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(f"git clone failed for {repo}@{ref}: {exc}") from exc
    return repo_dir


def fetch_github_repo(repo: str, ref: str, dest: Path) -> Path:
    owner, name = validate_repo(repo)
    archive_url = f"https://codeload.github.com/{owner}/{name}/zip/{urllib.parse.quote(ref, safe='')}"
    try:
        archive = dest / "repo.zip"
        archive.write_bytes(fetch_bytes(archive_url))
        extract_dir = dest / "repo"
        extract_dir.mkdir()
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                parts = Path(member.filename).parts
                if not parts or any(part == ".." for part in parts):
                    fail(f"unsafe path in GitHub archive: {member.filename}")
            zf.extractall(extract_dir)
        roots = [path for path in extract_dir.iterdir() if path.is_dir()]
        if len(roots) != 1:
            fail(f"could not locate repository root in GitHub archive for {repo}@{ref}")
        return roots[0]
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return fetch_github_repo_git(repo, ref, dest)


def github_skill_dirs(repo_root: Path) -> list[Path]:
    skills = repo_root / "public" / "skills"
    if not skills.is_dir():
        fail(f"GitHub repo archive has no public/skills directory: {repo_root}")
    return sorted(path for path in skills.iterdir() if (path / "SKILL.md").is_file())


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def _strip_preamble(text: str) -> str:
    """Remove an injected freshness-check preamble block from SKILL.md text, if present."""
    start = text.find(_PREAMBLE_START)
    end = text.find(_PREAMBLE_END)
    if start == -1 or end == -1:
        return text
    return text[:start] + text[end + len(_PREAMBLE_END):].lstrip("\n")


def direct_package_files(skill_source: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(skill_source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_source)
        if any(part in EXCLUDED_DIRS or part == "overrides" or part.startswith(".") for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(rel)
    return files


def merged_cowork_skill_text(skill_source: Path) -> str:
    text = (skill_source / "SKILL.md").read_text(encoding="utf-8")
    # Strip any injected preamble so content_hash is preamble-independent.
    text = _strip_preamble(text)
    override = skill_source / "overrides" / "cowork.md"
    if override.is_file():
        body = strip_frontmatter(override.read_text(encoding="utf-8")).strip()
        if body:
            text = text.rstrip() + "\n\n" + body + "\n"
    return text


def _inject_preamble(text: str, skill_name: str) -> str:
    """Prepend a freshness-check preamble into skill text, inserted after frontmatter."""
    preamble = (
        _PREAMBLE_START + "\n\n"
        "## Freshness check\n\n"
        f"Before executing this skill, check whether `{skill_name}` has updates:\n\n"
        "1. The skills-hub management script is at:\n"
        f"   `<this SKILL.md's directory>/../skills-hub/scripts/manage_cowork_skills.py`\n"
        "   If that file does not exist, skip this check and proceed silently.\n"
        f"2. Run: `python \"<path>\" inventory --names {skill_name} --json`\n"
        "3. Branch on the result status:\n"
        "   - `current`: proceed silently.\n"
        f"   - `stale`: tell the user — \"This skill has updates available. Run\n"
        f"     `/skills-hub update {skill_name}` to get the latest version, or\n"
        "     continue with the installed version.\" Wait for their choice.\n"
        f"   - `modified`: tell the user — \"This skill has local modifications.\n"
        f"     Run `/skills-hub push {skill_name}` to contribute your changes\n"
        "     upstream.\" Then proceed.\n"
        f"   - `diverged`: tell the user — \"This skill has both local edits and\n"
        f"     hub updates. Run `/skills-hub update {skill_name}` to review\n"
        "     options.\" Wait for their choice.\n"
        "   - Any error or non-zero exit: proceed silently.\n\n"
        + _PREAMBLE_END + "\n\n"
    )
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            header = text[:end + 4]
            body = text[end + 4:].lstrip("\n")
            return header + "\n\n" + preamble + body
    return preamble + text


def content_hash(skill_dir_path: Path) -> str:
    """Hash all publishable files in a skill directory for freshness comparison."""
    digest = hashlib.sha256()
    for rel in direct_package_files(skill_dir_path):
        digest.update(rel.as_posix().encode("utf-8"))
        if rel.as_posix() == "SKILL.md":
            digest.update(merged_cowork_skill_text(skill_dir_path).encode("utf-8"))
        else:
            digest.update((skill_dir_path / rel).read_bytes())
    return digest.hexdigest()


def github_catalog(repo_root: Path) -> dict:
    return {
        "skills": [
            {"name": path.name, "content_hash": content_hash(path)}
            for path in github_skill_dirs(repo_root)
        ]
    }


def read_lockfile(install_root: Path) -> dict:
    path = install_root / LOCKFILE_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("skills", {}) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_lockfile(install_root: Path, lock: dict) -> None:
    path = install_root / LOCKFILE_NAME
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps({"schema_version": 1, "skills": lock}, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except OSError:
        pass


def record_install(install_root: Path, skill_name: str, content_hash_value: str, source_ref: str) -> None:
    lock = read_lockfile(install_root)
    lock[skill_name] = {
        "content_hash": content_hash_value,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source_ref": source_ref,
    }
    write_lockfile(install_root, lock)


def merge_lockfiles(install_roots: list[Path]) -> dict:
    merged: dict[str, dict] = {}
    for root in install_roots:
        for name, entry in read_lockfile(root).items():
            existing = merged.get(name)
            if existing is None or entry.get("installed_at", "") > existing.get("installed_at", ""):
                merged[name] = entry
    return merged


CATALOG_CACHE_NAME = "skills-hub-catalog-cache.json"


def cache_catalog(install_root: Path, catalog: dict, ref_sha: str | None = None) -> None:
    path = install_root / CATALOG_CACHE_NAME
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(
                {
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "ref_sha": ref_sha,
                    "catalog": catalog,
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except OSError:
        pass


def read_cached_catalog(install_roots: list[Path]) -> tuple[dict, str, str | None] | None:
    best: tuple[dict, str, str | None] | None = None
    for root in install_roots:
        path = root / CATALOG_CACHE_NAME
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = data.get("cached_at", "")
            ref_sha = data.get("ref_sha")
            catalog = data.get("catalog")
            if isinstance(catalog, dict) and (best is None or cached_at > best[1]):
                best = (catalog, cached_at, ref_sha)
        except (json.JSONDecodeError, OSError):
            continue
    return best


def write_direct_skill_package(
    repo_root: Path, skill: str, output_dir: Path, repo: str, ref: str, as_json: bool, sha: str | None = None
) -> FetchResult:
    skill_source = repo_root / "public" / "skills" / skill
    if not (skill_source / "SKILL.md").is_file():
        emit_structured_error(skill, "skill not found in GitHub repo", as_json)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        emit_structured_error(skill, f"output directory not writable: {output_dir}; pass --output-dir <writable dir> ({exc})", as_json)
    package = output_dir / f"{skill}.skill"
    try:
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel in direct_package_files(skill_source):
                archive_name = f"{skill}/{rel.as_posix()}"
                if rel.as_posix() == "SKILL.md":
                    skill_text = merged_cowork_skill_text(skill_source)
                    if skill != "skills-hub":
                        skill_text = _inject_preamble(skill_text, skill)
                    zf.writestr(archive_name, skill_text)
                else:
                    zf.write(skill_source / rel, archive_name)
    except OSError as exc:
        emit_structured_error(skill, f"output directory not writable: {output_dir}; pass --output-dir <writable dir> ({exc})", as_json)
    source_ref = f"{repo}@{sha}" if sha else f"{repo}@{ref}"
    return FetchResult(
        skill=skill,
        package_path=str(package),
        package_url=f"https://github.com/{repo}/tree/{urllib.parse.quote(ref, safe='')}/public/skills/{urllib.parse.quote(skill)}",
        sha256=sha256_file(package),
        size=package.stat().st_size,
        content_hash=content_hash(skill_source),
        source_ref=source_ref,
    )


def catalog_unavailable(message: str) -> None:
    raise CatalogUnavailable(message)


def load_catalog(
    *,
    index_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    if manifest_path:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    if index_path:
        return json.loads(index_path.read_text(encoding="utf-8"))
    fail("no catalog source; pass --manifest or --index")


def catalog_names(catalog: dict) -> set[str]:
    return {entry["name"] for entry in catalog.get("skills", [])}


def catalog_hashes(catalog: dict) -> dict[str, str]:
    return {
        entry["name"]: entry["content_hash"]
        for entry in catalog.get("skills", [])
        if "content_hash" in entry
    }


def skill_dir_install_root() -> list[Path]:
    parent = skill_dir().parent
    if parent.name == "skills" and parent.parent.exists():
        plugin_level = parent.parent
        for ancestor in plugin_level.parents:
            if ancestor.name == "skills-plugin":
                return [ancestor]
            if ancestor.name == ".remote-plugins":
                claude_dir = ancestor.parent / ".claude"
                if (claude_dir / "skills").is_dir():
                    return [claude_dir]
                break
        return [plugin_level]
    return []


def default_install_roots() -> list[Path]:
    roots = skill_dir_install_root()
    home = Path.home()
    claude_home = home / ".claude"
    if (claude_home / "skills").is_dir() and claude_home not in roots:
        roots.append(claude_home)
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "Claude" / "local-agent-mode-sessions" / "skills-plugin"
        if base.exists() and base not in roots:
            roots.append(base)
    return roots


def normalize_install_roots(roots: list[Path]) -> list[Path]:
    normalized: list[Path] = []
    for root in roots:
        corrected = root.parent if root.name == "skills" else root
        if corrected not in normalized:
            normalized.append(corrected)
    return normalized


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


def classify_installed(
    name: str,
    installed: list[InstalledSkill],
    catalog_hash: str | None = None,
    lock_hash: str | None = None,
) -> InventoryRow:
    if len(installed) > 1:
        return InventoryRow(
            name=name,
            status="conflict",
            evidence=f"multiple installed copies found ({len(installed)}); newest listed",
            path=installed[0].skill_md,
        )
    item = installed[0]
    try:
        installed_hash = content_hash(Path(item.root))
    except OSError:
        return InventoryRow(
            name=name,
            status="stale",
            evidence="could not read installed skill files for comparison",
            path=item.skill_md,
        )
    if catalog_hash and installed_hash == catalog_hash:
        return InventoryRow(name=name, status="current", evidence="content matches GitHub source", path=item.skill_md)
    if lock_hash:
        user_modified = installed_hash != lock_hash
        hub_updated = catalog_hash is not None and catalog_hash != lock_hash
        if user_modified and hub_updated:
            return InventoryRow(name=name, status="diverged", evidence="local edits and hub updates — review locally or force-update", path=item.skill_md)
        if user_modified:
            return InventoryRow(name=name, status="modified", evidence="locally edited; hub content unchanged", path=item.skill_md)
        if hub_updated:
            return InventoryRow(name=name, status="stale", evidence="hub updated; safe to update", path=item.skill_md)
        return InventoryRow(name=name, status="current", evidence="unchanged since install", path=item.skill_md)
    if catalog_hash:
        return InventoryRow(name=name, status="stale", evidence="content differs from GitHub source; no install record", path=item.skill_md)
    return InventoryRow(name=name, status="stale", evidence="could not compare", path=item.skill_md)


def build_inventory(catalog: dict, installed: dict[str, list[InstalledSkill]], install_roots: list[Path] | None = None) -> list[InventoryRow]:
    names = catalog_names(catalog)
    hashes = catalog_hashes(catalog)
    lock = merge_lockfiles(install_roots) if install_roots else {}
    rows: list[InventoryRow] = []
    for name in sorted(names):
        if name not in installed:
            rows.append(InventoryRow(name=name, status="missing", evidence="present in Skills-hub catalog but not installed"))
        else:
            lock_hash = lock.get(name, {}).get("content_hash")
            rows.append(classify_installed(name, installed[name], hashes.get(name), lock_hash))
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


def inventory_roots(args, context: dict) -> list[Path]:
    roots = [Path(p) for p in args.install_root] if args.install_root else context_install_roots(context)
    if not roots:
        roots = default_install_roots()
    return normalize_install_roots(roots)


def no_install_root_message(args, context: dict) -> str:
    explicit = ", ".join(args.install_root) if args.install_root else "none supplied"
    stub = context.get("original_stub_dir") or "absent"
    home_claude = str(Path.home() / ".claude")
    appdata = os.environ.get("APPDATA") or "absent"
    own_parent = skill_dir().parent
    own_hint = f"{own_parent} (not under a skills/ parent)" if own_parent.name != "skills" else "absent"
    return (
        "could not find Cowork install root. Tried:\n"
        f"  --install-root: {explicit}\n"
        f"  context original_stub_dir: {stub}\n"
        f"  skill_dir parent: {own_hint}\n"
        f"  HOME/.claude: {home_claude}\n"
        f"  APPDATA: {appdata}\n"
        "  Rerun with --install-root <dir that CONTAINS skills/> "
        "(the parent of the skills/ directory; the skills/ dir itself is auto-corrected)."
    )


def warn_empty_install_roots(roots: list[Path]) -> None:
    listed = "\n".join(f"  - {root}" for root in roots)
    print(
        "skills-hub manager: scanned install roots but found 0 SKILL.md under */skills/*/:\n"
        f"{listed}\n"
        "  Is --install-root the parent of skills/ (the dir that CONTAINS skills/)?",
        file=sys.stderr,
    )


def classify_local_installed(name: str, installed: list[InstalledSkill]) -> LocalInventoryRow:
    if len(installed) > 1:
        return LocalInventoryRow(
            name=name,
            local_status="conflict",
            evidence=f"multiple installed copies found ({len(installed)}); newest listed",
            path=installed[0].skill_md,
        )
    return LocalInventoryRow(
        name=name,
        local_status="installed",
        evidence="installed locally; freshness cannot be verified without catalog",
        path=installed[0].skill_md,
    )


def build_local_inventory(installed: dict[str, list[InstalledSkill]]) -> list[LocalInventoryRow]:
    return [classify_local_installed(name, installed[name]) for name in sorted(installed)]


def print_degraded_inventory(error: str, rows: list[LocalInventoryRow], as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "catalog": {"status": "blocked", "error": error},
                    "installed": [asdict(row) for row in rows],
                },
                indent=2,
            )
        )
        return
    print(f"catalog-blocked\t{error}")
    for row in rows:
        suffix = f" ({row.path})" if row.path else ""
        print(f"{row.local_status}\t{row.name}\t{row.evidence}{suffix}")


def parse_names_filter(args) -> set[str] | None:
    raw = getattr(args, "names", None)
    if not raw:
        return None
    return {n.strip() for n in raw.split(",") if n.strip()}


def cmd_inventory(args) -> None:
    context = read_context()
    repo = getattr(args, "repo", DEFAULT_GITHUB_REPO)
    ref = getattr(args, "ref", DEFAULT_GITHUB_REF)
    names_filter = parse_names_filter(args)
    use_github_catalog = not args.index and not args.manifest
    roots = inventory_roots(args, context)
    sha = None
    catalog_from_cache = False
    try:
        if use_github_catalog:
            sha = github_head_sha(repo, ref)
            cached_result = read_cached_catalog(roots) if roots else None
            if sha is not None and cached_result is not None and cached_result[2] == sha:
                catalog = cached_result[0]
                catalog_from_cache = True
            else:
                try:
                    with tempfile.TemporaryDirectory(prefix="skills-hub-github-") as tmp:
                        repo_root = fetch_github_repo(repo, ref, Path(tmp))
                        catalog = github_catalog(repo_root)
                except (urllib.error.HTTPError, urllib.error.URLError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
                    catalog_unavailable(f"could not download GitHub repo {repo}@{ref}: {exc}")
        else:
            catalog = load_catalog(
                index_path=args.index,
                manifest_path=args.manifest,
            )
    except CatalogUnavailable as exc:
        if roots:
            cached = read_cached_catalog(roots)
            if cached:
                catalog, cached_at, _ = cached
                installed = discover_installed(roots)
                rows = build_inventory(catalog, installed, roots)
                for row in rows:
                    row.evidence += f" (offline — using cached catalog from {cached_at})"
                if names_filter:
                    rows = [r for r in rows if r.name in names_filter]
                print_inventory(rows, args.json)
                return
        installed = discover_installed(roots) if roots else {}
        local_rows = build_local_inventory(installed)
        if names_filter:
            local_rows = [r for r in local_rows if r.name in names_filter]
        print_degraded_inventory(str(exc), local_rows, args.json)
        return
    if not roots:
        fail(no_install_root_message(args, context))
    installed = discover_installed(roots)
    if not installed:
        warn_empty_install_roots(roots)
    if use_github_catalog and not catalog_from_cache and roots:
        cache_catalog(roots[0], catalog, ref_sha=sha)
    rows = build_inventory(catalog, installed, roots)
    if names_filter:
        rows = [r for r in rows if r.name in names_filter]
    print_inventory(rows, args.json)


def cmd_fetch_package(args) -> None:
    repo = getattr(args, "repo", DEFAULT_GITHUB_REPO)
    ref = getattr(args, "ref", DEFAULT_GITHUB_REF)
    output_dir = args.output_dir
    sha = github_head_sha(repo, ref)
    try:
        with tempfile.TemporaryDirectory(prefix="skills-hub-github-") as tmp:
            repo_root = fetch_github_repo(repo, ref, Path(tmp))
            result = write_direct_skill_package(repo_root, args.skill, output_dir, repo, ref, args.json, sha=sha)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        emit_structured_error(args.skill, f"could not download GitHub repo {repo}@{ref}: {exc}", args.json)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(result.package_path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            f"- Pushed: {datetime.now(timezone.utc).isoformat()}",
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


def cmd_push_github_pr(args, source: Path, name: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        fail("GITHUB_TOKEN is required for --github-pr with contents:write and pull-requests:write access")
    owner, repo = validate_repo(args.repo)
    repo_path = f"/repos/{owner}/{repo}"
    target_path = f"public/skills/{name}"
    branch = f"skills-hub/push-{name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

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
            "title": f"Push {name}",
            "head": branch,
            "base": args.base,
            "body": f"Adds `{name}` to Skills-hub.\n\nSource: `{source}`\nLicense: {args.license}\n",
        },
        expected=(201,),
    )
    print(pr.get("html_url", ""))


def cmd_push(args) -> None:
    source = args.source.resolve()
    if not source.is_dir():
        fail(f"source skill directory not found: {source}")
    name = args.name or source.name
    if not (source / "SKILL.md").is_file():
        fail(f"source has no SKILL.md: {source}")
    if getattr(args, "github_pr", False):
        cmd_push_github_pr(args, source, name)
        return

    repo_root = find_repo_root()
    dest = repo_root / "public" / "skills" / name
    if dest.exists():
        fail(f"target skill already exists: {dest}")
    dest.mkdir(parents=True)
    copy_skill_source(source, dest)
    write_provenance(dest, source, args.license)
    print(dest)


def cmd_record_install(args) -> None:
    context = read_context()
    roots = [Path(p) for p in args.install_root] if args.install_root else context_install_roots(context)
    if not roots:
        roots = default_install_roots()
    roots = normalize_install_roots(roots)
    if not roots:
        fail(no_install_root_message(args, context))
    installed = discover_installed(roots)
    if args.skill not in installed:
        fail(f"skill '{args.skill}' not found in any install root; cannot record install")
    item = installed[args.skill][0]
    install_root = Path(item.root)
    for parent in [install_root, *install_root.parents]:
        if parent.name == "skills" and parent.parent in roots:
            record_install(parent.parent, args.skill, args.content_hash, args.source_ref)
            print(json.dumps({"recorded": args.skill, "lockfile": str(parent.parent / LOCKFILE_NAME)}))
            return
    record_install(roots[0], args.skill, args.content_hash, args.source_ref)
    print(json.dumps({"recorded": args.skill, "lockfile": str(roots[0] / LOCKFILE_NAME)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("--install-root", action="append", default=[])
    inventory.add_argument("--names", help="comma-separated skill names to include")
    inventory.add_argument("--index", type=Path)
    inventory.add_argument("--manifest", type=Path)
    inventory.add_argument("--repo", default=DEFAULT_GITHUB_REPO)
    inventory.add_argument("--ref", default=DEFAULT_GITHUB_REF)
    inventory.add_argument("--json", action="store_true")
    inventory.set_defaults(func=cmd_inventory)

    fetch_package = sub.add_parser("fetch-package")
    fetch_package.add_argument("skill")
    fetch_package.add_argument("--repo", default=DEFAULT_GITHUB_REPO)
    fetch_package.add_argument("--ref", default=DEFAULT_GITHUB_REF)
    fetch_package.add_argument("--output-dir", type=Path, default=Path("outputs") / "skills-hub-packages")
    fetch_package.add_argument("--json", action="store_true")
    fetch_package.set_defaults(func=cmd_fetch_package)

    rec = sub.add_parser("record-install")
    rec.add_argument("skill")
    rec.add_argument("--content-hash", required=True, dest="content_hash")
    rec.add_argument("--source-ref", required=True, dest="source_ref")
    rec.add_argument("--install-root", action="append", default=[])
    rec.set_defaults(func=cmd_record_install)

    push = sub.add_parser("push")
    push.add_argument("--source", type=Path, required=True)
    push.add_argument("--name")
    push.add_argument("--license", default="unknown")
    push.add_argument("--github-pr", action="store_true")
    push.add_argument("--repo", default=DEFAULT_GITHUB_REPO)
    push.add_argument("--base", default="main")
    push.set_defaults(func=cmd_push)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
