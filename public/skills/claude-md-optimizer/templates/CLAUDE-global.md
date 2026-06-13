# Global CLAUDE.md Template

*Location: `~/.claude/CLAUDE.md` — loaded at startup for every session, regardless of project.*

Scope: personal, cross-project preferences only. Do NOT put project-specific content here. Target size: 30–80 lines.

---

## Principles
- [Core working principles that apply everywhere, e.g.:]
- Surface failures; do not build fallbacks that hide errors from the developer.
- Fix root causes, not symptoms.

## Communication Preferences
- [Tone, verbosity, explanation level, e.g.:]
- Be terse. Skip trailing summaries when a diff speaks for itself.
- Ask before making non-reversible changes (force push, schema drops, rm -rf).

## Default Tooling
- [Preferred tools across all projects, e.g.:]
- Package manager: `pnpm` (not npm/yarn) unless a repo specifies otherwise.
- Editor: VS Code. Shell: bash on Windows (use Unix syntax, forward slashes).

## Git Etiquette
- [Personal git conventions, e.g.:]
- Use Conventional Commits.
- Never commit directly to `main`.
- Never skip hooks (`--no-verify`) without explicit approval.

## Personal Overrides (Optional)
- [@import personal prefs stored outside the global file:]
- `@~/.claude/personal.md`
