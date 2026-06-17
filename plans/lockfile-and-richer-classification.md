# Install lockfile and richer classification

## Context

After the content-hash refactor (2026-06-17), inventory classifies installed
skills as `current` (hash matches catalog) or `stale` (hash differs). This is
a two-way comparison: installed hash vs. catalog hash. Without recording the
install-time hash, we can't distinguish three situations that all report `stale`:

| Scenario | Installed | Install-time | Catalog | Correct status |
|---|---|---|---|---|
| Hub updated, user didn't touch it | == install-time | (unknown) | differs | `stale` |
| User edited locally, hub unchanged | differs | (unknown) | == install-time | `modified` |
| Both changed | differs | (unknown) | differs from both | `diverged` |

This matters most for `/skills-hub update`: if a user modified an installed
skill locally and runs update, their edits are silently overwritten. A lockfile
prevents that data loss.

Secondary gap: when the catalog is unreachable (degraded mode), inventory can
only report `installed` — it can't say whether the skill is current or stale.
Caching the last-synced catalog locally would let offline inventory still
compare hashes.

## Current code layout

- `content_hash(skill_dir)` — hashes all publishable files (line 180)
- `classify_installed(name, installed, catalog_hash)` — two-way compare (line 321)
- `build_inventory(catalog, installed)` — assembles rows (line 344)
- `classify_local_installed(name, installed)` — degraded path, returns `installed` (line 402)
- `write_direct_skill_package(...)` — builds `.skill` zip (line 201)
- `cmd_fetch_package(args)` — CLI entry for package build (line 486)
- `cmd_inventory(args)` — CLI entry for inventory (line 447)
- `FetchResult` dataclass — returned by `write_direct_skill_package` (line 60)

All in `public/skills/skills-hub/scripts/manage_cowork_skills.py`.

## Plan

### 1. Define the lockfile format and I/O

**File:** `manage_cowork_skills.py`

Add a `LOCKFILE_NAME = "skills-hub-lock.json"` constant.

Add functions:

```python
def read_lockfile(install_root: Path) -> dict:
    """Read {skill_name: {content_hash, installed_at, source_ref}} from lockfile.
    Returns {} if the file doesn't exist or is malformed — no hard failure."""

def write_lockfile(install_root: Path, lock: dict) -> None:
    """Write lockfile atomically (write to .tmp, os.replace).
    Use os.replace() — os.rename() fails on Windows if target exists.
    Silently skip if the directory is read-only (catch OSError)."""

def record_install(install_root: Path, skill_name: str, content_hash: str, source_ref: str) -> None:
    """Read existing lockfile, upsert one entry with installed_at timestamp, write back."""

def merge_lockfiles(install_roots: list[Path]) -> dict:
    """Read lockfiles from all roots, merge by skill name. If the same skill
    appears in multiple roots, keep the entry with the latest installed_at."""
```

The lockfile lives at `<install_root>/skills-hub-lock.json`. Format:

```json
{
  "schema_version": 1,
  "skills": {
    "alpha": {
      "content_hash": "abc123...",
      "installed_at": "2026-06-17T...",
      "source_ref": "Mharbulous/skills-hub@main"
    }
  }
}
```

`source_ref` records `<repo>@<ref>` so future inventory can report where the
install came from.

`read_lockfile` returns `{}` if the file doesn't exist or is malformed — no
hard failure on a corrupt lockfile.

### 2. Write lockfile entries at install time

**File:** `manage_cowork_skills.py`

Add `content_hash` and `source_ref` fields to `FetchResult`:

```python
@dataclass
class FetchResult:
    skill: str
    package_path: str
    package_url: str
    sha256: str
    size: int
    content_hash: str    # NEW — hash of the skill content inside the package
    source_ref: str      # NEW — "repo@ref" string
```

In `write_direct_skill_package`, add a `content_hash(skill_source)` call
(this does NOT already exist — the function currently only computes
`sha256_file(package)` which hashes the zip, not the content). Populate
both new fields in the returned `FetchResult`:

```python
c_hash = content_hash(skill_source)
return FetchResult(
    ...,
    content_hash=c_hash,
    source_ref=f"{repo}@{ref}",
)
```

Then add a new CLI subcommand `record-install`:

```bash
python scripts/manage_cowork_skills.py record-install <skill> --content-hash <hash> --source-ref <ref> [--install-root <path>]
```

`--install-root` is optional. If omitted, auto-detect using the same
`inventory_roots()` / `context_install_roots()` / `default_install_roots()`
chain that `cmd_inventory` uses. Before writing the lockfile entry, verify
the skill directory actually exists at the resolved root (glob for
`**/skills/<skill>/SKILL.md`). If not found, error — a lockfile entry for
a missing install is useless.

