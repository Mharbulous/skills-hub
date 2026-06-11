# ADR 001: Swarm dispatch uses paste-body + warmup-then-parallel

**Status:** Accepted (revised 2026-04-19 post-experiment review)
**Date:** 2026-04-19
**Context:** `/swarm` fans out the same skill across N files via one subagent per file.

## Context

The original `/swarm` dispatched all N typed subagents in a single parallel Agent-tool message, each invoking the Skill tool at runtime to load the skill body. This paid N× the skill's token cost with no shared cache.

Two assumptions had to be tested before committing to an optimized design:

1. When a custom subagent declares `skills:` in YAML frontmatter, is the skill content placed in the cached system-prompt prefix (shareable across sibling spawns) or in the conversation body (not shared)?
2. Do typed sibling subagents of the same `subagent_type` share cache hits on the system prompt?

Official Anthropic docs were ambiguous on (1). Community sources claimed (2) was false — that each typed subagent got an independent cache. Both needed empirical confirmation.

## Test

See `handovers/completed/014_test-skills-frontmatter-cache.md` for full methodology (originally commit `fdcc2e8`, rewritten locally as `0eff733` after a `sanitize-commit.sh` amend collision — content unchanged). Three arms, each spawned N=3 subagents sequentially, measured `cache_creation_input_tokens` and `cache_read_input_tokens` on each spawn's first assistant message from the session transcript.

- **Arm A**: custom subagent_type with `skills: [<probe>]` in frontmatter. Probe was the 13,140-byte pre-mortem skill.
- **Arm B**: `general-purpose` subagent with the full skill body pasted into the user prompt.
- **Arm C**: bare custom subagent_type (no `skills:` field) — the baseline against Arm A.

Sequential spawns were used (not parallel) because parallel spawns race the cache write and produce a null signal before the first response lands.

## Findings

1. **`skills:` frontmatter lands in the cached system-prompt prefix.** The delta between Arm A and Arm C matched exactly: `A1.cache_creation − C1.cache_creation = A2.cache_read − C2.cache_read = 1,615 tokens`. Every byte Spawn 1 wrote to cache came back as `cache_read` on Spawns 2–3.
2. **Typed sibling subagents DO share cache** on the system-prompt prefix, contradicting the community claim that each typed subagent has an independent cache. Sharing is real when `subagent_type` and frontmatter are byte-identical.
3. **Parallel spawns race the cache write.** If all N spawn in one message, none has finished writing before the others begin, so no spawn reads from cache. The warmup-then-parallel pattern is required to realize savings.
4. **Arm B (pasted body) also hits cache across siblings.** Spawns 2–3 showed `cache_read = 12,784` on the pasted content, confirming identical user-prompt prefixes cache across sibling typed subagents just as system prompts do.

## Post-experiment review — two caveats

### Caveat 1: Injected token count is not linear in skill file size

Arm A injected the 13,140-byte pre-mortem skill and measured 1,615 tokens in the cached prefix — roughly 8 chars/token, about half the density markdown typically tokenizes at. Cross-check against Arm B (the same skill body pasted into the user prompt) showed a delta of 12,784 tokens against Arm C.

The ~8× gap between frontmatter-injected size (1,615) and pasted-body size (12,784) for the same source file means **Claude Code is injecting a compressed, truncated, or otherwise reduced form of the skill via `skills:`, not the raw SKILL.md body**. Any savings projection that scales linearly with skill file size is unvalidated — the injected size may be capped, concave, or otherwise nonlinear.

**Consequence:** this ADR does not publish a file-size-based savings formula. Before making claims of the form "a KB skill saves tokens per sibling," measure the spawn-1 `cache_creation_input_tokens` for that specific skill against a bare control. A useful scaling probe: run the experiment with one ~2KB skill and one ≥30KB skill; combined with the 13KB probe result, three data points reveal whether the curve is linear, capped, or concave.

### Caveat 2: New agent files are not hot-reloaded mid-session

