# case-data terminology crosswalk

`references\schema.sql` and `references\triggers.sql` are authoritative. This crosswalk is only a light map from glossary terms to the current schema. Update it when schema anchors named here change.

| Term | Schema anchor | Note |
|---|---|---|
| Matter | `main.matter_metadata`; `coclerk.json` pointer | Matter identity lives in the database; the pointer only locates the store. |
| Proceeding | `main.proceedings` | Court-filed case metadata. |
| Party / Role | `main.parties`; `main.proceeding_parties.role` | A party can have a role in a proceeding. |
| Source / Non-privileged Source | `main.sources` | Case-specific material that can participate in evidence and position links. |
| Privileged Source | `privileged.privileged_sources` | Structurally isolated from evidence links. |
| Authority | `law.authorities` | Reusable legal material, not case-specific source material. |
| Fact | `main.facts` | Includes provenance through `source_id` and `source_locator`. |
| Provenance | `main.facts.source_id`; `privileged.fact_provenance` | Where a fact was learned from; not proof by itself. |
| Evidence | `main.evidence_links` | Relationship from non-privileged source to fact with strength. |
| Position | `main.positions` | Current and historical party stance on a fact. |
| Claim Position / Admit / Deny / Silent | `main.positions.position` | Valid values are `claim`, `admit`, `deny`, and `silent`. |
| No Knowledge | `main.positions.position = 'silent'` | Preserve original wording in `qualification` or `notes` when needed. |
| Fact Posture | `v_fact_status` in `references\queries.sql` | Derived from current positions; not stored as a column. |
| Issue | `main.issues` | Material question in a matter. |
| Factual / Legal / Mixed Issue | `main.issues.issue_type` | Valid values are `factual`, `legal`, and `mixed`. |
| Issue-Fact Link | `main.issue_facts` | Facts relevant to an issue. |
| Issue-Criterion Link | `main.issue_criteria` | Legal criteria relevant to an issue. |
| Legal Concept | `law.legal_concepts` | Catalogue of cause of action, doctrine, test, defence, and remedy concepts. |
| Cause of Action Concept | `law.legal_concepts.concept_type = 'cause_of_action'` | General legal concept. |
| Asserted Cause of Action | `main.causes_of_action` | Matter-specific claim tied to a legal concept. |
| Legal Criterion | `law.legal_criteria` | Requirement belonging to a legal concept. |
| Element / Factor | `law.legal_criteria.requirement_type` | Valid values are `element` and `factor`. |
| Concept Authority | `law.concept_authorities` | Authority relationship at concept level. |
| Criterion Authority | `law.legal_criteria.authority_id` | Authority support for a specific criterion. |
| Listed | `main.sources.listed` | Disclosure-list status. |
| Admissible | `main.sources.admissible` | Trial-use assessment for a source. |
| Verified | `verified` columns | Extraction/classification quality state, not truth or proof. |
| Source Citation | `sources.file_path` plus `source_locator` | Display format is described in `SKILL.md`. |
| Legal Citation | `law.authorities.citation` | Legal citation for an authority. |
