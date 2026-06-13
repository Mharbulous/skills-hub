"""
Determine next handover number by scanning all handover folders.

This script provides deterministic computation of the next handover number
by scanning queued/, WIP/, and completed/ folders for existing handover files.
Extracts numeric prefixes (ignoring letter suffixes) and returns highest + 1.

Scans both handovers/ (primary) and .handovers/ (legacy) to avoid
number collisions during migration.

Usage:
    # As module
    from scripts.get_next_handover_number import get_next_handover_number
    next_num = get_next_handover_number(Path("/path/to/repo"))

    # As CLI
    python get_next_handover_number.py [repo_path]

Examples:
    $ python get_next_handover_number.py
    039

    $ python get_next_handover_number.py /path/to/repo
    042

Naming Convention:
    Files must match pattern: {NNN}[{LETTER}]{_|-}{slug}.md
    - NNN: 3-digit number (001, 038, etc.)
    - LETTER: Optional A-Z suffix for chains (038A, 038B)
    - slug: Descriptive name with hyphens

    Examples:
    - 037_merge-predict-types.md → 37
    - 038A_create-script.md → 38
    - 038B_integrate-script.md → 38
"""

import re
from pathlib import Path
from typing import Optional


def get_next_handover_number(repo_path: Optional[Path] = None) -> int:
    """
    Scan all handover folders and return next available handover number.

    Searches both handovers/ (primary) and .handovers/ (legacy) for
    files matching the handover naming convention. Extracts numeric prefix
    from each file, ignoring letter suffixes (A, B, C, etc.), and returns
    highest + 1.

    Both locations are scanned to avoid number collisions during migration
    from .handovers/ to handovers/.

    Args:
        repo_path: Repository root path. Defaults to current directory.

    Returns:
        Next handover number as integer. Returns 1 if no handovers found
        or if folders don't exist.

    Examples:
        >>> get_next_handover_number(Path("/repo"))  # Has 037, 038A, 038B
        39

        >>> get_next_handover_number(Path("/empty"))  # No handovers
        1
    """
    if repo_path is None:
        repo_path = Path.cwd()

    # Scan both locations to avoid number collisions during migration
    handover_bases = [
        repo_path / "handovers",
        repo_path / ".handovers",
    ]
    folders = ["queued", "WIP", "completed"]

    highest = 0
    pattern = re.compile(r'^(\d+)[A-Z]?[_-]')

    for handovers_base in handover_bases:
        for folder_name in folders:
            folder = handovers_base / folder_name
            if not folder.exists():
                continue

            for filepath in folder.iterdir():
                if filepath.is_file() and filepath.suffix == ".md":
                    match = pattern.match(filepath.name)
                    if match:
                        num = int(match.group(1))
                        highest = max(highest, num)

    return highest + 1


def main():
    """CLI entry point."""
    import sys

    repo_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    next_number = get_next_handover_number(repo_path)
    print(f"{next_number:03d}")


if __name__ == "__main__":
    main()
