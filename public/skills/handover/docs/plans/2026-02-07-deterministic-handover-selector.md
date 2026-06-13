# Deterministic Handover Selector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Python script that deterministically selects the next eligible handover, replacing LLM-based selection reasoning.

**Architecture:** A `select_next_handover()` function scans queued/, checks dependencies and overlaps against WIP/ and completed/, and returns the first eligible handover with a status code. The skill's process-mode.md will invoke this script and act on its output.

**Tech Stack:** Python 3.11+, PyYAML for frontmatter parsing, existing test fixtures from conftest.py

---

## Task 1: Create SelectionResult and HandoverMeta Data Classes

**Files:**
- Create: `scripts/handover_selector.py`
- Test: `tests/test_handover_selector.py`

**Step 1: Write the failing test for data classes**

```python
# tests/test_handover_selector.py
"""Tests for deterministic handover selection."""
import pytest
from pathlib import Path


class TestDataClasses:
    """Tests for SelectionResult and HandoverMeta data classes."""

    def test_selection_result_ready_status(self):
        """SelectionResult can represent a ready-to-process handover."""
        from handover_selector import SelectionResult, SelectionStatus

        result = SelectionResult(
            status=SelectionStatus.READY,
            file=Path("queued/005_task.md"),
            skip_reasons={}
        )

        assert result.status == SelectionStatus.READY
        assert result.file is not None
        assert result.skip_reasons == {}

    def test_selection_result_blocked_status(self):
        """SelectionResult can represent all handovers blocked."""
        from handover_selector import SelectionResult, SelectionStatus

        result = SelectionResult(
            status=SelectionStatus.ALL_BLOCKED,
            file=None,
            skip_reasons={"005B_task.md": "waiting for 005A"}
        )

        assert result.status == SelectionStatus.ALL_BLOCKED
        assert result.file is None
        assert "005B_task.md" in result.skip_reasons

    def test_handover_meta_parses_filename(self):
        """HandoverMeta extracts number and letter from filename."""
        from handover_selector import HandoverMeta

        meta = HandoverMeta(
            filename="005B_some-task.md",
            number=5,
            letter="B",
            write_targets=["src/file.py"],
            read_only_targets=["docs/readme.md"],
            blocked_by=[]
        )

        assert meta.number == 5
        assert meta.letter == "B"
        assert meta.write_targets == ["src/file.py"]
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestDataClasses -v`
Expected: FAIL with "No module named 'handover_selector'"

**Step 3: Write minimal implementation**

```python
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


class SelectionStatus(Enum):
    """Possible outcomes of handover selection."""
    READY = "ready"              # Found an eligible handover
    REPAIR = "repair"            # Handover needs frontmatter repair
    ALL_BLOCKED = "all_blocked"  # All queued handovers blocked by dependencies
    ALL_OVERLAPPED = "all_overlapped"  # All queued handovers overlap with WIP
    WIP_ONLY = "wip_only"        # Queue empty but WIP has files (needs user input)
    EMPTY = "empty"              # Both queued and WIP are empty


@dataclass
class SelectionResult:
    """Result of handover selection."""
    status: SelectionStatus
    file: Optional[Path]
    skip_reasons: dict[str, str] = field(default_factory=dict)


@dataclass
class HandoverMeta:
    """Parsed metadata from a handover file."""
    filename: str
    number: int
    letter: Optional[str]
    write_targets: list[str]
    read_only_targets: list[str]
    blocked_by: list[str]
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestDataClasses -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add data classes for deterministic selection"
```

---

## Task 2: Implement parse_frontmatter Function

**Files:**
- Modify: `scripts/handover_selector.py`
- Modify: `tests/test_handover_selector.py`

**Step 1: Write the failing test**

