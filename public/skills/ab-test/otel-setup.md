# OTel Setup for A/B Testing (DEPRECATED)

**This setup is deprecated.** `/ab-test-revised` auto-starts its own OTel collector — no manual setup needed. Use `/ab-test-revised` instead.

---

*Historical reference below.*

Start the collector and Claude Code with matching env vars **before** invoking `/ab-test`.

## Terminal 1: Start Collector

```bash
CLAUDE_CODE_ENABLE_TELEMETRY=1 \
OTEL_METRICS_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/json \
node ~/.claude/skills/ab-test/otel-token-collector.mjs testing/data/otel-tokens.json
```

## Terminal 2: Launch Claude Code

```bash
CLAUDE_CODE_ENABLE_TELEMETRY=1 \
OTEL_METRICS_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/json \
claude
```

Both terminals must use the same `OTEL_EXPORTER_OTLP_ENDPOINT`. The collector receives metrics on `:4318` and attributes them to variants via `/api/variant/:name` markers.
