-- =========================================================================
-- Case Data — queries v6.1
-- Queries v6.2.
-- Views and canonical queries for the main/law/privileged architecture.
--
-- Views are CREATE VIEW statements (created in main.sqlite after ATTACH).
-- Canonical queries are parameterized SQL (? placeholders).
--
-- Query numbering:
--   01-12: v6 core queries (07 and 11 eliminated — contests/privilege_challenges removed)
--   13-17: v6.1 legal taxonomy queries
-- =========================================================================

-- =========================================================================
-- VIEWS
-- =========================================================================

-- -----------------------------------------------------------------
-- v_current_positions: current, non-rejected positions
-- -----------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_current_positions AS
SELECT  p.position_id,
        p.fact_id,
        p.party_id,
        p.position,
        p.qualification,
        p.source_id,
        p.source_locator,
        p.valid_from,
        p.verified
FROM    positions p
WHERE   p.valid_to IS NULL
  AND   p.verified >= 0;

-- -----------------------------------------------------------------
-- v_fact_status: one row per fact with derived posture
-- Posture rules:
--   Both parties claim same fact → agreed
--   Claim + admit → admitted
--   Claim + deny → disputed
--   Claim + silent → not_denied
--   Claim, no response → claimed
--   No claim → unclaimed
-- -----------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_fact_status AS
SELECT
    f.fact_id,
    f.description,
    f.category,
    f.date_of_fact,
    f.verified,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM v_current_positions p1
            JOIN v_current_positions p2 ON p2.fact_id = f.fact_id
            WHERE p1.fact_id = f.fact_id
              AND p1.position = 'claim' AND p2.position = 'claim'
              AND p1.party_id != p2.party_id
        ) THEN 'agreed'
        WHEN EXISTS (
            SELECT 1 FROM v_current_positions WHERE fact_id = f.fact_id AND position = 'deny'
        ) THEN 'disputed'
        WHEN EXISTS (
            SELECT 1 FROM v_current_positions WHERE fact_id = f.fact_id AND position = 'admit'
        ) THEN 'admitted'
        WHEN EXISTS (
            SELECT 1 FROM v_current_positions WHERE fact_id = f.fact_id AND position = 'silent'
        ) THEN 'not_denied'
        WHEN EXISTS (
            SELECT 1 FROM v_current_positions WHERE fact_id = f.fact_id AND position = 'claim'
        ) THEN 'claimed'
        ELSE 'unclaimed'
    END AS posture
FROM facts f
WHERE f.verified >= 0;

-- =========================================================================
-- CANONICAL QUERIES
-- =========================================================================

-- -----------------------------------------------------------------
-- @query_01_denied_facts_no_evidence
-- Facts that are denied but have no evidence link supporting them.
-- -----------------------------------------------------------------
SELECT
    f.fact_id,
    f.description,
    f.category
FROM facts f
JOIN v_current_positions p ON p.fact_id = f.fact_id AND p.position = 'deny'
WHERE f.verified >= 0
  AND NOT EXISTS (
    SELECT 1 FROM evidence_links el
    WHERE el.fact_id = f.fact_id
      AND el.valid_to IS NULL
      AND el.verified >= 0
      AND el.strength > 0
  )
ORDER BY f.fact_id;

-- -----------------------------------------------------------------
-- @query_02_universally_admitted_facts
-- Facts where all responding parties admit (no deny positions).
-- -----------------------------------------------------------------
SELECT
    f.fact_id,
    f.description,
    f.category
FROM facts f
WHERE f.verified >= 0
  AND EXISTS (
    SELECT 1 FROM v_current_positions WHERE fact_id = f.fact_id AND position = 'admit'
  )
  AND NOT EXISTS (
    SELECT 1 FROM v_current_positions WHERE fact_id = f.fact_id AND position = 'deny'
  )
ORDER BY f.fact_id;

-- -----------------------------------------------------------------
-- @query_03_coa_gap_analysis
-- Criteria for a cause of action with sufficiency assessment.
-- Parameter: ? = coa_id
-- -----------------------------------------------------------------
SELECT
    le.criterion_id,
    le.requirement_type,
    le.criterion_order,
    le.criterion_description,
    ce.sufficiency,
    CASE
        WHEN le.requirement_type = 'element' AND (ce.sufficiency IS NULL OR ce.sufficiency = 'gap')
        THEN 'FATAL GAP'
        WHEN le.requirement_type = 'factor' AND (ce.sufficiency IS NULL OR ce.sufficiency = 'gap')
        THEN 'WEAK (factor gap)'
        ELSE 'OK'
    END AS gap_severity
FROM causes_of_action coa
JOIN law.legal_criteria le ON le.concept_id = coa.concept_id
LEFT JOIN coa_criteria ce ON ce.coa_id = coa.coa_id AND ce.criterion_id = le.criterion_id
WHERE coa.coa_id = ?
ORDER BY le.criterion_order;

