# Scenario: Co-Authored-By Stripping

## Candidate Under Test
Co-Authored-By enforcement wrapper — the script that strips `Co-Authored-By: Claude.*noreply@anthropic\.com` from commit messages.

## Test Cases

### TC1: Previous commit contains Co-Authored-By
**Input:** Most recent commit has message:
```
feat(auth): add login endpoint

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
**Expected:** Script amends previous commit to:
```
feat(auth): add login endpoint
```
(trailing blank lines also removed)

### TC2: Previous commit is clean
**Input:** Most recent commit has message:
```
fix(api): handle null response
```
**Expected:** Script does nothing to previous commit (no amend).

### TC3: New commit message contains Co-Authored-By
**Input:** Commit message passed to script:
```
refactor(db): normalize schema

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
**Expected:** Script strips the line before committing. Resulting commit message:
```
refactor(db): normalize schema
```

### TC4: New commit message is clean
**Input:** Commit message passed to script:
```
docs: update README
```
**Expected:** Script commits with message as-is.

### TC5: Post-commit verification catches Co-Authored-By
**Input:** After commit, `git log -1 --format="%B"` returns:
```
chore: bump deps

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
**Expected:** Script amends to strip the line. Final message:
```
chore: bump deps
```

### TC6: Multiple Co-Authored-By lines
**Input:** Commit message:
```
feat: multi-model support

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
**Expected:** Both lines stripped. Result:
```
feat: multi-model support
```

### TC7: Non-Anthropic Co-Authored-By preserved
**Input:** Commit message:
```
feat: pair programming session

Co-Authored-By: Alice <alice@example.com>
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
**Expected:** Only the Anthropic line stripped:
```
feat: pair programming session

Co-Authored-By: Alice <alice@example.com>
```

### TC8: Pattern variants
**Input:** Messages containing:
- `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- `Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`
- `Co-authored-by: Claude Code <noreply@anthropic.com>` (lowercase)
**Expected:** All variants matched and stripped.