```python
class TestParseFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_parses_valid_frontmatter(self, tmp_path):
        """Parses write_targets, read_only_targets, blocked_by from YAML."""
        handover = tmp_path / "005_task.md"
        handover.write_text("""---
write_targets:
  - src/feature.py
  - src/utils.py
read_only_targets:
  - docs/readme.md
blocked_by:
  - 004_other.md
---

# Task Content
Do the thing.
""")

        from handover_selector import parse_frontmatter

        meta = parse_frontmatter(handover)

        assert meta.filename == "005_task.md"
        assert meta.number == 5
        assert meta.letter is None
        assert meta.write_targets == ["src/feature.py", "src/utils.py"]
        assert meta.read_only_targets == ["docs/readme.md"]
        assert meta.blocked_by == ["004_other.md"]

    def test_parses_letter_suffix(self, tmp_path):
        """Extracts letter suffix from filename."""
        handover = tmp_path / "005B_chain-task.md"
        handover.write_text("""---
write_targets: []
read_only_targets: []
---
Content
""")

        from handover_selector import parse_frontmatter

        meta = parse_frontmatter(handover)

        assert meta.number == 5
        assert meta.letter == "B"

    def test_missing_frontmatter_returns_none(self, tmp_path):
        """File without frontmatter returns None (needs repair)."""
        handover = tmp_path / "005_task.md"
        handover.write_text("""# No Frontmatter

Just content here.
""")

        from handover_selector import parse_frontmatter

        result = parse_frontmatter(handover)

        assert result is None

    def test_missing_targets_returns_none(self, tmp_path):
        """Frontmatter without write_targets AND read_only_targets returns None."""
        handover = tmp_path / "005_task.md"
        handover.write_text("""---
title: Some Task
---

Content
""")

        from handover_selector import parse_frontmatter

        result = parse_frontmatter(handover)

        assert result is None

    def test_empty_targets_is_valid(self, tmp_path):
        """Empty lists for targets is valid (no overlap possible)."""
        handover = tmp_path / "005_task.md"
        handover.write_text("""---
write_targets: []
read_only_targets: []
---
Content
""")

        from handover_selector import parse_frontmatter

        meta = parse_frontmatter(handover)

        assert meta is not None
        assert meta.write_targets == []
        assert meta.read_only_targets == []

    def test_defaults_blocked_by_to_empty(self, tmp_path):
        """Missing blocked_by defaults to empty list."""
        handover = tmp_path / "005_task.md"
        handover.write_text("""---
write_targets:
  - src/file.py
read_only_targets: []
---
Content
""")

        from handover_selector import parse_frontmatter

        meta = parse_frontmatter(handover)

        assert meta.blocked_by == []
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestParseFrontmatter -v`
Expected: FAIL with "cannot import name 'parse_frontmatter'"

**Step 3: Write minimal implementation**

Add to `scripts/handover_selector.py`:

```python
import re
import yaml


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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestParseFrontmatter -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add parse_frontmatter for YAML extraction"
```

---

## Task 3: Implement check_letter_dependency Function

**Files:**
- Modify: `scripts/handover_selector.py`
- Modify: `tests/test_handover_selector.py`

**Step 1: Write the failing test**

```python
class TestLetterDependency:
    """Tests for letter-suffix dependency checking."""

    def test_no_letter_is_unblocked(self, mock_completed_dir):
        """Handover without letter suffix has no letter dependency."""
        from handover_selector import check_letter_dependency, HandoverMeta

        meta = HandoverMeta(
            filename="005_solo-task.md",
            number=5,
            letter=None,
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_letter_dependency(meta, mock_completed_dir)

        assert result is None  # None means unblocked

    def test_letter_a_is_unblocked(self, mock_completed_dir):
        """Letter A is always unblocked (first in chain)."""
        from handover_selector import check_letter_dependency, HandoverMeta

        meta = HandoverMeta(
            filename="005A_first-task.md",
            number=5,
            letter="A",
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_letter_dependency(meta, mock_completed_dir)

        assert result is None

    def test_letter_b_blocked_without_a(self, mock_completed_dir):
        """Letter B is blocked if A not in completed."""
        from handover_selector import check_letter_dependency, HandoverMeta

        meta = HandoverMeta(
            filename="005B_second-task.md",
            number=5,
            letter="B",
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_letter_dependency(meta, mock_completed_dir)

        assert result == "waiting for 005A"

    def test_letter_b_unblocked_with_a_complete(self, mock_completed_dir):
        """Letter B is unblocked when A exists in completed."""
        # Create 005A in completed
        (mock_completed_dir / "005A_first-task.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import check_letter_dependency, HandoverMeta

        meta = HandoverMeta(
            filename="005B_second-task.md",
            number=5,
            letter="B",
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_letter_dependency(meta, mock_completed_dir)

        assert result is None

    def test_letter_c_requires_both_a_and_b(self, mock_completed_dir):
        """Letter C requires both A and B complete."""
        # Only create A, not B
        (mock_completed_dir / "005A_first-task.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import check_letter_dependency, HandoverMeta

        meta = HandoverMeta(
            filename="005C_third-task.md",
            number=5,
            letter="C",
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_letter_dependency(meta, mock_completed_dir)

        assert result == "waiting for 005B"

    def test_letter_c_unblocked_with_both(self, mock_completed_dir):
        """Letter C is unblocked when both A and B exist."""
        (mock_completed_dir / "005A_first-task.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_completed_dir / "005B_second-task.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import check_letter_dependency, HandoverMeta

        meta = HandoverMeta(
            filename="005C_third-task.md",
            number=5,
            letter="C",
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_letter_dependency(meta, mock_completed_dir)

        assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestLetterDependency -v`
