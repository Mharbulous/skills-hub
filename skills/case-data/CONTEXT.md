# case-data terminology

This glossary is the source of truth for case-data domain terms. It defines ordinary legal terms as used in this skill; implementation mappings live in `references\terminology-crosswalk.md`.

## Glossary

**Matter.** The law-office file or engagement context; a matter can exist before filing and can contain zero, one, or multiple proceedings.

**Proceeding.** A court-filed case within a matter, identified by court, registry, file number, parties, and status.

**Party.** A person or organization participating in a proceeding or otherwise relevant to the matter.

**Role.** The capacity in which a party participates in a proceeding, such as plaintiff, defendant, applicant, respondent, or petitioner.

**Source.** Case-specific recorded material relevant to a matter.

**Non-privileged Source.** A source that can be used in the ordinary case record without crossing the privilege firewall.

**Privileged Source.** A source protected by solicitor-client privilege, litigation privilege, or another privilege rule; it may explain how a fact was discovered but cannot be treated as evidence.

**Document.** A common kind of source. Source is broader than document and can include recordings, records, photographs, reports, transcripts, statements, and similar captured material.

**Authority.** Reusable legal material, such as case law, legislation, regulations, rules, or treatises; an authority is not a case-specific source.

**Fact.** A discrete factual assertion about what happened, did not happen, existed, or was communicated in the real world.

**Provenance.** Where a fact, position, or source-linked assertion was learned from.

**Evidence.** Non-privileged material linked to a fact because it supports or undermines that fact.

**Proof.** The conclusion that a fact is established for litigation purposes; proof can rest on evidence, an admission, an agreed fact, or another accepted proof path.

**Position.** A party's stance on a fact.

**Claim Position.** A position where a party asserts that a fact is true.

**Admit.** A position where a party concedes that a fact is true.

**Deny.** A position where a party disputes a fact.

**Silent.** A position where a party does not take a substantive stance on a fact.

**No Knowledge.** Pleading language that ordinarily maps to Silent, with the original wording preserved as context.

**Qualified Admission.** An admission with limiting or reserving language preserved verbatim.

**Fact Posture.** The derived state of a fact based on current positions, such as agreed, claimed, not denied, admitted, disputed, or unclaimed.

**Issue.** A material question to resolve in a matter.

**Factual Issue.** A question of fact; a question about what happened or what can be established from one or more facts.

**Legal Issue.** A question of law; a matter-specific question about the governing rule, test, element, doctrine, defence, remedy, or authority.

**Mixed Issue.** A question of mixed fact and law; a question about whether facts satisfy legal criteria.

**Research Question.** A workflow artifact derived from a legal issue and phrased for legal research.

**Westlaw Query.** A research question optimized for Westlaw AI Deep Research; it is not itself the legal issue.

**Legal Concept.** A named body of law with its own criteria and authorities.

**Cause of Action Concept.** A legal concept that defines a claim type in general law, such as negligence or breach of contract.

**Asserted Cause of Action.** A matter-specific assertion that one party has a cause of action against another party using a cause of action concept.

**Legal Criterion.** A requirement, element, or factor belonging to a legal concept.

**Element.** A mandatory legal criterion that must be satisfied.

**Factor.** A legal criterion that is weighed rather than strictly required.

**Listed.** Marked as listed for disclosure in the matter record.

**Producible.** Eligible or required to be disclosed or produced.

**Admissible.** Eligible to be used before the court as evidence.

**Privileged.** Protected from disclosure or use because of privilege.

**Verified.** Checked for extraction or classification quality; verified does not mean true, proven, admitted, or accepted by the court.

**Source Citation.** A computed reference to case-specific material, usually a source path plus a pinpoint locator.

**Legal Citation.** A legal reference for an authority, such as a reported case citation or statutory citation.

## Synonyms

Use these synonym pairs consistently:

| Canonical term | Synonym |
|---|---|
| Legal Issue | Question of Law |
| Factual Issue | Question of Fact |
| Mixed Issue | Question of Mixed Fact and Law |
| Source Citation | Case-data citation |
| Legal Citation | Authority citation |

## Usage Notes

- Do not use Claim as shorthand for Cause of Action. Use Claim Position for factual assertions and Asserted Cause of Action for matter-specific claims.
- Do not use Legal Theory as a canonical term. Prefer Legal Concept, Legal Criterion, Asserted Cause of Action, Legal Issue, or law application.
- Unrecorded or merely anticipated viva voce evidence is not a Source until captured in a statement, transcript, memo, will-say, or similar record.
- Status is a lifecycle word. Use Fact Posture for the derived state of a fact.
