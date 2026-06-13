---
name: ab-test-revised
description: "A/B test orchestrator using claude -p for main-agent-level variant execution. Supports tasks requiring subagent spawning (e.g., /writing-plans). Sequential execution with randomized order and metrics comparison."
disable-model-invocation: true
---

# A/B Test Orchestrator (Revised)

Uses `claude -p --agent` to run each variant as its own main agent process, enabling subagent spawning within variants. Metrics come from `claude -p --output-format json` output.

## Task

`$ARGUMENTS`

## Mode Selection

If `$ARGUMENTS` starts with `--passthrough`: Read and follow `passthrough.md` in this skill directory.

Otherwise: Read and follow `full-test.md` in this skill directory.
