# Case Data -- Local Utility Scripts

Files in `references/scripts/` are local/testing utilities only. In Claude Cowork, do not execute, import, copy, or stage these `.py` files from the mounted skill tree; FUSE can serve stale source bytes and produce truncated scripts. Cowork operations must use the inline snippets in the operation files.

## Local Utilities

| Script | Purpose | Local CLI |
|--------|---------|-----------|
| `resolve_pointer.py` | Resolve or create `coclerk.json`; migrate `9. AI` databases to native `0. CASE DATA` on use | `python resolve_pointer.py <matter_root>` |
| `resolve_paths.py` | Module: load pointers and resolve `case_data_dir` / `evidence.sql` paths | Imported by local utilities |
| `fuse_safe_io.py` | Module: marker-validated text reads for local utilities | Imported by local utilities |
| `get_matter_profile.py` | Generate matter profile JSON for downstream local checks | `python get_matter_profile.py --matter-root <path>` |
| `get_facts_for_drafting.py` | Fetch facts with v6.2 computed citations, evidence counts, position citations, and posture for form-drafting | `python get_facts_for_drafting.py --matter-root <path>` |
| `dump.py` | Dump `main.sqlite`, `law.sqlite`, `privileged.sqlite` into one `evidence.sql` with v6 section markers | `python dump.py --matter-root <path>` |
| `rebuild.py` | Rebuild `main.sqlite`, `law.sqlite`, `privileged.sqlite` from `evidence.sql`; atomic -- case-data folder untouched on failure | `python rebuild.py --matter-root <path>` |
| `migrate_v2_to_v3.py` | Move matter identity from v2 `coclerk.json` into `main.matter_metadata`, slim the pointer, and refresh `evidence.sql` | `python migrate_v2_to_v3.py --matter-root <path>` |
| `verify_sources.py` | Check `sources.file_path` plus v6.2 computed citation locators; exit 1 if any broken | `python verify_sources.py --matter-root <path>` |
| `get_legal_authorities_for_drafting.py` | Fetch legal criteria and authority support for form-drafting | `python get_legal_authorities_for_drafting.py --matter-root <path>` |

## Cowork Rule

Cowork should read operation markdown and run the inline code shown there. Do not use these local utilities as Cowork entrypoints.

Critical skill references (`schema.sql`, `triggers.sql`, `queries.sql`) should be read by Claude's host-side Read tool before their contents are used in an inline script. Read `evidence.sql` this way only for Maintain/Rebuild or explicit dump inspection; never read it to inspect live matter state during ingest/profile/query. Copying text files to `/tmp` is not a truncation fix because the copy can inherit stale FUSE file-size metadata.

SQLite binaries are different: they must live in native `0. CASE DATA` storage, and every read/write operation must copy the closed `.sqlite` files to a fresh temporary directory before opening them with SQLite.

## Historical Migration Scripts

Older migration scripts (`migrate_v3_to_v4.py`, `migrate_v5_to_v6.py`) are not deployed. They were single-use and exist in git history only. Schema version is tracked in `references/schema.sql` header comments.
