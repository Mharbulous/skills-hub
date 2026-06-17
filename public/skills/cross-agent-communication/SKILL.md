---
name: cross-agent-communication
description: Use when you need to communicate with Claude Code agents running in other repositories. Enables asynchronous messaging via NDJSON threads and file sharing via dropbox at C:\Users\Brahm\Git\.cross-agent\. Check for messages, send messages, share files, and coordinate cross-repo work.
disable-model-invocation: true
---

# Cross-Agent Communication

Asynchronous messaging between Claude Code agents working in different repositories.

## Location

```
C:\Users\Brahm\Git\.cross-agent\
├── README.txt           # Full protocol documentation
├── threads/             # Active conversation threads (.ndjson files)
│   └── archived/        # Completed threads
└── dropbox/             # Shared file exchange
```

## Agent Names

| Repo       | Agent Name |
|------------|------------|
| StoryTree  | Maple      |
| SyncoPaid  | Sync       |

Your agent name = your repository directory name (or use assigned name above).

## Quick Reference

Treat the directory containing this `SKILL.md` as `SKILL_DIR` before running
helper scripts.

### Check for Messages

Read first 2-3 lines of `.ndjson` files in `threads/`:

```bash
python "$SKILL_DIR/scripts/check_messages.py"
```

Or manually read the thread file - line 1 is header, line 2 is newest message.

### Send a Message

Insert new message as line 2 (after header). Use the helper script:

```bash
python "$SKILL_DIR/scripts/send_message.py" <thread-file> <to-agent> <subject> <body>
```

Or manually edit the NDJSON file.

### Create New Thread

Create `threads/{thread-id}.ndjson` with header line, then first message:

```json
{"type":"header","thread_id":"my-thread","created":"2026-01-06T12:00:00Z","participants":["Maple","Sync"],"subject":"Thread subject"}
{"id":1,"timestamp":"2026-01-06T12:00:00Z","from":"Maple","to":"Sync","subject":"Hello","body":"First message","status":"unread"}
```

## Message Format

Each message is one JSON line:

```json
{
  "id": 1,
  "timestamp": "2026-01-06T12:00:00Z",
  "from": "Maple",
  "to": "Sync",
  "subject": "Brief subject",
  "body": "Message content (escape newlines as \\n)",
  "status": "unread"
}
```

**Status values:** `unread` → `read` → `acknowledged`

## Protocol Rules

1. **Newest first** - Messages ordered newest at top (line 2), oldest at bottom
2. **Efficient reads** - Only read first 2-3 lines to check for new messages
3. **Mark as read** - Update status field when you've read a message
4. **Escape newlines** - Body must be single line JSON (use `\n` for newlines)
5. **Increment IDs** - Each new message gets next integer ID

## Dropbox (File Sharing)

Location: `C:\Users\Brahm\Git\.cross-agent\dropbox\`

### Rules

1. **Date prefix required** - All files must start with `YYYY-MM-DD-` (deposit date)
2. **Max 3 dates** - Dropbox can only contain files from 3 different calendar dates
3. **Auto-cleanup** - When >3 dates exist, the oldest date's files are deleted

### Usage

```bash
# List files (runs cleanup automatically)
python "$SKILL_DIR/scripts/dropbox.py" list

# Deposit a file (adds date prefix automatically)
python "$SKILL_DIR/scripts/dropbox.py" deposit /path/to/file.txt

# Get full path to a file
python "$SKILL_DIR/scripts/dropbox.py" get filename.txt
```

Or manually copy files with proper naming: `2026-01-06-myfile.txt`

### Cleanup Responsibility

**Every agent interacting with dropbox must run cleanup first.** The helper scripts do this automatically. If manually accessing, check for >3 dates and delete all files from the oldest date.

## When to Use

- Coordinating work that spans multiple repositories
- Notifying another agent about changes that affect their repo
- Requesting information or action from another agent
- Handoff of cross-repo tasks
- Sharing files between agents (use dropbox)

## Full Protocol

For complete details, see: `C:\Users\Brahm\Git\.cross-agent\README.txt`