Expected: FAIL with "cannot import name 'check_letter_dependency'"

**Step 3: Write minimal implementation**

Add to `scripts/handover_selector.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestLetterDependency -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add letter-suffix dependency checking"
```

---

## Task 4: Implement check_blocked_by Function

**Files:**
- Modify: `scripts/handover_selector.py`
- Modify: `tests/test_handover_selector.py`

**Step 1: Write the failing test**

```python
class TestBlockedBy:
    """Tests for explicit blocked_by dependency checking."""

    def test_empty_blocked_by_is_unblocked(self, mock_completed_dir):
        """No blocked_by entries means unblocked."""
        from handover_selector import check_blocked_by, HandoverMeta

        meta = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=[],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_blocked_by(meta, mock_completed_dir)

        assert result is None

    def test_blocked_by_missing_file(self, mock_completed_dir):
        """Blocked if blocker not in completed."""
        from handover_selector import check_blocked_by, HandoverMeta

        meta = HandoverMeta(
            filename="004_dependent.md",
            number=4,
            letter=None,
            write_targets=[],
            read_only_targets=[],
            blocked_by=["005_blocker.md"]
        )

        result = check_blocked_by(meta, mock_completed_dir)

        assert result == "blocked by 005_blocker.md"

    def test_blocked_by_satisfied(self, mock_completed_dir):
        """Unblocked when blocker exists in completed."""
        (mock_completed_dir / "005_blocker.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import check_blocked_by, HandoverMeta

        meta = HandoverMeta(
            filename="004_dependent.md",
            number=4,
            letter=None,
            write_targets=[],
            read_only_targets=[],
            blocked_by=["005_blocker.md"]
        )

        result = check_blocked_by(meta, mock_completed_dir)

        assert result is None

    def test_multiple_blockers_all_required(self, mock_completed_dir):
        """All blockers must be complete."""
        (mock_completed_dir / "006_first.md").write_text("---\nwrite_targets: []\n---\n")
        # 005_second.md NOT created

        from handover_selector import check_blocked_by, HandoverMeta

        meta = HandoverMeta(
            filename="004_dependent.md",
            number=4,
            letter=None,
            write_targets=[],
            read_only_targets=[],
            blocked_by=["006_first.md", "005_second.md"]
        )

        result = check_blocked_by(meta, mock_completed_dir)

        assert result == "blocked by 005_second.md"
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestBlockedBy -v`
Expected: FAIL with "cannot import name 'check_blocked_by'"

**Step 3: Write minimal implementation**

Add to `scripts/handover_selector.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestBlockedBy -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add blocked_by dependency checking"
```

---

## Task 5: Implement check_write_overlap Function

**Files:**
- Modify: `scripts/handover_selector.py`
- Modify: `tests/test_handover_selector.py`

**Step 1: Write the failing test**

