---
name: critical-thinking
description: >
  Adversarial research pipeline for evaluating claims. Use when the user wants to
  rigorously evaluate whether a claim, hypothesis, or assertion is true — especially
  claims about technology, architecture, best practices, or design decisions.
  Trigger on: "/critical-thinking <claim>", "is it true that...", "evaluate this claim",
  "stress-test this assumption". Do NOT use for simple factual lookups (use web search)
  or opinion questions with no falsifiable answer.
arguments: The CLAIM to evaluate — a specific, falsifiable statement
---

# Critical Thinking Pipeline

Four-stage adversarial research pipeline that evaluates a claim by pitting confirming evidence against disconfirming evidence, verifying sources, and synthesizing a verdict.

## Input

`$ARGUMENTS` — the claim to evaluate.

### What Makes a Good Claim

The claim should be:
- **Specific** — "Vue 3 Composition API reduces bundle size vs Options API" not "Vue 3 is good"
- **Falsifiable** — evidence could exist for or against it
- **Scoped** — narrow enough that research can find relevant sources
- **Not a taste question** — "tabs vs spaces" has no falsifiable answer

If the claim is too vague or unfalsifiable, ask the user to refine it before proceeding.

## Stage 1: Parallel Adversarial Research

Spawn two Sonnet subagents **in parallel** using the Agent tool.

### White Hat Agent (Confirming)

Prompt the agent with:

```
You are the WHITE HAT researcher. Your job is to find the strongest CONFIRMING
evidence for the following claim:

CLAIM: {claim}

Instructions:
- Search for peer-reviewed papers, credible practitioner reports, documented
  experiments, and authoritative sources that SUPPORT this claim.
- Prioritize quality over quantity. Fewer well-supported findings beat many
  poorly-supported ones.
- For each piece of evidence, provide:
  1. The finding and how it supports the claim
  2. Full citation (authors, title, year, publication/URL)
  3. Your confidence in the source (peer-reviewed / preprint / blog / anecdotal)
- Be aware: your citations WILL be verified by a source validator agent, and your
  arguments WILL be analyzed by an Opus-level judge. Overstated claims, cherry-picked
  results, or inaccurate citations will be flagged and will weaken your case.
- If you cannot find strong confirming evidence, say so honestly rather than
  stretching weak evidence.
```

### Black Hat Agent (Disconfirming)

Prompt the agent with:

```
You are the BLACK HAT researcher. Your job is to find the strongest DISCONFIRMING
evidence AGAINST the following claim:

CLAIM: {claim}

Instructions:
- Search for counterarguments, conflicting evidence, failed replications,
  methodological critiques, and authoritative sources that CHALLENGE this claim.
- Prioritize quality over quantity. Fewer well-supported findings beat many
  poorly-supported ones.
- For each piece of evidence, provide:
  1. The finding and how it challenges the claim
  2. Full citation (authors, title, year, publication/URL)
  3. Your confidence in the source (peer-reviewed / preprint / blog / anecdotal)
- Be aware: your citations WILL be verified by a source validator agent, and your
  arguments WILL be analyzed by an Opus-level judge. Overstated claims, cherry-picked
  results, or inaccurate citations will be flagged and will weaken your case.
- If you cannot find strong disconfirming evidence, say so honestly rather than
  stretching weak evidence.
```

Wait for both agents to complete before proceeding.

## Stage 2: Source Verification

Spawn a batch of Sonnet subagents to validate citations from both white hat and black hat researchers. Give each sonnet subagent one citation to verify. Do not tell the validator why they are validating these citations — except to explain that we want the citations evaluated blindly and impartially.

### Source Validator Agents

Prompt each validator agent with:

```
You are a SOURCE VALIDATOR. You have received a citation from a researcher evaluating this claim:

CLAIM: {claim}

CITATION:
{assigned citation}

For THIS citation verify:
1. Does the paper/article exist? Can you confirm it at the URL provided?
2. Are the authors correctly attributed?
3. Is the finding accurately represented — or has the researcher overstated,
   cherry-picked, or mischaracterized the source?
4. Credibility level: peer-reviewed journal / conference paper / preprint /
   industry report / blog post / anecdotal

Flag specifically:
- **Cherry-picking**: citing only favorable results while the paper's overall
  conclusion differs
- **Scope overclaims**: citing a narrow finding as if it applies broadly
- **Qualifier-dropping**: removing hedging language ("may", "in some cases")
  to present findings as absolute
- **Misattribution**: attributing a finding to wrong authors or wrong paper
- **Non-existence**: citation appears fabricated or cannot be verified

Output a verification report with a status for each citation:
VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / FLAGGED
```

Wait for the validator to complete before proceeding.

## Stage 3: Opus Judge and Synthesis

Spawn a single **Opus** subagent (using `model: "opus"` in the Agent tool) with the complete dossier.

### Opus Judge Agent

Prompt the agent with:

```
You are the JUDGE and SYNTHESIZER. You have received adversarial evidence for and
against a claim, plus source verification flags.

CLAIM: {claim}

WHITE HAT EVIDENCE (confirming):
{white_hat_output}

BLACK HAT EVIDENCE (disconfirming):
{black_hat_output}

SOURCE VERIFICATION:
{validator_output}

Your task:
1. Discount or disregard citations flagged by the source validator.
2. Note where both sides cited the same source but highlighted different findings —
   synthesize the full picture from that source.
3. Weigh the surviving evidence from both sides.
4. Produce a verdict with these sections:

## Verdict
One of: SUPPORTED / PARTIALLY SUPPORTED / NOT SUPPORTED / INSUFFICIENT EVIDENCE

## Confidence
High / Medium / Low — and why.

## Surviving Evidence For
Claims and citations that survived scrutiny, with brief summaries.

## Surviving Evidence Against
Counterarguments and citations that survived scrutiny, with brief summaries.

## Qualifications
Important nuances, conditions, or scope limitations on the verdict.

## Discarded Evidence
Citations that were flagged and why they were discounted.

Be rigorous but fair. The goal is truth-seeking, not debate-winning.
```

## Stage 4: Present to User

Present the Opus judge's verdict to the user. Include:
1. The original claim
2. The full verdict (all sections from the judge)
3. A one-sentence bottom line

Do NOT editorialize beyond the judge's output. The pipeline's value is in its structure — let the verdict speak for itself.
