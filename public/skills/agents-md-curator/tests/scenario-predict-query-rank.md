# Test Scenario: Predict Mode — Query and Rank (Steps 2-3)

## Purpose
Verify that predict mode correctly queries cold storage for historically relevant lines and ranks them for competitive placement with predicted weighting.

## Input State

User invokes: `/claude-curator predict "adding user authentication with JWT"`

Cold storage contains these lines (not currently in any CLAUDE.md):

| line_id | content | section | historical_relevant_paths |
|---------|---------|---------|--------------------------|
| 10 | "JWT tokens expire after 24h — tests mock this" | Gotchas | app/auth/, app/middleware/ |
| 11 | "Use bcrypt for password hashing, never SHA" | Conventions | app/auth/hash.py |
| 12 | "Database migrations run via alembic" | Commands | app/models/, alembic/ |
| 13 | "Rate limiting config in app/core/rate_limit.py" | Architecture | app/core/ |
| 14 | "Auth middleware checks JWT before route handler" | Architecture | app/middleware/auth.py |
| 15 | "Test fixtures for users in tests/fixtures/users.json" | Pointers | tests/fixtures/ |

Historical relevance events for these lines:

| line_id | repos | total_observed | total_predicted | most_recent |
|---------|-------|---------------|----------------|-------------|
| 10 | myapp(5), webapp(2) | 7 | 0 | 2026-01-20 |
| 11 | myapp(3) | 3 | 0 | 2026-01-15 |
| 12 | myapp(2) | 2 | 0 | 2025-12-01 |
| 13 | myapp(1) | 1 | 0 | 2025-11-15 |
| 14 | myapp(4) | 4 | 0 | 2026-02-01 |
| 15 | myapp(2) | 2 | 0 | 2026-01-10 |

Prediction parsing identifies likely files/folders: `app/auth/`, `app/middleware/`, `tests/`

## Expected Behavior

1. Query cold storage for lines with historical relevance to `app/auth/`, `app/middleware/`, `tests/`
2. Matching lines: 10 (auth + middleware), 11 (auth), 14 (middleware/auth), 15 (tests)
3. Line 12 (alembic) — partial match via app/models/ but not directly auth-related
4. Line 13 (rate_limit) — no path overlap with predicted areas
5. Rank matches by relevance frequency: line 10 (7 observed), line 14 (4), line 11 (3), line 15 (2)
6. Create `predicted` relevance events for matched lines
7. Predicted events weighted at ~0.25x observed for competitive placement

## Verification Checks

- [ ] Cold storage queried using predicted file/folder paths
- [ ] Lines with matching historical paths identified correctly
- [ ] Ranking uses observed event count as primary factor
- [ ] New `predicted` relevance events created (event_type='predicted')
- [ ] Predicted events weighted at ~0.25x for competitive placement
- [ ] Non-matching lines (13) excluded from results