```python
class TestWriteOverlap:
    """Tests for write target overlap detection with WIP."""

    def test_no_wip_files_means_no_overlap(self, mock_wip_dir):
        """Empty WIP directory means no overlap possible."""
        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=["src/file.py"],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert result is None

    def test_no_overlap_different_files(self, mock_wip_dir):
        """No overlap when candidate and WIP target different files."""
        (mock_wip_dir / "004_other.md").write_text("""---
write_targets:
  - src/other.py
read_only_targets: []
---
""")

        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=["src/file.py"],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert result is None

    def test_both_write_same_file_is_conflict(self, mock_wip_dir):
        """Conflict when both want to write same file."""
        (mock_wip_dir / "004_other.md").write_text("""---
write_targets:
  - src/shared.py
read_only_targets: []
---
""")

        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=["src/shared.py"],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert "src/shared.py" in result
        assert "both write" in result

    def test_candidate_writes_wip_reads_is_conflict(self, mock_wip_dir):
        """Conflict when candidate writes what WIP reads."""
        (mock_wip_dir / "004_other.md").write_text("""---
write_targets: []
read_only_targets:
  - src/shared.py
---
""")

        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=["src/shared.py"],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert "src/shared.py" in result
        assert "candidate writes, WIP reads" in result

    def test_candidate_reads_wip_writes_is_conflict(self, mock_wip_dir):
        """Conflict when WIP writes what candidate reads."""
        (mock_wip_dir / "004_other.md").write_text("""---
write_targets:
  - src/shared.py
read_only_targets: []
---
""")

        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=[],
            read_only_targets=["src/shared.py"],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert "src/shared.py" in result
        assert "WIP writes, candidate reads" in result

    def test_both_read_same_file_is_ok(self, mock_wip_dir):
        """No conflict when both only read same file."""
        (mock_wip_dir / "004_other.md").write_text("""---
write_targets: []
read_only_targets:
  - src/shared.py
---
""")

        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=[],
            read_only_targets=["src/shared.py"],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert result is None

    def test_malformed_wip_treated_as_full_overlap(self, mock_wip_dir):
        """WIP file without valid frontmatter blocks everything."""
        (mock_wip_dir / "004_other.md").write_text("# No frontmatter\n")

        from handover_selector import check_write_overlap, HandoverMeta

        candidate = HandoverMeta(
            filename="005_task.md",
            number=5,
            letter=None,
            write_targets=["src/anything.py"],
            read_only_targets=[],
            blocked_by=[]
        )

        result = check_write_overlap(candidate, mock_wip_dir)

        assert result is not None
        assert "malformed" in result.lower() or "004_other.md" in result
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestWriteOverlap -v`
Expected: FAIL with "cannot import name 'check_write_overlap'"

**Step 3: Write minimal implementation**

Add to `scripts/handover_selector.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestWriteOverlap -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add write target overlap detection with WIP"
```

---

## Task 6: Implement select_next_handover Main Function

**Files:**
- Modify: `scripts/handover_selector.py`
- Modify: `tests/test_handover_selector.py`

**Step 1: Write the failing test**

```python
class TestSelectNextHandover:
    """Tests for main selection function."""

    def test_empty_queue_and_wip_returns_empty(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Empty queue and WIP returns EMPTY status."""
        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.EMPTY
        assert result.file is None

    def test_empty_queue_with_wip_returns_wip_only(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Empty queue but files in WIP returns WIP_ONLY."""
        (mock_wip_dir / "005_in-progress.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.WIP_ONLY
        assert result.file is None

    def test_single_unblocked_returns_ready(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Single unblocked handover returns READY."""
        handover = mock_queued_dir / "005_task.md"
        handover.write_text("---\nwrite_targets: []\nread_only_targets: []\n---\nContent")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.READY
        assert result.file == handover

    def test_malformed_returns_repair(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Malformed handover returns REPAIR status."""
        handover = mock_queued_dir / "005_broken.md"
        handover.write_text("# No frontmatter\nJust content")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.REPAIR
        assert result.file == handover

    def test_selects_highest_number_first(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Higher numbers processed before lower (LIFO)."""
        (mock_queued_dir / "003_low.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005_high.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "004_mid.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.READY
        assert result.file.name == "005_high.md"

    def test_skips_blocked_letter_dependency(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Skips handover blocked by letter dependency."""
        (mock_queued_dir / "005B_second.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "004_fallback.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.READY
        assert result.file.name == "004_fallback.md"
        assert "005B_second.md" in result.skip_reasons

    def test_skips_blocked_by_dependency(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Skips handover blocked by explicit blocked_by."""
        (mock_queued_dir / "004_blocked.md").write_text("""---
write_targets: []
blocked_by:
  - 005_blocker.md
---
""")
        (mock_queued_dir / "003_fallback.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.READY
        assert result.file.name == "003_fallback.md"
        assert "004_blocked.md" in result.skip_reasons

    def test_skips_wip_overlap(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Skips handover with WIP overlap."""
        (mock_wip_dir / "006_active.md").write_text("""---
write_targets:
  - src/shared.py
read_only_targets: []
---
""")
        (mock_queued_dir / "005_overlapping.md").write_text("""---
write_targets:
  - src/shared.py
read_only_targets: []
---
""")
        (mock_queued_dir / "004_safe.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.READY
        assert result.file.name == "004_safe.md"
        assert "005_overlapping.md" in result.skip_reasons

    def test_all_blocked_returns_all_blocked(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Returns ALL_BLOCKED when all handovers have dependency issues."""
        (mock_queued_dir / "005B_needs_a.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "004_needs_blocker.md").write_text("""---
write_targets: []
blocked_by:
  - 006_not_done.md
---
""")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.ALL_BLOCKED
        assert result.file is None
        assert len(result.skip_reasons) == 2

    def test_all_overlapped_returns_all_overlapped(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Returns ALL_OVERLAPPED when all handovers overlap with WIP."""
        (mock_wip_dir / "006_active.md").write_text("""---
write_targets:
  - src/file.py
read_only_targets: []
---
""")
        (mock_queued_dir / "005_overlap1.md").write_text("""---
write_targets:
  - src/file.py
read_only_targets: []
---
""")
        (mock_queued_dir / "004_overlap2.md").write_text("""---
write_targets: []
read_only_targets:
  - src/file.py
---
""")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        assert result.status == SelectionStatus.ALL_OVERLAPPED
        assert result.file is None
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestSelectNextHandover -v`
Expected: FAIL with "cannot import name 'select_next_handover'"

