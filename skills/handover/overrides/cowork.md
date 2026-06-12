---
description: >
  Resume queued work from a prior session, or write a handover file at the end of
  the current session so the next session can pick up. Use whenever the user says
  "handover", "resume handover", "process handover", "create a handover",
  "handover for next session", "pick up where I left off", "what was I working
  on?", or opens a new session clearly expecting prior work to be resumed.
  Auto-detects mode from conversation state: empty conversation enters Process;
  conversation with progress enters Create. Handovers live in the project
  workspace under AI/handovers/ (project-local). v1 scope:
  Process, Create, and Repair modes only -- no chain batching, no auto-commit.
---

# Cowork Override

**IMPORTANT: When running in Cowork, ignore the canonical handover instructions above and follow
the Cowork-specific handover workflow below.**

# Handover

Context-aware handover management for Cowork. Either resume work from a queued
handover or summarize the current conversation into one for the next session.

## What is a handover

A handover is a small YAML+Markdown file that captures *just enough* for a
future session to pick up a task: what was being done, what files are
involved, and what the concrete next steps are. Handovers live per-project:

```
{workspace}/
  AI/
    handovers/
      queued/     <- new handovers waiting to be picked up
      WIP/        <- the one currently being worked on (parallel-session safety)
      completed/  <- finished handovers
```

Create the folders on demand if they don't exist.

## Finding the workspace root

The handover root is always:

```
{workspace}\AI\handovers\
```

where `{workspace}` is the user's connected Cowork project folder — NOT
Codex's internal outputs directory, NOT the Coclerk repo, and NOT any shell
working directory.

**How to determine `{workspace}`:**

1. The Cowork session context (system prompt) always lists the user's connected
   workspace folder(s). Use that path directly.
