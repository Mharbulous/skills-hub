---
name: critical-skill-finder
description: Find and evaluate publicly available Claude skills using logically valid metrics. Use when searching for custom skills for a specific purpose. Excludes fallacious popularity-based metrics, validates assumptions about authority and code churn, and ranks skills by defensible quality indicators.
---

# Critical Skill Finder

Find publicly available Claude skills for a specific purpose using rigorous evaluation metrics with validated logical connections to quality.

## When to Use This Skill

Trigger this skill when:
- Searching for custom Claude skills for a specific capability
- Evaluating multiple skills to find the best fit
- Comparing skills across repositories
- Validating claims made by skill authors

## Core Principle: Logical Validity

Every evaluation metric must have a **defensible logical connection** to skill quality. Metrics are categorized by validity:

- ✅ **Valid**: Direct logical connection to quality
- ⚠️ **Moderate**: Plausible connection, requires context
- ⚠️ **Conditional**: Valid only if assumptions are verified
- ❌ **Fallacious**: No valid logical connection (excluded)

## Excluded Metrics (Logically Fallacious)

**DO NOT use these metrics to assess skill quality:**

- **Popularity metrics** (stars, forks, downloads, awesome-list mentions) — argumentum ad populum; popularity ≠ quality
- **Effort proxies** (total commits, LOC, age, contributor count) — effort/size/age ≠ outcome quality

## Evaluation Framework

### Tier 1: Content Analysis (Most Valid)

Directly examine the SKILL.md artifact. This is the most defensible evaluation method.

| Metric | Validity | How to Assess |
|--------|----------|---------------|
| **Domain specificity** | ✅ Valid (fitness for purpose) | Search for domain-specific terms, patterns, frameworks |
| **Framework flexibility** | ✅ Valid (fitness for purpose) | Does it assume one tool or support multiple? |
| **Instruction depth** | ⚠️ Moderate | Assess structure, comprehensiveness, clarity |
| **Capability coverage** | ⚠️ Moderate | What specific capabilities does it enable? |
| **Example quality** | ⚠️ Moderate | Are examples specific and actionable? |

**Action**: Fetch and read the raw SKILL.md file. Quote relevant sections as evidence.

### Tier 2: Iterative Refinement (Moderate - Validate for Churn)

Examine git history for the specific skill file, not the whole repository.

| Metric | Validity | How to Assess |
|--------|----------|---------------|
| **Commits to skill file** | ⚠️ Moderate | Git history for the exact file path |
| **Commit message quality** | ⚠️ Moderate | "fix", "improve" vs "add", "initial", formatting |
| **Churn-controlled ratio** | ⚠️ Moderate (better) | (skill commits / total repo commits) adjusted for (skill size / repo size) |

**Validation required**: High commit count could indicate:
- ✅ Active refinement based on feedback (good)
- ❌ Churn from instability or poor initial design (bad)
- ❌ Cosmetic changes (typos, formatting) (neutral)

**How to validate**: Read actual commit messages. Compare skill-specific commit ratio to repo-wide activity. High ratio in active repo = focused attention. High ratio in dead repo = unclear signal.

### Tier 3: Authority Signals (Conditional - Validate Relevance)

Author credentials can indicate quality, but only if:
1. Credentials are verifiable
2. Expertise is relevant to the skill's domain

| Metric | Validity | How to Assess |
|--------|----------|---------------|
| **Author's stated background** | ⚠️ Conditional | GitHub bio, linked portfolio |
| **Author's related projects** | ⚠️ Conditional | Other repos in same domain? |

**Validation required**:
- Is the claimed expertise verifiable (public profile, blog, employer)?
- Is the expertise relevant (QA background for QA skill, not general "developer")?
- Beware: Authority in unrelated domain = fallacious appeal to authority

### Tier 4: Published Outcomes (Rare but Valuable)

Empirical evidence of skill effectiveness is strongest, but rare.

| Metric | Validity | How to Assess |
|--------|----------|---------------|
| **Case studies with metrics** | ⚠️ Moderate | Search for skill name + "results" |
| **Before/after comparisons** | ⚠️ Moderate | Documented usage outcomes |

**Validation required**:
- What was the methodology?
- Is it self-reported (selection bias risk)?
- Are results reproducible or anecdotal?

## Search Strategy

### Step 1: Identify Candidate Skills

Search these sources:

```
GitHub:
- "claude skill [purpose]"
- "SKILL.md [purpose]"
- Repositories: anthropics/skills, travisvn/awesome-claude-skills,
  obra/superpowers, wshobson/agents, daymade/claude-code-skills

Skill directories:
- claude-plugins.dev
- skillsmp.com
```

### Step 2: Fetch and Analyze Content (Tier 1)

For each candidate:
1. Fetch the raw SKILL.md file
2. Assess domain specificity for user's stated purpose
3. Evaluate instruction depth and example quality
4. Quote relevant sections as evidence

### Step 3: Check Git History (Tier 2)

For promising candidates:
1. Check commits to the specific skill file
2. Calculate churn-controlled ratio
3. Read commit messages to validate refinement vs churn
4. Note file creation date vs last modification

### Step 4: Validate Authority (Tier 3)

For top candidates:
1. Look up author's GitHub profile
2. Check for relevant domain expertise
3. Verify credentials are real (not just claimed)
4. Note if expertise is relevant or tangential

### Step 5: Search for Outcomes (Tier 4)

For finalists:
1. Web search for skill name + outcomes/results/case study
2. Check author's blog for usage reports
3. Assess methodology of any claimed outcomes

## Output Format

For each skill, report: source URL, SKILL.md path, then assessments per tier (content analysis with quoted evidence, churn ratio with commit message validation, authority relevance check, any published outcomes). End with strengths/weaknesses/fitness-for-purpose rating (high/medium/low).

## Final Ranking

Rank skills by weighted validity:

1. **Tier 1 (Content)** - Primary factor. Poor content = disqualify regardless of other metrics.
2. **Tier 2 (Refinement)** - Secondary factor, only if churn validated as improvement.
3. **Tier 3 (Authority)** - Tiebreaker, only if credentials validated as relevant.
4. **Tier 4 (Outcomes)** - Strongest evidence if found, but rare.

## Validation Example

> "47 commits to the file; 38 substantive ('fix edge case...', 'add support for...'), 9 cosmetic. 81% substantive rate = genuine iteration, not churn."

Always cite specific commit messages and verify author credentials against the skill's domain.
