# Anti-Pattern: Vague Instructions

**Category:** Clarity Anti-Pattern
**Severity:** Medium

## The Problem

Vague instructions like "do your best", "be creative", or "try your hardest" provide no actionable criteria. They delegate decision-making to the model without guidance.

### Examples

**Bad: "Do Your Best"**
```
Do your best to summarize this document.
```

**Good:**
```
Summarize this document in 3-5 bullet points, each under 20 words.
```

**Bad: "Be Creative" (Alone)**
```
Be creative and write something about our product.
```

**Good:**
```
Write 3 tagline options for our product. Each should be under 10 words, highlight the speed benefit, and use an active voice.
```

## Why It Fails

- No success criteria to measure against
- Model cannot know when "best" or "creative enough" is achieved
- Results vary unpredictably
- Creativity without bounds = chaos
- No way to evaluate if output meets needs

## Fix

Replace vague instructions with specific requirements:

**For effort-based phrases ("do your best", "try hard"):**
- Quantities: "exactly 3", "between 2-5"
- Quality criteria: "include key statistics", "focus on actionable items"
- Constraints: "under 100 words", "in bullet format"

**For creativity requests ("be creative", "be original"):**
- Format constraints: "3 options", "in haiku form"
- Content requirements: "must mention X", "focus on Y"
- Style guidance: "playful tone", "professional register"

## Scoring Impact

Deduct 2-3 points from Clarity & Specificity per instance.
