# Passthrough Mode (DEPRECATED)

**This mode is deprecated.** Use `/ab-test-revised` instead. Stop here and switch to `/ab-test-revised`.

---

*Historical reference below — do not execute.*

Run a single variant on a task and log metrics. Used by automation scripts that aggregate results externally.

## Arguments

`--passthrough --variant A|B [--output-format dead-code-json] <task>`

## Steps

1. Extract variant (`A` or `B`) and remaining task from arguments
2. Check OTel: `curl -s http://localhost:4318/api/health 2>/dev/null`
   - If available: `curl -s -X POST http://localhost:4318/api/variant/{A|B}`
3. Launch the agent (`testA-baseline` for A, `testB-jcodemunch` for B) with the task
4. **If `--output-format dead-code-json` is NOT present** (default passthrough):
   1. Review the agent's prose answer for qualitative observations — anything surprising, notable, or not captured by metrics (e.g., "agent tried 3 different search strategies before finding the right file", "missed all .vue files", "indexed repo twice"). If any exist, include them as `notes` in the NDJSON line. If nothing notable, omit the field.
   2. Append one NDJSON line to `testing/data/ab-test-log.ndjson`:
      ```json
      {"timestamp":"2026-03-18T00:00:00Z","variant":"A","task":"...","total_tokens":0,"tool_uses":0,"duration_ms":0,"notes":"agent re-indexed repo mid-task after initial search returned no results"}
      ```
      Use actual values from the Agent tool result. `notes` is optional — only include when there's a genuine qualitative insight.
   3. Done — no report synthesis.

5. **If `--output-format dead-code-json` IS present**:
   1. Do NOT append to `ab-test-log.ndjson` (the bash runner manages its own NDJSON files).
   2. Extract the JSON array findings from the agent's response — scan for a JSON array starting with `[` that contains objects with `file` keys.
   3. Collect agent metrics from the Agent tool result: `total_tokens`, `tool_uses`, `duration_ms`.
   4. Output a single JSON envelope to stdout (no markdown fences, no surrounding text):
      ```json
      {"agent_metrics":{"total_tokens":N,"tool_uses":N,"duration_ms":N},"findings":[...]}
      ```
      Where `findings` is the extracted JSON array from step 5.2.
   5. Done — the bash runner parses this envelope.
