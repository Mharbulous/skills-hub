---
name: ab-test
description: "DEPRECATED — use /ab-test-revised instead. Original A/B test harness using Agent tool subagents (no nesting). Kept for historical reference only."
disable-model-invocation: true
---

# A/B Test Orchestrator (DEPRECATED)

**This skill is deprecated.** Use `/ab-test-revised` instead, which:
- Auto-starts the OTel collector (no session-level env vars needed)
- Supports tasks requiring subagent spawning
- Has validated token measurement accuracy (internal consistency confirmed)

The original harness required launching Claude Code with OTel env vars and used the Agent tool (subagents), which prevented nested subagent spawning within variants.

Historical test reports using this harness are in `testing/reports/`.
