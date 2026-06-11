# Gemini Prompt Structure Best Practices

**Created**: 2026-03-21

Guide for structuring `systemInstruction` vs `contents` in Gemini API calls. Based on Google's official documentation, academic research, and Google AI forum expert guidance.

## Why the Split Matters

Gemini's `systemInstruction` and `contents` are not interchangeable slots. They differ in three evidence-backed dimensions:

### 1. Caching (90% Cost Reduction)

Gemini's **implicit caching** (enabled by default, no code changes needed) detects when consecutive API requests share a common prefix and reuses cached computations. System instructions form the start of that prefix.

- Same `systemInstruction` across calls = stable prefix = cache hits = **90% discount** on cached tokens
- Variable data in `systemInstruction` = prefix changes every call = no cache hits = full price every time

| Model | Minimum Tokens for Cache Hit | Cached Token Discount |
|---|---|---|
| Gemini 2.5 Flash | 1,024 | 90% |
| Gemini 2.5 Pro | 4,096 | 90% |

Verify cache hits via `usageMetadata.cachedContentTokenCount` in responses.

**Source**: [Context caching docs](https://ai.google.dev/gemini-api/docs/caching), [Implicit caching announcement](https://developers.googleblog.com/en/gemini-2-5-models-now-support-implicit-caching/)

### 2. Attention Weight (Instruction Adherence)

Gemini models are instruction-tuned to give **higher weight to system instruction patterns** than to content patterns:

> "The models that use it have been tuned to more heavily weigh the patterns that are part of the system prompt more than later patterns."
> -- Google AI Developers Forum expert

This means: rules in `systemInstruction` are followed more reliably than the same rules placed in `contents`. The system instruction occupies position 0 in the token sequence, benefiting from **primacy bias** -- the well-documented phenomenon where LLMs attend more strongly to tokens at the beginning and end of input, with a 30%+ attention drop for middle tokens.

**Sources**: [Google AI Forum expert statement](https://discuss.ai.google.dev/t/expert-opinion-on-system-instruction/3240), "Lost in the Middle" (arXiv 2307.03172)

### 3. Multi-Turn Stability

In multi-turn conversations, `systemInstruction` stays at position 0 regardless of how many turns accumulate. Instructions placed in early content turns gradually drift toward the "middle" of the context window as the conversation grows, entering the attention dead zone.

Research shows a **39% average performance drop** in multi-turn vs single-turn settings, and up to **73% degradation** with long prior context. Keeping behavioral rules in `systemInstruction` mitigates this.

**Source**: "LLMs Get Lost In Multi-Turn Conversation" (arXiv 2505.06120)

## What Goes Where

### `systemInstruction` -- Stable, Behavioral, Cacheable

Content that is **identical across all calls for a given stage**:

- **Role definition**: "You are a legal document analyst for a Canadian law firm."
- **Output format rules**: JSON structure requirements, field naming conventions
- **Domain knowledge**: Folder naming conventions, legal document type hierarchies
- **Behavioral constraints**: What to include/exclude, confidence level definitions
- **Guardrails**: Safety boundaries, scope limitations

### `contents` -- Variable, Per-Request, Task-Specific

Content that **changes between calls**:

- **Task directive**: "Analyze the attached document and extract all requested fields."
- **Source documents**: PDF bytes, file manifests, document metadata
- **Per-matter context**: Client names, opposing parties, firm roster, existing cast list
- **Per-firm context**: Firm name, firm identity section
- **Field definitions**: Which fields to extract (when dynamically configured)
- **Negative constraints**: Place at the **end** of contents (see below)

### Negative Constraints Go Last

Google's Gemini 3 prompting guide explicitly states:

> "The model may drop negative constraints (specific instructions on what not to do) or formatting or quantitative constraints if they appear too early in the prompt. Place your core request and most critical restrictions as the final line of your instruction."

Structure contents as:
1. Context data (matterContext, firmSection)
2. Task directive
3. Source material (documents, file lists)
4. Negative constraints and critical restrictions (LAST)

## The Golden Rule

**If it changes per call, it does not belong in `systemInstruction`.**

This rule maximizes implicit cache hits. Every token of variable data in `systemInstruction` breaks the prefix match and costs you the 90% caching discount on ALL system instruction tokens, not just the variable ones.

### Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| `matterContext` prepended to systemInstruction | Per-matter YAML breaks cache prefix every call | Move to contents |
| `firmName` interpolated into systemInstruction | Per-firm value breaks cache across firms | Move firm identity to contents |
| Stable instructional text in contents only | Misses caching, lower attention weight | Move to systemInstruction |
| No systemInstruction at all | All tokens at full price, no attention priority | Extract stable portions into systemInstruction |
| Negative constraints at start of prompt | Model may drop them on complex requests | Move to end of contents |

## Recommended Prompt Architecture

```
systemInstruction:                          # STABLE per stage -- cached
  "You are a [role] for [domain].           # Role definition
                                            #
  RULES:                                    # Behavioral constraints
  1. [Rule about output format]             #
  2. [Rule about scope]                     #
                                            #
  DOMAIN KNOWLEDGE:                         # Stable reference material
  [Conventions, hierarchies, definitions]   #
                                            #
  OUTPUT FORMAT:                            # Schema/format rules
  [Field definitions, confidence levels]"   #

contents:                                   # VARIABLE per call
  [0] matterContext (YAML/XML)              # Per-matter context
  [1] firmSection                           # Per-firm identity
  [2] Task directive                        # What to do
  [3] Source material (docs, file lists)    # Input data
  [4] Negative constraints                  # LAST: "Do NOT..."
```

## Verifying Cache Hits

After restructuring prompts, verify that implicit caching is working:

```javascript
const response = await ai.models.generateContent({ ... });

// Check usage metadata
const usage = response.usageMetadata;
console.log('Cached tokens:', usage.cachedContentTokenCount);  // Should be > 0
console.log('Total input tokens:', usage.promptTokenCount);
console.log('Cache hit rate:', usage.cachedContentTokenCount / usage.promptTokenCount);
```

If `cachedContentTokenCount` is 0 across consecutive calls with the same stage, the system instruction is not stable enough for prefix matching.

## Explicit Caching (Optional, for High-Volume Stages)

For stages that make many calls in a short window (e.g., batch extraction across 50 documents), explicit caching guarantees cache hits with the same 90% discount:

```javascript
const cache = await ai.caches.create({
  model: 'gemini-2.5-flash',
  config: {
    systemInstruction: 'Your stable system prompt...',
    contents: [],
    ttl: '3600s',  // 1 hour
  },
});

// Use in subsequent calls
const response = await ai.models.generateContent({
  model: 'gemini-2.5-flash',
  contents: 'Per-request task and data...',
  config: { cachedContent: cache.name },
});
```

**Note**: Explicit caching has storage costs (see pricing tables below). Only use for high-volume batch operations where implicit caching hit rates are unreliable.

## Pricing

All prices are USD per 1M tokens. Thinking tokens are billed at the output rate.*

### Gemini 2.5 Flash

| Category | Rate |
|---|---|
| Input (text/image/video) | $0.30 |
| Input (audio) | $1.00 |
| Output (incl. thinking) | $2.50 |
| Cache read (text/image/video) | $0.03 |
| Cache read (audio) | $0.10 |
| Cache storage (explicit only) | $1.00/hr |
| Min cacheable tokens | 1,024 |

### Gemini 2.5 Pro

| Category | ≤200K tokens | >200K tokens |
|---|---|---|
| Input | $1.25 | $2.50 |
| Output (incl. thinking) | $10.00 | $15.00 |
| Cache read | $0.125 | $0.25 |
| Cache storage (explicit only) | $4.50/hr | $4.50/hr |
| Min cacheable tokens | 4,096 | 4,096 |

### Gemini 2.5 Flash Lite

| Category | Rate |
|---|---|
| Input (text/image/video) | $0.10 |
| Input (audio) | $0.30 |
| Output | $0.40 |
| Cache read (text/image/video) | $0.01 |
| Cache read (audio) | $0.03 |
| Cache storage (explicit only) | $1.00/hr |

### Implicit vs Explicit Caching

| Dimension | Implicit | Explicit |
|---|---|---|
| Read rate | 90% off input (same as explicit) | 90% off input (same as implicit) |
| Storage cost | None | $1.00–$4.50/M tokens/hr (model-dependent) |
| TTL control | Google manages | You set TTL (default: 1 hour) |
| Cache hit guarantee | No — opportunistic | Yes — guaranteed for TTL duration |
| Code changes | None | Must create cache object with TTL |

*\*Rates verified accurate as of March 2026. See [Google AI pricing](https://ai.google.dev/gemini-api/docs/pricing) for current rates.*

## Google Search Grounding Compatibility

`systemInstruction` IS compatible with the `googleSearch` tool. The two known constraints with Google Search grounding are:

1. **`contents` must be a plain string** (not `[{ text: prompt }]` array format) -- array format causes consistent empty responses.
2. **`responseMimeType: 'application/json'` is incompatible** -- returns 400 error.

Neither constraint affects `systemInstruction`. Stable instructions can and should be placed in `systemInstruction` even when using `googleSearch`, following the same split pattern as non-grounded calls.

```javascript
await ai.models.generateContent({
  model: 'gemini-2.5-flash-lite',
  contents: variablePrompt,              // Must be a string, not array
  config: {
    tools: [{ googleSearch: {} }],
    systemInstruction: stableInstructions, // Works alongside googleSearch
    // responseMimeType: 'application/json'  // NOT allowed with googleSearch
  },
});
```

## Research References

| Source | Key Finding |
|---|---|
| [Google Context Caching](https://ai.google.dev/gemini-api/docs/caching) | Implicit caching enabled by default, 90% discount, prefix matching |
| [Google Prompting Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) | Place behavioral constraints in system instruction |
| [Gemini 3 Prompting Guide](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/gemini-3-prompting-guide) | Negative constraints should go at the end |
| [Firebase AI - System Instructions](https://firebase.google.com/docs/ai-logic/system-instructions) | System instructions are a "preamble" processed before user content |
| [Google AI Forum](https://discuss.ai.google.dev/t/expert-opinion-on-system-instruction/3240) | Models tuned to weigh system instruction patterns more heavily |
| arXiv 2307.03172 "Lost in the Middle" | 30%+ attention drop for middle-position tokens |
| arXiv 2505.06120 "LLMs Get Lost in Multi-Turn" | 39% average performance drop in multi-turn settings |
| arXiv 2502.12197 "System Prompt Robustness" | Performance degrades with >5-10 guardrails in system prompt |
| arXiv 2602.15228 "System Prompts for Code Gen" | More detailed system prompts improve output quality |
