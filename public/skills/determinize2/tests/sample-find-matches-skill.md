---
name: find-matches
description: Find candidate matches between a query record and a set of reference records, using deterministic normalization and keyword rules where possible, and human judgment for final relevance review.
---

# Find-Matches

Given a query record and a set of reference records, find the reference
records that most plausibly correspond to the same real-world entity.

## Phase 1: Normalization

Before comparing any two records, normalize their text fields using this
fixed table of transformation rules, applied in order:

| Rule | Transformation |
|---|---|
| 1 | Lowercase the entire string |
| 2 | Trim leading/trailing whitespace |
| 3 | Collapse internal whitespace runs to a single space |
| 4 | Strip punctuation: `.,;:'"()[]{}` |
| 5 | Replace `&` with `and` |
| 6 | Strip common legal suffixes: `inc`, `llc`, `ltd`, `corp`, `co` |
| 7 | Replace accented characters with their unaccented equivalents |

Every field used in matching runs through all 7 rules, in the order listed,
before any comparison happens.

## Phase 2: Candidate Retrieval

Given the normalized query, retrieve every reference record that shares at
least one normalized token with the query. This is a cheap pre-filter, not
the final match decision — it exists only to avoid comparing the query
against every reference record in Phase 3.

## Phase 3: Partial Containment and Word-Boundary Matching

For each candidate from Phase 2, apply these deterministic containment
rules to the normalized query string `Q` and candidate string `C`:

| Condition | Result |
|---|---|
| `Q == C` | Exact match |
| `Q` is a whitespace-bounded substring of `C` (word-boundary containment) | Strong partial match |
| `C` is a whitespace-bounded substring of `Q` (word-boundary containment) | Strong partial match |
| `Q` and `C` share every token but in a different order | Reordered match |
| `Q` and `C` share more than half their tokens, word-boundary aligned | Weak partial match |
| None of the above | No match |

Word-boundary containment means the substring must start and end at a space
or string boundary — `"art"` inside `"cartwright"` does NOT count, but
`"art"` inside `"fine art gallery"` does.

## Phase 4: Relevance Review

Not every string-level match is a real-world match, and not every miss is a
real miss. Review the Phase 3 results in context: does the candidate's
industry, location, or other surrounding fields make sense given what the
query is actually looking for? A "Strong partial match" on a common word
(e.g. "the", "group", "services") may still be a false positive; a "Weak
partial match" between a well-known abbreviation and its full name may
still be correct. This step requires judging plausibility in context — it
is not reducible to a fixed rule table, and different reviewers may
reasonably disagree at the margins.

## Phase 5: Keyword Extraction

From the fields that survive Phase 4, extract a ranked list of keywords
using this fixed pipeline:

1. Tokenize the normalized string on whitespace.
2. Drop tokens shorter than 3 characters.
3. Drop tokens present in the fixed stopword list: `the`, `and`, `of`, `for`,
   `a`, `an`, `in`, `on`, `at`, `to`.
4. Count remaining token frequency across all surviving Phase 4 records.
5. Sort tokens by frequency descending, then alphabetically ascending for
   ties.
6. Keep the top 10 tokens as the record's keyword set.

Every step in this pipeline is a fixed, enumerable rule — there is no
judgment call anywhere in Phase 5.

## Output

Return the surviving candidates from Phase 4, each annotated with its
Phase 3 match type and its Phase 5 keyword set, sorted by match strength
(Exact > Strong partial > Reordered > Weak partial).
