---
name: judicial-decisions
description: Use when analyzing uploaded court decisions or case law. Covers facts found, disputed facts, legal principles applied/rejected, authorities cited tables, and orders/costs.
---

# Judicial Decisions Analysis Skill

## Overview

This skill provides structured analysis of judicial decisions across seven distinct task types. When analyzing uploaded decisions, determine which tasks the user needs, then execute them following the guidelines below.

## Task Types

1. **Facts as Found:** Summarize factual findings made by the judge or trier of fact
2. **Alternative Facts Rejected:** Summarize disputed factual contentions that were rejected
3. **Legal Principles for Fact-Finding:** Identify evidentiary rules and standards applied to find facts
4. **Legal Principles Applied:** Summarize substantive legal rules, tests, and doctrines applied
5. **Legal Principles Rejected/Distinguished:** Identify legal arguments or precedents considered but not applied
6. **Authorities Cited Table:** Create structured table of all cited authorities with principles and references
7. **Order Pronounced:** State the court's disposition, including costs and any ancillary orders

## Workflow: Determining User Needs

### When Request is Ambiguous

If the user says something generic like "summarize this decision" or "analyze this case," present the 7 task types and ask which they need:

> "I can help analyze this judicial decision. Which aspects would you like me to focus on?
> 
> 1. Facts as found by the court
> 2. Disputed facts that were rejected
> 3. Legal principles applied to fact-finding (evidentiary standards)
> 4. Substantive legal principles applied (ratio decidendi)
> 5. Legal principles rejected or distinguished
> 6. Authorities cited (cases and statutes)
> 7. Orders pronounced (disposition and costs)
>
> Please let me know which tasks you'd like, or say 'all' for a comprehensive analysis."

### When Request is Specific

Map user requests to relevant tasks automatically:

| User Request Pattern | Relevant Tasks |
|---------------------|----------------|
| "Summarize the facts" | Task 1 |
| "What facts were disputed?" / "Contested facts" | Task 2 |
| "What's the ratio?" / "Legal principles" / "Holdings" | Task 4 |
| "What authorities are cited?" / "Cases cited" | Task 6 |
| "What was the order?" / "Disposition" | Task 7 |
| "Costs" / "Who pays costs?" | Task 7 (focus on costs portion) |
| "How did they find the facts?" / "Standard of proof" | Task 3 |
| "What cases were distinguished?" / "Rejected precedents" | Task 5 |
| "Full analysis" / "Complete summary" / "All aspects" | All tasks |

### Narrowed Requests

When user asks about a specific issue within the decision (e.g., "What does this case say about costs?" or "Summarize the negligence analysis"), focus the relevant tasks on that specific issue only.

## Executing Each Task

### Task 1: Facts as Found

**Objective:** Provide a clear narrative of the factual findings made by the court.

**Process:**
1. Identify the section(s) where the court makes factual findings
2. Extract facts the court determined to be true
3. Organize chronologically or by issue as appropriate
4. Distinguish background facts from disputed facts that were determined
5. Note any credibility findings or evidentiary determinations

**Output:** See `references/output-templates.md` for formatting examples.

### Task 2: Alternative Facts Rejected

**Objective:** Summarize factual contentions that were disputed but rejected by the court.

**Process:**
1. Identify where parties' versions of facts diverged
2. Extract the alternative factual contentions
3. Note which party advanced each contention
4. Explain why the court rejected each version (credibility, evidence, consistency)
5. Distinguish rejections based on credibility vs. legal grounds

**Output:** See `references/output-templates.md` for formatting examples.

### Task 3: Legal Principles Applied to Fact-Finding

**Objective:** Identify the evidentiary rules, burdens, and standards that governed fact-finding.

**Process:**
1. Identify the applicable burden of proof (balance of probabilities, beyond reasonable doubt, etc.)
2. Extract evidentiary principles applied (credibility assessment, weight of evidence, inferences)
3. Note any presumptions or procedural rules that affected fact-finding
4. Explain how these principles influenced the court's factual determinations

**Output:** See `references/output-templates.md` for formatting examples.

### Task 4: Legal Principles Applied

**Objective:** Summarize the substantive legal rules, tests, and doctrines applied to resolve legal issues (the ratio decidendi).

