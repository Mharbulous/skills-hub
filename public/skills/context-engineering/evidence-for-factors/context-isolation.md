# Factor 1: Context Isolation (Working-State Pollution)

## Evidence For

- **Context rot is empirically real.** Chroma (2025) tested 18 frontier models — all degrade as context grows. Three mechanisms: "lost-in-the-middle" (30%+ accuracy drop for buried info), attention dilution, distractor interference. (research.trychroma.com/context-rot)
- **Coding agents are especially vulnerable.** Augment Code: accumulative context, high distractor density, long task horizons maximize context rot. Recommendation: isolate search into subagents, return only precise results. (augmentcode.com)
- **Anthropic's own data.** Token usage explains 80% of performance variance. Isolated subagents used ~9K tokens vs ~15K for single-window. (anthropic.com/engineering/effective-context-engineering)
- **Framework consensus.** LangGraph: isolated subgraph state as first-class pattern. "Share memory by communicating." (langchain-ai.github.io/langgraphjs)

## Evidence Against

- **"Lost in the middle" doesn't apply at skill scale.** Liu et al. studied 15-20 documents. Effect "not very visible" with 3-4 small chunks. Skills (~hundreds of tokens) never reach the degradation zone. (MIT Press TACL)
- **Context management alternatives exist.** Progressive summarization, selective pruning, sliding windows — all work without spawning agents. (Redis, Milvus, Phil Schmid Context Engineering series)
- **Agent spawn costs ~2-3K tokens minimum.** If inline task takes 500 tokens, isolation destroys value. The "9K vs 15K" comparison cherry-picks multi-domain queries. (DEV Community, Augment Code)
- **Single-agent matches multi-agent under normalized compute.** April 2026 paper tested 5 multi-agent architectures — single-agent matches or outperforms when compute equalized. (arxiv 2604.02460)
- **Coordination failures.** UC Berkeley: isolated agents decide on stale/incomplete info. Overhead scales O(n^2). (arxiv 2503.13657)

## Judge Synthesis

The factor is real but narrower than originally framed. Context isolation matters for **working-state pollution** (output tokens from file reads, iteration, error cycles), NOT for instruction loading (skill definitions are too small to matter). MCP tool pollution is an additional unconsidered dimension — agents with restricted tools get a leaner tool surface.

**Key reframing:** A skill saying "read every file and fix bugs" uses trivial instruction tokens but produces massive working state. The decision is about the OUTPUT, not the definition.

Factor weight should scale with **task duration**, not task type. Applies to ~20% of skill-vs-agent decisions — specifically messy, iterative, high-volume subtasks.
