# JavaScript / TypeScript / Vue Reference

Language-specific patterns for the fallback-remover skill.

## File Types

`.js`, `.ts`, `.jsx`, `.tsx`, `.vue`, `.svelte`

## Source Directories

Infer from project structure: `src/`, `lib/`, `app/`, `packages/`. Exclude `node_modules/`, test files, build output, `.gitignore` entries.

## Severity Tiers

Classify each finding under its **highest** matching tier only (no duplicates).

### CRITICAL — Console log + return fallback value

Catch blocks that log an error AND return a default value (`null`, `[]`, `false`, `0`, `''`, `""`, `{}`). The caller cannot distinguish a real result from a masked failure.

### HIGH — Fire-and-forget with only console log

`.catch()` or catch blocks that only call `console.error`/`console.warn` without rethrowing, setting user-visible error state, or being documented as intentionally fire-and-forget.

### MEDIUM — Empty catch blocks

Catch blocks with no body, only comments, or `.catch(() => {})` without a documenting comment explaining why the error is safe to ignore.

## False Positive Rules

**EXCLUDE these patterns:**

1. **Documented fire-and-forget** — catch blocks where an adjacent comment (within 2 lines) explicitly explains why the error is safe to ignore
2. **Pre-load/pre-render optimizations** — catch blocks in preloading code where failure only means slower UX, AND the comment documents this
3. **Cleanup/teardown** — catch blocks in cleanup code (deleting temp files, closing connections) where failure is non-critical AND documented
4. **Catch-and-set-error-state** — catch blocks that set user-visible error state in addition to logging. These ARE surfacing the error. Examples:
   - `error.value = '...'` (Vue 3 Composition API)
   - `setState({error})` (React)
   - `setError(...)`, `snackbar.show(...)`
   - `$emit('error', ...)` (Vue)
   - Pinia store error state mutations

**When in doubt, INCLUDE the finding.**

## Fix Patterns

**CRITICAL — console + return fallback:**
```js
// BEFORE
catch (err) { console.error('Failed:', err); return []; }
// AFTER
catch (err) { throw err; }
// or if error ref in scope:
catch (err) { error.value = 'Failed to load'; throw err; }
```

**HIGH — fire-and-forget with console only:**
```js
// BEFORE
.catch(err => { console.error('Failed:', err); })
// AFTER — if failure matters, remove .catch() or set error state
// AFTER — if truly fire-and-forget, document WHY:
.catch(() => {}) // Best-effort: [reason]
```

**MEDIUM — empty/undocumented catch:**
```js
// BEFORE
.catch(() => {})
// AFTER
.catch(() => {}) // Best-effort: [reason failure is non-critical]
```

## Test Runner Detection

Check `package.json` for: `vitest`, `jest`, `mocha`. Run tests after fixing to verify no regressions.
