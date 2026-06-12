---
name: swarm
description: "Apply a skill or process to multiple files in parallel using one sub-agent per file. Use when the user runs /swarm with file paths, or asks to apply the same operation across many files."
---

# Swarm — Parallel File Processing

Applies a skill or freeform process to a list of files, one subagent per file. When a skill is specified, the orchestrator reads the skill body once, pastes it verbatim as the shared prefix of each spawn's prompt, and uses a sequential-warmup-then-parallel dispatch pattern so spawns 2..N hit the cache written by spawn 1.

See `reference/ADR.md` for the empirical tests that drove this design, including two post-experiment caveats that rule out lazy-generated custom subagents and invalidate any linear savings projection.

## Phase 1: Parse Inputs

Parse `$ARGUMENTS` into up to four token types. Respect double-quoted paths with spaces.

| Token type | Recognition |
|-----------|-------------|
| **Agent override** | `agent:<name>` — overrides the `subagent_type` used for dispatch |
| **Skill** | `/<name>` or `/<namespace>:<name>` where `<name>` matches an available skill in the current conversation |
| **Files** | Path-like tokens: have an extension, contain `\`, or are absolute paths (including Unix-style `/tmp/...`) |
| **Process** | All remaining tokens joined as free-text. When they follow a skill token, they are also forwarded as the skill's `args` |

Rules:
- A token that starts with `/` but does not match a known skill is a file path (e.g., `/tmp/foo.py`, `/etc/hosts`).
- Resolve files to absolute paths, normalize separators, and **deduplicate** — the same file listed twice becomes one agent.
- Default `subagent_type` is `general-purpose` unless `agent:<name>` supplies an override. The same `subagent_type` is used for every spawn in a single swarm run — do NOT generate custom subagent files at runtime (new agent files are not hot-reloaded into a running session; see ADR caveat 2).

### Missing files
Ask: "Which files should I process?" Wait for the answer.

### Missing process/skill
List the parsed files, then ask:
> "What should I apply to each file? You can describe the operation or name a skill (e.g., `/simplify`, `/doc-audit`)."

**STOP** — do not continue until both files and process are known.

## Phase 2: Confirm & Sharpen

Once files and process are known, critically review the operation for:
- **Unnecessary parts**: steps or constraints that add no value
- **Counterproductive parts**: steps that would undermine the goal
- **Naive requirements**: rigid or redundant specifications a smarter version would avoid

If improvements exist, draft a **sharpened** version — same intent, cleaner wording.

Then present the task back via `AskUserQuestion` with a single decision:

> **Files** (N): `<first 10 listed; "… and K more" if truncated>`
> **Subagent**: `<type>` (`general-purpose` unless `agent:<name>` was supplied)
> **Operation**: `<original, verbatim>`
> _(if sharpened differs)_ **Sharpened**: `<cleaner rewrite>`
> _(if N > 15)_ ⚠️ This will spawn N parallel agents.

Options:
1. Proceed with **original**
2. Proceed with **sharpened** _(only when a sharpened version exists)_
3. **Specify** a different operation
4. **Cancel**

**STOP** — do not dispatch until the user picks an option.

## Phase 3: Dispatch

Dispatch differs by whether a skill was specified.

### Path A: Skill specified (paste-body + warmup-then-parallel)

1. **Read the skill body once.** Locate the resolved skill's `SKILL.md`; for Skills-hub stubs, first fetch the authoritative body with the stub protocol. Read it in full. Hold the content in orchestrator context as `<SKILL_BODY>`.
2. **Build the per-spawn prompt** using the template below. The shared prefix (`<SKILL_BODY>` + boilerplate) must be **byte-identical across all spawns** — only the trailing per-file section varies. This is the portion that lands in the cached prefix.
3. **Warmup spawn (serial)**: dispatch ONE Agent call (`subagent_type: general-purpose`, or `agent:<name>` override) for the first file. Wait for completion. This populates the cache.
4. **Parallel tail**: dispatch the remaining N−1 Agent calls in a single message, same `subagent_type`, same shared prefix. They hit the cache written by the warmup spawn.
5. If N = 1, skip the warmup distinction (single serial spawn).

**Why paste over runtime-generated custom subagents:** new agent files are not hot-reloaded into a running Claude Code session — spawning a subagent_type that was written mid-session fails with "Agent type not found." See ADR caveat 2. The paste pattern sidesteps this entirely and still gets sibling cache sharing (Arm B in the test).

### Path B: No skill (freeform process)

Dispatch all N Agent calls in a single parallel message, `subagent_type` = `agent:<name>` override if supplied, else `general-purpose`. No warmup — no shared skill content to cache.

### Concurrency cap
If N > 15 in the parallel tail, batch into groups of 15. Run each batch as a single parallel message and wait for it to finish before launching the next. Announce the batching plan ("dispatching 47 files in 4 batches of ≤15") before starting.

### Agent prompt template (one per file)

Shared prefix (identical across all spawns in Path A):

```
You are a swarm worker applying the following skill to a single file.

<SKILL_BODY>

---
```

Per-file tail (varies):

```
Process the file at: <ABSOLUTE_PATH>

Task: <PROCESS_DESCRIPTION>[ with args: <SKILL_ARGS>]

Steps:
1. Read the file before editing — do not edit blind.
2. Apply the skill only to <ABSOLUTE_PATH>. Do not touch any other file.
3. Return a single-line status as your final message:
   - Success: "DONE: <filename> — <one-sentence summary of change>"
   - Failure: "FAIL: <filename> — <reason>"
```

**Do NOT** interpolate per-file values into the shared prefix — that would break the byte-identical requirement and defeat cache sharing.

## Phase 4: Synthesize

After all agents complete (warmup + parallel tail, combined), parse each result's **first non-empty line** tolerantly:

- Regex: `^\s*(DONE|FAIL)\s*:\s*([^—\-]+?)\s*[—\-]\s*(.+)$` (case-insensitive)
- If a result doesn't match, treat it as a **soft-fail**: use the raw first line as the summary and flag it.

Output:
- One bullet per file: `✓`/`✗` filename — summary
- Totals: `N done, M failed, K soft-failed`
- List any soft-fails separately with their raw output for review.
