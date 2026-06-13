"""
Add 'listbot' relevance events to lines 257-264 so they become cross-repo
and depth_placement routes them to the global ~/.claude/CLAUDE.md.
"""
import sqlite3
from datetime import datetime, timezone

DB = r'C:\Users\Brahm\.claude\skills\claude-curator\claude-storage.db'
COMMIT_RANGE = 'b3cfbb94..f917f095'

line_ids = [257, 258, 259, 260, 261, 262, 263, 264]

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
now = datetime.now(timezone.utc).isoformat()

for line_id in line_ids:
    line = db.execute('SELECT id, content FROM lines WHERE id = ?', (line_id,)).fetchone()
    if not line:
        print(f'Line {line_id} not found, skipping')
        continue

    # Check if listbot event already exists
    existing = db.execute(
        "SELECT id FROM relevance_events WHERE line_id = ? AND repo = 'listbot'",
        (line_id,)
    ).fetchone()
    if existing:
        print(f'Line {line_id} already has listbot event, skipping')
        continue

    db.execute(
        """INSERT INTO relevance_events (line_id, repo, relevant_paths, commit_range, event_type, notes)
           VALUES (?, 'listbot', '', ?, 'observed', 'Cross-repo routing fix: guidance applies to listbot')""",
        (line_id, COMMIT_RANGE)
    )
    print(f'Added listbot event for line {line_id}: {line["content"][:70]}')

db.commit()
db.close()
print('\nDone.')
