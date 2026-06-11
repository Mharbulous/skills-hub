# Complex Commit Scenarios

## Table of Contents
- Pre-commit hook failures
- Merge conflicts
- Splitting into multiple commits
- Amending commits
- Partial staging (mixed intent)
- Rebasing and squashing

---

## Pre-commit Hook Failures

When a pre-commit hook fails, the commit did NOT happen.

1. Read the hook output to understand the failure
2. Fix the issue (lint error, test failure, etc.)
3. Re-stage the fixed files
4. Create a NEW commit (do NOT use `--amend` -- that would modify the previous commit)

If the hook failure is in files unrelated to the user's changes, inform the user and ask how to proceed. Never use `--no-verify` unless explicitly instructed.

## Merge Conflicts

When `git status` shows merge conflicts:

1. List all conflicted files for the user
2. Ask which resolution strategy they prefer:
   - **Review each**: open each file sequentially, present both sides, let user choose
   - **Accept theirs/ours**: bulk resolution for simple cases
   - **Manual**: user resolves, then you commit
3. After resolution, stage resolved files and commit with message:
   ```
   merge: resolve conflicts in [files] during merge of [branch]
   ```

Never silently pick a side in a merge conflict. Always inform the user of conflicting sections.

## Splitting Into Multiple Commits

When the user asks to split changes, or changes span 4+ unrelated scopes:

1. Group files by scope/feature
2. Present the proposed grouping to the user for approval
3. Stage and commit each group sequentially
4. Each commit gets its own conventional commit message

Example grouping:
```
Commit 1: fix(auth): correct token refresh logic
  - src/auth/tokenService.js
  - tests/auth/tokenService.test.js

Commit 2: feat(dashboard): add weekly summary widget
  - src/dashboard/WeeklySummary.vue
  - src/dashboard/composables/useWeeklySummary.js
```

## Amending Commits

Only when user explicitly says "amend":

1. Confirm: "This will modify the most recent commit. Proceed?"
2. Stage new changes
3. `git commit --amend` (opens with existing message)
4. If the user wants to change the message, use `--amend -m "new message"`

Warning: never amend a commit that has been pushed to a shared branch. Check with `git log --oneline origin/main..HEAD` first.

## Partial Staging (Mixed Intent)

When `git status` shows both staged and unstaged changes that appear to serve different purposes:

1. Inform the user: "You have pre-staged changes that differ from your unstaged changes."
2. Present options:
   - Commit only the staged changes
   - Add unstaged changes and commit everything
   - Review the difference and decide
3. Proceed based on user's choice

## Rebasing and Squashing

When the user asks to rebase or squash:

- `git rebase -i` is NOT supported (interactive mode)
- For squashing the last N commits, use: `git reset --soft HEAD~N && git commit`
- For rebasing onto main: `git rebase main` (non-interactive)
- Always confirm before rebase since it rewrites history
- Never rebase commits that are already pushed to shared branches without explicit user approval

If a rebase encounters conflicts, follow the merge conflicts procedure above, using `git rebase --continue` after each resolution.