The SKILL.md instructions will tell Claude to run `record-install` after the
user clicks Save skill and inventory confirms `current`. The `content_hash`
and `source_ref` values come from the `fetch-package` JSON output.

### 3. Upgrade classification to three-way comparison

**File:** `manage_cowork_skills.py`

Change `classify_installed` signature to accept the lockfile hash:

```python
def classify_installed(
    name: str,
    installed: list[InstalledSkill],
    catalog_hash: str | None = None,
    lock_hash: str | None = None,
) -> InventoryRow:
```

New classification logic (after the existing multi-copy `conflict` check):

```
installed_hash = content_hash(installed_dir)

if catalog_hash and installed_hash == catalog_hash:
    → current

if lock_hash:
    user_modified = (installed_hash != lock_hash)

    if catalog_hash is not None:
        hub_updated = (catalog_hash != lock_hash)
    else:
        hub_updated = False  # can't determine without catalog

    if user_modified and hub_updated:
        → diverged ("local edits and hub updates — review locally or force-update")
    if user_modified and not hub_updated:
        → modified ("locally edited; hub content unchanged")
    if not user_modified and hub_updated:
        → stale ("hub updated; safe to update")
    if not user_modified and not hub_updated:
        → current ("unchanged since install")  # handles catalog_hash=None edge case

# no lock_hash — fall back to two-way (backward compat with pre-lockfile installs)
if catalog_hash:
    → stale ("content differs from GitHub source; no install record")
→ stale ("could not compare")
```

Update `build_inventory` to read the lockfile and pass lock hashes:

```python
def build_inventory(catalog, installed, install_roots) -> list[InventoryRow]:
    lock = merge_lockfiles(install_roots)
    ...
    lock_hash = lock.get(name, {}).get("content_hash")
    classify_installed(name, items, catalog_hash, lock_hash)
```

Update `cmd_inventory` to pass `roots` as the third argument to
`build_inventory`.

### 4. Cache the catalog for offline staleness

**File:** `manage_cowork_skills.py`

After a successful GitHub catalog fetch in `cmd_inventory`, write the catalog
to a cache file alongside the lockfile:

```python
CATALOG_CACHE_NAME = "skills-hub-catalog-cache.json"

def cache_catalog(install_root: Path, catalog: dict) -> None:
    """Write catalog + cached_at timestamp to cache file.
    Silently skip on OSError (root may be read-only)."""

def read_cached_catalog(install_roots: list[Path]) -> tuple[dict, str] | None:
    """Read most recent catalog cache. Returns (catalog, cached_at_iso) or None."""
```

Cache format:

```json
{
  "cached_at": "2026-06-17T12:00:00+00:00",
  "catalog": { "skills": [...] }
}
```

In `cmd_inventory`, when the GitHub fetch succeeds, call
`cache_catalog(roots[0], catalog)` to persist it. Wrap in try/except OSError
so a read-only first root doesn't crash the command.

In the `CatalogUnavailable` handler, before falling back to
`build_local_inventory`, try `read_cached_catalog(roots)`. If found, use it
with `build_inventory` (the full classification path), but add a note in the
evidence field: `"(offline — using cached catalog from <cached_at>)"`. If no
cache exists, fall back to the current degraded path.

### 5. Update SKILL.md instructions

**File:** `public/skills/skills-hub/SKILL.md`

**Install flow** — after the user clicks Save skill and inventory confirms
`current`, add a `record-install` step:

```bash
python scripts/manage_cowork_skills.py record-install <skill> \
  --content-hash <hash from fetch-package result> \
  --source-ref <source_ref from fetch-package result>
```

(No `--install-root` needed — auto-detected.)

**Update flow** — same: after save + inventory confirmation, run
`record-install` to update the lockfile entry.

**Update all** — same: `record-install` after each successful save.

**New status documentation** — update the inventory command section's valid
status list from:

```
current, missing, stale, orphan, conflict
```

to:

```
current, missing, stale, modified, diverged, orphan, conflict
```

Add brief definitions:

- `modified` — locally edited; hub content unchanged
- `diverged` — both local edits and hub updates exist

**Modified/diverged handling** — add a new subsection:

> If inventory shows `modified`, the skill was edited locally after install.
> Running update would overwrite those edits. Ask the user whether to proceed
> (their edits will be lost) or skip.
>
> If inventory shows `diverged`, both local edits and hub updates exist. Warn
> the user that updating will overwrite their local edits, and ask for explicit
> confirmation before proceeding.

