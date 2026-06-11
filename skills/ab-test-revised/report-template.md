# A/B Test Report Template (Revised)

Write to: `testing/reports/{date}-AB-test-report-{slug}.md`

```markdown
# A/B Test Report — {Task Title}

**Date:** {YYYY-MM-DD}
**Task:** {task description}
**Orchestration:** `claude -p --agent` (main-agent-level variant execution)

---

## Executive Summary

{2-3 sentence summary: which variant performed best on accuracy, efficiency, and tool usage. Lead with the efficiency ratio.}

---

## Test Setup

| Parameter | Value |
|-----------|-------|
| **Orchestrator** | ab-test-revised skill |
| **Execution method** | `claude -p --agent` (each variant runs as main agent) |
| **Subagent model** | {model used by variants — check JSON output or default} |
| **Codebase** | {project name and tech stack} |
| **Task type** | {categorize: enumeration, tracing, planning, audit, etc.} |
| **Date** | {date} |
| **Execution order** | {e.g., "B first, then A" — randomized} |

---

## Efficiency Comparison

| Metric | Test A (Native) | Test B (JCodeMunch) |
|--------|-----------------|---------------------|
| **Absolute difference** | ${total_cost_A - total_cost_B} | — |
| **Gross ratio** | {total_cost_A / total_cost_B} | — |
| **Corrected ratio** | {net_cost_A / net_cost_B} or "unreliable" | — |
| Total cost | ${total_cost_usd} | ${total_cost_usd} |
| Overhead | ${overhead_A} | ${overhead_B} |
| Net cost | ${net_cost_A} | ${net_cost_B} |
| Duration (ms) | {duration_ms} | {duration_ms} |
| Num turns | {num_turns} | {num_turns} |
| Output tokens | {outputTokens} | {outputTokens} |

> **Primary metric:** Absolute cost difference. Corrected ratio shown when both net costs exceed $0.01; otherwise marked unreliable.
> **Overhead formula:** `0.15 + num_turns × 0.0167` (calibrated 2026-03-22, R²=0.9999).
> **Gross ratio** is shown for transparency — expect it to be compressed toward 1.0.

### Raw Token Breakdown

| Token Type | Test A | Test B |
|------------|--------|--------|
| cacheCreationInputTokens | {val} | {val} |
| cacheReadInputTokens | {val} | {val} |
| outputTokens | {val} | {val} |
| inputTokens | {val} | {val} |

## Accuracy Comparison

{Compare task outputs qualitatively — did both reach the same conclusion? Items found by one but missed by the other?}

## Subagent Tool Enforcement

{Document whether the task spawned subagents. Confirm that subagents were spawned as the variant's own type (testA-main/testB-main) per the self-spawning rule, ensuring tool restrictions propagated. Note any evidence of enforcement failure (e.g., a subagent using Grep in variant B, or jcodemunch in variant A).}

## Observations

### Strengths by Variant
- **Test A (Native):** {what it did well}
- **Test B (JCodeMunch):** {what it did well}

### Gaps by Variant
- **Test A:** {what it missed or struggled with}
- **Test B:** {what it missed or struggled with}

## Recommendations

{Actionable takeaways for tool selection}

```

Fill in all `{placeholders}` from collected metrics. For qualitative sections (accuracy, observations, recommendations, subagent leakage), analyze the variants' `result` text from the JSON output.
