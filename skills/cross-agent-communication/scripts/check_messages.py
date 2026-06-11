#!/usr/bin/env python3
"""
Check for unread cross-agent messages.

Usage: python check_messages.py [agent_name]

If agent_name not provided, derives from current repo directory name.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

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
    Returns (agent_name, repo_name) tuple. Both should be checked in participants.
    """
    if len(sys.argv) > 1:
        name = sys.argv[1]
        return (name, name)

    # Try to derive from current working directory
    cwd = Path.cwd()
    repo_name = cwd.name
    agent_name = AGENT_NAMES.get(repo_name, repo_name)

    return (agent_name, repo_name)


def check_thread(thread_file: Path, agent_name: str, repo_name: str) -> list:
    """Check a thread file for unread messages addressed to agent."""
    unread = []
    my_names = {agent_name, repo_name}  # Both names are valid for matching

    try:
        with open(thread_file, 'r', encoding='utf-8') as f:
            # Line 1: Header
            header_line = f.readline().strip()
            if not header_line:
                return unread

            header = json.loads(header_line)
            participants = header.get("participants", [])

            # Check if we're a participant (using either name)
            if not any(name in participants for name in my_names):
                return unread

            thread_id = header.get("thread_id", thread_file.stem)

            # Read up to 5 recent messages
            for _ in range(5):
                msg_line = f.readline().strip()
                if not msg_line:
                    break

                msg = json.loads(msg_line)
                to_agent = msg.get("to", "")
                status = msg.get("status", "")
                from_agent = msg.get("from", "")

                # Check if message is for us and unread (match either name)
                is_for_me = to_agent in my_names or to_agent == "all"
                is_from_me = from_agent in my_names

                if status == "unread" and is_for_me and not is_from_me:
                    unread.append({
                        "thread": thread_id,
                        "thread_file": str(thread_file),
                        "from": from_agent,
                        "subject": msg.get("subject", ""),
                        "body": msg.get("body", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "id": msg.get("id"),
                    })

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {thread_file}: {e}", file=sys.stderr)

    return unread


def main():
    agent_name, repo_name = get_agent_names()
    if agent_name != repo_name:
        print(f"Checking messages for: {agent_name} (repo: {repo_name})")
    else:
        print(f"Checking messages for: {agent_name}")
    print(f"Threads directory: {THREADS_DIR}")
    print("-" * 50)

    if not THREADS_DIR.exists():
        print("No threads directory found.")
        return

    all_unread = []

    for thread_file in THREADS_DIR.glob("*.ndjson"):
        unread = check_thread(thread_file, agent_name, repo_name)
        all_unread.extend(unread)

    if not all_unread:
        print("No unread messages.")
        return

    print(f"Found {len(all_unread)} unread message(s):\n")

    for msg in all_unread:
        print(f"Thread: {msg['thread']}")
        print(f"From: {msg['from']}")
        print(f"Subject: {msg['subject']}")
        print(f"Time: {msg['timestamp']}")
        print(f"Body: {msg['body']}")
        print(f"File: {msg['thread_file']}")
        print("-" * 50)


if __name__ == "__main__":
    main()
