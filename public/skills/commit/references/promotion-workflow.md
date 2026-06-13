# Promotion Workflow: Main → Production

Load this reference when asked to promote, deploy, or merge to production.

## Squash Merge Process

1. Verify on main: `git branch --show-current`
2. Verify clean: `git status --porcelain` (must be empty)
3. Sync: `git fetch origin`
4. Get commits to promote: `git log origin/production..HEAD --oneline`
5. Test merge: `git checkout production && git merge --no-commit --no-ff main && git merge --abort`
6. Execute: `git merge --squash main`
7. Create squash commit message (see template below)
8. Commit: `git commit -F /tmp/commit_msg.txt`
9. Push: `git push origin production`
10. Return to main: `git checkout main`

## Squash Message Template

```
Deploy: [primary feature or fix summary]

Squash merge of N commits from main:
- [commit 1 summary]
- [commit 2 summary]
- [commit 3 summary]

Deployed: [ISO timestamp]
```

## Check Branch Status

1. Current branch: `git branch --show-current`
2. Status: `git status --porcelain`
3. Commits ahead/behind: `git fetch && git rev-list --left-right --count origin/main...HEAD`
4. Recent commits: `git log --oneline -5`

## Verify Production Alignment

1. `git fetch origin`
2. `git merge-base --is-ancestor origin/main origin/production`
3. If true → production includes all main commits
4. If false → promotion needed
