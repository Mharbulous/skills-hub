---
name: consult-expert
description: >
  Consults domain expert agents for cross-component architectural understanding —
  how multiple components wire together, what the data flow is, what would break
  if X changed, and what gotchas exist across a feature's surface area.
  Also invocable manually via /consult-expert <question>.

  Trigger this skill when: (1) planning or designing a change that spans multiple
  components or features and the architecture is not already clear from current
  context; (2) answering a question about cross-component wiring, data flow, or
  side effects that cannot be resolved by reading 1-3 known files; (3) debugging
  a problem whose location is unknown and likely spans multiple components.

  Skip this skill when the affected files are already known and the answer is
  obtainable by reading or grepping those files directly — try Grep, Read, or
  jcodemunch first. Single-file changes, known-location bug fixes, and questions
  about a specific function's behavior do not need an expert. If those direct
  lookups fail to produce an answer, then escalate here.
user_invocable: true
arguments: The question to route to an expert, optional when auto-triggered
---

# /consult-expert

Consult domain expert agents before planning or designing source code changes. Each expert maintains its own reference files and answers from validated source code knowledge.

## When This Triggers

**Automatically** — at the start of any planning or design session for source code changes, regardless of which directory the code lives in:
- Writing an implementation plan (`/writing-plans`, `/design-software`)
- Designing a new component, composable, or service
- Refactoring or restructuring code
- Adding navigation, configuration, or wiring that relates to a feature
- Debugging an issue where the bug's location is unknown and spans multiple components

**Automatically** — when the user asks questions that require understanding a feature's architecture or core business logic:
- "How does X work?" / "What happens when Y?" about a feature's internals
- "Why is X done this way?" about design decisions or patterns
- "What would break if I changed X?" about dependencies or side effects
- Questions about data flow, component relationships, or Firestore schema for a feature

**Automatically** — for impact analysis, cross-feature coordination, and context recovery:
- Impact analysis before changes: "What depends on this component/store/composable?" before renaming, moving, or changing signatures
- Cross-feature coordination: "Does feature X already handle this, or does feature Y need to?" when work spans multiple features
- Code review / PR review: understanding existing conventions and patterns before judging whether new code fits
- Context recovery: re-establishing understanding of a feature after many sessions away (e.g., resuming from a handover)
- Incident response: "A user reports X — what's the expected flow?" tracing expected vs actual behavior

**Manually** — `/consult-expert <question>` for ad-hoc questions.

## Expert Discovery

**No static registry.** Experts are discovered dynamically at runtime.

### Step 1: Scan

Glob for `*-expert.md` in two directories:
1. `.claude/agents/` — local experts (repo-specific)
2. `~/.claude/agents/` — global experts (technology/tool)

### Step 2: Build Roster

Read each discovered file's YAML frontmatter to extract `name` and `description`. Build a runtime roster of available experts.

If a file lacks valid agent frontmatter (name + description), skip it — not a consult-expert-style agent.

### Step 3: Route

Match the question/task context against expert descriptions (keywords, source paths, feature domain).

- **Single match** → spawn that agent with the Agent tool (`subagent_type` = the agent's `name` from frontmatter)
- **Multiple matches** → spawn each relevant expert in parallel with feature-specific questions
- **No match** → proceed to New Expert Creation Protocol

**Local precedence:** If a local and global expert share a name, use the local expert.

## Questions to Ask Each Expert

Before planning changes, ask the expert for the affected feature these questions (adapt as needed):

### Architecture Context (ask before any change)
- "What components, composables, and services exist in this feature? How are they wired together?"
- "What is the page layout and dependency graph?"

### Before Adding a New Component or Composable
- "What existing components/composables handle [similar concern]? Could I extend one instead of creating new?"
- "What provide/inject or store dependencies would a new component in this feature need?"

### Before Refactoring
- "What are the known gotchas and non-obvious patterns in this feature?"
- "What task flows pass through the code I'm about to change?"

### Before Modifying Firestore Interactions
- "What is the Firestore data model for this feature? What fields and collections are involved?"
- "What cross-feature queries depend on this data?"

### Before Debugging
- "What are the known gotchas for this feature?"
- "What is the expected task flow for [user action]?"

## Response Format

Prefix each expert's response with attribution:

```
**Answered by: upload-expert** (local)

## Q1: What components exist in the upload feature?
[expert's structured answer with source citations]
```

## New Expert Creation Protocol

When no expert in the roster covers the question's domain:

### Classify

Apply this heuristic:
- **Named technology** (language, framework, library, tool, standard, protocol) → **global** expert at `~/.claude/agents/`
- **Abstract concept** (meaning only concrete in the context of a specific codebase) → **local** expert at `.claude/agents/`

Examples:
| Expert | Classification | Why |
|--------|---------------|-----|
| `vue-expert` | Global | Framework |
| `firebase-expert` | Global | Platform/tool |
| `tanstack-expert` | Global | Library |
| `workbench-expert` | Local | Abstract — specific to this repo's AI Workbench |
| `upload-expert` | Local | Abstract — specific to this repo's upload pipeline |

### Name

`{domain}-expert` — consistent naming enables the `*-expert.md` glob pattern in discovery.

### Create from Template

Read the appropriate template from `~/.claude/skills/consult-expert/templates/`:
- Local → `local-expert-template.md`
- Global → `global-expert-template.md`

Create:
1. Agent definition file: `{location}/{name}-expert.md` (replacing template placeholders)
2. Empty references directory: `{location}/{name}-expert/references/`
3. Empty reference files per template specification

### Dispatch

Send the original question to the newly created expert. The expert populates its references as needed on first query.
