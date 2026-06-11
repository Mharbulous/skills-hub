# Submodule Handling

Load this reference when `git submodule status` returns results.

## Detection

```bash
# Am I inside a submodule? (non-empty = yes)
git rev-parse --show-superproject-working-tree 2>/dev/null

# Are there modified submodules?
git submodule status
git submodule foreach --quiet 'git status --porcelain | grep -q . && echo "$name has uncommitted changes"'
```

## Commit/Push Order (MANDATORY)

Always commit/push submodule FIRST, then parent:

1. **Submodule first:**
   ```bash
   cd <submodule-path>
   git add -A
   git commit -m "message"
   git push origin $(git branch --show-current)
   cd ..
   ```

2. **Parent second (updates submodule reference):**
   ```bash
   git add <submodule-path>
   git commit -m "chore: update <submodule-name> submodule"
   git push origin $(git branch --show-current)
   ```

**Why this order:** The parent stores a pointer to a specific submodule commit. Pushing parent first creates a broken reference on the remote.

## Diverged Submodule Branches

```bash
cd <submodule-path>
git fetch origin
git status  # Look for "Your branch and 'origin/X' have diverged"
```

If diverged → ESCALATE (return escalation JSON). Diverged branches require merge strategy decision.

## Escalation Triggers

STOP and return escalation JSON when:
- Submodule branch has diverged from remote
- Submodule is on detached HEAD
- Submodule remote URL mismatch
- Parent and submodule have conflicting changes
- `git submodule update` fails
