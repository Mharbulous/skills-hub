#!/usr/bin/env python3
"""
Send a cross-agent message.

Usage: python send_message.py <thread_file> <to_agent> <subject> <body>

Example:
  python send_message.py storytree-migration.ndjson Sync "Update complete" "The migration is done."
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

CROSS_AGENT_DIR = Path(r"C:\Users\Brahm\Git\.cross-agent")
THREADS_DIR = CROSS_AGENT_DIR / "threads"

# Known agent name mappings (repo_name -> agent_name)
AGENT_NAMES = {
    "StoryTree": "Maple",
    "SyncoPaid": "Sync",
}


def get_agent_name() -> str:
    """Derive preferred agent name from current working directory."""
    cwd = Path.cwd()
    repo_name = cwd.name
    return AGENT_NAMES.get(repo_name, repo_name)


def get_next_id(lines: list) -> int:
    """Find the highest message ID and return next one."""
    max_id = 0
    for line in lines[1:]:  # Skip header
        try:
            msg = json.loads(line.strip())
            msg_id = msg.get("id", 0)
            if isinstance(msg_id, int) and msg_id > max_id:
                max_id = msg_id
        except json.JSONDecodeError:
            continue
    return max_id + 1


def send_message(thread_file: Path, to_agent: str, subject: str, body: str):
    """Send a message to a thread."""
    from_agent = get_agent_name()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read existing file
    with open(thread_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        print(f"Error: Thread file is empty: {thread_file}", file=sys.stderr)
        sys.exit(1)

    # Get next message ID
    next_id = get_next_id(lines)

    # Create new message
    message = {
        "id": next_id,
        "timestamp": timestamp,
        "from": from_agent,
        "to": to_agent,
        "subject": subject,
        "body": body.replace("\n", "\\n"),  # Escape newlines
        "status": "unread"
    }

    new_msg_line = json.dumps(message) + "\n"

    # Insert message after header (line 0)
    header = lines[0]
    existing_messages = lines[1:]

    with open(thread_file, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write(new_msg_line)
        f.writelines(existing_messages)

    print(f"Message sent successfully!")
    print(f"  From: {from_agent}")
    print(f"  To: {to_agent}")
    print(f"  Subject: {subject}")
    print(f"  Thread: {thread_file}")
    print(f"  ID: {next_id}")


def main():
    if len(sys.argv) < 5:
        print("Usage: python send_message.py <thread_file> <to_agent> <subject> <body>")
        print()
        print("Arguments:")
        print("  thread_file  - Name of .ndjson file (with or without path)")
        print("  to_agent     - Recipient agent name (e.g., 'Sync', 'Maple')")
        print("  subject      - Message subject")
        print("  body         - Message body")
        sys.exit(1)

    thread_file = sys.argv[1]
    to_agent = sys.argv[2]
    subject = sys.argv[3]
    body = sys.argv[4]

    # Resolve thread file path
    thread_path = Path(thread_file)
    if not thread_path.is_absolute():
        # Check if it's just a filename
        if not thread_path.exists():
            thread_path = THREADS_DIR / thread_file

    if not thread_path.exists():
        print(f"Error: Thread file not found: {thread_path}", file=sys.stderr)
        sys.exit(1)

    send_message(thread_path, to_agent, subject, body)


if __name__ == "__main__":
    main()
