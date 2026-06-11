---
name: glimpse
description: Use when visual verification would help - captures Windows application windows as PNG screenshots that Claude Code can read. Triggers proactively for UI debugging, CI output, build results, error dialogs, browser previews.
---

# Glimpse - Window Screenshot Tool

Capture what's on the user's screen so you can see it. No user permission needed per capture.

## Usage

Go straight to `capture` — if the title doesn't match, the error lists available windows.

```bash
python "$HOME/.claude/skills/glimpse/src/glimpse.py" capture "window title"
```

Case-insensitive substring match. Prints the saved PNG path. Read it with your Read tool.

### Options

- `--downscale <max_width>` — resize proportionally so width does not exceed the given value

### Other commands

| Command | Purpose |
|---------|---------|
| `windows` | List visible windows as compact JSON (debug/fallback) |
| `status` | Show screenshot count and last capture time |
| `clean` | Delete oldest screenshots beyond the 50-file limit |

## Dependencies

Requires `pywin32` and `Pillow`. If exit code is 2, ask user to run `pip install pywin32 Pillow`.
