# Factor 2: Persona as Task-Dependent Steering

## Evidence For (Expert Personas Damage Retrieval Accuracy)

- **PRISM paper** (arXiv:2603.18507, USC): On MMLU, baseline 71.6%, expert persona dropped to 68.0%, longer expert to 66.3%. Expert personas "hurt pretrained knowledge retrieval." Mechanism: activates instruction-following mode (confident tone) at cost of factual recall. VERIFIED.
- **Zheng et al.** (arXiv:2311.10054, EMNLP 2024): 162 roles, 4 LLM families, 2,410 questions. Persona system prompts showed "no or small negative effects." Peer-reviewed. VERIFIED.
- **DEBATE paper** (arXiv:2405.09935): Devil's Advocate + Scorer methodological roles achieved SOTA on SummEval and TopicalChat. Procedural roles, not identity-based. VERIFIED.

## Evidence Against (Expert Personas Help on Generative Tasks)

- **Same PRISM paper** — expert personas IMPROVED 5 of 8 MT-Bench categories: Writing +0.40, Reasoning +0.40, Extraction +0.65, STEM +0.60, Roleplay. Both sides cherry-picked this paper; the full picture is task-dependent.
- **Mollick et al.** (SSRN:5879722, Wharton): No statistically significant improvement on GPQA Diamond and MMLU-Pro, except Gemini 2.0 Flash. Effect is model-dependent. VERIFIED.
- **"Position is Power"** (arXiv:2505.21091, ACM FAccT 2025): Same persona in system vs user prompt produces measurably different outputs. Persona placement IS architectural, not purely content. VERIFIED.
- **Methodology/identity distinction is leaky.** "Researcher" activates discourse conventions and stylistic patterns beyond pure methodology. Persona effects are inconsistent, suggesting identity-shaped pattern-matching against training data.

## Evidence on Multi-Persona Composition

- **Solo Performance Prompting (SPP)** (NAACL 2024): Single LLM holding multiple concurrent personas improved outcomes — reduced hallucination, stronger reasoning. But this is one study.
- **No peer-reviewed study directly tests composing multiple simultaneous personas in a single context window.** The composition claim is unverified, not confirmed.
- **Single-persona isolation can amplify biases** (arxiv 2511.11789): Fixed personas amplify individual biases, introduce new ones. Isolation may be more pathological than blending.

## Judge Synthesis

Expert personas are a **double-edged sword**, not universally harmful:
- **Hurts:** Knowledge retrieval, math, coding, humanities (factual accuracy tasks)
- **Helps:** Writing, extraction, STEM explanation, roleplay (structured output tasks)
- **Mechanism:** Expert persona activates confident structured output at the cost of factual recall

Methodological framing ("investigate," "verify") is safer for analytical tasks. The methodology/identity distinction is useful but leaky. Persona is a **prompt engineering choice**, not a skill-vs-agent differentiator — both can carry persona framing. But placement matters (system prompt > user prompt).

**Dropped from original framing:** Dunning-Kruger analogy (causal link inferred, not demonstrated; DKE itself contested). Multi-persona composition as a design principle (unverified). Universal "expert damages accuracy" claim (replaced with task-dependent finding).