2. If multiple workspaces are mounted, prefer the one that already contains
   `AI\handovers\`. Use Glob to check:
   `**/handovers/queued/**` with `path` set to the candidate workspace.
3. If no workspace has that subfolder yet (Create mode only), use the primary
   workspace (the one most relevant to the current task, or first listed) and
   create the folder structure on demand.
4. Never guess or derive the workspace path from the shell `cwd`, Codex's
   outputs folder, or any installed plugin path — those are the wrong locations.

The subfolder structure `AI\handovers\` is consistent across
machines because the workspace syncs via OneDrive. Only the user path prefix
(e.g. `C:\Users\Brahm\...`) varies by computer.

> **Glob anti-pattern — do not use literal subdirectory prefixes.**
> The Cowork Glob tool cannot resolve patterns like `AI/handovers/queued/**`
> from a parent directory. Always lead with `**` so the glob engine traverses
> into subfolders: use `**/handovers/queued/**`, not `AI/handovers/queued/**`.
> Alternatively, set the Glob `path` parameter directly to the target folder
> and use a simple pattern like `*.md`.

## File format

```yaml
---
title: <one-line intent>          # required
created: 2026-04-18T14:30         # required
write_targets:                    # required; use [] if none
  - path/to/file.md
read_only_targets:                # optional; omit or [] if none
  - path/to/reference.md
blocked_by:                       # optional; names another queued handover
---

## Intent
<one paragraph: what was the user doing, and why>

## Next steps
1. <concrete step>
2. <concrete step>
```

Filename convention: `NNN_kebab-case-title.md`, where `NNN` is a
zero-padded sequence number (`001`, `002`, ...). For chains, append a letter
suffix (`005A`, `005B`, `005C`) — letters within the same number run in letter
order and are typically `blocked_by` each other.

## Mode detection

Look at the conversation state *before* deciding what to do:

| Conversation state                                    | Mode    |
| ----------------------------------------------------- | ------- |
| Empty, or only the user's "handover" trigger message  | Process |
| The user and you have made real progress on a task    | Create  |

"Real progress" means: you've read files, written files, run tools, or had a
meaningful back-and-forth about an ongoing task. A stray `hello` isn't
progress; a debugging session is.

Queue contents do not affect mode selection. A file sitting in `queued/` is
not a signal to enter Process — only an empty/near-empty conversation is. If
real progress was made, enter Create even when queued handovers exist; the
new handover joins the queue behind them.

If the user passes an explicit arg (`handover create`, `handover process`),
that arg overrides detection. Arg forms:

- `handover` or `handover process` — Process mode
- `handover create` — Create mode (force, even from empty conversation)
- `handover chat` — Create mode but output to chat only, skip file write
- `handover file` — Create mode but write file only, skip chat output

If you need to repair a malformed file you encountered during Process, that's
a sub-path of Process — handle it inline, don't make the user re-invoke.

## Process mode

Resume work from a queued handover.

1. Determine `{workspace}` using the "Finding the workspace root" section
   above. The handover root is `{workspace}\AI\handovers\`.
   Look in `{handover_root}\queued\`. If it doesn't exist **or contains no
   handover files**, tell the user there's nothing queued and stop — do not
   create the folder or any file.
2. If `{handover_root}\WIP\` already has a file, that's a crashed prior
   session. Offer to resume that one first rather than starting a new queued
   handover. Don't silently move things around — ask.
3. Pick the handover to work on. A file is **eligible** if its `blocked_by`
   field is absent, empty, or names a file that already exists in
   `completed/`. Then, among eligible files:
   a. Take the lowest number. An eligible 001 beats a blocked 002 — a higher
      unblocked number never jumps ahead of a lower one that's ready.
   b. Letter suffixes within the same number (e.g., `005A, 005B`) go in
      letter order — A before B before C.
4. Move the chosen file from `queued/` to `WIP/`. Do this **before reading
   or executing its contents** — the move is the lock, so claim first, then
   open. The move signals to any parallel session that this handover is
   claimed.
5. Read the handover. Parse the frontmatter. If parsing fails, enter Repair
   mode (see below) and then continue.
6. Execute the "Next steps" in order. Treat the handover as your task list.
7. When all next steps are done, move the file from `WIP/` to `completed/`.
   Announce completion and the path to the archived file. Do not
   automatically start another handover — one handover per session.

### Repair mode (inline sub-path of Process)

Triggered when a file in `WIP/` has malformed frontmatter (unparseable YAML,
missing required fields, mangled delimiters).

1. Read the raw file.
2. Identify what's broken. Common failures: missing `---` delimiters,
   unquoted colons in values, tab-indented lists, missing `title`.
3. Reconstruct the frontmatter conservatively — preserve all user content,
   only fix syntax. If a field is genuinely missing and not inferable, leave
   it out rather than inventing a value. The required field is `title`; if
   it's missing, infer from the first heading or the filename.
4. Write the repaired file back to `WIP/`.
5. Tell the user what you repaired, briefly — announce before resuming so
   they can catch a bad repair before you act on it.
6. Re-read the repaired file (don't execute against stale in-memory content
   from before the fix), then continue Process mode from step 6.

## Create mode

Summarize the current conversation into a new handover file.

1. Scan the conversation for:
   - **Title**: one-line intent of what the user was working on.
   - **Intent paragraph**: the "why" — context a future session won't have.
   - **Write targets**: absolute paths of files that were modified or
     that the next session will need to modify.
   - **Read-only targets**: absolute paths of files the next session should
     read for context but won't edit.
   - **Next steps**: concrete, ordered, actionable items. Each step should
     name specific files or commands where possible. Avoid vague items like
     "continue working on X".
2. Determine `{workspace}` using the "Finding the workspace root" section
   above. The handover root is `{workspace}\AI\handovers\`.
   Determine the filename:
   - List existing files in `{handover_root}\queued\` and `{handover_root}\completed\`.
   - Take the highest numeric prefix seen, add 1, zero-pad to 3 digits.
   - Slugify the title into kebab-case for the rest of the filename.
   - Example: last file was `007_foo.md`, new file is `008_fix-parser-bug.md`.
3. Write the file to `{handover_root}\queued\`.
4. Announce the path and show the user the handover contents.

### Arg variants

- `handover create` — full default: write file AND show in chat.
- `handover file` — write file only, suppress chat output.
- `handover chat` — show in chat only, skip file write. Useful when the user
  wants to review before committing.

### When progress is thin

If Create mode is triggered on a conversation with very little real progress
(Process would have been the better mode but user forced Create), produce a
minimal handover and tell the user it's lightweight. Don't refuse.

## Chain dependencies (limited v1 support)

v1 supports `blocked_by` in frontmatter for **ordering**, but does not do
multi-handover batch processing. The practical effect:

- Process mode respects `blocked_by` when picking the next file.
- Create mode can write a handover with `blocked_by` pointing at another
  queued file — useful when splitting a task into stages.
- If the user asks for "chain mode" or "process all queued handovers",
  explain that v1 handles one handover per session and suggest they invoke
  `handover` in successive sessions, or note that chain mode is a planned
  future addition.

## Principles

- **One handover per session.** Process picks one and stops after it. The
  user drives the next one.
- **WIP before work.** Always move the file to `WIP/` before executing. The
  move is the lock.
- **Completed is archival.** Move to `completed/` after work succeeds. Don't
  leave finished work in `WIP/` — a crashed future session would try to
  resume it.
- **No deletion.** Handover files move through queued -> WIP -> completed.
  They don't get deleted by the skill.
- **The workspace is the project.** All handover paths resolve from the
  user's connected Cowork workspace folder, under `AI\handovers\`.
  The workspace is identified from the Cowork session context, not from any
  shell working directory or Codex's internal outputs folder. If multiple
  workspaces are mounted, the skill picks the one that contains the handover
  folder (or the primary workspace for new handovers in Create mode).

## What this skill does NOT do

- Does not batch-process multiple handovers (no chain mode in v1).
- Does not auto-commit changes after completing a handover.
- Does not spawn subagents. Work happens in the main session.
- Does not enforce any particular handover file count or cleanup policy —
  `completed/` grows unbounded until the user prunes it.
