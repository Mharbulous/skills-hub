# Skill Writing Guide

Reference for how to write effective skills. Read this during Phase 2 (drafting) and Phase 3 (improving).

## Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

## Progressive Disclosure

Skills use three levels of loading:

1. **Metadata** (name + description) — always in context (~100 words)
2. **SKILL.md body** — loaded when skill triggers (<500 lines ideal)
3. **Bundled resources** — loaded as needed (unlimited; scripts can execute without loading)

Key patterns:

- Keep SKILL.md under 500 lines. If approaching this limit, add hierarchy with clear pointers to reference files.
- Reference files clearly from SKILL.md with guidance on when to read them.
- For large reference files (>300 lines), include a table of contents.

### Domain organization

When a skill supports multiple domains/frameworks, organize by variant:

```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

Claude reads only the relevant reference file.

## Writing Patterns

Use the imperative form in instructions.

**Defining output formats:**

```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Including examples:**

```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

## Writing Style

Explain why things matter instead of relying on heavy-handed MUSTs. LLMs have good theory of mind — when they understand the reasoning, they go beyond rote instruction-following and make good judgment calls. If you find yourself writing ALWAYS/NEVER in all caps, that's a yellow flag. Try reframing as reasoning: explain why the thing matters so the model internalizes it rather than mechanically following a rule.

Make skills general rather than narrow to specific examples. Write a draft, then review with fresh eyes and improve.

## Principle of Lack of Surprise

Skills must not contain malware, exploit code, or anything that could compromise security. A skill's contents should not surprise the user in their intent if described. Don't create misleading skills or skills for unauthorized access or data exfiltration. Roleplay-style skills are fine.