-- -----------------------------------------------------------------
-- @query_04_witness_dependencies
-- Sources that are the sole evidence for any fact (single point of failure).
-- -----------------------------------------------------------------
SELECT
    s.source_id,
    s.title,
    s.category,
    COUNT(DISTINCT el.fact_id) AS facts_solely_proven
FROM evidence_links el
JOIN sources s ON s.source_id = el.source_id
WHERE el.valid_to IS NULL
  AND el.verified >= 0
  AND el.strength > 0
  AND NOT EXISTS (
    SELECT 1 FROM evidence_links el2
    WHERE el2.fact_id = el.fact_id
      AND el2.source_id != el.source_id
      AND el2.valid_to IS NULL
      AND el2.verified >= 0
      AND el2.strength > 0
  )
GROUP BY s.source_id
ORDER BY facts_solely_proven DESC;

-- -----------------------------------------------------------------
-- @query_05a_verification_backlog_unverified
-- All unverified rows (verified = 0) across tables.
-- -----------------------------------------------------------------
SELECT 'facts' AS table_name, fact_id AS row_id, description AS summary
FROM facts WHERE verified = 0
UNION ALL
SELECT 'sources', source_id, title FROM sources WHERE verified = 0
UNION ALL
SELECT 'positions', position_id, position FROM positions WHERE verified = 0 AND valid_to IS NULL
UNION ALL
SELECT 'evidence_links', evidence_link_id, CAST(strength AS TEXT) FROM evidence_links WHERE verified = 0 AND valid_to IS NULL
UNION ALL
SELECT 'issues', issue_id, title FROM issues WHERE verified = 0
ORDER BY table_name, row_id;

-- -----------------------------------------------------------------
-- @query_05b_verification_needs_human
-- Rows flagged for human review (verified = 2).
-- -----------------------------------------------------------------
SELECT 'facts' AS table_name, fact_id AS row_id, description AS summary
FROM facts WHERE verified = 2
UNION ALL
SELECT 'sources', source_id, title FROM sources WHERE verified = 2
UNION ALL
SELECT 'positions', position_id, position FROM positions WHERE verified = 2 AND valid_to IS NULL
UNION ALL
SELECT 'evidence_links', evidence_link_id, CAST(strength AS TEXT) FROM evidence_links WHERE verified = 2 AND valid_to IS NULL
UNION ALL
SELECT 'issues', issue_id, title FROM issues WHERE verified = 2
ORDER BY table_name, row_id;

-- -----------------------------------------------------------------
-- @query_06_drift_detection
-- Sources with file_hash set — for recompute-and-compare integrity check.
-- -----------------------------------------------------------------
SELECT
    source_id,
    title,
    file_path,
    file_hash
FROM sources
WHERE file_hash IS NOT NULL
  AND file_path IS NOT NULL
ORDER BY source_id;

-- -----------------------------------------------------------------
-- @query_08_issue_heatmap
-- Issues ranked by number of linked facts and criteria.
-- -----------------------------------------------------------------
SELECT
    i.issue_id,
    i.title,
    i.status,
    i.priority,
    COUNT(DISTINCT if2.fact_id) AS linked_facts,
    COUNT(DISTINCT ie.criterion_id) AS linked_criteria
FROM issues i
LEFT JOIN issue_facts if2 ON if2.issue_id = i.issue_id
LEFT JOIN issue_criteria ie ON ie.issue_id = i.issue_id
WHERE i.verified >= 0
GROUP BY i.issue_id
ORDER BY i.priority, linked_facts DESC;

-- -----------------------------------------------------------------
-- @query_09a_fact_position_history
-- Full position history for a fact (including superseded).
-- Parameter: ? = fact_id
-- -----------------------------------------------------------------
SELECT
    p.position_id,
    p.party_id,
    pa.name AS party_name,
    p.position,
    p.qualification,
    p.source_id,
    s.title AS source_title,
    p.valid_from,
    p.valid_to,
    p.prior_id,
    p.verified
FROM positions p
JOIN parties pa ON pa.party_id = p.party_id
LEFT JOIN sources s ON s.source_id = p.source_id
WHERE p.fact_id = ?
ORDER BY p.valid_from DESC;

-- -----------------------------------------------------------------
-- @query_09b_fact_evidence_history
-- Full evidence link history for a fact (including superseded).
-- Parameter: ? = fact_id
-- -----------------------------------------------------------------
SELECT
    el.evidence_link_id,
    el.source_id,
    s.title AS source_title,
    s.category AS source_category,
    el.source_locator,
    el.strength,
    el.valid_from,
    el.valid_to,
    el.prior_id,
    el.verified
FROM evidence_links el
JOIN sources s ON s.source_id = el.source_id
WHERE el.fact_id = ?
ORDER BY el.valid_from DESC;

