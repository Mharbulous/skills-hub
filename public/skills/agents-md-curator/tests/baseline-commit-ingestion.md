# Baseline Results: Commit Ingestion (Phase 1)

## Test Scenario Summary
- **Input:** 5 simulated commits with varying file counts and commit types
- **Agent:** Haiku (as specified by introspect.md Phase 1)
- **Date:** 2026-02-16

## Haiku Baseline Output (Verbatim)

```json
[
  {
    "hash": "bbb2222222222222222222222222222222222222",
    "msg": "feat: add user authentication",
    "files": ["src/auth/login.py", "src/auth/middleware.py", "tests/test_auth.py"],
    "areas_touched": ["auth", "tests"],
    "trivial": false
  },
  {
    "hash": "ccc3333333333333333333333333333333333333",
    "msg": "fix typo in readme",
    "files": ["README.md"],
    "areas_touched": ["docs"],
    "trivial": true
  },
  {
    "hash": "ddd4444444444444444444444444444444444444",
    "msg": "refactor: reorganize utils and helpers",
    "files": ["src/utils/helpers.py", "src/utils/formatters.py", "src/core/config.py"],
    "areas_touched": ["utils", "core"],
    "trivial": false
  },
  {
    "hash": "eee5555555555555555555555555555555555555",
    "msg": "style: fix formatting",
    "files": ["src/auth/login.py"],
    "areas_touched": ["auth"],
    "trivial": true
  },
  {
    "hash": "fff6666666666666666666666666666666666666",
    "msg": "feat: add file upload with hashing",
    "files": ["src/upload/handler.py", "src/upload/hasher.py", "src/workers/hash_worker.py", "tests/test_upload.py"],
    "areas_touched": ["upload", "workers", "tests"],
    "trivial": false
  }
]
```

## Discrepancy Analysis

### 1. areas_touched — Semantic Interpretation Instead of Path Extraction

| File Path | Haiku Output | Correct Output | Issue |
|-----------|-------------|----------------|-------|
| `src/auth/login.py` | `"auth"` | `"src/auth/"` | Dropped `src/` prefix, semantic label |
| `tests/test_auth.py` | `"tests"` | `"tests/"` | Missing trailing slash |
| `README.md` | `"docs"` | `""` (root) | Fabricated directory — README.md is at root |
| `src/utils/helpers.py` | `"utils"` | `"src/utils/"` | Dropped `src/` prefix |
| `src/core/config.py` | `"core"` | `"src/core/"` | Dropped `src/` prefix |
| `src/upload/handler.py` | `"upload"` | `"src/upload/"` | Dropped `src/` prefix |
| `src/workers/hash_worker.py` | `"workers"` | `"src/workers/"` | Dropped `src/` prefix |

**Root cause:** Haiku interprets "areas_touched" as semantic categories rather than mechanically extracting parent directory paths from file paths. This is the core variance — a script would use `os.path.dirname()` and get it right every time.

### 2. Output Formatting

Haiku wrapped output in markdown code fences despite being instructed to return raw JSON only. Minor issue for parsing (can strip fences) but demonstrates instruction-following variance.

### 3. Correct Behaviors Preserved

| Behavior | Status |
|----------|--------|
| Hash extraction (full 40-char SHA) | PASS |
| Message extraction (after `\|`) | PASS |
| File list (correct order) | PASS |
| Trivial detection: "fix typo" | PASS |
| Trivial detection: "style:" prefix | PASS |
| Non-trivial: "feat:", "refactor:" | PASS |
| Commit count (5 in, 5 out) | PASS |

## Conclusion

Haiku correctly handles: hash/message parsing, file listing, and trivial commit classification. The critical failure is in `areas_touched` derivation — Haiku applies semantic interpretation instead of mechanical path extraction. This is exactly the LLM variance that script extraction eliminates.

**The hardened script must:**
1. Extract parent directory from each file path (`os.path.dirname()`)
2. Deduplicate areas
3. Produce trailing-slash directory paths
4. Handle root-level files (empty parent = root indicator)
5. Return valid JSON without markdown wrapping
