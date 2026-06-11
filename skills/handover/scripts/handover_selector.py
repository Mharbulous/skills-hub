# scripts/handover_selector.py
"""
Deterministic handover selection.

Selects the next eligible handover by checking dependencies and overlaps
without requiring LLM reasoning.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import re
import yaml


class SelectionStatus(Enum):
    """Possible outcomes of handover selection."""
    READY = "ready"              # Found an eligible handover
    REPAIR = "repair"            # Handover needs frontmatter repair
    CONFLICT = "conflict"        # Top-priority file conflicts with WIP — user must decide
    ALL_BLOCKED = "all_blocked"  # All queued handovers blocked by dependencies
    WIP_ONLY = "wip_only"        # Queue empty but WIP has files (needs user input)
    EMPTY = "empty"              # Both queued and WIP are empty


@dataclass
class SelectionResult:
    """Result of handover selection."""
    status: SelectionStatus
    file: Optional[Path]
    skip_reasons: dict[str, str] = field(default_factory=dict)
    conflict_with: Optional[str] = None  # WIP filename causing conflict (CONFLICT status only)


@dataclass
class HandoverMeta:
    """Parsed metadata from a handover file."""
    filename: str
    number: int
    letter: Optional[str]
    write_targets: list[str]
    read_only_targets: list[str]
    blocked_by: list[str]


def parse_frontmatter(filepath: Path) -> Optional[HandoverMeta]:
    """
    Parse YAML frontmatter from a handover file.

    Returns HandoverMeta if valid, None if malformed or missing required fields.
    Malformed files should trigger Repair mode.

    Args:
        filepath: Path to the handover markdown file

    Returns:
        HandoverMeta with parsed data, or None if repair needed
    """
    content = filepath.read_text(encoding="utf-8")

    # Check for frontmatter delimiter
    if not content.startswith("---"):
        return None

    # Extract frontmatter block
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_text = parts[1].strip()
    if not frontmatter_text:
        return None

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None

    if not isinstance(frontmatter, dict):
        return None

    # Require at least one of write_targets or read_only_targets
    write_targets = frontmatter.get("write_targets")
    read_only_targets = frontmatter.get("read_only_targets")

    if write_targets is None and read_only_targets is None:
        return None

    # Parse filename for number and letter
    filename = filepath.name
    pattern = re.compile(r"^(\d+)([A-Z])?_")
    match = pattern.match(filename)

    if not match:
        return None

    number = int(match.group(1))
    letter = match.group(2)  # None if no letter

    return HandoverMeta(
        filename=filename,
        number=number,
        letter=letter,
        write_targets=write_targets or [],
        read_only_targets=read_only_targets or [],
        blocked_by=frontmatter.get("blocked_by") or [],
    )


def check_letter_dependency(meta: HandoverMeta, completed_dir: Path) -> Optional[str]:
    """
    Check if letter-suffix dependencies are satisfied.

    Letter suffixes encode implicit dependencies:
    - 005A: No dependency (first in chain)
    - 005B: Requires 005A in completed
    - 005C: Requires 005A and 005B in completed

    Args:
        meta: Parsed handover metadata
        completed_dir: Path to completed/ directory

    Returns:
        None if unblocked, or reason string if blocked (e.g., "waiting for 005A")
    """
    if meta.letter is None or meta.letter == "A":
        return None

    # Check all preceding letters
    for preceding in range(ord("A"), ord(meta.letter)):
        preceding_letter = chr(preceding)
        pattern = f"{meta.number:03d}{preceding_letter}_*.md"
        matches = list(completed_dir.glob(pattern))

        if not matches:
            return f"waiting for {meta.number:03d}{preceding_letter}"

    return None


def check_blocked_by(meta: HandoverMeta, completed_dir: Path) -> Optional[str]:
    """
    Check if explicit blocked_by dependencies are satisfied.

    Args:
        meta: Parsed handover metadata
        completed_dir: Path to completed/ directory

    Returns:
        None if unblocked, or reason string if blocked
    """
    for blocker in meta.blocked_by:
        blocker_path = completed_dir / blocker
        if not blocker_path.exists():
            return f"blocked by {blocker}"

    return None


def check_write_overlap(candidate: HandoverMeta, wip_dir: Path) -> Optional[str]:
    """
    Check for write target overlaps with WIP handovers.

    Conflict rules:
    - candidate.write_targets ∩ WIP.write_targets = CONFLICT (both write)
    - candidate.write_targets ∩ WIP.read_only_targets = CONFLICT (candidate writes what WIP reads)
    - candidate.read_only_targets ∩ WIP.write_targets = CONFLICT (WIP writes what candidate reads)
    - candidate.read_only_targets ∩ WIP.read_only_targets = OK (both just reading)

    Args:
        candidate: Parsed metadata for candidate handover
        wip_dir: Path to WIP/ directory

    Returns:
        None if no conflict, or detailed conflict description if blocked
    """
    if not wip_dir.exists():
        return None

    wip_files = list(wip_dir.glob("*.md"))
    if not wip_files:
        return None

    candidate_writes = set(candidate.write_targets)
    candidate_reads = set(candidate.read_only_targets)

    for wip_file in wip_files:
        wip_meta = parse_frontmatter(wip_file)

        if wip_meta is None:
            # Malformed WIP file - treat as blocking everything
            return f"WIP file {wip_file.name} has malformed frontmatter (treat as full overlap)"

        wip_writes = set(wip_meta.write_targets)
        wip_reads = set(wip_meta.read_only_targets)

        # Check: both write same file
        both_write = candidate_writes & wip_writes
        if both_write:
            file = next(iter(both_write))
            return f"conflict with {wip_file.name}: {file} (both write)"

        # Check: candidate writes what WIP reads
        candidate_writes_wip_reads = candidate_writes & wip_reads
        if candidate_writes_wip_reads:
            file = next(iter(candidate_writes_wip_reads))
            return f"conflict with {wip_file.name}: {file} (candidate writes, WIP reads)"

        # Check: WIP writes what candidate reads
        wip_writes_candidate_reads = wip_writes & candidate_reads
        if wip_writes_candidate_reads:
            file = next(iter(wip_writes_candidate_reads))
            return f"conflict with {wip_file.name}: {file} (WIP writes, candidate reads)"

    return None


from handover_utils import sort_handovers, resolve_handovers_base


def _extract_wip_filename(reason: str) -> Optional[str]:
    """Extract WIP filename from overlap reason string."""
    match = re.search(r'conflict with ([^:]+):', reason)
    if match:
        return match.group(1).strip()
    match = re.search(r'WIP file ([^\s]+)', reason)
    if match:
        return match.group(1).strip()
    return None


def select_next_handover(
    queued_dir: Path,
    wip_dir: Path,
    completed_dir: Path,
    exclude: Optional[set] = None,
) -> SelectionResult:
    """
    Deterministically select the next eligible handover.

    Algorithm:
    1. Scan queued/ for *.md files, sorted by dual order (numbers DESC, letters ASC)
    2. Skip any files named in `exclude`
    3. For each file:
       a. Parse YAML frontmatter (if malformed → REPAIR)
       b. Check letter-suffix dependencies (if blocked → skip silently)
       c. Check blocked_by field (if blocked → skip silently)
       d. Check write target overlaps with WIP (if conflict → STOP, return CONFLICT)
       e. Return first unblocked file as READY
    4. If no file eligible, return appropriate status

    WIP conflicts surface to the user (CONFLICT status) instead of silent skip,
    because they may represent an abandoned session or accidental artifact.
    Use `exclude` to skip a specific file after the user resolves or defers a conflict.

    Args:
        queued_dir: Path to queued/ directory
        wip_dir: Path to WIP/ directory
        completed_dir: Path to completed/ directory
        exclude: Optional set of filenames to skip (e.g. after user defers a conflict)

    Returns:
        SelectionResult with status and optional file
    """
    skip_reasons: dict[str, str] = {}
    blocked_count = 0

    # Check for empty queue
    if not queued_dir.exists():
        queued_files = []
    else:
        queued_files = sort_handovers(queued_dir)

    if not queued_files:
        # Check if WIP has files
        wip_files = list(wip_dir.glob("*.md")) if wip_dir.exists() else []
        if wip_files:
            return SelectionResult(
                status=SelectionStatus.WIP_ONLY,
                file=None,
                skip_reasons={}
            )
        return SelectionResult(
            status=SelectionStatus.EMPTY,
            file=None,
            skip_reasons={}
        )

    for filepath in queued_files:
        # Skip explicitly excluded files
        if exclude and filepath.name in exclude:
            continue

        # Parse frontmatter
        meta = parse_frontmatter(filepath)
        if meta is None:
            return SelectionResult(
                status=SelectionStatus.REPAIR,
                file=filepath,
                skip_reasons=skip_reasons
            )

        # Check letter dependency — structural, skip silently
        letter_reason = check_letter_dependency(meta, completed_dir)
        if letter_reason:
            skip_reasons[meta.filename] = letter_reason
            blocked_count += 1
            continue

        # Check blocked_by — declared dependency, skip silently
        blocked_reason = check_blocked_by(meta, completed_dir)
        if blocked_reason:
            skip_reasons[meta.filename] = blocked_reason
            blocked_count += 1
            continue

        # Check WIP overlap — ambiguous situation, STOP and surface to user
        overlap_reason = check_write_overlap(meta, wip_dir)
        if overlap_reason:
            return SelectionResult(
                status=SelectionStatus.CONFLICT,
                file=filepath,
                skip_reasons=skip_reasons,
                conflict_with=_extract_wip_filename(overlap_reason),
            )

        # Found eligible handover
        return SelectionResult(
            status=SelectionStatus.READY,
            file=filepath,
            skip_reasons=skip_reasons
        )

    return SelectionResult(
        status=SelectionStatus.ALL_BLOCKED,
        file=None,
        skip_reasons=skip_reasons
    )


import json as json_module
import shutil
import sys


def to_json(result: SelectionResult, claimed: bool = False, claimed_path: Optional[Path] = None) -> str:
    """Convert SelectionResult to JSON string for CLI output."""
    data = {
        "status": result.status.value,
        "file": str(result.file) if result.file else None,
        "skip_reasons": result.skip_reasons
    }
    if result.conflict_with:
        data["conflict_with"] = result.conflict_with
    if claimed:
        data["claimed"] = True
        data["claimed_path"] = str(claimed_path)
    return json_module.dumps(data, indent=2)


def claim_file(filepath: Path, wip_dir: Path) -> Optional[Path]:
    """
    Atomically move a handover file from queued/ to WIP/.

    Returns the new WIP path on success, None if the file is already gone
    (race condition with another session).
    """
    wip_dir.mkdir(parents=True, exist_ok=True)
    dest = wip_dir / filepath.name
    try:
        shutil.move(str(filepath), str(dest))
        return dest
    except FileNotFoundError:
        # File was claimed by another session between selection and move
        return None


def main():
    """CLI entry point for deterministic handover selection."""
    args = sys.argv[1:]
    claim = "--claim" in args
    args = [a for a in args if a != "--claim"]

    # Parse --exclude=file1.md,file2.md
    exclude: set[str] = set()
    positional = []
    for a in args:
        if a.startswith("--exclude="):
            names = a[len("--exclude="):].split(",")
            exclude.update(n.strip() for n in names if n.strip())
        else:
            positional.append(a)
    args = positional

    repo_path = Path(args[0]) if args else Path.cwd()

    handovers_base = resolve_handovers_base(repo_path)
    queued_dir = handovers_base / "queued"
    wip_dir = handovers_base / "WIP"
    completed_dir = handovers_base / "completed"

    result = select_next_handover(queued_dir, wip_dir, completed_dir, exclude=exclude or None)

    if claim and result.status == SelectionStatus.READY and result.file:
        claimed_path = claim_file(result.file, wip_dir)
        if claimed_path:
            print(to_json(result, claimed=True, claimed_path=claimed_path))
        else:
            # File vanished — re-scan to find next eligible
            result = select_next_handover(queued_dir, wip_dir, completed_dir)
            print(to_json(result))
    else:
        print(to_json(result))


if __name__ == "__main__":
    main()
