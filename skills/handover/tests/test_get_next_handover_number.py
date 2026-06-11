import pytest
from pathlib import Path
import tempfile
import subprocess
import sys
from get_next_handover_number import get_next_handover_number


def test_returns_next_number_when_completed_has_files():
    """Should return highest number + 1 from completed folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create folder structure
        handovers = repo_path / ".handovers"
        completed = handovers / "completed"
        wip = handovers / "WIP"
        queued = handovers / "queued"

        completed.mkdir(parents=True)
        wip.mkdir(parents=True)
        queued.mkdir(parents=True)

        # Create test files
        (completed / "035_test.md").touch()
        (completed / "036_another.md").touch()
        (completed / "037_latest.md").touch()

        result = get_next_handover_number(repo_path)

        assert result == 38


def test_ignores_letter_suffixes():
    """Should extract numeric prefix only, ignoring letter suffixes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        handovers = repo_path / ".handovers"
        completed = handovers / "completed"
        wip = handovers / "WIP"
        queued = handovers / "queued"

        completed.mkdir(parents=True)
        wip.mkdir(parents=True)
        queued.mkdir(parents=True)

        # Files with letter suffixes
        (completed / "036_task.md").touch()
        (wip / "038A_chain-task.md").touch()
        (wip / "038B_another-chain.md").touch()

        result = get_next_handover_number(repo_path)

        assert result == 39  # 038B → 38 → next is 39


def test_returns_one_when_all_folders_empty():
    """Should return 1 when no handover files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        handovers = repo_path / ".handovers"
        (handovers / "completed").mkdir(parents=True)
        (handovers / "WIP").mkdir(parents=True)
        (handovers / "queued").mkdir(parents=True)

        result = get_next_handover_number(repo_path)

        assert result == 1


def test_returns_one_when_folders_missing():
    """Should return 1 when handover folders don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        result = get_next_handover_number(repo_path)

        assert result == 1


def test_matches_hyphen_separator():
    """Should match files using hyphen separator between number and slug."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        handovers = repo_path / ".handovers"
        completed = handovers / "completed"
        completed.mkdir(parents=True)
        (handovers / "WIP").mkdir(parents=True)
        (handovers / "queued").mkdir(parents=True)

        # Mix of underscore and hyphen separators
        (completed / "153A-brainstorm-visual.md").touch()
        (completed / "155_move-buttons.md").touch()
        (completed / "156_reverse-tabs.md").touch()

        result = get_next_handover_number(repo_path)

        assert result == 157  # 156 is highest


def test_ignores_malformed_filenames():
    """Should skip files that don't match naming convention."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        handovers = repo_path / ".handovers"
        completed = handovers / "completed"
        completed.mkdir(parents=True)
        (handovers / "WIP").mkdir(parents=True)
        (handovers / "queued").mkdir(parents=True)

        # Valid files
        (completed / "010_valid.md").touch()

        # Invalid files (should be ignored)
        (completed / "readme.md").touch()
        (completed / "no-number.md").touch()
        (completed / "A10_wrong-order.md").touch()

        result = get_next_handover_number(repo_path)

        assert result == 11  # Only 010 counted


def test_scans_all_three_folders():
    """Should find highest number across queued, WIP, and completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        handovers = repo_path / ".handovers"
        completed = handovers / "completed"
        wip = handovers / "WIP"
        queued = handovers / "queued"

        completed.mkdir(parents=True)
        wip.mkdir(parents=True)
        queued.mkdir(parents=True)

        # Spread numbers across folders
        (completed / "037_done.md").touch()
        (wip / "038A_working.md").touch()
        (queued / "040_waiting.md").touch()  # Highest

        result = get_next_handover_number(repo_path)

        assert result == 41


def test_cli_returns_just_number():
    """CLI should output just the number for easy integration."""
    result = subprocess.run(
        [sys.executable, "scripts/get_next_handover_number.py"],
        cwd="C:/Users/Brahm/.claude/skills/handover",
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    output = result.stdout.strip()
    assert output.isdigit()
    assert int(output) >= 1


def test_cli_accepts_repo_path_argument():
    """CLI should accept optional repository path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        handovers = repo_path / ".handovers"
        completed = handovers / "completed"
        completed.mkdir(parents=True)
        (handovers / "WIP").mkdir(parents=True)
        (handovers / "queued").mkdir(parents=True)

        (completed / "025_test.md").touch()

        result = subprocess.run(
            [sys.executable, "scripts/get_next_handover_number.py", str(repo_path)],
            cwd="C:/Users/Brahm/.claude/skills/handover",
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "026"


def test_integration_with_gitilation_repo():
    """Integration test: should return 039 for current Gitilation state."""
    gitilation_path = Path("C:/Users/Brahm/Git/Gitilation")

    if not gitilation_path.exists():
        pytest.skip("Gitilation repository not found at expected path")

    result = get_next_handover_number(gitilation_path)

    # Based on handover context: highest is 037 in completed, 038A in WIP
    # So next should be 039
    assert result >= 39, f"Expected at least 39, got {result}"