**Process:**
1. Identify the legal issue(s) the court addressed
2. Extract the legal test or standard applied to each issue
3. Note the source of each legal principle (case law, statute, regulation)
4. Explain how the court applied the law to the facts
5. Organize following the court's logical progression
6. Focus on holdings that constitute binding precedent

**Output:** See `references/output-templates.md` for formatting examples.

**Key Distinction:** This task focuses on substantive legal principles (negligence test, contract interpretation rules, statutory construction), not evidentiary principles (which are Task 3).

### Task 5: Legal Principles Rejected or Distinguished

**Objective:** Identify legal arguments, precedents, or principles that were considered but not applied.

**Process:**
1. Identify arguments advanced by parties that were rejected
2. Find precedents the court distinguished
3. Note legal principles explicitly rejected or found inapplicable
4. Explain the basis for rejection/distinction (factual differences, legal differences, overruled)
5. Identify which party relied on each rejected principle

**Output:** See `references/output-templates.md` for formatting examples.

### Task 6: Authorities Cited Table

**Objective:** Create a comprehensive, organized table of all legal authorities cited.

**Process:**
1. Read through the entire decision and extract all cited authorities
2. For each authority, identify: (a) full citation, (b) principle it was cited for, (c) location in decision
3. Organize authorities by type: cases, statutes, regulations, other
4. Within each type, organize by hierarchy and chronology
5. Use the template in `assets/authorities-template.md` as a starting point
6. Follow formatting guidelines in `references/authorities-table-format.md`

**Special considerations:**
- Mark distinguished or rejected authorities clearly
- If authority cited for multiple principles, create separate rows or list clearly
- Include dissenting opinions' authorities if relevant
- Use full citations, not short-form references

**Output:** Three-column table (Authority | Principle/Proposition | Reference). See `references/authorities-table-format.md` for detailed formatting guidance and examples.

### Task 7: Order Pronounced

**Objective:** State the court's disposition and all ancillary orders clearly.

**Process:**
1. Identify the main disposition (judgment for plaintiff/defendant, conviction/acquittal, appeal allowed/dismissed)
2. Extract any damages awarded or other monetary relief
3. Detail costs awards with specificity:
   - Amount or scale
   - Who pays whom
   - Any conditions or timelines
4. Note any injunctive relief, specific performance, or declaratory relief
5. Include any stays, timelines for compliance, or directions for further proceedings
6. Identify any conditions attached to orders

**Output:** Clear, comprehensive statement of all orders. See `references/output-templates.md` for formatting examples.

## Quality Guidelines

### Accuracy
- Quote key phrases when helpful for precision
- Use pinpoint citations (paragraph or page numbers) when referencing decision
- Verify legal principles are accurately stated
- Do not add interpretation beyond what the court stated

### Clarity
- Use clear, professional legal writing
- Maintain objectivity - report what the court found/held, not personal analysis
- Use precise legal terminology appropriate to the jurisdiction
- Break complex issues into digestible sections

### Completeness
- Cover all relevant aspects of each task requested
- Don't omit important details for brevity
- For authorities table, include all cited authorities, not just prominent ones
- For orders, include all components and conditions

### Organization
- Present information in logical order
- Use headings for multi-issue decisions
- Group related points together
- Follow the court's organizational structure when appropriate

## Multi-Task Responses

When user requests multiple tasks (or "all tasks"), structure the response with clear headings:

```markdown
# Analysis of [Case Name]

## 1. Facts as Found
[Task 1 content]

## 2. Disputed Facts Rejected
[Task 2 content]

## 3. Legal Principles Applied to Fact-Finding
[Task 3 content]

[Continue for all requested tasks]
```

## Working with References

- Consult `references/output-templates.md` for formatting examples for each task
- Consult `references/authorities-table-format.md` for detailed guidance on creating authorities tables
- Use `assets/authorities-template.md` as a starting point for Task 6

## Tips for Efficiency

- Read the decision's headnote or summary first if available
- Identify the decision's structure (facts, issues, analysis, conclusion)
- For Task 6 (authorities), extract citations during initial read-through
- Use the court's own language for legal tests and principles
- For lengthy decisions, work through systematically rather than trying to hold everything in memory
