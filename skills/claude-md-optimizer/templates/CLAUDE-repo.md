# Repo-Root CLAUDE.md Template

*Location: `<repo>/CLAUDE.md` — loaded at startup whenever Claude runs inside this repo.*

Scope: project-wide context every session needs. Target: 60–100 lines; hard max 300. Each line ~20 tokens.

---

# Project: [Name]

## Critical Rules
- **YOU MUST** [absolute requirement, e.g. run `pnpm test` before creating any PR]
- **IMPORTANT**: [high-priority guideline, e.g. never commit directly to `main`]
- **NEVER** [prohibited action, e.g. use `--foo` flag (causes memory leaks); use `--bar` instead]
- **ALWAYS** [consistent behavior, e.g. use TypeScript strict mode]

## Tech Stack
- Language: [e.g. TypeScript 5.x]
- Runtime/Framework: [e.g. Node 20, Next.js 14]
- Database: [e.g. Postgres 16 via Prisma]
- Test: [e.g. Vitest]

## Commands
- `pnpm dev` - Start dev server
- `pnpm test` - Run test suite
- `pnpm lint` - Lint (also runs via pre-commit hook)
- `pnpm typecheck` - Type-check without emitting
- `pnpm build` - Production build

## Project Structure
- `src/` - Application source
- `src/api/` - HTTP handlers
- `src/db/` - Schema and migrations
- `tests/` - Integration tests
- `docs/` - Deeper docs (reference on-demand)

## Code Conventions
*(Only conventions NOT enforced by linters/formatters — those belong in ESLint/Prettier + hooks.)*
- [e.g. Use ES modules (import/export), not CommonJS.]
- [e.g. Database access only through `src/db/client.ts`.]

## Project-Specific Quirks
- [Non-obvious warnings, e.g. `pnpm dev` requires `.env.local`; copy from `.env.example`.]
- [e.g. Migrations must be generated via `pnpm db:migrate:dev`, never edited by hand.]

## References (load on demand)
- Architecture overview: `@docs/architecture.md`
- Auth flow: see `docs/AUTH.md`
- API conventions: see `docs/API.md`

## Final Steps
**IMPORTANT**: After completing changes:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm test`
4. Verify the change works end-to-end for the affected feature.
