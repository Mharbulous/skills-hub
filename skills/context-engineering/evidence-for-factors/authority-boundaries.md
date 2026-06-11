# Factor 3: Authority Boundaries (Structural Clarity)

## Evidence For

- **Principle of least privilege is mainstream.** AWS Well-Architected GenAI Lens, FINOS governance framework, 78% of practitioners identify AI agent access control as top concern.
- **Real incidents.** Amazon AI agent deleted production environment (6-hour outage, 6.3M orders). Replit agent deleted production database during solo founder's experiment.
- **Hard restrictions beat instructions.** Unit 42 (Palo Alto): hard tool controls are the only deterministic protection. AGENTIF benchmark: best models follow <30% of multi-constraint instructions.
- **Claude Code confirms the asymmetry.** Skills cannot restrict tools. Agents can specify allowlist (`tools:`) or denylist (`disallowedTools:`).

## Evidence Against

- **Cited incidents involve production data.** For a solo dev on a local git repo, worst case is `git reset`. Blast radius is environment-dependent.
- **Trust boundaries are partially theater for solo devs.** One person controls everything. OWASP/Red Hat zero-trust frameworks target multi-tenant systems.
- **Alternatives exist.** Rubrik Agent Rewind (per-action rollback), Anthropic Auto Mode (classifier-based per-call risk), git-native safety.
- **Approval fatigue.** Anthropic's "Lies-in-the-Loop" problem — users stop reading approval prompts. Their solution was Auto Mode, not agent isolation.

## Judge Synthesis

Hard tool restrictions are valuable, but for a solo developer the value is **structural clarity**, not security. A `tools: Read, Glob, Grep` allowlist is like marking a function `const` — communicates intent and prevents a category of mistakes. Two levels are sufficient: read-only agents and full-access skills. Zero weight when both approaches need write access.
