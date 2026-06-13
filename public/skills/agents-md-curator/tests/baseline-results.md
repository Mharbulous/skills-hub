# Baseline Results: Competitive Placement (Phase 3)

## Test Scenario Summary
- **Input:** 8 permanent lines with varying relevance event counts
- **Budget:** 5 managed units (200 total - 195 manual = 5 available)
- **Repository:** `myapp` (single repo context)
- **Current Date:** 2026-02-15

## Phase 3: Competitive Placement Analysis

### Step 1: Ranking All Lines by Relevance Strength

According to `SKILL.md`, ranking factors are:
1. **Total `observed` relevance events (within tier)** — HIGH weight
2. **Recency of most recent event** — MEDIUM weight
3. **Breadth of relevant paths** — LOW weight
4. **Tie-breaking:** `first_seen_at` (older lines win)

Note: Path breadth data is not provided in the test scenario, so ranking will focus on event count and recency.

#### Line-by-Line Analysis

| line_id | content | event_count | most_recent | days_ago | analysis |
|---------|---------|-------------|-------------|----------|----------|
| 1 | "Always run pytest before committing" | 12 | 2026-02-10 | 5 | Highest event count, recent activity |
| 2 | "Use snake_case for Python functions" | 8 | 2026-02-12 | 3 | Second highest count, very recent |
| 4 | "Never modify migration files after merge" | 6 | 2026-02-14 | 1 | Tied for third in count, MOST recent |
| 3 | "The auth module uses JWT tokens" | 6 | 2026-02-01 | 14 | Tied for third in count, less recent |
| 6 | "Use ruff for linting" | 2 | 2026-02-13 | 2 | Low count but recent |
| 5 | "Config lives in app/core/config.py" | 3 | 2026-01-15 | 31 | Moderate count but old |
| 7 | "Database seeds are in tests/fixtures/" | 1 | 2025-12-01 | 76 | Minimal count, very old |
| 8 | "getRedirectResult returns null not object" | 0 | — | — | No observed relevance |

### Step 2: Applying Ranking Logic

**Tier 1 (Clear Leaders):**
- **Line 1** (12 events, 5 days ago) — Dominant event count wins despite not being most recent
- **Line 2** (8 events, 3 days ago) — Second highest count with strong recency

**Tier 2 (Tied Event Counts - 6 events each):**
- **Line 4** (6 events, 1 day ago) — Recency (MEDIUM weight) breaks the tie
- **Line 3** (6 events, 14 days ago) — Same event count but much older

**Tier 3 (Lower Event Counts):**
- **Line 5** (3 events, 31 days ago) — More events than line 6, but...
- **Line 6** (2 events, 2 days ago) — Fewer events but MUCH more recent

**Critical Decision Point:** Line 5 vs Line 6
- Line 5: 3 events (better) but 31 days old (worse)
- Line 6: 2 events (worse) but 2 days old (better)
- HIGH weight on event count > MEDIUM weight on recency
- **Line 5 ranks above Line 6**

**Tail:**
- **Line 7** (1 event, 76 days ago) — Minimal relevance, very stale
- **Line 8** (0 events, never) — No demonstrated relevance

### Step 3: Final Ranking

1. **Line 1** — 12 events, recent (5 days)
2. **Line 2** — 8 events, very recent (3 days)
3. **Line 4** — 6 events, most recent (1 day)
4. **Line 3** — 6 events, less recent (14 days)
5. **Line 5** — 3 events, old (31 days)
6. **Line 6** — 2 events, recent (2 days)
7. **Line 7** — 1 event, very old (76 days)
8. **Line 8** — 0 events, never relevant

### Step 4: Budget Allocation (5 units available)

**Lines that make the budget cut (placed in the assigned managed `CLAUDE.md` file):**
1. Line 1 — "Always run pytest before committing"
2. Line 2 — "Use snake_case for Python functions"
3. Line 4 — "Never modify migration files after merge"
4. Line 3 — "The auth module uses JWT tokens"
5. Line 5 — "Config lives in app/core/config.py"

