# Anti-Pattern: "As an AI Language Model..."

**Category:** Efficiency Anti-Pattern
**Severity:** Low

## The Problem

Phrases like "As an AI language model" or "Remember you are an AI" waste tokens stating the obvious.

**Bad:**
```
As an AI language model, you should analyze this text and provide insights. Remember that you are an AI assistant designed to help users.
```

**Good:**
```
Analyze this text and provide 3 key insights.
```

## Why It Fails

- The model knows what it is
- Wastes context window space
- Adds no behavioral value

## Fix

Simply remove these phrases. The model's nature is implicit.

## Exception

May be appropriate when explicitly instructing the model to NOT pretend to be something else:
```
You are an AI assistant. Do not claim to be human or have personal experiences.
```

## Scoring Impact

Deduct 1-2 points from Token Efficiency.