The test discovered this the hard way: `agents/cache-probe.md` was created during the session but the Agent tool's registry didn't recognize it; the test had to use agents that already existed in the registry at session start.

**Consequence:** the earlier draft of this decision (lazily generate `agents/swarm-<skill-slug>.md` at `/swarm` time and spawn it) is **broken** as designed. Mid-session generation produces "Agent type not found" errors.

Three options were considered:
- **A. Pre-declare** a fixed set of `swarm-probe-<skill>.md` agents for supported skills. Works, but fixes the set of skills ahead of time.
- **B. Two-phase with restart.** Phase 1 writes the agent files and tells the user to restart; Phase 2 runs post-restart. Works but is clumsy.
- **C. Paste the skill body** into each spawn's user prompt. No restart, no pre-declaration. Arm B confirms this still gets sibling cache sharing (`cache_read = 12,784` on spawns 2–3).

## Decision (revised)

`/swarm` routes skill-specified work through **paste-body + warmup-then-parallel** (Option C):

1. Orchestrator reads the skill's `SKILL.md` body once.
2. Builds a byte-identical shared prefix (skill body + boilerplate) that is pasted into every spawn's prompt.
3. Dispatches a single warmup spawn serially, waits for completion.
4. Dispatches the remaining N−1 spawns in one parallel message. These hit the cache written by the warmup.

`subagent_type` stays `general-purpose` (or the user's `agent:<name>` override). No runtime generation of custom agents.

When no skill is specified (freeform text), fall back to plain parallel dispatch — no shared prefix to cache.

## Consequences

**Positive:**
- Works in any session without pre-declaration, restart, or agent-registry warm-up.
- Siblings 2..N get measurable cache sharing on the skill body (empirically validated in Arm B).
- Simpler mental model: one skill read in the orchestrator, one prompt template, one `subagent_type`.

**Negative:**
- Warmup serialization adds one spawn's worth of latency before the parallel tail begins. For N=2, this roughly doubles wall time vs. pure parallel. Acceptable for non-trivial N.
- The orchestrator pays the skill's token cost once to read the SKILL.md. Spawn 1 writes it to cache at creation cost. Spawns 2..N read from cache at ~10% of normal input cost. Total skill-token cost is `orchestrator_read + spawn1_creation + (N-1) × cache_read_price`.
- The shared prefix must be byte-identical across spawns. Any per-file interpolation in the prefix (e.g., "Processing `<PATH>`:" above the skill body) breaks caching. The prompt template puts all variable content below a fixed delimiter.

**Neutral:**
- If the declared skill is edited between swarm runs, the next run picks up the updated body automatically (orchestrator re-reads on each invocation).
- Pre-declared custom subagents with `skills:` frontmatter remain viable as a future optimization for heavily-used skills, but require the user to create and commit those agent files between sessions. Not wired in by default.

## Open questions for future work

- Scaling curve of the `skills:` frontmatter injection (Caveat 1 probe: 2KB + 30KB data points).
- Whether the frontmatter-injected form is a summarization, truncation, or deterministic transformation of SKILL.md — affects whether pre-declared agents would deliver reliable skill fidelity for any given skill.
- Whether Path A (pre-declared custom subagents) beats Path C (paste) on large skills where the compressed-injected form may exceed the paste cost per spawn.

## References

- Official: [Create custom subagents](https://code.claude.com/docs/en/sub-agents) — confirms `skills:` frontmatter injects content at startup; does not specify prefix vs body, does not mention hot-reload behavior.
- Official: [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — "parallel requests needing cache hits, wait for the first response before sending subsequent requests."
- Third-party (empirical, fork-specific): [Sub-agent best practices](https://claudefa.st/blog/guide/agents/sub-agent-best-practices).
- Test artifact: `handovers/completed/014_test-skills-frontmatter-cache.md` (commit `0eff733`; previously `fdcc2e8` before a local history rewrite).
