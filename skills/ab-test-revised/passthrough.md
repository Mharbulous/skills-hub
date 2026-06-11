# Passthrough Mode (Revised)

Run a single variant via `claude -p --agent` and log metrics. Used by automation scripts that aggregate results externally.

## Arguments

`--passthrough --variant A|B [--output-format dead-code-json] <task>`

## Steps

1. Extract variant (`A` or `B`) and remaining task from arguments
2. Write the task to a temp file with variant-specific efficiency preamble prepended:

   **For variant A:**
   ```bash
   cat > /tmp/ab-task-prompt.txt << 'TASK_EOF'
   ## Efficiency Guidelines

   - **Batch searches:** When looking for multiple things, combine into fewer tool calls. Use `Grep` with broader patterns rather than one call per keyword.
   - **Parallel calls:** Make independent tool calls in the same message — don't serialize calls that have no dependency.
   - **Glob before Grep:** Use `Glob` to narrow the file set, then `Grep` only the relevant paths.
   - **Avoid redundant reads:** If a tool result already gave you the information, don't re-read the same file.

   ---

   <task description>
   TASK_EOF
   ```

   **For variant B:**
   ```bash
   cat > /tmp/ab-task-prompt.txt << 'TASK_EOF'
   ## Efficiency Guidelines

   - **Batch searches:** Combine related lookups into fewer tool calls. Use `search_symbols` with broader queries rather than one call per symbol.
   - **Parallel calls:** Make independent tool calls in the same message — don't serialize calls that have no dependency.
   - **Use `detail_level: "compact"`** on `search_symbols` when you only need names and paths (not full signatures/docs). This returns ~15 tokens/result vs ~75 at standard.
   - **Set `token_budget`** on search calls to cap response size when you expect many results.
   - **Prefer `get_file_outline`** over `get_file_content` when you only need to know what's defined in a file, not read every line.
   - **Avoid redundant reads:** If a tool result already gave you the information, don't re-read the same file.

   ---

   <task description>
   TASK_EOF
   ```
3. Run the variant:
   ```bash
   claude -p --agent {testA-main|testB-main} --output-format json < /tmp/ab-task-prompt.txt > /tmp/ab-variant-result.json
   ```
   Use Bash `timeout` of 600000ms. Map variant A -> `testA-main`, B -> `testB-main`.
4. Read `/tmp/ab-variant-result.json` and extract: `total_cost_usd`, `duration_ms`, `duration_api_ms`, `num_turns`, `is_error`, `result`, and `modelUsage` token fields (`outputTokens`, `cacheCreationInputTokens`, `cacheReadInputTokens`, `inputTokens`). The `modelUsage` object is keyed by model name — use the first (typically only) key to access token fields.
5. **Compute net cost:**
   ```
   overhead = 0.15 + num_turns × 0.0167
   net_cost_usd = total_cost_usd - overhead
   ```
6. **If `--output-format dead-code-json` is NOT present** (default passthrough):
   1. Review the variant's `result` text for qualitative observations — anything surprising or notable. If any exist, include as `notes`.
   2. Append one NDJSON line to `testing/data/ab-test-log.ndjson`:
      ```json
      {"timestamp":"2026-03-22T00:00:00Z","variant":"A","task":"...","total_cost_usd":1.50,"overhead":0.40,"net_cost_usd":1.10,"duration_ms":30000,"num_turns":15,"output_tokens":2500,"cache_creation_tokens":75000,"cache_read_tokens":150000,"notes":"optional qualitative insight"}
      ```
      Use actual values from the JSON result. `notes` is optional.
   3. Done — no report synthesis.

7. **If `--output-format dead-code-json` IS present**:
   1. Do NOT append to `ab-test-log.ndjson`.
   2. Extract the JSON array findings from the variant's `result` text.
   3. Collect metrics: `total_cost_usd`, `overhead`, `net_cost_usd`, `duration_ms`, `num_turns`, `output_tokens`, `cache_creation_tokens`.
   4. Output a single JSON envelope to stdout:
      ```json
      {"agent_metrics":{"total_cost_usd":1.50,"overhead":0.40,"net_cost_usd":1.10,"duration_ms":30000,"num_turns":15,"output_tokens":2500,"cache_creation_tokens":75000},"findings":[...]}
      ```
   5. Done.