Note: `/skills-hub absorb` currently does not support updating an existing
skill in the hub repo. Until absorb is extended, do not suggest it as a
resolution for `modified` or `diverged` — that is a separate feature.

**Update targeting** — the current SKILL.md already targets
`status == "stale"` for `update all`. Add `modified` and `diverged` to the
exclusion list explicitly:

> For `modified` or `diverged` rows, skip unless the user explicitly asks to
> force-update. Warn that local edits will be lost.

### 6. Update tests

**File:** `tests/test_manage_cowork_skills.py`

New tests:

- `test_read_lockfile_missing_returns_empty` — no file → `{}`.
- `test_read_lockfile_corrupt_returns_empty` — garbage content → `{}`.
- `test_record_install_creates_lockfile` — run `record_install`, verify the
  lockfile is written with correct schema, entry, and `installed_at` field.
- `test_record_install_upserts_existing` — create a lockfile with one entry,
  record a second, verify both exist. Then update the first, verify it changed.
- `test_merge_lockfiles_across_roots` — two roots with different skills →
  merged dict contains both. Same skill in both → latest `installed_at` wins.
- `test_classify_current_ignores_lockfile` — installed matches catalog,
  lockfile present → `current` (lockfile doesn't interfere).
- `test_classify_stale_with_lockfile` — install with lockfile hash, don't
  modify, catalog differs → `stale`.
- `test_classify_modified_when_user_edited` — install with lockfile hash,
  modify installed content, catalog unchanged → `modified`.
- `test_classify_diverged_when_both_changed` — install with lockfile hash,
  modify installed content, catalog also differs → `diverged`.
- `test_classify_stale_without_lockfile` — no lockfile, content differs →
  `stale` with "no install record" evidence (backward compat).
- `test_classify_current_when_no_catalog_hash_but_lock_matches` — lock_hash
  matches installed, catalog_hash is None → `current`.
- `test_cached_catalog_enables_offline_staleness` — cache a catalog, mock
  `fetch_github_repo` to raise `URLError`, run inventory → uses cached
  catalog, reports correct statuses with offline evidence.
- `test_install_then_record_then_inventory_current` — end-to-end: fetch
  package (monkeypatched), extract, record-install, inventory → `current`.
- `test_fetch_package_includes_content_hash_and_source_ref` — run
  `cmd_fetch_package`, verify JSON output contains `content_hash` and
  `source_ref` fields.

Updated tests:

- `test_inventory_classifies_missing_stale_orphan_and_current` — add lockfile
  entries for the installed skills so the test exercises the lockfile path.
  Pass `install_roots` to `build_inventory`.
- `test_direct_install_then_inventory_shows_current` — after install, call
  `record_install`, verify lockfile exists.

### 7. Update E2E test docs

**Files:** `tests/e2e_cowork_prompt.md`, `tests/e2e_skills_hub_cowork.md`

- Update valid status lists to include `modified` and `diverged`.
- Add a note in install/update verification steps: after install/update +
  Save skill, `record-install` should have been called automatically. Verify
  that `skills-hub-lock.json` exists in the install root.
- Add Phase 6d (optional): manually edit an installed skill's SKILL.md,
  rerun inventory, expect `modified` status.

## Verification

```bash
# 1. Run the full test suite
python -m pytest tests -v

# 2. Build the index
python build/build_index.py

# 3. Verify lockfile round-trip in tests
python -m pytest tests/test_manage_cowork_skills.py -k "lockfile or record_install or merge_lock" -v

# 4. Verify three-way classification tests
python -m pytest tests/test_manage_cowork_skills.py -k "classify_modified or classify_diverged or classify_stale_with or classify_current" -v
```

## Dependency order

Steps 1 → 2 → 3 (each builds on prior). Step 4 is independent of 1-3 but
touches the same `cmd_inventory` function, so apply after step 3. Step 5
depends on the new statuses from step 3 and the `record-install` command from
step 2. Step 6 can be written alongside steps 1-4 but must reference the final
APIs. Step 7 is last since it documents the completed behavior.

## Out-of-scope (future work)

- **Absorb for existing skills.** `cmd_absorb` blocks on
  `target skill already exists`. Until absorb supports update/overwrite, SKILL.md
  should not suggest absorb as a resolution for `modified`/`diverged` skills.
- **Lockfile-aware degraded mode.** Even without a cached catalog, the lockfile
  could distinguish `installed` from `modified` (compare installed_hash to
  lock_hash). Marginal benefit since Step 4's cached catalog covers the main
  use case.
