---
name: process-diagrammer
description: Create comprehensive JSON process diagrams from git commit history with human-readable Mermaid visualizations. Use when (1) documenting workflows that evolved through commits, (2) extracting canonical process records from development history, (3) distinguishing process execution from tooling development. Produces JSON diagrams with co-located Mermaid visualizations (same folder, .md extension).
disable-model-invocation: true
---

# Process Diagrammer

Generate native JSON process diagrams and Mermaid visualizations from git commit history.

## Default Behavior

When invoked without arguments, the skill uses intelligent defaults:

### Branch Selection
- Uses the **current git branch** (output of `git branch --show-current`)
- No branch argument needed for typical usage

### Existing Diagram Detection
1. Check `.claude/diagram-log.json` for an entry matching current branch
2. If entry exists: **incremental mode** - analyze only new commits
3. If no entry: **full mode** - analyze complete branch history

### Incremental Updates
When a diagram already exists for the current branch:
- Parse `commitRange` from the diagram entry (format: `first..last`)
- Analyze only commits **after** the `last` commit hash
- Append new steps to the existing diagram
- Update `commitRange` to reflect the extended range
- Add new commit hashes to `includedCommits`

Example: If `commitRange` is `093773c..7e580b1`, analyze commits from `7e580b1..HEAD`.

### Tracking File Updates
Always update both tracking files after diagram generation:
- **.claude/diagram-log.json**: Add/update entry for the branch
- **.claude/process-creation.json**: Add entries for any excluded commits

### Quick Reference

| Condition | Behavior |
|-----------|----------|
| No existing diagram | Full history analysis → JSON + Mermaid |
| Existing diagram, no new commits | Report "Diagram is current" |
| Existing diagram, new commits | Incremental append → regenerate Mermaid |
| JSON updated | Always regenerate Mermaid visualization |

## Workflow

### 1. Analyze Commit History

```bash
git log --oneline --all --date-order
git log --stat --date=short
```

Identify:
- **Date range**: When the process started and ended
- **Commit clusters**: Related commits that form logical steps
- **File patterns**: Which folders/files changed together

### 2. Classify Commits

**Process Commits** (include in diagram):
- Create/modify matter-specific content
- Execute extraction, analysis, or assembly steps
- Produce outputs in matter folders (e.g., `FACTs/`, `LAW/`, `ISSUEs/`)

**Tooling Commits** (exclude from process diagram):
- Create/modify scripts in `scripts/`
- Create/modify skills in `.claude/skills/`
- Refactor tools for general reuse
- Add tests or documentation for tools

**Classification heuristics:**
```
PROCESS if commit touches:
  - [Matter ID]/*
  - FACTs/*, LAW/*, ISSUEs/*, APPLICATIONs/*
  - Matter-specific data files

TOOLING if commit touches:
  - scripts/*.py
  - .claude/skills/*
  - *.md documentation for tools
  - Test files for scripts
```

### 3. Group into Phases

Cluster process commits into logical phases:
- Look for natural breaks in timestamps
- Group by output folder (e.g., all FACTs/ commits = extraction phase)
- Identify dependencies between commit groups

### 4. Extract Steps from Commits

For each process commit, extract:
```json
{
  "id": "step_N.M",
  "name": "Derived from commit message",
  "description": "What the commit accomplished",
  "commitHash": "abc1234",
  "commitDate": "2026-01-15",
  "inputs": ["Files that existed before"],
  "outputs": ["Files created/modified"],
  "tools": ["Scripts or skills invoked"],
  "dependencies": ["Prior step IDs"]
}
```

### 5. Build Dependency Graph

Analyze file dependencies across commits:
- If commit B modifies files created by commit A, B depends on A
- Use `git log --follow` to trace file lineage
- Group concurrent commits with no mutual dependencies

### 6. Generate Diagram JSON

Output to: `diagrams/json/[branch-name].json`

**Naming**: File is named after the branch (forward slashes replaced with hyphens).

Include metadata linking to source commits:
```json
{
  "metadata": {
    "sourceType": "git-commit-history",
    "branch": "master",
    "commitRange": "abc1234..def5678",
    "extractedDate": "2026-02-01"
  }
}
```

### 7. Generate Mermaid Visualization

**Always generate Mermaid after creating/updating JSON.**

**Output location**: Co-located with JSON file (same folder, `.md` extension instead of `.json`).

Convert the JSON diagram to a human-readable Mermaid flowchart:
- Each phase becomes a subgraph
- Each step becomes a node with ID and name
- Dependencies become arrows between nodes
- Parallel groups become nested track subgraphs

**Critical: Use invisible anchor chains for proper vertical layout.**

When phases contain nested subgraphs (parallel tracks), Mermaid spreads them horizontally. Fix this by adding invisible anchor nodes and `~~~` links to create a vertical spine.

See [references/mermaid-generation.md](references/mermaid-generation.md) for:
- Complete anchor chain technique
- JSON-to-Mermaid mapping rules
- Phase color palette
- Generation algorithm

### 8. Update Tracking Files

After generating a diagram, update the tracking files:

**.claude/diagram-log.json** - Add entry for the new diagram:
```json
{
  "diagramPath": "diagrams/json/[branch-name].json",
  "branch": "[branch-name]",
  "createdDate": "[YYYY-MM-DD]",
  "commitRange": "[first]..[last]",
  "includedCommits": ["abc1234", "def5678"]
}
```

**.claude/process-creation.json** - Add entries for excluded commits:
```json
{
  "commitHash": "abc1234",
  "commitDate": "YYYY-MM-DD",
  "commitMessage": "Original commit message",
  "category": "tooling|infrastructure|documentation|testing",
  "reason": "Why this commit improves general process rather than executing specific instance",
  "filesChanged": ["path/to/file.py"]
}
```

**Complete Coverage Principle**: Every commit in the analyzed range must appear in exactly one place:
- In a diagram's `includedCommits` (process execution)
- In `.claude/process-creation.json` (process improvement)

## References

- **Schema**: See [references/schema.json](references/schema.json) for JSON structure
- **Examples**: See [references/examples.md](references/examples.md) for patterns
- **Mermaid**: See [references/mermaid-generation.md](references/mermaid-generation.md) for visualization technique
