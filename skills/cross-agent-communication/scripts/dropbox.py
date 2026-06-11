#!/usr/bin/env python3
"""
Cross-agent dropbox for file sharing.

Usage:
  python dropbox.py list              # List files (runs cleanup first)
  python dropbox.py deposit <file>    # Deposit a file (adds date prefix)
  python dropbox.py cleanup           # Manually run cleanup
  python dropbox.py get <filename>    # Get full path to a file

Rules:
  - Files must start with YYYY-MM-DD (date deposited)
  - Max 3 different calendar dates allowed
  - Oldest date's files are deleted when >3 dates present
"""

import sys
import shutil
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DROPBOX_DIR = Path(r"C:\Users\Brahm\Git\.cross-agent\dropbox")
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})")
MAX_DATES = 3


def get_files_by_date() -> dict:
    """Get all files grouped by their date prefix."""
    files_by_date = defaultdict(list)

    if not DROPBOX_DIR.exists():
        return files_by_date

    for f in DROPBOX_DIR.iterdir():
        if f.is_file():
            match = DATE_PATTERN.match(f.name)
            if match:
                date_str = match.group(1)
                files_by_date[date_str].append(f)
            else:
                # File without proper date prefix - report it
                print(f"Warning: File without date prefix: {f.name}", file=sys.stderr)

    return files_by_date


def cleanup_oldest() -> int:
    """
    If more than MAX_DATES different dates exist, delete oldest dates until only MAX_DATES remain.
    Returns total number of files deleted.
    """
    total_deleted = 0

    while True:
        files_by_date = get_files_by_date()
        dates = sorted(files_by_date.keys())

        if len(dates) <= MAX_DATES:
            break

        # Delete files from oldest date
        oldest_date = dates[0]
        files_to_delete = files_by_date[oldest_date]

        print(f"Cleanup: Dropbox has {len(dates)} dates (max {MAX_DATES})")
        print(f"Deleting {len(files_to_delete)} file(s) from oldest date: {oldest_date}")

        for f in files_to_delete:
            try:
                f.unlink()
                print(f"  Deleted: {f.name}")
                total_deleted += 1
            except OSError as e:
                print(f"  Error deleting {f.name}: {e}", file=sys.stderr)

    return total_deleted


def list_files():
    """List all files in dropbox, grouped by date."""
    # Always run cleanup first
    cleanup_oldest()

    files_by_date = get_files_by_date()

    if not files_by_date:
        print("Dropbox is empty.")
        return

    print(f"\nDropbox contents ({DROPBOX_DIR}):")
    print("-" * 50)

    for date_str in sorted(files_by_date.keys(), reverse=True):
        files = files_by_date[date_str]
        print(f"\n{date_str} ({len(files)} file(s)):")
        for f in sorted(files, key=lambda x: x.name):
            size = f.stat().st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            print(f"  {f.name} ({size_str})")


def deposit_file(source_path: str):
    """
    Deposit a file into the dropbox with today's date prefix.
    """
    source = Path(source_path)

    if not source.exists():
        print(f"Error: File not found: {source}", file=sys.stderr)
        sys.exit(1)

    if not source.is_file():
        print(f"Error: Not a file: {source}", file=sys.stderr)
        sys.exit(1)

    # Always run cleanup first
    cleanup_oldest()

    # Create destination filename with date prefix
    today = datetime.now().strftime("%Y-%m-%d")
    original_name = source.name

    # Check if file already has a date prefix
    if DATE_PATTERN.match(original_name):
        # Replace existing date with today's date
        dest_name = DATE_PATTERN.sub(today, original_name)
    else:
        dest_name = f"{today}-{original_name}"

    dest = DROPBOX_DIR / dest_name

    # Handle duplicate names
    if dest.exists():
        base = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = DROPBOX_DIR / f"{base}-{counter}{suffix}"
            counter += 1

    # Ensure dropbox exists
    DROPBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(source, dest)

    print(f"File deposited successfully!")
    print(f"  Source: {source}")
    print(f"  Destination: {dest}")
    print(f"  Date: {today}")


def get_file(filename: str):
    """Get the full path to a file in the dropbox."""
    # Always run cleanup first
    cleanup_oldest()

    file_path = DROPBOX_DIR / filename

    if file_path.exists():
        print(str(file_path))
    else:
        # Try partial match
        matches = list(DROPBOX_DIR.glob(f"*{filename}*"))
        if len(matches) == 1:
            print(str(matches[0]))
        elif len(matches) > 1:
            print(f"Multiple matches found:", file=sys.stderr)
            for m in matches:
                print(f"  {m.name}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Error: File not found: {filename}", file=sys.stderr)
            sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python dropbox.py list              # List files")
        print("  python dropbox.py deposit <file>    # Deposit a file")
        print("  python dropbox.py cleanup           # Run cleanup")
        print("  python dropbox.py get <filename>    # Get file path")
        print()
        print("Rules:")
        print("  - Files are prefixed with YYYY-MM-DD (deposit date)")
        print(f"  - Max {MAX_DATES} different dates allowed")
        print("  - Oldest date's files auto-deleted when limit exceeded")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        list_files()
    elif command == "deposit":
        if len(sys.argv) < 3:
            print("Error: Please specify a file to deposit", file=sys.stderr)
            sys.exit(1)
        deposit_file(sys.argv[2])
    elif command == "cleanup":
        deleted = cleanup_oldest()
        if deleted == 0:
            print(f"No cleanup needed (max {MAX_DATES} dates, currently have {len(get_files_by_date())})")
    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: Please specify a filename", file=sys.stderr)
            sys.exit(1)
        get_file(sys.argv[2])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
