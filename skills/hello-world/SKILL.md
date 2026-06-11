---
name: hello-world
description: Example skill demonstrating the skills-hub structure — canonical body plus optional per-harness overrides. Use when asked to test that skills-hub skills are loading.
---

# Hello World

This is the **canonical** body, shared by every harness.

When invoked, reply with:

1. A one-line greeting naming which harness you are running in.
2. Confirmation that this skill was loaded from skills-hub.

To see how overrides work, compare `dist/claude/skills/hello-world/SKILL.md`
with `dist/codex/skills/hello-world/SKILL.md` after running
`python3 build/build.py` — the Codex variant has an extra section appended
from `overrides/codex.md`.
