# Recipe: add_position_kind

Adding a new row to `core.position_kind` requires extending the `CHECK` constraint on `ev.positions(position)`. SQLite has no `DROP CONSTRAINT`, so the path is table-rename + recreate + data-copy. Run inside one transaction on a connection with `core`, `internal`, and `ev` ATTACHed and `journal_mode = DELETE`. Replace `<KIND_ID>`, `<KIND_NAME>`, `<PRECEDENCE>`, `<ALLOWED_VALUES_TUPLE>` before running.

```sql
-- =========================================================================
-- Recipe: add a new row to core.position_kind and extend the
-- ev.positions(kind, value) CHECK constraint.
-- SQLite has no DROP CONSTRAINT, so a CHECK update requires the
-- table-rename / recreate / data-copy dance.
-- Run inside one transaction on a connection with core + internal + ev
-- ATTACHed and journal_mode = DELETE.
-- Replace <KIND_ID>, <KIND_NAME>, <PRECEDENCE>, <ALLOWED_VALUES_TUPLE>.
-- =========================================================================

BEGIN;

-- 1. Add the new kind row.
INSERT INTO core.position_kind (kind_id, kind_name, precedence)
VALUES (<KIND_ID>, '<KIND_NAME>', <PRECEDENCE>);

-- 2. Drop dependent triggers + indexes on ev.positions.
--    Triggers on positions (all TEMP — must be recreated after COMMIT via triggers.sql):
--      trg_positions_fact_fk_ins / _upd
--      trg_positions_party_fk_ins / _upd
--      trg_positions_proc_fk_ins / _upd
--      trg_positions_source_doc_fk_ins / _upd
--      trg_positions_kind_fk_ins / _upd
--    SQLite DROP TABLE (Step 5) destroys all triggers on the dropped table,
--    including TEMP triggers — the connection staying open does not preserve them.
--    The DROP steps below are for permanent indexes only (TEMP triggers have no
--    DROP INDEX equivalent — they vanish with the table).
DROP INDEX  IF EXISTS ev.idx_positions_fact;
DROP INDEX  IF EXISTS ev.idx_positions_fact_current;
DROP INDEX  IF EXISTS ev.idx_positions_kind;
DROP INDEX  IF EXISTS ev.idx_positions_party;
DROP INDEX  IF EXISTS ev.idx_positions_chain;

-- 3. Recreate the table with the extended CHECK.
CREATE TABLE ev.positions_new (
    position_id          INTEGER PRIMARY KEY,
    fact_id              INTEGER NOT NULL,
    position_kind_id     INTEGER NOT NULL,
    party_id             INTEGER NOT NULL,
    proceeding_id        INTEGER,
    source_document_id   INTEGER,
    source_locator       TEXT,
    position             TEXT NOT NULL,
    qualification        TEXT,
    asserted_at          TEXT,
    deemed               INTEGER NOT NULL DEFAULT 0 CHECK (deemed IN (0,1)),
    valid_from           TEXT NOT NULL DEFAULT (date('now')),
    valid_to             TEXT,
    prior_id             INTEGER REFERENCES positions_new(position_id),
    verified             INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (-1,0,1,2)),
    source_ref           TEXT,
    notes                TEXT,
    CHECK (
        (position_kind_id = 1 AND position IN ('found_proven','found_false','judicially_noticed'))
     OR (position_kind_id = 2 AND position = 'admit')
     OR (position_kind_id = 3 AND position IN ('admit','deny','no_knowledge'))
     OR (position_kind_id = 4 AND position IN ('admit','deny','no_knowledge'))
     OR (position_kind_id = 5 AND position = 'asserts')
     OR (position_kind_id = <KIND_ID> AND position IN <ALLOWED_VALUES_TUPLE>)  -- NEW
    ),
    CHECK (deemed = 0 OR position_kind_id = 2)
);

-- 4. Copy data verbatim.
INSERT INTO ev.positions_new SELECT * FROM ev.positions;

-- 5. Swap.
DROP TABLE ev.positions;
ALTER TABLE ev.positions_new RENAME TO positions;

-- 6. Recreate indexes (per references/schema.sql ev section).
CREATE INDEX ev.idx_positions_fact            ON positions(fact_id);
CREATE INDEX ev.idx_positions_fact_current    ON positions(fact_id, valid_to);
CREATE INDEX ev.idx_positions_kind            ON positions(position_kind_id);
CREATE INDEX ev.idx_positions_party           ON positions(party_id);
CREATE INDEX ev.idx_positions_chain           ON positions(prior_id);

COMMIT;

-- 7. Reload triggers from references/triggers.sql after COMMIT.
--    TEMP triggers are session-scoped; reload them on the same connection:
--      from fuse_safe_io import read_text
--      connection.executescript(read_text(
--          'triggers.sql',
--          required_markers=(
--              'CREATE TEMP TRIGGER trg_criteria_facts_criterion_id_insert',
--              'CREATE TEMP TRIGGER trg_facts_delete_guard',
--          ),
--      ))
--    or re-paste the ten CREATE TEMP TRIGGER statements from references/triggers.sql.

-- 8. Run audit_triggers.py — every positions FK trigger must still ABORT on orphan
--    inserts after the swap.
```
