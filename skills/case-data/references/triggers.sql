-- =========================================================================
-- Case Data — v6.1 cross-database FK triggers
-- Loaded per-session AFTER all three databases are ATTACHed:
--   main     = case-specific data (proceedings, parties, facts, etc.)
--   law      = universal legal taxonomy (legal_concepts, legal_criteria)
--   privileged = solicitor-client privileged material
--
-- 6 cross-DB FK pairs enforced (INSERT + UPDATE each = 12 triggers):
--   1. main.criteria_facts.criterion_id       → law.legal_criteria.criterion_id
--   2. main.coa_criteria.criterion_id        → law.legal_criteria.criterion_id
--   3. main.issue_criteria.criterion_id      → law.legal_criteria.criterion_id
--   4. privileged.privileged_sources.proceeding_id → main.proceedings.proceeding_id
--   5. privileged.fact_provenance.fact_id   → main.facts.fact_id
--   6. main.causes_of_action.concept_id    → law.legal_concepts.concept_id
--
-- 4 delete guards (BEFORE DELETE on referenced tables):
--   - law.legal_criteria   (referenced by #1, #2, #3)
--   - law.legal_concepts   (referenced by #6)
--   - main.proceedings     (referenced by #4)
--   - main.facts           (referenced by #5)
--
-- Convention: CREATE TEMP TRIGGER — triggers live in temp schema only,
-- so they exist for the session lifetime and do not persist in any DB file.
-- =========================================================================

-- =====================================================================
-- FK #1: main.criteria_facts.criterion_id → law.legal_criteria.criterion_id
-- =====================================================================
CREATE TEMP TRIGGER trg_criteria_facts_criterion_id_insert
BEFORE INSERT ON criteria_facts
WHEN NEW.criterion_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: criterion_id not found in legal_criteria')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_criteria WHERE criterion_id = NEW.criterion_id
    );
END;

CREATE TEMP TRIGGER trg_criteria_facts_criterion_id_update
BEFORE UPDATE OF criterion_id ON criteria_facts
WHEN NEW.criterion_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: criterion_id not found in legal_criteria')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_criteria WHERE criterion_id = NEW.criterion_id
    );
END;

-- =====================================================================
-- FK #2: main.coa_criteria.criterion_id → law.legal_criteria.criterion_id
-- =====================================================================
CREATE TEMP TRIGGER trg_coa_criteria_criterion_id_insert
BEFORE INSERT ON coa_criteria
WHEN NEW.criterion_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: criterion_id not found in legal_criteria')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_criteria WHERE criterion_id = NEW.criterion_id
    );
END;

CREATE TEMP TRIGGER trg_coa_criteria_criterion_id_update
BEFORE UPDATE OF criterion_id ON coa_criteria
WHEN NEW.criterion_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: criterion_id not found in legal_criteria')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_criteria WHERE criterion_id = NEW.criterion_id
    );
END;

-- =====================================================================
-- FK #3: main.issue_criteria.criterion_id → law.legal_criteria.criterion_id
-- =====================================================================
CREATE TEMP TRIGGER trg_issue_criteria_criterion_id_insert
BEFORE INSERT ON issue_criteria
WHEN NEW.criterion_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: criterion_id not found in legal_criteria')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_criteria WHERE criterion_id = NEW.criterion_id
    );
END;

CREATE TEMP TRIGGER trg_issue_criteria_criterion_id_update
BEFORE UPDATE OF criterion_id ON issue_criteria
WHEN NEW.criterion_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: criterion_id not found in legal_criteria')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_criteria WHERE criterion_id = NEW.criterion_id
    );
END;

-- =====================================================================
-- FK #4: privileged.privileged_sources.proceeding_id → main.proceedings.proceeding_id
-- =====================================================================
CREATE TEMP TRIGGER trg_privileged_sources_proceeding_id_insert
BEFORE INSERT ON privileged.privileged_sources
WHEN NEW.proceeding_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: proceeding_id not found in proceedings')
    WHERE NOT EXISTS (
        SELECT 1 FROM main.proceedings WHERE proceeding_id = NEW.proceeding_id
    );
END;

