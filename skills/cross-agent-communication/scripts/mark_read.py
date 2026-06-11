#!/usr/bin/env python3
"""
Mark a message as read or acknowledged.

Usage: python mark_read.py <thread_file> <message_id> [status]

Status can be 'read' (default) or 'acknowledged'.

Example:
  python mark_read.py storytree-migration.ndjson 5
  python mark_read.py storytree-migration.ndjson 5 acknowledged
"""

import json
import sys
from pathlib import Path

CROSS_AGENT_DIR = Path(r"C:\Users\Brahm\Git\.cross-agent")
THREADS_DIR = CROSS_AGENT_DIR / "threads"


def mark_read(thread_file: Path, message_id: int, status: str = "read"):
    """Mark a message as read or acknowledged."""
    with open(thread_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    new_lines = []

    for i, line in enumerate(lines):
        if i == 0:  # Header
            new_lines.append(line)
            continue

        try:
            msg = json.loads(line.strip())
            if msg.get("id") == message_id:
                msg["status"] = status
                updated = True
                new_lines.append(json.dumps(msg) + "\n")
            else:
                new_lines.append(line)
        except json.JSONDecodeError:
            new_lines.append(line)

    if not updated:
        print(f"Error: Message ID {message_id} not found in {thread_file}", file=sys.stderr)
        sys.exit(1)

    with open(thread_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Message {message_id} marked as '{status}'")


def main():
    if len(sys.argv) < 3:
        print("Usage: python mark_read.py <thread_file> <message_id> [status]")
        print()
        print("Arguments:")
        print("  thread_file  - Name of .ndjson file")
        print("  message_id   - Integer ID of the message")
        print("  status       - 'read' (default) or 'acknowledged'")
        sys.exit(1)

    thread_file = sys.argv[1]
    message_id = int(sys.argv[2])
    status = sys.argv[3] if len(sys.argv) > 3 else "read"

    if status not in ("read", "acknowledged"):
        print(f"Error: Invalid status '{status}'. Use 'read' or 'acknowledged'.", file=sys.stderr)
        sys.exit(1)

    # Resolve thread file path
    thread_path = Path(thread_file)
    if not thread_path.is_absolute():
        if not thread_path.exists():
            thread_path = THREADS_DIR / thread_file

    if not thread_path.exists():
        print(f"Error: Thread file not found: {thread_path}", file=sys.stderr)
        sys.exit(1)

    mark_read(thread_path, message_id, status)


if __name__ == "__main__":
    main()
