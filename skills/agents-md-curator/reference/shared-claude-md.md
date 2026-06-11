# Future: Shared AGENTS.md and Popularity Dimension

## Status: Deferred

This document describes the planned third dimension (popularity) for managing the shared project AGENTS.md (`./AGENTS.md`). Implementation is deferred because testing requires multiple team members contributing relevance data.

## Concept

The current two-tier system (global + project local) uses two scoring dimensions:
- **Relevance** -- is this line useful for current work?
- **Generality** -- is this line useful across repos?

A third dimension, **popularity**, would determine whether a line belongs in the shared AGENTS.md vs the local CLAUDE.local.md:
- Lines relevant to multiple team members working on different areas (frontend, backend) belong in shared
- Lines relevant to only one developer's workflow belong in local

## Design Sketch

### New data needed

The `relevance_events` table would need a `user_id` or `author` field to track which team member's work triggered the relevance event.

### Promotion logic

- Lines relevant to 2+ team members --> shared AGENTS.md (`./AGENTS.md`)
- Lines relevant to 1 team member --> local CLAUDE.local.md
- The threshold adjusts based on the shared AGENTS.md's 200-unit budget (same competitive model)

### Challenges

- Requires each team member to run `/agents-md-curator` independently, contributing to the same database
- Database location would need to be accessible to all team members (possibly in-repo rather than in `~/.claude/`)
- Git conflicts on `./AGENTS.md` if multiple members' runs try to rewrite it
- Need a merge strategy or single-writer model for the shared file

## Prerequisites Before Implementation

- Core skill working with 2+ team members using it daily
- Shared database access strategy decided (in-repo SQLite? remote DB?)
- Git conflict resolution strategy for shared AGENTS.md writes
