---
name: commit
description: "Commit git changes with well-crafted conventional commit messages."
---

# Commit — Operation Layer

> **AGENT-ONLY GUARD**: If you are reading this as the main model (not a spawned agent), do NOT execute the workflow below. Return to `commands/commit.md` and spawn an agent first.

Loaded by the agent spawned from `/commit` (`commands/commit.md`).

## Commit Message Format

```
type(scope): imperative description under 50 chars
```

Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build

Rules:
- Imperative mood ("add" not "added"), no period, lowercase
- Scope is optional — use affected component
- **NO attribution lines** — never add Co-Authored-By or any Claude/Anthropic credit

## Output Contract

Final output must be exactly one of these JSON structures:

**Success:**
```json
{"status": "success", "hash": "<short hash>", "message": "<commit message first line>"}
```

**Escalation** (complex scenario requiring human decision — merge conflict, pre-commit hook failure in unrelated files):
```json
{"status": "escalation", "reason": "<brief description>", "details": "<actionable context for the caller>", "files": ["<affected files>"]}
```

**Error** (nothing was committed):
```json
{"status": "error", "reason": "<what went wrong>"}
```

## Workflow

1. **Locate this skill's directory** and treat it as `SKILL_DIR`.
2. **Run:** `bash "$SKILL_DIR/scripts/gather-context.sh"`
   - JSON includes `prev_commit_message`, `prev_commit_diff_stat`, `prev_commit_pushed`
3. **Review previous commit** — skip if `prev_commit_pushed` is true OR `prev_commit_message` is empty.
   Otherwise check for:
   - **Accuracy:** Does `prev_commit_message` match `prev_commit_diff_stat`? Flag: wrong type (e.g. "fix" but files were added), wrong scope (e.g. "lesson3" but 9 files changed), missing info, misleading description.
   - **Co-authorship:** Does `prev_commit_message` contain a Co-Authored-By line for Claude/Anthropic?
   - If either issue → draft corrected message and run `git commit --amend -m "<corrected message>"`. Do this silently — no user approval needed.
4. If `has_changes` is false → return `{"status":"error","reason":"Nothing to commit"}`
5. Draft commit message using `diff_stat`, `sample_diffs`, and `recent_commits` from the JSON
6. **Run:** `bash "$SKILL_DIR/scripts/sanitize-commit.sh" --message "<message>" --files "all"`
7. Return the script's JSON output directly

## Safety Rules

1. NEVER force push
2. NEVER `git reset --hard` without explicit user confirmation
3. NEVER skip hooks (--no-verify) unless explicitly requested
4. Branch is verified by `gather-context.sh` (in the `branch` field) — do not run `git branch` separately

## Token Efficiency

- `gather-context.sh` handles diff sampling automatically (full context for ≤5 files, minimal for >5)
- Do not run additional `git diff` or `git status` commands — all context is in the gather JSON
- Return JSON output — no verbose prose
