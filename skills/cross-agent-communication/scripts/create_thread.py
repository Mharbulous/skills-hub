#!/usr/bin/env python3
"""
Create a new cross-agent communication thread.

Usage: python create_thread.py <thread_id> <participants> <subject> [initial_message]

Example:
  python create_thread.py my-feature "Maple,Sync" "Feature coordination" "Let's sync on this feature"
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


def get_agent_names() -> tuple:
    """
    Get both agent name and repo name for backwards compatibility.
    Returns (agent_name, repo_name) tuple.
    """
    cwd = Path.cwd()
    repo_name = cwd.name
    agent_name = AGENT_NAMES.get(repo_name, repo_name)
    return (agent_name, repo_name)


def create_thread(thread_id: str, participants: list, subject: str, initial_message: str = None):
    """Create a new thread file."""
    agent_name, repo_name = get_agent_names()
    my_names = {agent_name, repo_name}  # Both names are valid for matching
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Ensure threads directory exists
    THREADS_DIR.mkdir(parents=True, exist_ok=True)

    thread_file = THREADS_DIR / f"{thread_id}.ndjson"

    if thread_file.exists():
        print(f"Error: Thread already exists: {thread_file}", file=sys.stderr)
        sys.exit(1)

    # Create header
    header = {
        "type": "header",
        "thread_id": thread_id,
        "created": timestamp,
        "participants": participants,
        "subject": subject
    }

    lines = [json.dumps(header) + "\n"]

    # Add initial message if provided
    if initial_message:
        # Determine recipient (first participant that isn't us)
        to_agent = "all"
        for p in participants:
            if p not in my_names:  # Check both agent name and repo name
                to_agent = p
                break

        message = {
            "id": 1,
            "timestamp": timestamp,
            "from": agent_name,  # Use preferred agent name
            "to": to_agent,
            "subject": subject,
            "body": initial_message.replace("\n", "\\n"),
            "status": "unread"
        }
        lines.append(json.dumps(message) + "\n")

    with open(thread_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Thread created successfully!")
    print(f"  File: {thread_file}")
    print(f"  Thread ID: {thread_id}")
    print(f"  Participants: {', '.join(participants)}")
    print(f"  Subject: {subject}")
    if initial_message:
        print(f"  Initial message sent to: {to_agent}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python create_thread.py <thread_id> <participants> <subject> [initial_message]")
        print()
        print("Arguments:")
        print("  thread_id       - Unique thread identifier (lowercase, hyphenated)")
        print("  participants    - Comma-separated agent names (e.g., 'Maple,Sync')")
        print("  subject         - Thread subject")
        print("  initial_message - Optional first message body")
        print()
        print("Example:")
        print('  python create_thread.py feature-sync "Maple,Sync" "Feature coordination"')
        sys.exit(1)

    thread_id = sys.argv[1]
    participants = [p.strip() for p in sys.argv[2].split(",")]
    subject = sys.argv[3]
    initial_message = sys.argv[4] if len(sys.argv) > 4 else None

    create_thread(thread_id, participants, subject, initial_message)


if __name__ == "__main__":
    main()
