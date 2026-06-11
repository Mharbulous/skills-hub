# Factor 4: Model Selection (Cost Optimization)

## Evidence For

- **MasRouter (ACL 2025):** 1.8-8.2% accuracy improvement, up to 52% overhead reduction from intelligent model routing.
- **Anthropic's cost-quality ladder:** Haiku ~60%, Sonnet ~30%, Opus ~10% of tasks.
- **3.75-5x cost multiplier per tier.** MindStudio: 50% cost reduction in PR review from routing.
- **`context: fork` in skills** enables skills to spawn agents with specific models — the inverted pattern is natively supported.

## Evidence Against

- **Benchmark convergence.** Sonnet 4.6: 79.6% SWE-bench vs Opus 4.6: 80.8% — 1.2 points. Meaningful gap only in deep scientific reasoning (GPQA: 74.1% vs 91.3%).
- **Solo dev cost savings negligible.** Tens of dollars/month difference. Enterprise routing justifies at 2M+ tokens/day.
- **Static pinning creates technical debt.** Models deprecate on 12-18 month cycles. "Model Dependency Debt" is formally categorized. Skills inheriting caller model are inherently model-agnostic.
- **Prompt quality dominates model tier.** Right prompt on cheaper model outperforms wrong prompt on expensive model (PromptHub, Wix Engineering).
- **Dynamic routing outperforms static.** MasRouter's gains come from learned routing, not hardcoded model IDs. Static pinning is the coarser approximation.

## Judge Synthesis

The developer's current practice (Opus main, agents pinned to Sonnet) is reasonable. Model pinning is a **bonus** of choosing an agent for other reasons — not a reason to create one. Pin to tier names not versions. The main LLM already acts as an implicit dynamic router by choosing when to spawn agents. Convergence is eroding this factor's weight over time.
