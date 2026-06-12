# Custom skill architecture: wrapper + repo source

Reference for any session that's about to modify a custom skill for the
first time. This is the layout skill-updater normalizes *into* on first
edit. It is **not** a layout creation needs to produce up front — see "When
this rule kicks in" below.

## The rule

Once a custom skill (one Brahm authors, as opposed to third-party plugin
skills) is edited for the first time, it should live in two places:

1. **Source** — `C:\Users\Brahm\Git\Coclerk\.agents\skills\<name>\` — full
   skill directory: SKILL.md plus any `scripts/`, `references/`, `assets/`,
   `evals/`, etc. This is the authoritative copy. Git tracks it.
2. **Wrapper** — `C:\Users\Brahm\Git\Coclerk\.claude\wrappers\<name>\SKILL.md` — a
   tiny SKILL.md whose body just points at the repo source. Packaged into a
   `.skill` file and installed in the usual skills-plugin location. This is
   what the plugin manager sees and loads.

The installed wrapper is what the trigger engine reads for routing. The
actual instructions come from the repo source, loaded on demand via `Read`.

## When this rule kicks in

**First edit, not creation.** A freshly-created skill that's never been
modified has only one version, so there's nothing for git to rescue yet.
Some skills stay in that state forever — quick one-off tools the user
builds and never touches again. Forcing the wrapper layout at creation adds
ceremony with no payoff in those cases.

Version-control concerns appear at the moment of the second version —
i.e., the first edit. That's the trigger for skill-updater to migrate the
skill into the repo + wrapper split.

**Implication for skill-creator-improved:** it should NOT produce this
layout by default. Creating custom skills directly in the installed plugin
directory (or wherever is convenient) is fine. skill-updater handles the
migration when and if the skill is ever edited.

## Why

- **Git is the backstop.** Any edit to the repo source is `git diff` / `git
  restore`-able. No other persistence layer Brahm uses right now gives him
  that.
- **The installed wrapper is safe to overwrite.** Plugin updates can clobber
  it without losing the real skill content — the content lives in the repo,
  and the wrapper is regenerable from the wrapper stub in `Coclerk/.claude/wrappers/`.
- **Versioning is automatic.** `git log .agents/skills/<name>/` tells you
  exactly how the skill evolved, which was previously invisible inside the
  installed directory.

## Wrapper template

```markdown
---
name: <skill-name>
description: >
  <same description as the source SKILL.md — this is what drives triggering,
  not the source's frontmatter, so they must match>
---

# <Skill Display Name> (dev shell)

This is a development shell skill. Read the full skill instructions from the
source file before proceeding:

**Source:** `C:\Users\Brahm\Git\Coclerk\.agents\skills\<skill-name>\SKILL.md`

## Instructions

1. Use the `Read` tool to read the full SKILL.md at the path above
2. Follow all instructions in that file exactly
3. If the source file references other files in its directory (scripts,
   references, assets), read those from
   `C:\Users\Brahm\Git\Coclerk\.agents\skills\<skill-name>\` as needed
```

Model: `Coclerk/.claude/wrappers/ar-follow-up/SKILL.md`. Match that shape exactly.

## Why the description field matters

Trigger matching uses the *installed* SKILL.md's frontmatter. The source
SKILL.md's frontmatter is read after triggering and does not affect which
skill fires. If the descriptions drift, the user's trigger-language won't
match what they wrote in the source.

**Keep them in sync.** On any description or name change, edit both.

## Packaging

Package the wrapper stub into a `.skill`, not the full source:

```bash
python "C:\Users\Brahm\Git\Coclerk\.agents\skills\skill-creator-improved\scripts\package_skill.py" \
  "C:\Users\Brahm\Git\Coclerk\.claude\wrappers\<name>" \
  "C:\Users\Brahm\Git\Coclerk"
```

That produces `<name>.skill` in the Coclerk root. Installing it drops the
wrapper into the skills-plugin tree.

## What NOT to enforce at creation

skill-creator-improved does not need to produce the split layout. Creating
a skill directly in `skills-plugin/` (or wherever is easiest) is fine. Many
skills will stay there forever because they're never edited.

The wrapper layout is a *migration target*, not a creation template. When
the user returns to a custom skill for the first edit, skill-updater moves
it into the split layout at that point. This keeps creation light and
puts the layout cost where it has actual value.

## What this does NOT apply to

- **Third-party plugin skills** (anything that came in via a plugin Brahm
  didn't author). Those stay plugin-only. Preview-first edits only. No
  repo mirror.
- **Scratch experiments** that will never be committed. Fine to iterate on
  in a temp workspace. But if it becomes real, move it into the repo layout
  before you start relying on it.
