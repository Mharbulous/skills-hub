# Test Scenario: Commit Ingestion (Phase 1)

## Purpose
Verify that Phase 1 correctly parses git log output into structured JSON with hash, message, files, areas_touched, and trivial classification.

## Input State

Database contains a repo cursor:
```sql
SELECT last_commit_hash FROM repo_cursors WHERE repo = 'testrepo';
-- Returns: 'aaa1111111111111111111111111111111111111'
```

Git log output (simulated, 5 commits after cursor):

```
COMMIT:bbb2222222222222222222222222222222222222|feat: add user authentication

src/auth/login.py
src/auth/middleware.py
tests/test_auth.py
COMMIT:ccc3333333333333333333333333333333333333|fix typo in readme

README.md
COMMIT:ddd4444444444444444444444444444444444444|refactor: reorganize utils and helpers

src/utils/helpers.py
src/utils/formatters.py
src/core/config.py
COMMIT:eee5555555555555555555555555555555555555|style: fix formatting

src/auth/login.py
COMMIT:fff6666666666666666666666666666666666666|feat: add file upload with hashing

src/upload/handler.py
src/upload/hasher.py
src/workers/hash_worker.py
tests/test_upload.py
```

## Expected Output (JSON)

```json
[
  {
    "hash": "bbb2222222222222222222222222222222222222",
    "msg": "feat: add user authentication",
    "files": [
      "src/auth/login.py",
      "src/auth/middleware.py",
      "tests/test_auth.py"
    ],
    "areas_touched": [
      "src/auth/",
      "tests/"
    ],
    "trivial": false
  },
  {
    "hash": "ccc3333333333333333333333333333333333333",
    "msg": "fix typo in readme",
    "files": [
      "README.md"
    ],
    "areas_touched": [
      ""
    ],
    "trivial": true
  },
  {
    "hash": "ddd4444444444444444444444444444444444444",
    "msg": "refactor: reorganize utils and helpers",
    "files": [
      "src/utils/helpers.py",
      "src/utils/formatters.py",
      "src/core/config.py"
    ],
    "areas_touched": [
      "src/utils/",
      "src/core/"
    ],
    "trivial": false
  },
  {
    "hash": "eee5555555555555555555555555555555555555",
    "msg": "style: fix formatting",
    "files": [
      "src/auth/login.py"
    ],
    "areas_touched": [
      "src/auth/"
    ],
    "trivial": true
  },
  {
    "hash": "fff6666666666666666666666666666666666666",
    "msg": "feat: add file upload with hashing",
    "files": [
      "src/upload/handler.py",
      "src/upload/hasher.py",
      "src/workers/hash_worker.py",
      "tests/test_upload.py"
    ],
    "areas_touched": [
      "src/upload/",
      "src/workers/",
      "tests/"
    ],
    "trivial": false
  }
]
```

## Verification Checks

- [ ] Each commit parsed into separate object with hash, msg, files, areas_touched, trivial
- [ ] Hash is full 40-char SHA
- [ ] Message extracted correctly (everything after `|` in COMMIT line)
- [ ] Files listed in order they appear in git log output
- [ ] areas_touched derived from file paths (parent directory of each file, deduplicated)
- [ ] Root-level files have area "" (empty string) or root-level indicator
- [ ] Trivial commits detected: typos (message contains "typo"), formatting-only ("style:", "format")
- [ ] Non-trivial commits have `trivial: false`
- [ ] Empty lines between commits handled correctly
- [ ] Commit count matches input (5 commits in, 5 objects out)

## Edge Cases

### Edge Case 1: Root-level file only
```
COMMIT:aaa...|docs: update changelog
CHANGELOG.md
```
Expected: `areas_touched` includes root indicator, `trivial: false` (documentation change has substance)

### Edge Case 2: Deep nesting
```
COMMIT:bbb...|feat: add nested component
src/components/auth/forms/login/LoginForm.vue
```
Expected: `areas_touched` includes `src/components/auth/forms/login/` (immediate parent directory)

### Edge Case 3: Single file, trivial
```
COMMIT:ccc...|fix typo
src/config.py
```
Expected: `trivial: true`, `areas_touched: ["src/"]`

### Edge Case 4: Mixed conventional commit prefixes
- `fix:` — not trivial (bug fix)
- `feat:` — not trivial (new feature)
- `style:` — trivial (formatting only)
- `docs:` — not trivial (documentation has substance)
- `chore:` — not trivial (maintenance)
- `refactor:` — not trivial (structural change)
- Message contains "typo" — trivial
- Message contains "formatting" — trivial