CREATE TEMP TRIGGER trg_privileged_sources_proceeding_id_update
BEFORE UPDATE OF proceeding_id ON privileged.privileged_sources
WHEN NEW.proceeding_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: proceeding_id not found in proceedings')
    WHERE NOT EXISTS (
        SELECT 1 FROM main.proceedings WHERE proceeding_id = NEW.proceeding_id
    );
END;

-- =====================================================================
-- FK #5: privileged.fact_provenance.fact_id → main.facts.fact_id
-- =====================================================================
CREATE TEMP TRIGGER trg_fact_provenance_fact_id_insert
BEFORE INSERT ON privileged.fact_provenance
WHEN NEW.fact_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: fact_id not found in facts')
    WHERE NOT EXISTS (
        SELECT 1 FROM main.facts WHERE fact_id = NEW.fact_id
    );
END;

CREATE TEMP TRIGGER trg_fact_provenance_fact_id_update
BEFORE UPDATE OF fact_id ON privileged.fact_provenance
WHEN NEW.fact_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: fact_id not found in facts')
    WHERE NOT EXISTS (
        SELECT 1 FROM main.facts WHERE fact_id = NEW.fact_id
    );
END;

-- =====================================================================
-- FK #6: main.causes_of_action.concept_id → law.legal_concepts.concept_id
-- =====================================================================
CREATE TEMP TRIGGER trg_causes_of_action_concept_id_insert
BEFORE INSERT ON causes_of_action
WHEN NEW.concept_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: concept_id not found in legal_concepts')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_concepts WHERE concept_id = NEW.concept_id
    );
END;

CREATE TEMP TRIGGER trg_causes_of_action_concept_id_update
BEFORE UPDATE OF concept_id ON causes_of_action
WHEN NEW.concept_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'FK violation: concept_id not found in legal_concepts')
    WHERE NOT EXISTS (
        SELECT 1 FROM law.legal_concepts WHERE concept_id = NEW.concept_id
    );
END;

-- =====================================================================
-- Delete guard: law.legal_criteria.criterion_id
-- Referenced by: main.criteria_facts, main.coa_criteria, main.issue_criteria
-- =====================================================================
CREATE TEMP TRIGGER trg_legal_criteria_delete_guard
BEFORE DELETE ON law.legal_criteria
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete: referenced by criteria_facts')
    WHERE EXISTS (
        SELECT 1 FROM main.criteria_facts WHERE criterion_id = OLD.criterion_id
    );
    SELECT RAISE(ABORT, 'Cannot delete: referenced by coa_criteria')
    WHERE EXISTS (
        SELECT 1 FROM main.coa_criteria WHERE criterion_id = OLD.criterion_id
    );
    SELECT RAISE(ABORT, 'Cannot delete: referenced by issue_criteria')
    WHERE EXISTS (
        SELECT 1 FROM main.issue_criteria WHERE criterion_id = OLD.criterion_id
    );
END;

-- =====================================================================
-- Delete guard: law.legal_concepts.concept_id
-- Referenced by: main.causes_of_action
-- =====================================================================
CREATE TEMP TRIGGER trg_legal_concepts_delete_guard
BEFORE DELETE ON law.legal_concepts
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete: referenced by causes_of_action')
    WHERE EXISTS (
        SELECT 1 FROM main.causes_of_action WHERE concept_id = OLD.concept_id
    );
END;

-- =====================================================================
-- Delete guard: main.proceedings.proceeding_id
-- Referenced by: privileged.privileged_sources
-- =====================================================================
CREATE TEMP TRIGGER trg_proceedings_delete_guard
BEFORE DELETE ON proceedings
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete: referenced by privileged_sources')
    WHERE EXISTS (
        SELECT 1 FROM privileged.privileged_sources WHERE proceeding_id = OLD.proceeding_id
    );
END;

-- =====================================================================
-- Delete guard: main.facts.fact_id
-- Referenced by: privileged.fact_provenance
-- =====================================================================
CREATE TEMP TRIGGER trg_facts_delete_guard
BEFORE DELETE ON facts
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete: referenced by fact_provenance')
    WHERE EXISTS (
        SELECT 1 FROM privileged.fact_provenance WHERE fact_id = OLD.fact_id
    );
END;
