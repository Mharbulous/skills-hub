# Three-Layer Agent Architecture

## Overview

| Artifact | Layer | Concerns |
|----------|-------|----------|
| Slash command | **Orchestration** | Context extraction, interface contract (input shape + handshake), agent orchestration (parallel/series), shared context cache, result routing (success/escalation/error) |
| Custom agent | **Isolation** | Execution boundary (isolated context fork), model pin, tool restrictions, escalation protocol, MCP isolation, skill selection |
| Custom skill | **Operation** | Core instructions (SKILL.md -- always loaded), progressive disclosure (references/ -- on demand), executable references (scripts/ -- invoked, never read), skill memory (memory/ -- persistent state), personas + behavior, output contract (result shapes + semantics) |

## Rationale

### Context only where needed

Tokens cost money and superflous tokens degrade performance.  

### Why three layers?

Workflows generally have three distiguishable context layers:  (1) The messy body of all available information; (2) the isolation layer admits necessary tokens and excludes superflous tokens; (3) the operation layer of information relevant to the task at hand.

The orchestration layer has access to the messy body of availablle information, and identifes: (1) what tasks need to done; (2) what information is need to do those tasks; and (3) what tools and skills those tasks require. 

The isolation layer creates an isolated context for tools, instructions and information; admitting what is necessary and filtering out what is superflous. Isolation layers also make parallel and background inference possible.

The operation layer is where intelligence is most valuable. The orchestration layer and isolation layer exist so that the operation layer can be at it's most intelligent by minimizing available context when working on core tasks. 

### Result ownership splits cleanly

The skill defines result semantics (what "success", "escalation", and "error" mean and what data they carry). The agent relays results without transformation. The orchestration layer decides what to *do* with each resulting shape (report to user, escalate, retry, progress to next step). This prevents contention between the agent and skill, and ensures that the layer with the most task-specific knowledge owns result reporting.

### Two result delivery modes

The orchestration layer's contract specifies how results should be delivered:

1. **Passthrough.** The operation layer returns structured data back through the agent and orchestration layer, which formats it for the user. Use when the result is a status, summary, or decision that the user needs to see.
2. **Direct write.** The operation layer writes or modifies files directly in the repo. The return path carries only a lightweight confirmation (e.g., status + file paths affected), not the full content. Use when the result *is* the file change itself — passing large diffs or generated content back through the layers would bloat the context budget without adding value.

The orchestration layer chooses the delivery mode per task. The skill's output contract reflects this: a direct-write contract specifies what files to produce and what confirmation shape to return, while a passthrough contract specifies the full result shape.

### Execution guards — preventing inline bypass

When the system loads a SKILL.md into the main model's context (which happens automatically on `/command` invocation), the main model can read the operation-layer workflow and execute it directly — bypassing the agent spawn entirely. Both layers must carry guards to prevent this:

**Orchestration guard** (`commands/<name>.md`) — place at the top of the agent-spawn section:
> **CRITICAL**: You MUST spawn an Agent to perform this workflow. Do NOT execute the skill inline in the main context, even if SKILL.md content is already loaded. Spawn the agent first — always.

**Operation guard** (`skills/<name>/SKILL.md`) — place immediately after the `# Title` heading:
> **AGENT-ONLY GUARD**: If you are reading this as the main model (not a spawned agent), do NOT execute the workflow below. Return to the orchestration layer and spawn an agent first.

The two guards are bidirectional: the orchestration guard instructs the main model to spawn; the operation guard catches the case where skill content loads before the orchestration instruction fires. Both are required.

### Foreground vs background spawn

The orchestration layer specifies spawn mode in its Agent tool call.

**Default: background.** Use when the operation is self-contained and the conversation can continue before the result arrives — commits, file writes, linting, long-running analysis. The user is not blocked.

**Use foreground only** when the orchestration layer needs the agent's result before it can proceed — e.g., a multi-step workflow where step 2's inputs depend on step 1's output, or when the result must be routed to the user before the session ends.

In the orchestration template, mark the spawn mode explicitly:
- `run_in_background: true` — background (default for self-contained operations)
- `run_in_background: false` (or omit) — foreground (only when result is needed to continue)

### Three skill subfolder categories serve different purposes

Skills typically use three types of conditionally relevant information that is best disclosed progressively:
1. **References.**  Conditional read-only knowledge that enters context only when triggered (submodule handling, complex scenarios). 
2. **Scripts.** Executable utilities that run deterministic algorithims without using valuable context (validators, tools). 
3. **Memory.** A method for persisting output (learned patterns, accumulated data) so that it is available for future sessions..

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant O as Slash Command<br/>Orchestration
    participant A as Custom Agent<br/>Isolation
    participant S as Skill (SKILL.md)<br/>Operation
    participant F as Repo Files
    participant R as references/<br/>On Demand
    participant M as memory/<br/>Persistent State
    participant X as scripts/<br/>Executable

    U->>O: /command [args]
    activate O
    Note over O: Extract relevant context<br/>from conversation history<br/>(files, commits, state)
    Note over O: Contract specifies<br/>delivery mode:<br/>passthrough or direct-write
    O->>A: Spawn agent (foreground or background)<br/>with extracted context + delivery mode
    deactivate O

    activate A
    Note over A: Isolated context fork<br/>Pinned model + restricted tools
    A->>S: Load SKILL.md via skills: directive
    activate S
    Note over S: Determine operating mode<br/>from context + args

    alt condition requires reference knowledge
        S->>R: Read relevant reference doc
        R-->>S: Domain-specific procedures
    end

    alt condition requires deterministic processing
        S->>X: Execute script (bash, python, etc.)
        X-->>S: Structured output (JSON, etc.)
    end

    opt persistent state needed
        S->>M: Read/write skill memory
        M-->>S: Accumulated data or patterns
    end

    Note over S: Apply output contract

    alt direct-write delivery
        S->>F: Write/modify repo files directly
        Note over S: Return lightweight<br/>confirmation only
        S-->>A: {status, files_affected}
    else passthrough delivery
        S-->>A: {status, data} per contract
    end

    deactivate S
    Note over A: Passthrough — no<br/>transformation of results
    A-->>O: {status, ...}
    deactivate A

    activate O
    Note over O: Route on status field:<br/>success → report to user<br/>escalation → handle or re-prompt<br/>error → retry or surface
    O-->>U: Formatted result
    deactivate O
```

## Context Budget

```mermaid
graph LR
    subgraph "What enters context"
        C1["Orchestration:<br/>~20 lines<br/><i>prompt template</i>"]
        C2["Agent:<br/>~30 lines<br/><i>boundary + escalation</i>"]
        C3["Skill core:<br/>~100 lines<br/><i>workflows + contract</i>"]
        C4["References:<br/>0-90 lines<br/><i>only when triggered</i>"]
        C5["Memory:<br/>variable<br/><i>read/write on demand</i>"]
        C6["Scripts:<br/>0 lines<br/><i>executed, not read</i>"]
    end

    C1 --> C2 --> C3
    C3 -.-> C4
    C3 -.-> C5
    C3 -.-> C6

    classDef always fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef ondemand fill:#50C878,stroke:#3A9A5C,color:#fff
    classDef zero fill:#95A5A6,stroke:#7F8C8D,color:#fff

    class C1,C2,C3 always
    class C4,C5 ondemand
    class C6 zero
```