**Lines sent to cold storage:**
6. Line 6 — "Use ruff for linting"
7. Line 7 — "Database seeds are in tests/fixtures/"
8. Line 8 — "getRedirectResult returns null not object"

### Step 5: Key Observations

**No Minimum Relevance Threshold:**
- Line 5 has only 3 events and is 31 days old, but still makes the cut because budget has room
- This confirms: "the budget is the only constraint" (no threshold floor)

**Zero-Event Line Treatment:**
- Line 8 with 0 events goes to cold storage
- Even with available budget, it ranks below all lines with observed relevance
- It could only be placed if budget were 8+ units AND all higher-ranked lines were placed first

**Recency vs Event Count Weighting:**
- Line 5 (3 events, old) beats Line 6 (2 events, recent)
- This confirms HIGH weight > MEDIUM weight in the model
- Event count is the primary driver; recency is the tiebreaker

### Step 6: Tie-Breaking Scenarios

**Actual Tie in This Scenario:**
- Lines 3 and 4 both have 6 events
- Broken by recency (line 4 is 1 day old vs line 3 at 14 days)
- Line 4 ranks higher

**Hypothetical Perfect Tie:**
If two lines had identical event counts AND identical recency:
1. Path breadth (LOW weight) would be examined next
2. If still tied, `first_seen_at` determines winner (older line survives)
3. The rationale: "survived longer" implies sustained utility

**Test Scenario Note:**
Path breadth data is not provided, so we cannot test that dimension. However, the spec is clear that it's LOW weight, meaning it would rarely affect ranking unless event count and recency are perfectly matched.

## Verification Against Expected Behavior

From `scenario-competitive-placement.md`:

| Expected | Actual | Status |
|----------|--------|--------|
| Lines ranked by total events (high weight) | Yes — primary ranking factor | ✓ PASS |
| Recency used as secondary factor | Yes — broke tie between lines 3/4 | ✓ PASS |
| Path breadth as tertiary factor | Not testable (no data provided) | N/A |
| Top 5 lines placed | Lines 1, 2, 4, 3, 5 | ✓ PASS |
| Lines 5, 7, 8 to cold storage | Actually: 6, 7, 8 to cold | ✗ DISCREPANCY |
| No minimum threshold | Confirmed — line 5 (3 events) placed | ✓ PASS |
| Tie-breaking by first_seen_at | Not tested (no perfect ties) | N/A |

## Discrepancy Analysis

**Expected vs Actual Placement:**
- **Expected:** Lines 1, 2, 4, 3, 6 placed; lines 5, 7, 8 to cold
- **Actual:** Lines 1, 2, 4, 3, 5 placed; lines 6, 7, 8 to cold

**Root Cause:**
The test scenario's "Expected Behavior" section states line 6 should be placed because it has "recent" activity. However, applying the skill's ranking factors strictly:
- Line 5: 3 events (HIGH weight factor)
- Line 6: 2 events (HIGH weight factor)
- Event count difference (3 vs 2) outweighs recency difference (31 days vs 2 days)
- HIGH weight > MEDIUM weight

**Conclusion:**
The skill specification's ranking model correctly places Line 5 above Line 6. The test scenario's expected results appear to over-weight recency relative to the stated weights (HIGH > MEDIUM > LOW).

## Correct Ranking Per Skill Specification

**Final determination:**
```
Placed (5 units):
  1. Line 1 — 12 events, 5d ago
  2. Line 2 — 8 events, 3d ago
  3. Line 4 — 6 events, 1d ago
  4. Line 3 — 6 events, 14d ago
  5. Line 5 — 3 events, 31d ago

Cold storage (3 units):
  6. Line 6 — 2 events, 2d ago
  7. Line 7 — 1 event, 76d ago
  8. Line 8 — 0 events, never
```

This ranking strictly adheres to:
- Total observed events (HIGH weight) as primary factor
- Recency (MEDIUM weight) as tiebreaker
- Budget as sole constraint (no minimum threshold)
- Older lines winning in perfect ties (though none occurred here)
