#!/usr/bin/env python3
"""Create a test database matching the tier rebalancing baseline scenario."""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "tier_test.db")
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "..", "schema.sql")


def setup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

    # Insert test lines (permanent)
    lines = [
        (1, "Always run tests before committing", "imported", "Commands", "2025-06-01"),
        (2, "Use type hints on all functions", "imported", "Conventions", "2025-06-02"),
        (3, "Never force-push to main", "imported", "Gotchas", "2025-06-03"),
        (4, "Check authStore.isInitialized first", "imported", "Gotchas", "2025-06-04"),
        (5, "Use named exports not default", "imported", "Conventions", "2025-06-05"),
    ]
    for lid, content, origin, section, promoted_at in lines:
        conn.execute(
            "INSERT INTO lines (id, content, origin, section, promoted_at) VALUES (?, ?, ?, ?, ?)",
            (lid, content, origin, section, promoted_at)
        )

    # Set current tier via placement records:
    # Lines 1, 2, 4 are project-local (myapp) — default, no global placement
    # Line 3 is global — needs a promote-to-global placement record
    # Line 5 is global — needs a promote-to-global placement record
    placements = [
        (3, "global", "promote", "2025-07-01"),
        (5, "global", "promote", "2025-07-01"),
    ]
    for line_id, target, action, created_at in placements:
        conn.execute(
            "INSERT INTO placements (line_id, target, action, created_at) VALUES (?, ?, ?, ?)",
            (line_id, target, action, created_at)
        )

    # Insert relevance events matching the scenario
    events = [
        # Line 1: myapp (8 events), webapp (3 events), api-service (2 events)
        *[(1, "myapp", "app/tests/", "observed", f"2026-01-{i:02d}") for i in range(1, 9)],
        *[(1, "webapp", "src/tests/", "observed", f"2026-01-{i:02d}") for i in range(10, 13)],
        *[(1, "api-service", "tests/", "observed", f"2026-01-{i:02d}") for i in range(14, 16)],
        # Line 2: myapp (5 events), webapp (4 events)
        *[(2, "myapp", "app/utils/", "observed", f"2026-01-{i:02d}") for i in range(1, 6)],
        *[(2, "webapp", "src/utils/", "observed", f"2026-01-{i:02d}") for i in range(6, 10)],
        # Line 3: myapp (1 event) only — was global, now single-repo
        (3, "myapp", "app/git/", "observed", "2026-01-15"),
        # Line 4: myapp (10 events) only
        *[(4, "myapp", "app/auth/", "observed", f"2026-01-{i:02d}") for i in range(1, 11)],
        # Line 5: myapp (2 events), webapp (1 event), cli-tool (1 event)
        (5, "myapp", "app/exports/", "observed", "2026-01-01"),
        (5, "myapp", "app/exports/", "observed", "2026-01-10"),
        (5, "webapp", "src/exports/", "observed", "2026-01-05"),
        (5, "cli-tool", "src/index.js", "observed", "2026-01-08"),
    ]

    for line_id, repo, paths, event_type, created_at in events:
        conn.execute(
            "INSERT INTO relevance_events (line_id, repo, relevant_paths, event_type, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (line_id, repo, paths, event_type, created_at)
        )

    conn.commit()
    conn.close()
    print(f"Tier test database created at: {DB_PATH}")
    return DB_PATH


if __name__ == "__main__":
    setup()
