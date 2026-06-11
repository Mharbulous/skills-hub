-- Claude Curator skill database schema
-- Create with: python -c "import sqlite3; conn = sqlite3.connect('claude-storage.db'); conn.executescript(open('schema.sql').read()); conn.close()"

CREATE TABLE proposed_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    origin_repo TEXT NOT NULL,
    origin_commits TEXT,
    gap_notes TEXT,
    section TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    origin TEXT NOT NULL CHECK(origin IN ('imported', 'generated')),
    source_proposed_id INTEGER,
    section TEXT,
    promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_proposed_id) REFERENCES proposed_lines(id)
);

-- Immutability: prevent content changes on permanent lines
CREATE TRIGGER prevent_content_mutation
BEFORE UPDATE OF content ON lines
BEGIN
    SELECT RAISE(ABORT, 'Content of permanent lines is immutable');
END;

CREATE TRIGGER prevent_origin_mutation
BEFORE UPDATE OF origin ON lines
BEGIN
    SELECT RAISE(ABORT, 'Origin of permanent lines is immutable');
END;

CREATE TABLE relevance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id INTEGER NOT NULL,
    repo TEXT NOT NULL,
    relevant_paths TEXT,
    commit_range TEXT,
    event_type TEXT NOT NULL CHECK(event_type IN ('observed', 'predicted')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (line_id) REFERENCES lines(id)
);

-- Append-only: prevent mutation of historical events
CREATE TRIGGER prevent_relevance_mutation
BEFORE UPDATE ON relevance_events
BEGIN
    SELECT RAISE(ABORT, 'Relevance events are append-only');
END;

-- placements.target is a filesystem path identifying the managed file
-- (e.g. "~/.claude/CLAUDE.md", "<repo>/CLAUDE.md", "<repo>/features/spellcheck/CLAUDE.md").
-- The string "global"/"project" convention is obsolete.
CREATE TABLE placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id INTEGER NOT NULL,
    target TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('promote', 'demote')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (line_id) REFERENCES lines(id)
);

-- Managed files discovered by walking the tree for CLAUDE.md files containing
-- a <CURATED> block. Populated by scripts/discover_managed_files.py.
-- depth = directory depth relative to repo root (-1 for ~/.claude/CLAUDE.md).
CREATE TABLE managed_files (
    path TEXT PRIMARY KEY,
    repo TEXT,
    depth INTEGER,
    last_written_at TIMESTAMP
);

-- Append-only: prevent rewriting placement history
CREATE TRIGGER prevent_placement_mutation
BEFORE UPDATE ON placements
BEGIN
    SELECT RAISE(ABORT, 'Placement history is append-only');
END;

CREATE TABLE repo_cursors (
    repo TEXT PRIMARY KEY,
    last_commit_hash TEXT NOT NULL,
    last_commit_timestamp TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX idx_relevance_line ON relevance_events(line_id);
CREATE INDEX idx_relevance_repo ON relevance_events(repo);
CREATE INDEX idx_placements_line ON placements(line_id);
CREATE INDEX idx_placements_target ON placements(target);
CREATE INDEX idx_lines_section ON lines(section);
CREATE INDEX idx_managed_files_repo ON managed_files(repo);
