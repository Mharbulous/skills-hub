---
name: patent-convergence-analyzer
description: Use when analyzing whether iterative document editing is converging toward stability or diverging - performs git commit history analysis with 5-category classification, growth metrics, deceleration series, and structured convergence verdict. Triggers on "convergence analysis", "is this document stabilizing", "how much churn", "editing velocity"
disable-model-invocation: true
---

# Patent Convergence Analyzer

Analyze a tracked file's commit history to determine whether iterative editing is **converging** (approaching stability) or **diverging** (still expanding scope).

## Arguments

```
/patent-convergence-analyzer <file-path> [--baseline <commit-hash> [--prior-verdict DIVERGING|CONVERGING|CONVERGED]]
```

- **file-path** (required): Repository-relative path to the file
- **--baseline** (optional): Commit hash from a prior analysis. Only examines commits after baseline; produces a delta report.
- **--prior-verdict** (optional, requires --baseline): Verdict from the prior analysis. Used for comparison phrasing in the delta report. If omitted, infer from baseline data or state "prior verdict not provided."

## Phase 1: Data Collection

**Sandbox constraints:** Do NOT use pipes (`|`), `wc -l`, `cat`, or `head`/`tail` — they fail in sandbox.

### 1. Commit list

```bash
# Full analysis
git log --oneline -- <path>

# Delta analysis (baseline provided)
git log --oneline <baseline>..HEAD -- <path>
```

### 2. Full hashes + timestamps

```bash
git log --format="%H %ai" --reverse [<baseline>..HEAD] -- <path>
```

### 3. Per-commit diff stats

For each commit hash, run individually (no for-loops with `&&`):

```bash
git diff --numstat <hash>~1 <hash> -- <path>
```

### 4. File size at each commit

Two-step — get blob hash, then size. Run each individually or in parallel batches:

```bash
git ls-tree <hash> -- <path>
# Output: <mode> blob <blob-hash>\t<filename>

git cat-file -s <blob-hash>
```

### 5. Anchor line count

Get the line count at the first commit (or baseline) to anchor cumulative calculations. Use `git grep -c` (no pipes needed):

```bash
git grep -c "" <hash> -- <path>
```

Then derive line counts at subsequent commits by accumulating per-commit numstat insertions/deletions from Step 3.

### 6. Cumulative net change (verification)

```bash
git diff --numstat <first-hash> <last-hash> -- <path>
```

**Note:** This may differ slightly from summing per-commit numstats (overlapping edits within same lines across commits). Use per-commit accumulation for line tracking; this step is a sanity check only.

## Phase 2: Analysis

### Commit Categorization

Classify each commit into exactly ONE category using the commit message and diff stats:

| Category | Signal |
|----------|--------|
| **Addition** | New content, sections, or concepts introduced |
| **Fix** | Internal consistency corrections, contradictions resolved |
| **Figure** | Figure updates, diagram annotations, visual changes |
| **Reframing** | Structural reorganization, terminology changes, section moves |
| **Trimming** | Removal of excess, tightening language, net-negative lines |

### Growth Metrics

Select ~6 evenly spaced sample points (plus first and last). Compute at each:

- Line count (from anchor + accumulated numstat)
- Byte size (from `git cat-file -s`)
- Cumulative growth % from initial (bytes)
- **Bytes-per-interval**: byte delta between consecutive sample points in the growth table. Should decelerate if converging.

### Convergence Signals

Evaluate all of:

1. **Line count frozen duration** — consecutive commits with net zero line change
2. **Last new concept** — most recent commit introducing genuinely new material (not reworking existing)
3. **Alignment ratio** — % of total commits that are pure Fix/Figure/Trimming (no new content)
4. **Scope trend** — average insertions per commit over time (should decrease)
5. **Late-stage commit size** — are recent commits surgical (few lines) or expansive?

### Section Rework Tracking

Identify sections touched by 3+ commits. Determine if rework is:
- **Convergent** — narrowing toward stable form (each edit smaller/more precise)
- **Circular** — oscillating between alternatives (reverts, contradictory changes)

**Long-line documents:** When the file uses one-line-per-paragraph formatting, line-level analysis underrepresents edit magnitude. Supplement with byte-level analysis — a +1/-1 numstat can mask 500+ words of rewritten prose.

## Phase 3: Verdict

| Verdict | Criteria |
|---------|----------|
| **DIVERGING** | New concepts still appearing, line count growing, no deceleration in bytes-per-interval |
| **CONVERGING** | New concepts stopped, line count stabilizing, byte growth decelerating, but edits still substantial |
| **CONVERGED** | Structure frozen, all changes are alignment/polish, commit scope at floor level |

Provide 3-5 specific evidence points supporting the verdict.

## Output Format

### Full Analysis Report

```markdown
## Convergence Analysis — <filename>
**Commits analyzed:** N (hash_first..hash_last)
**Time span:** start_date — end_date

### File Growth
| Sample | Commit | Lines | Bytes | Cumulative Growth |
|--------|--------|-------|-------|-------------------|
| Initial | <hash> | N | N | -- |
| ~Commit N | <hash> | N | N | +N% |
...

### Bytes Per Interval (deceleration series)
N → N → N → N → N → N

### Commit Categorization
| # | Hash | Time | Category | Summary |
|---|------|------|----------|---------|
...

### Category Distribution
| Category | Count | % |
|----------|-------|---|
...

### Section Rework Summary
- **Section name**: N touches (pattern: convergent/circular)
...

### Verdict: [DIVERGING/CONVERGING/CONVERGED]
1. Evidence point 1
2. Evidence point 2
...
```

### Delta Report (when --baseline provided)

Same structure, but:
- Header shows baseline commit, lines, bytes vs current
- Only new commits in categorization table
- Growth table starts at baseline row, then new sample points (prior sample points are not reconstructed unless a prior report artifact is available)
- Verdict compares against prior verdict if provided: "continued converging", "reversed to diverging", "reached converged". If no prior verdict supplied, state current verdict independently.

## Common Mistakes

- **Using pipes or `wc -l`**: Will fail silently or error. Use `git grep -c ""` for line counts, `git ls-tree` + `git cat-file -s` for sizes, `git diff --numstat` for per-commit changes.
- **Chaining `git cat-file` in for-loops**: `&&` chaining in loops fails. Run each blob size query as a separate command or in parallel batches.
- **Confusing "Fix" with "Reframing"**: Fix = correcting errors/contradictions. Reframing = reorganizing structure or changing terminology without fixing errors.
- **Counting terminology changes as "Addition"**: Renaming/redefining terms is Reframing, not Addition. Addition means genuinely new concepts.
- **Trusting cumulative numstat for line counts**: `git diff --numstat <first> <last>` may differ from summing per-commit numstats due to overlapping line edits. Use per-commit accumulation from an anchor point for accurate line tracking.
