---
name: finalize
description: "Finalize an implementation plan for execution. Validates via plan gatekeeping, decomposes large files, and reviews for quality. Iterates until the plan passes all checks."
---

# Finalize

Prepare an implementation plan for successful execution through validation, decomposition, and quality review.

## Workflow

### 1. Plan Selection

Analyze files in the `planning\2. TODOs\` folder and ask the user to choose one.

### 2. Plan Gatekeeping

Validate the plan satisfies gatekeeping requirements using the plan-gatekeeper agent.

- If the plan fails gatekeeping, correct the issues and re-validate. Repeat until the plan passes.
- If the plan fails due to lack of documented internet research, perform the research and document it in the planning document.
- After documenting internet research, consider whether the plan should be updated to use any discovered patterns or best practices. If rejecting a discovered pattern, document only the search methodology and keywords — never describe rejected patterns or practices in the plan.

### 3. Code Decomposition

For any files over 300 lines of code, break them into smaller components using the code-decomposer agent.

If the code-decomposer was triggered:
- Identify the "key files" section of the plan
- Update it with:
  - New line counts for all original files after decomposition
  - Entries for new files created during decomposition
  - Any files that became architecturally significant during decomposition
- Ensure the updated plan accurately reflects the post-decomposition file structure

### 4. Quality Review

Assess the plan for best practices and adherence to fundamental principles of good software design using the plan-reviewer agent.

- If the plan reviewer declines to approve, update the plan to address the identified problems and resubmit. Repeat until approved.

## Context

The planning structure follows this hierarchy:
- `planning\2. TODOs\` contains implementation plans ready for finalization

Plan form requirements include:
- Clear problem statement
- Detailed implementation steps
- Architecture considerations
- Testing strategy
- Risk assessment
- Dependencies identification

When identifying key files for modification:
- Look for direct dependencies mentioned in the plan
- Consider related components that may be affected
- Identify test files that need updates
- Consider documentation that needs changes

For code decomposition (files >300 lines):
- Analyze the file structure and responsibilities
- Identify logical boundaries for splitting
- Propose single-responsibility components
- Consider dependency injection patterns
- Plan for maintaining backward compatibility
