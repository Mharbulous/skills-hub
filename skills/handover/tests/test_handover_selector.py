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

    def test_wip_conflict_returns_conflict_status(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """WIP conflict on highest-priority file stops and returns CONFLICT (not silent skip)."""
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

        # Must stop at the conflict and report it — NOT silently skip to 004_safe.md
        assert result.status == SelectionStatus.CONFLICT
        assert result.file.name == "005_overlapping.md"
        assert result.conflict_with == "006_active.md"

    def test_wip_conflict_lower_priority_file_not_selected(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """When top-priority file has WIP conflict, lower-priority file is NOT returned."""
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

        # 004_safe.md must NOT be selected — user must decide what to do about 005
        assert result.file is None or result.file.name != "004_safe.md"

    def test_letter_dep_still_skips_silently(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """Letter dependency blocks still skip silently (not a CONFLICT), allowing lower priority to run."""
        (mock_queued_dir / "005B_second.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "004_fallback.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_selector import select_next_handover, SelectionStatus

        result = select_next_handover(
            mock_queued_dir, mock_wip_dir, mock_completed_dir
        )

        # Letter dep is a structural dependency — skip silently and continue
        assert result.status == SelectionStatus.READY
        assert result.file.name == "004_fallback.md"
        assert "005B_second.md" in result.skip_reasons

    def test_exclude_bypasses_conflict_and_selects_next(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """--exclude flag skips specified file, allowing selector to continue to next."""
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
            mock_queued_dir, mock_wip_dir, mock_completed_dir,
            exclude={"005_overlapping.md"}
        )

        assert result.status == SelectionStatus.READY
        assert result.file.name == "004_safe.md"

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

    def test_multiple_wip_conflicts_stops_at_first(self, mock_queued_dir, mock_wip_dir, mock_completed_dir):
        """When multiple files have WIP conflicts, stops at the highest-priority one."""
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

        # Stops at 005 (highest priority), not 004
        assert result.status == SelectionStatus.CONFLICT
        assert result.file.name == "005_overlap1.md"
        assert result.conflict_with == "006_active.md"


import json
import subprocess


class TestCLI:
    """Tests for CLI interface."""

    def test_cli_outputs_json(self, tmp_path):
        """CLI outputs valid JSON to stdout."""
        # Create directory structure (primary .handovers/ path)
        queued = tmp_path / ".handovers" / "queued"
        wip = tmp_path / ".handovers" / "WIP"
        completed = tmp_path / ".handovers" / "completed"
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
        queued = tmp_path / ".handovers" / "queued"
        wip = tmp_path / ".handovers" / "WIP"
        completed = tmp_path / ".handovers" / "completed"
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