**Step 3: Write minimal implementation**

Add to `scripts/handover_selector.py`:

```python
from handover_utils import sort_handovers


def select_next_handover(
    queued_dir: Path,
    wip_dir: Path,
    completed_dir: Path
) -> SelectionResult:
    """
    Deterministically select the next eligible handover.

    Algorithm:
    1. Scan queued/ for *.md files, sorted by dual order (numbers DESC, letters ASC)
    2. For each file:
       a. Parse YAML frontmatter (if malformed → REPAIR)
       b. Check letter-suffix dependencies (if blocked → skip)
       c. Check blocked_by field (if blocked → skip)
       d. Check write target overlaps with WIP (if conflict → skip)
       e. Return first unblocked file as READY
    3. If no file eligible, return appropriate status

    Args:
        queued_dir: Path to queued/ directory
        wip_dir: Path to WIP/ directory
        completed_dir: Path to completed/ directory

    Returns:
        SelectionResult with status and optional file
    """
    skip_reasons: dict[str, str] = {}
    blocked_count = 0
    overlapped_count = 0

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
        # Parse frontmatter
        meta = parse_frontmatter(filepath)
        if meta is None:
            return SelectionResult(
                status=SelectionStatus.REPAIR,
                file=filepath,
                skip_reasons=skip_reasons
            )

        # Check letter dependency
        letter_reason = check_letter_dependency(meta, completed_dir)
        if letter_reason:
            skip_reasons[meta.filename] = letter_reason
            blocked_count += 1
            continue

        # Check blocked_by
        blocked_reason = check_blocked_by(meta, completed_dir)
        if blocked_reason:
            skip_reasons[meta.filename] = blocked_reason
            blocked_count += 1
            continue

        # Check WIP overlap
        overlap_reason = check_write_overlap(meta, wip_dir)
        if overlap_reason:
            skip_reasons[meta.filename] = overlap_reason
            overlapped_count += 1
            continue

        # Found eligible handover
        return SelectionResult(
            status=SelectionStatus.READY,
            file=filepath,
            skip_reasons=skip_reasons
        )

    # All skipped - determine why
    if overlapped_count > 0 and blocked_count == 0:
        return SelectionResult(
            status=SelectionStatus.ALL_OVERLAPPED,
            file=None,
            skip_reasons=skip_reasons
        )

    return SelectionResult(
        status=SelectionStatus.ALL_BLOCKED,
        file=None,
        skip_reasons=skip_reasons
    )
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestSelectNextHandover -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add select_next_handover main function"
```

---

## Task 7: Add CLI Interface and JSON Output

**Files:**
- Modify: `scripts/handover_selector.py`
- Modify: `tests/test_handover_selector.py`

**Step 1: Write the failing test**

