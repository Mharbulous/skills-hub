# Folder-Level (Subdirectory) CLAUDE.md Template

*Location: `<repo>/<subdir>/CLAUDE.md` — NOT loaded at startup; loads lazily when Claude reads or @-mentions a file in this subtree. More specific rules here override the root CLAUDE.md.*

Scope: only what's unique to this subtree. Do NOT repeat anything already in the root CLAUDE.md. Target: 30–80 lines; hard max 300.

Use cases: monorepo package, legacy folder with different conventions, bounded subsystem with its own stack or quirks.

---

# [Subsystem / Package Name]

## Intent
[1-2 sentences — what was the intended purpose of this folder when created]

## Function
[1-2 sentences - what purpose has been functionally implemented.]

## Local Overrides
*(Rules here override the root CLAUDE.md for files in this subtree only.)*
- [e.g. This folder uses JavaScript, not TypeScript — legacy code, do not convert.]
- [e.g. Use CommonJS (`require`/`module.exports`) here; the rest of the repo uses ESM.]

## Local Stack (if it differs)
- [e.g. Framework: React 18 + Vite (root is Next.js).]
- [e.g. Test runner: Jest (root uses Vitest).]

## Key Files
- `index.ts` - Entry point
- `[file]` - [role]
- `[file]` - [role]

## Local Commands
- [Only commands specific to this folder, e.g. `pnpm --filter frontend dev`]
- [e.g. `pnpm --filter frontend test`]

## Quirks & Warnings
- [Non-obvious gotchas local to this subtree, e.g. Don't import from `../shared/legacy/` — scheduled for removal.]
- [e.g. This package publishes to npm; version bumps must go through `pnpm changeset`.]

## References
- [Pointers to deeper docs, e.g. `@./README.md` or `@./docs/design.md`]
