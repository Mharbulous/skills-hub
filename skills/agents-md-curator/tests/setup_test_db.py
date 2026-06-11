#!/usr/bin/env python3
"""Create a test database matching the competitive placement baseline scenario."""

import os
import sqlite3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "test.db")
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "..", "..", "claude-curator", "schema.sql")


def setup():
    # Remove existing test db
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    # Create schema
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

    # Insert test lines (permanent)
    lines = [
        (1, "Always run pytest before committing", "imported", "Commands", "2025-06-01"),
        (2, "Use snake_case for Python functions", "imported", "Conventions", "2025-06-02"),
        (3, "The auth module uses JWT tokens", "imported", "Architecture", "2025-06-03"),
        (4, "Never modify migration files after merge", "imported", "Gotchas", "2025-06-04"),
        (5, "Config lives in app/core/config.py", "imported", "Architecture", "2025-06-05"),
        (6, "Use ruff for linting", "imported", "Commands", "2025-06-06"),
        (7, "Database seeds are in tests/fixtures/", "imported", "Pointers", "2025-06-07"),
        (8, "getRedirectResult returns null not object", "imported", "Gotchas", "2025-06-08"),
    ]
    for lid, content, origin, section, promoted_at in lines:
        conn.execute(
            "INSERT INTO lines (id, content, origin, section, promoted_at) VALUES (?, ?, ?, ?, ?)",
            (lid, content, origin, section, promoted_at)
        )

    # Insert relevance events matching the baseline scenario
    events = [
        # Line 1: 12 observed events, most recent 2026-02-10
        *[(1, "myapp", "app/tests/", "observed", f"2026-01-{i:02d}") for i in range(1, 12)],
        (1, "myapp", "app/tests/", "observed", "2026-02-10"),
        # Line 2: 8 observed events, most recent 2026-02-12
        *[(2, "myapp", "app/utils/", "observed", f"2026-01-{i:02d}") for i in range(1, 8)],
        (2, "myapp", "app/utils/", "observed", "2026-02-12"),
        # Line 3: 6 observed events, most recent 2026-02-01
        *[(3, "myapp", "app/auth/", "observed", f"2025-12-{i:02d}") for i in range(1, 6)],
        (3, "myapp", "app/auth/", "observed", "2026-02-01"),
        # Line 4: 6 observed events, most recent 2026-02-14
        *[(4, "myapp", "app/models/", "observed", f"2026-01-{i:02d}") for i in range(1, 6)],
        (4, "myapp", "app/models/", "observed", "2026-02-14"),
        # Line 5: 3 observed events, most recent 2026-01-15
        (5, "myapp", "app/core/", "observed", "2025-12-01"),
        (5, "myapp", "app/core/", "observed", "2026-01-01"),
        (5, "myapp", "app/core/", "observed", "2026-01-15"),
        # Line 6: 2 observed events, most recent 2026-02-13
        (6, "myapp", "app/lint/", "observed", "2026-02-01"),
        (6, "myapp", "app/lint/", "observed", "2026-02-13"),
        # Line 7: 1 observed event, most recent 2025-12-01
        (7, "myapp", "tests/fixtures/", "observed", "2025-12-01"),
        # Line 8: 0 events
    ]

    for line_id, repo, paths, event_type, created_at in events:
        conn.execute(
            "INSERT INTO relevance_events (line_id, repo, relevant_paths, event_type, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (line_id, repo, paths, event_type, created_at)
        )

    conn.commit()
    conn.close()
    print(f"Test database created at: {DB_PATH}")
    return DB_PATH


if __name__ == "__main__":
    setup()
