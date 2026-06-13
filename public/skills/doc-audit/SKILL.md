---
name: doc-audit
description: "Validate that documentation accurately reflects the current codebase implementation. Scans .md files, CLAUDE.md files, and READMEs, cross-references claims against code, and reports discrepancies by severity."
---

# Doc Audit

Perform comprehensive documentation reconciliation to identify discrepancies between documentation and actual code implementation.

## Workflow

### 1. Scan Documentation Files

- Find all .md files in docs/ directories
- Find all CLAUDE.md files (project and global)
- Identify README files throughout the codebase

### 2. Extract Documentation Claims

- API references and function signatures
- Code examples and usage patterns
- Architectural descriptions and component relationships
- Configuration requirements and environment variables
- Command-line instructions and scripts
- File paths and directory structures

### 3. Cross-Reference Against Code

- Verify API signatures match actual implementations
- Confirm code examples execute correctly
- Validate architectural descriptions reflect current structure
- Check file paths and imports are accurate
- Verify environment variables are actually used
- Confirm npm scripts and commands exist

### 4. Report Discrepancies

- List documentation files with issues
- Provide specific file:line references for problems
- Categorize by severity: CRITICAL / IMPORTANT / MINOR
- Suggest specific fixes for each issue

### 5. Generate Summary

- Overall documentation health score
- Count of issues by severity
- Prioritized action items
- Files requiring immediate attention

## Severity Definitions

- **CRITICAL**: Wrong information that could break implementations
- **IMPORTANT**: Incomplete or outdated information
- **MINOR**: Formatting issues or improvements

## Context

This skill works across multi-repository workspaces and should:

- Respect project-specific conventions in CLAUDE.md files
- Recognize common documentation anti-patterns:
  - Outdated API examples
  - References to removed files
  - Incorrect command syntax
  - Missing new features
  - Stale architecture diagrams
- Prioritize accuracy over completeness
- Follow the "single source of truth" principle

## Output Format

```
## Documentation Reconciliation Report

### CRITICAL Issues (N)
1. **file:line** - Description of discrepancy

### IMPORTANT Issues (N)
1. **file:line** - Description of discrepancy

### MINOR Issues (N)
1. **file:line** - Description of discrepancy

### Summary
- Documentation Health: X%
- Total Issues: N (critical, important, minor)
- Priority Actions:
  1. [action]

### Recommended Next Steps
1. Address all CRITICAL issues immediately
2. Review and update IMPORTANT issues before next release
3. Schedule MINOR issues for documentation maintenance sprint
```