```python
import json
import subprocess


class TestCLI:
    """Tests for CLI interface."""

    def test_cli_outputs_json(self, tmp_path):
        """CLI outputs valid JSON to stdout."""
        # Create directory structure
        queued = tmp_path / ".claude" / "handovers" / "queued"
        wip = tmp_path / ".claude" / "handovers" / "WIP"
        completed = tmp_path / ".claude" / "handovers" / "completed"
        queued.mkdir(parents=True)
        wip.mkdir(parents=True)
        completed.mkdir(parents=True)

        (queued / "005_task.md").write_text("---\nwrite_targets: []\n---\nContent")

        result = subprocess.run(
            ["python", "-m", "handover_selector", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent / "scripts")
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "ready"
        assert "005_task.md" in output["file"]

    def test_cli_empty_queue_exit_code(self, tmp_path):
        """CLI returns exit code 0 even for empty queue."""
        queued = tmp_path / ".claude" / "handovers" / "queued"
        wip = tmp_path / ".claude" / "handovers" / "WIP"
        completed = tmp_path / ".claude" / "handovers" / "completed"
        queued.mkdir(parents=True)
        wip.mkdir(parents=True)
        completed.mkdir(parents=True)

        result = subprocess.run(
            ["python", "-m", "handover_selector", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent / "scripts")
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "empty"
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestCLI -v`
Expected: FAIL with "No module named handover_selector"

**Step 3: Write minimal implementation**

Add to end of `scripts/handover_selector.py`:

```python
import json as json_module
import sys


def to_json(result: SelectionResult) -> str:
    """Convert SelectionResult to JSON string for CLI output."""
    return json_module.dumps({
        "status": result.status.value,
        "file": str(result.file) if result.file else None,
        "skip_reasons": result.skip_reasons
    }, indent=2)


def main():
    """CLI entry point for deterministic handover selection."""
    repo_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    handovers_base = repo_path / ".claude" / "handovers"
    queued_dir = handovers_base / "queued"
    wip_dir = handovers_base / "WIP"
    completed_dir = handovers_base / "completed"

    result = select_next_handover(queued_dir, wip_dir, completed_dir)
    print(to_json(result))


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/test_handover_selector.py::TestCLI -v`
Expected: PASS

**Step 5: Commit**

```bash
cd ~/.claude/skills/handover
git add scripts/handover_selector.py tests/test_handover_selector.py
git commit -m "feat(handover): add CLI with JSON output for selector"
```

---

## Task 8: Update process-mode.md to Use Deterministic Selector

**Files:**
- Modify: `reference/process-mode.md`

**Step 1: Review current process-mode.md**

Read current content and identify sections that describe LLM-based selection.

**Step 2: Add script invocation section**

Add after "## Workflow" section header:

```markdown
## Deterministic Selection

Before manually checking files, invoke the deterministic selector:

```bash
python -m handover_selector [repo_path]
```

The script outputs JSON with one of these statuses:

| Status | Action |
| --- | --- |
| `ready` | Move `file` to WIP and begin work |
| `repair` | Read `reference/repair-mode.md` for `file` |
| `all_blocked` | Inform user: "All queued handovers blocked by dependencies" |
| `all_overlapped` | Inform user: "All queued handovers overlap with WIP" |
| `wip_only` | Ask user about WIP files (see Edge Cases) |
| `empty` | Inform user: "No handovers in queue" |

**Example output:**

```json
{
  "status": "ready",
  "file": ".claude/handovers/queued/005_task.md",
  "skip_reasons": {
    "006B_chain.md": "waiting for 006A"
  }
}
```

The `skip_reasons` field shows why other handovers were skipped, useful for debugging.
```

**Step 3: Update workflow section**

Replace the manual scanning steps with script invocation, keeping the "move to WIP" and subsequent steps.

**Step 4: Commit**

```bash
cd ~/.claude/skills/handover
git add reference/process-mode.md
git commit -m "docs(handover): update process-mode to use deterministic selector"
```

---

## Task 9: Run Full Test Suite and Verify Integration

**Files:**
- All files in `scripts/` and `tests/`

**Step 1: Run all handover tests**

Run: `cd ~/.claude/skills/handover && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Run integration test with real directory structure**

Create a temporary test that mimics the real `.claude/handovers/` structure and verifies the full workflow.

**Step 3: Verify script runs from command line**

Run: `cd ~/.claude/skills/handover && python scripts/handover_selector.py ~/.claude`
Expected: Valid JSON output

**Step 4: Final commit**

```bash
cd ~/.claude/skills/handover
git add .
git commit -m "test(handover): verify deterministic selector integration"
```

---

Plan complete and saved to `~/.claude/skills/handover/docs/plans/2026-02-07-deterministic-handover-selector.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?