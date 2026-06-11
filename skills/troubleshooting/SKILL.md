---
name: troubleshooting
description: Use when a GitHub Actions workflow fails or behaves unexpectedly, TanStack Virtual with Vue 3 renders incorrectly or shows no rows, CI/CD pipeline produces silent failures or infinite loops, or user asks to troubleshoot a known anti-pattern.
---

# Troubleshooting

Diagnose issues by matching symptoms against documented anti-patterns extracted from this project's commit history.

## Workflow

1. Identify the domain from the symptom
2. Read ONLY the matching reference file (never both)
3. Match symptoms to documented anti-patterns
4. Apply the documented fix
5. Verify the fix resolves the issue

## Reference Files

Read ONE file based on the domain. Do NOT read both.

### GitHub Workflows — `references/Github-Workflows.md`
Read ONLY when the issue involves: GitHub Actions, CI/CD pipelines, `.github/workflows/` files, Cloud Run deployment, `gcloud` commands in workflows, workflow orchestration, or `gh workflow` CLI commands.

### TanStack Virtual + Vue 3 — `references/TanStack.md`
Read ONLY when the issue involves: `@tanstack/vue-virtual`, `useVirtualizer`, `useVirtualTable`, virtual scrolling, `virtualTotalSize: 0`, rows not rendering, `onScopeDispose` warning, or scroll container detection.
