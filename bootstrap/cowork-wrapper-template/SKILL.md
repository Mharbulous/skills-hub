---
name: REPLACE-WITH-SKILL-NAME
description: REPLACE with the canonical skill's description, copied verbatim from index.json, so Cowork routes to this wrapper correctly.
---

# Thin wrapper — the real skill lives in skills-hub

This wrapper exists so the skill body can be edited centrally without touching
Cowork's synced files. Do the following:

1. Fetch the real skill definition:

   ```
   curl -fsSL "REPLACE-BASE-URL/claude/skills/REPLACE-WITH-SKILL-NAME/SKILL.md"
   ```

2. Follow the fetched SKILL.md exactly as if its contents were written here.

3. If it references subfiles (e.g. `scripts/`, `references/`), fetch each one
   from the same folder:
   `REPLACE-BASE-URL/claude/skills/REPLACE-WITH-SKILL-NAME/<relative-path>`