-- -----------------------------------------------------------------
-- @query_10_facts_only_privileged_sources
-- Facts that have provenance in privileged sources but no admissible
-- evidence link — trial-prep gaps.
-- -----------------------------------------------------------------
SELECT
    f.fact_id,
    f.description,
    f.category
FROM facts f
WHERE f.verified >= 0
  AND EXISTS (
    SELECT 1 FROM privileged.fact_provenance fp WHERE fp.fact_id = f.fact_id
  )
  AND NOT EXISTS (
    SELECT 1 FROM evidence_links el
    WHERE el.fact_id = f.fact_id
      AND el.valid_to IS NULL
      AND el.verified >= 0
      AND el.strength > 0
  )
ORDER BY f.fact_id;

-- -----------------------------------------------------------------
-- @query_12_unreviewed_sources
-- Sources that have never been ingested (no last_ingested_at).
-- -----------------------------------------------------------------
SELECT
    source_id,
    title,
    category,
    file_path,
    date
FROM sources
WHERE last_ingested_at IS NULL
  AND verified >= 0
ORDER BY date, source_id;

-- =========================================================================
-- v6.1 LEGAL TAXONOMY QUERIES
-- =========================================================================

-- -----------------------------------------------------------------
-- @query_13_concept_requirements
-- All requirements (elements + factors) for a concept.
-- Parameter: ? = concept_id
-- -----------------------------------------------------------------
SELECT
    le.criterion_id,
    le.requirement_type,
    le.criterion_order,
    le.criterion_description,
    le.burden_of_proof,
    le.determined_by_concept_id,
    det.name AS determined_by_name,
    le.authority_id,
    a.title AS authority_title,
    a.citation AS authority_citation,
    le.authority_proposition
FROM law.legal_criteria le
LEFT JOIN law.legal_concepts det ON det.concept_id = le.determined_by_concept_id
LEFT JOIN law.authorities a ON a.authority_id = le.authority_id
WHERE le.concept_id = ?
ORDER BY le.criterion_order;

-- -----------------------------------------------------------------
-- @query_14_concept_authorities
-- Authorities shaping a concept (concept-level linkage).
-- Parameter: ? = concept_id
-- -----------------------------------------------------------------
SELECT
    ca.relationship,
    ca.proposition,
    a.authority_id,
    a.title,
    a.citation,
    a.authority_type,
    a.jurisdiction
FROM law.concept_authorities ca
JOIN law.authorities a ON a.authority_id = ca.authority_id
WHERE ca.concept_id = ?
ORDER BY
    CASE ca.relationship
        WHEN 'establishes' THEN 1
        WHEN 'refines' THEN 2
        WHEN 'applies' THEN 3
        WHEN 'distinguishes' THEN 4
    END;

-- -----------------------------------------------------------------
-- @query_15_element_test_hierarchy
-- Full test hierarchy for a criterion (one level of nesting).
-- Returns the determining concept and all its requirements.
-- Parameter: ? = criterion_id
-- -----------------------------------------------------------------
SELECT
    le_parent.criterion_id AS parent_criterion_id,
    le_parent.criterion_description AS parent_description,
    lc.concept_id AS test_concept_id,
    lc.name AS test_name,
    le_child.criterion_id AS child_criterion_id,
    le_child.requirement_type AS child_requirement_type,
    le_child.criterion_order AS child_order,
    le_child.criterion_description AS child_description
FROM law.legal_criteria le_parent
JOIN law.legal_concepts lc ON lc.concept_id = le_parent.determined_by_concept_id
JOIN law.legal_criteria le_child ON le_child.concept_id = lc.concept_id
WHERE le_parent.criterion_id = ?
ORDER BY le_child.criterion_order;

-- -----------------------------------------------------------------
-- @query_16_coa_gap_analysis_v61
-- COA gap analysis with element vs factor severity.
-- Same as query_03 but explicitly named for v6.1 documentation.
-- Parameter: ? = coa_id
-- NOTE: query_03 already implements v6.1 gap analysis. This alias
-- exists for documentation purposes. Use query_03 in practice.
-- -----------------------------------------------------------------

-- -----------------------------------------------------------------
-- @query_17_concepts_by_type_jurisdiction
-- All concepts of a given type in a jurisdiction.
-- Parameters: ?1 = concept_type, ?2 = jurisdiction
-- -----------------------------------------------------------------
SELECT
    lc.concept_id,
    lc.name,
    lc.description,
    lc.notes,
    COUNT(le.criterion_id) AS requirement_count
FROM law.legal_concepts lc
LEFT JOIN law.legal_criteria le ON le.concept_id = lc.concept_id
WHERE lc.concept_type = ?
  AND lc.jurisdiction = ?
GROUP BY lc.concept_id
ORDER BY lc.name;
