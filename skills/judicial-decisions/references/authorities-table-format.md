# Authorities Cited Table Format

## Purpose

The Authorities Cited table provides a comprehensive reference of all legal authorities (cases, statutes, regulations, treaties) cited in the judicial decision, organized for easy reference.

## Table Structure

Use a three-column markdown table with the following headers:

| Authority | Principle/Proposition | Reference |
|-----------|----------------------|-----------|

### Column Definitions

**Authority:** Full citation of the case, statute, or other legal source
- Cases: Include style of cause, year, court, and citation (if available)
- Statutes: Include full title, jurisdiction, and section numbers
- Format consistently with the jurisdiction's citation style

**Principle/Proposition:** Brief statement of the legal principle for which the authority was cited
- Use clear, concise language
- Focus on the specific proposition, not the entire holding
- If cited for multiple principles, create separate rows or list them clearly

**Reference:** Location in the decision where the authority is cited
- Use paragraph numbers if available (e.g., "¶ 45")
- Use page numbers if paragraphs not numbered (e.g., "p. 12")
- If cited multiple times, list all references (e.g., "¶¶ 23, 45, 67")

## Organization

### Primary Organization by Type
Group authorities by type in this order:
1. **Cases** - Highest court to lowest, then chronologically
2. **Statutes** - Alphabetically by jurisdiction, then by title
3. **Regulations** - Alphabetically
4. **Secondary Sources** - Only if cited as authority
5. **International/Foreign** - Separately if numerous

### Alternative Organization by Topic
For complex decisions with distinct legal issues, consider organizing by topic/issue with subheadings.

## Formatting Guidelines

1. **Consistency:** Maintain consistent citation format throughout
2. **Completeness:** Include all authorities actually cited, not just those central to the holding
3. **Accuracy:** Verify citations and principles match the decision
4. **Brevity:** Keep principle descriptions concise (typically 1-2 sentences)
5. **Clarity:** Use plain language in principle descriptions where possible

## Example Table

### By Type (Recommended for most decisions)

| Authority | Principle/Proposition | Reference |
|-----------|----------------------|-----------|
| **Cases** | | |
| *Donoghue v. Stevenson*, [1932] AC 562 (HL) | Established duty of care in negligence; neighbour principle | ¶ 34 |
| *Mustapha v. Culligan of Canada Ltd.*, 2008 SCC 27 | Test for remoteness in psychiatric harm cases | ¶ 42 |
| *Clements v. Clements*, 2012 SCC 32 | "But for" test for causation in negligence | ¶¶ 48, 51 |
| *Smith v. Jones*, 2019 BCCA 123 | Contributory negligence and seatbelt use | ¶ 67 |
| **Statutes** | | |
| *Motor Vehicle Act*, RSBC 1996, c 318, s 127 | Duty to obey traffic control devices | ¶ 15 |
| *Negligence Act*, RSBC 1996, c 333, s 1 | Apportionment of liability | ¶ 72 |
| **Regulations** | | |
| *Rules of Court*, BC Reg 168/2009, Rule 14-1(10) | Authority to award costs | ¶ 89 |

### By Topic (Alternative for complex decisions)

| Authority | Principle/Proposition | Reference |
|-----------|----------------------|-----------|
| **Issue 1: Duty of Care** | | |
| *Donoghue v. Stevenson*, [1932] AC 562 (HL) | Neighbour principle; duty of care test | ¶ 34 |
| *Childs v. Desormeaux*, 2006 SCC 18 | Proximity analysis in duty of care | ¶ 36 |
| **Issue 2: Standard of Care** | | |
| *Ryan v. Victoria (City)*, [1999] 1 SCR 201 | Objective standard of reasonable person | ¶ 45 |
| **Issue 3: Causation** | | |
| *Clements v. Clements*, 2012 SCC 32 | "But for" test for factual causation | ¶¶ 48, 51 |

## Special Cases

### Authority Cited for Multiple Principles
If an authority is cited for different principles in different parts of the decision:

**Option 1:** Create separate rows for each distinct principle:
| Authority | Principle/Proposition | Reference |
|-----------|----------------------|-----------|
| *ABC v. XYZ*, 2020 SCC 1 | Test for duty of care | ¶ 23 |
| *ABC v. XYZ*, 2020 SCC 1 | Standard of review on appeal | ¶ 87 |

**Option 2:** Combine in one row with numbered points:
| Authority | Principle/Proposition | Reference |
|-----------|----------------------|-----------|
| *ABC v. XYZ*, 2020 SCC 1 | (1) Test for duty of care; (2) Standard of review on appeal | ¶¶ 23, 87 |

### Authority Distinguished or Rejected
Indicate when authority was considered but distinguished or rejected:

| Authority | Principle/Proposition | Reference |
|-----------|----------------------|-----------|
| *Smith v. Jones*, 2018 ONCA 45 | Contributory negligence in seatbelt cases [Distinguished] | ¶ 67 |
| *Brown v. Green*, 2015 ABQB 789 | Inevitable accident defence [Rejected] | ¶ 72 |

### Short-Form Citations
If the decision uses short-form citations (e.g., "*Smith*"), use the full citation in the table:
- Include the full style of cause and citation, not the short form
- This ensures the table is a complete standalone reference

## Tips for Efficiency

1. Extract authorities as you read through the decision
2. Use the decision's own citations when provided
3. Verify citation format if creating from scratch
4. Check for authorities mentioned in passing vs. those actually applied
5. Include dissenting opinions' authorities if relevant to the analysis
6. Consider using the template in `assets/authorities-template.md` as a starting point
