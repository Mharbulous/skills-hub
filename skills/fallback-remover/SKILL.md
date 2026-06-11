---
name: fallback-remover
description: Use when scanning a codebase for silent fallback anti-patterns (try/catch that swallows errors, log + return fallback, empty catch blocks) and interactively fixing them one at a time with user approval — supports JS/TS/Vue and C#/WPF
---

# Fallback Remover

Scan any codebase for try/catch blocks that swallow errors instead of surfacing them, then interactively fix them **one at a time** with user approval.

## Step 1: Detect Language

Auto-detect from project files:

| Signal | Language | Reference file |
|--------|----------|----------------|
| `.csproj` present | C# / WPF | `reference/csharp-wpf.md` |
| `package.json` + `.vue` files | JS/TS/Vue | `reference/javascript-vue.md` |
| `package.json` alone | JS/TS | `reference/javascript-vue.md` |

Read the matching reference file. It defines: severity tiers, false positive rules, fix patterns, file types, and test runner detection for that language.

If multiple languages detected, ask the user which to scan.

## Step 2: Scan for Patterns

Using severity tiers from the reference file, scan all source files (excluding directories and patterns listed in the reference). Classify each finding under its **highest** matching severity tier only (no duplicates).

## Step 3: Filter False Positives

Apply the false positive rules from the reference file. **When in doubt, INCLUDE the finding.**

## Step 4: Build Issue Queue

Sort findings by severity (CRITICAL first, then HIGH, then MEDIUM). Track each with: file path, line number, severity, problematic code snippet, proposed fix using patterns from the reference file.

**If no issues found**, report counts as 0 and stop.

## Step 5: Interactive Fix Loop

**CRITICAL: Present issues ONE AT A TIME. Do NOT dump all findings in a table or report.**

For each issue:

### 5a. Present

```
### Issue [N] of [TOTAL] — [SEVERITY]
**File:** `path/to/file:42`

**Current code:**
[catch block with ~5 lines of surrounding context]

**Problem:** [One sentence explaining why this is a silent fallback]

**Proposed fix:** [Show the replacement code]

**Actions:** approve | skip | acceptable
```

### 5b. STOP and Wait

**STOP generating output. Wait for the user to respond.**

- **approve** — Spawn a Sonnet subagent in the background to implement the fix (Step 6), then present the next issue
- **skip** — Move to next issue
- **acceptable** — Spawn a subagent to add a documenting comment (Step 6), then present the next issue
- **Any other response** — Answer the question, then re-present the same issue

### 5c. Same-File Serialization

If two approved issues are in the same file, **wait for the first subagent to complete** before dispatching the second.

### 5d. Loop

Repeat 5a-5b until all issues addressed.

## Step 6: Subagent Dispatch

For **approved** fixes:

```
Agent(
  description: "Fix silent fallback in [filename]",
  model: "sonnet",
  run_in_background: true,
  prompt: """
Fix a silent fallback anti-pattern.

**File:** [absolute path]
**Line:** [line number]

**Current code:**
[exact catch block and context]

**Required change:**
[specific fix from reference file patterns]

**Rules:**
- Read the file first
- Minimal change only — do not refactor surrounding code
- Preserve existing logging calls (logging is fine, silent FALLBACK is not)
- If an error state variable exists in scope, set it before rethrowing
- If no error state exists, just rethrow — do not add new error state infrastructure
- Detect test runner and run tests after fixing
- If tests fail due to your change, investigate and fix
"""
)
```

For **acceptable** (documenting comment only):

```
Agent(
  description: "Document acceptable catch in [filename]",
  model: "sonnet",
  run_in_background: true,
  prompt: """
Add a documenting comment to a catch block.

**File:** [absolute path]
**Line:** [line number]

**Current code:**
[catch block]

Add a comment on the same line as or directly above the catch explaining WHY this error is safe to ignore:
// Best-effort: [reason failure is non-critical]

Do NOT change catch logic — only add the comment.
"""
)
```

## Step 7: Summary

```
## Silent Fallback Scan Complete

**Fixed:** [N] issues
**Skipped:** [N] issues
**Marked acceptable:** [N] issues
**Excluded (false positives):** [N] patterns

### Still running:
[List any background subagents]
```

## Common Mistakes

| Mistake | Correct approach |
|---------|-----------------|
| Dump all findings in a table | Present ONE AT A TIME with approve/skip/acceptable |
| Fix everything without asking | Wait for user response on each issue |
| Dispatch concurrent edits to same file | Serialize subagents per file |
| Use severity tiers not from reference file | Use the language-specific reference file |
| Skip false positive filtering | Apply all exclusion rules from reference file |
| Tell user to fix it themselves | Spawn Sonnet subagent to implement the fix |
