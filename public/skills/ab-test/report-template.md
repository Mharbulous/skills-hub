# A/B Test Report Template (DEPRECATED)

**This template is deprecated.** `/ab-test-revised` has its own report template. Use `/ab-test-revised` instead.

---

*Historical reference below.*

Write to: `testing/reports/{date}-AB-test-report-{slug}.md`

```markdown
# A/B Test Report — {Task Title}

**Date:** {YYYY-MM-DD}
**Task:** {task description}

---

## Executive Summary

{2-3 sentence summary: which variant performed best on accuracy, efficiency, and tool usage}

---

## Test Setup

| Parameter | Value |
|-----------|-------|
| **Orchestrator** | ab-test skill |
| **Subagent model** | {same as orchestrator model — agents inherit it} |
| **Codebase** | {project name and tech stack} |
| **Task type** | {categorize: enumeration, tracing, planning, audit, etc.} |
| **Date** | {date} |
| **Baseline tokens** | {baseline_tokens from calibration run} |
| **Execution order** | {e.g., "B first, then A" — randomized} |

---

## Efficiency Comparison

| Metric | Test A (Native) | Test B (JCodeMunch) |
|--------|-----------------|---------------------|
| Total tokens (gross) | {from Agent result} | {from Agent result} |
| **Net search tokens** | {gross - baseline} | {gross - baseline} |
| Input tokens | {from OTel or "n/a"} | {from OTel or "n/a"} |
| Output tokens | {from OTel or "n/a"} | {from OTel or "n/a"} |
| Cache read tokens | {from OTel or "n/a"} | {from OTel or "n/a"} |
| Cache creation tokens | {from OTel or "n/a"} | {from OTel or "n/a"} |
| Duration (s) | {from Agent result} | {from Agent result} |
| Tool uses | {from Agent result} | {from Agent result} |

> **Token breakdown source:** {If OTel: "OTel OTLP collector (sequential execution)". If not: "Not available — start the collector before `/ab-test` for per-variant breakdown."}

## Accuracy Comparison

{Compare task outputs qualitatively — did both reach the same conclusion? Items found by one but missed by the other?}

## Observations

### Strengths by Variant
- **Test A (Native):** {what it did well}
- **Test B (JCodeMunch):** {what it did well}

### Gaps by Variant
- **Test A:** {what it missed or struggled with}
- **Test B:** {what it missed or struggled with}

## Recommendations

{Actionable takeaways for tool selection}

---

## Raw Metrics

- [`otel-tokens.json`](../data/otel-tokens.json) (OTel token breakdown, if collected)
```

Fill in all `{placeholders}` from collected metrics. For qualitative sections (accuracy, observations, recommendations), analyze the agents' text answers.
