# Classifying skill location

Decide which of the four layouts a target skill fits before choosing an edit
path. Do this even if the user just says "edit skill X" — the layout determines
the default and the consequences.

## Inputs

- Skill name (from the user, or inferred from the conversation).
- Optionally, a specific path the user pointed at.

## Paths to probe

### Installed locations (read-only on many systems)

The skills-plugin tree looks like this on Brahm's machine:

```
C:\Users\Brahm\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\
  <plugin-hash>\<session-hash>\skills\<skill-name>\SKILL.md
```

There are usually several hash combinations visible at once (older installs
that haven't been pruned). Treat *any* hit under `skills-plugin/` as "installed".
Multiple hits just mean multiple plugin generations — operate on the one with
the newest mtime, and tell the user if there are others.

### Repo source location

```
C:\Users\Brahm\Git\Coclerk\.agents\skills\<skill-name>\SKILL.md
```

### Wrapper source location (in-repo shadow of the installed wrapper)

```
C:\Users\Brahm\Git\Coclerk\.claude\wrappers\<skill-name>\SKILL.md
```

This is where the wrapper is authored before being packaged into the
`skills-plugin/` install. Its presence is strong evidence of layout 2.

## Detection procedure

1. Glob for `skills-plugin/**/skills/<name>/SKILL.md`. If multiple, pick the
   newest mtime.
2. Check if `Coclerk/.agents/skills/<name>/SKILL.md` exists.
3. Check if `Coclerk/.claude/wrappers/<name>/SKILL.md` exists.
4. If (1) hit, read the installed SKILL.md body (after the frontmatter). Is
   it a wrapper? A wrapper:
   - Is short (< 30 non-blank body lines)
   - Contains a literal filesystem path inside `Coclerk/.agents/skills/<name>/`
   - Contains instructions to read that path (look for the word "Source:" or
     "Read the full SKILL.md at")

Then classify:

| Installed hit? | Repo source? | Installed is wrapper? | Layout |
|----------------|-------------|----------------------|--------|
| Yes | No | n/a | 1. Plugin-only |
| Yes | Yes | Yes | 2. Split (wrapper + source) |
| No | Yes | n/a | 3. Repo-only |
| Yes | Yes | **No** | 4. Duplicate install (drift) |

## Ambiguity and failure modes

- **Installed copy exists but is short and has no path reference** → treat as
  plugin-only (layout 1), not a wrapper. Wrappers must name a concrete source
  path to count.
- **Two distinct repo sources, one in `.agents/skills/` and one in
  `wrappers/`** → this is normal. `wrappers/<name>/` holds the wrapper stub
  that was packaged into the install; `.agents/skills/<name>/` holds the real
  skill. Both are authored in the repo. The installed file was generated from
  the wrapper stub.
- **User names a skill that can't be found anywhere** → before assuming it
  doesn't exist, try the exact name, then fuzzy-match against the file tree.
  If still nothing, ask.
- **User gives an explicit path** → skip detection, use that path as the
  target, but still check the three other locations to see if a sibling copy
  exists (for the duplicate-install case).

## Third-party detection

After layout classification, decide whether the skill is custom or third-party:

- If `Coclerk/.agents/skills/<name>/` OR `Coclerk/.claude/wrappers/<name>/` exists →
  custom. Git covers it.
- Otherwise → third-party. Never normalize; preview-first always.

## What to report to the user

A one-line summary before choosing a flow:

> "That skill is installed as a wrapper pointing at `Coclerk/.agents/skills/
> skill-name/`. I'll edit the repo source directly (git's the backstop). Stop
> me if you'd rather review first."

Short, states the layout, states the default, offers the override. No menus
unless the user's intent is actually unclear.
