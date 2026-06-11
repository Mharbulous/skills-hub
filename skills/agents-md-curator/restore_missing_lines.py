"""
Restore lines that were in the CURATED block before the first introspect run
but were never imported into the database during Bootstrap.
These are inserted as permanent lines with a relevance event from the current
commit batch so they can compete in future runs.
"""
import sqlite3
from datetime import datetime, timezone

DB = r'C:\Users\Brahm\.claude\skills\claude-curator\claude-storage.db'
MANAGED_FILE = 'C:\\Users\\Brahm\\.claude\\CLAUDE.md'
COMMIT_RANGE = 'b3cfbb94..f917f095'

missing_lines = [
    {
        'content': 'Subagents should only be given only tools that are necessary to do the job that they are being assigned.',
        'section': 'Conventions',
    },
    {
        'content': 'Shell paths on Windows: Never pass raw Windows backslash paths (e.g. C:\\Users\\Brahm\\file.py) to Bash — backslashes are interpreted as escape characters, silently stripping them and corrupting the path. Always use $HOME with forward slashes and quote the arguments: "$HOME/.claude/skills/file.py".',
        'section': 'Gotchas',
    },
    {
        'content': 'Refer to yourself in the third person and model; i.e. "Claude Sonnet will..."',
        'section': 'Conventions',
    },
    {
        'content': 'Clarify user instructions that are contradictory, ambiguous or unclear.',
        'section': 'Conventions',
    },
    {
        'content': 'Use the AskUserQuestion tool if you have more than one question.',
        'section': 'Conventions',
    },
    {
        'content': 'Add comments only if the logic is non-obvious.',
        'section': 'Conventions',
    },
    {
        'content': 'When a test fails, print the failing assertion and the smallest reproducing input before attempting a fix.',
        'section': 'Conventions',
    },
    {
        'content': 'Before declaring a task complete, list what you verified (tests run, files read end-to-end) and what you assumed without verifying.',
        'section': 'Conventions',
    },
    # Also restore the Windows path line (line 254) that was unplaced
    {
        'content': 'Use native Windows path format with backslashes for all file operations (Read, Edit)',
        'section': 'Conventions',
    },
]

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
now = datetime.now(timezone.utc).isoformat()

inserted = []
for line in missing_lines:
    # Check not already present
    existing = db.execute(
        'SELECT id FROM lines WHERE content = ?', (line['content'],)
    ).fetchone()
    if existing:
        print(f'Already exists: {line["content"][:60]}...')
        inserted.append(existing['id'])
        continue

    # Insert as permanent line (like Bootstrap does)
    cur = db.execute(
        """INSERT INTO lines (content, section, status, first_seen_at, promoted_at)
           VALUES (?, ?, 'active', ?, ?)""",
        (line['content'], line['section'], now, now)
    )
    line_id = cur.lastrowid
    inserted.append(line_id)

    # Give it a relevance event from the current batch
    db.execute(
        """INSERT INTO relevance_events (line_id, repo, relevant_paths, commit_range, event_type, notes)
           VALUES (?, 'listbot', '', ?, 'observed', 'Restored from pre-bootstrap CURATED block')""",
        (line_id, COMMIT_RANGE)
    )

    # Record a placement
    db.execute(
        """INSERT INTO placements (line_id, action, target, created_at)
           VALUES (?, 'promote', ?, ?)""",
        (line_id, MANAGED_FILE, now)
    )

    print(f'Inserted line {line_id}: {line["content"][:70]}...')

db.commit()
db.close()
print(f'\nTotal lines now: {len(inserted)} restored')
