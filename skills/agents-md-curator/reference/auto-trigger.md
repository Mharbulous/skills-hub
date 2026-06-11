# Future: Automatic Brainstorming Hook

## Status: Deferred

This document describes the planned integration between `/agents-md-curator predict` and the design-software skill. Implementation is deferred until the core skill is working and validated.

## Concept

At the end of a design-software session, the design-software skill produces a design document that identifies affected areas of the codebase (files, folders, components). This naturally provides the input needed for predictive mode.

## Planned Integration

The design-software skill would be modified to:

1. Extract the list of target files/folders from the completed design
2. Invoke `/agents-md-curator predict` with that file/folder list
3. The claude-curator skill would then promote relevant cold-storage lines into the project AGENTS.md, preparing the context for implementation

## Trigger Point

The hook would fire after the design-software skill writes the design document to `docs/plans/` and before it asks "Ready to set up for implementation?"

## Prerequisites Before Implementation

- Core `/agents-md-curator` skill is working and stable
- Database has accumulated meaningful relevance data through several daily cycle runs
- Predictive mode (`/agents-md-curator predict`) is tested and working independently
- The design-software skill's output format is stable enough to parse reliably
