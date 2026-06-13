"""Tests for chain mode handover processing."""
import pytest
from pathlib import Path


class TestChainDetection:
    """Tests for detecting handover chains."""

    def test_detects_letter_suffix_chain(self, mock_queued_dir):
        """Chains have same number with letter suffixes."""
        # Create chain: 005A, 005B, 005C
        (mock_queued_dir / "005A_first-task.md").write_text("---\nwrite_targets: []\n---\nTask A")
        (mock_queued_dir / "005B_second-task.md").write_text("---\nwrite_targets: []\n---\nTask B")
        (mock_queued_dir / "005C_third-task.md").write_text("---\nwrite_targets: []\n---\nTask C")

        from handover_utils import detect_chains
        chains = detect_chains(mock_queued_dir)

        assert len(chains) == 1
        assert chains[0]["number"] == "005"
        assert len(chains[0]["files"]) == 3
        assert chains[0]["files"][0].name == "005A_first-task.md"
        assert chains[0]["files"][1].name == "005B_second-task.md"
        assert chains[0]["files"][2].name == "005C_third-task.md"

    def test_single_file_not_a_chain(self, mock_queued_dir):
        """Single numbered file is not a chain."""
        (mock_queued_dir / "005_solo-task.md").write_text("---\nwrite_targets: []\n---\nSolo")

        from handover_utils import detect_chains
        chains = detect_chains(mock_queued_dir)

        assert len(chains) == 0

    def test_multiple_chains_detected(self, mock_queued_dir):
        """Multiple separate chains are detected."""
        # Chain 1: 006A, 006B
        (mock_queued_dir / "006A_chain1-a.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "006B_chain1-b.md").write_text("---\nwrite_targets: []\n---\n")
        # Chain 2: 005A, 005B, 005C
        (mock_queued_dir / "005A_chain2-a.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005B_chain2-b.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005C_chain2-c.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_utils import detect_chains
        chains = detect_chains(mock_queued_dir)

        assert len(chains) == 2
        # Sorted by number descending (006 before 005)
        assert chains[0]["number"] == "006"
        assert chains[1]["number"] == "005"


class TestHandoverSorting:
    """Tests for handover file sorting."""

    def test_sorts_numbers_descending(self, mock_queued_dir):
        """Numbers sort in descending order (LIFO)."""
        (mock_queued_dir / "003_task.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "001_task.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "002_task.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_utils import sort_handovers
        sorted_files = sort_handovers(mock_queued_dir)

        assert [f.name for f in sorted_files] == [
            "003_task.md",
            "002_task.md",
            "001_task.md"
        ]

    def test_sorts_letters_ascending_within_number(self, mock_queued_dir):
        """Letters sort ascending within same number (FIFO)."""
        (mock_queued_dir / "005C_task.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005A_task.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005B_task.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_utils import sort_handovers
        sorted_files = sort_handovers(mock_queued_dir)

        assert [f.name for f in sorted_files] == [
            "005A_task.md",
            "005B_task.md",
            "005C_task.md"
        ]

    def test_mixed_sorting(self, mock_queued_dir):
        """Mixed numbers and letters sort correctly."""
        (mock_queued_dir / "004_solo.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005B_chain.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "005A_chain.md").write_text("---\nwrite_targets: []\n---\n")
        (mock_queued_dir / "006_another.md").write_text("---\nwrite_targets: []\n---\n")

        from handover_utils import sort_handovers
        sorted_files = sort_handovers(mock_queued_dir)

        # 006 first (highest), then 005A, 005B, then 004
        assert [f.name for f in sorted_files] == [
            "006_another.md",
            "005A_chain.md",
            "005B_chain.md",
            "004_solo.md"
        ]


class TestSubagentPromptGeneration:
    """Tests for generating work subagent prompts."""

    def test_generates_prompt_with_handover_content(self, mock_queued_dir):
        """Prompt includes handover file content."""
        handover_content = """---
write_targets:
  - src/feature.py
read_only_targets:
  - src/utils.py
---

## Task
Implement the feature as described.

## Acceptance Criteria
- Feature works correctly
"""
        handover_file = mock_queued_dir / "005A_implement-feature.md"
        handover_file.write_text(handover_content)

        from handover_utils import generate_subagent_prompt
        prompt = generate_subagent_prompt(handover_file, mock_queued_dir.parent.parent.parent)

        assert "005A_implement-feature.md" in prompt
        assert "Implement the feature as described" in prompt
        assert "src/feature.py" in prompt

    def test_prompt_includes_wip_move_instruction(self, mock_queued_dir):
        """Prompt instructs subagent to move file to WIP."""
        handover_file = mock_queued_dir / "005A_task.md"
        handover_file.write_text("---\nwrite_targets: []\n---\nDo something")

        from handover_utils import generate_subagent_prompt
        prompt = generate_subagent_prompt(handover_file, mock_queued_dir.parent.parent.parent)

        assert "WIP" in prompt
        assert "move" in prompt.lower() or "Move" in prompt

    def test_prompt_includes_json_response_format(self, mock_queued_dir):
        """Prompt requests JSON response for orchestrator parsing."""
        handover_file = mock_queued_dir / "005A_task.md"
        handover_file.write_text("---\nwrite_targets: []\n---\nDo something")

        from handover_utils import generate_subagent_prompt
        prompt = generate_subagent_prompt(handover_file, mock_queued_dir.parent.parent.parent)

        assert "JSON" in prompt
        assert "status" in prompt


class TestOrchestratorState:
    """Tests for orchestrator cumulative state management."""

    def test_initializes_empty_state(self):
        """Orchestrator starts with empty cumulative state."""
        from handover_utils import OrchestratorState
        state = OrchestratorState()

        assert state.processed == 0
        assert state.succeeded == 0
        assert state.failed == []
        assert state.new_handovers == 0

    def test_records_success(self):
        """State records successful handover completion."""
        from handover_utils import OrchestratorState
        state = OrchestratorState()

        result = {
            "status": "success",
            "files_modified": ["src/feature.py"],
            "commit_message": "feat: add feature",
            "new_handovers_created": 0
        }
        state.record_result("005A_task.md", result)

        assert state.processed == 1
        assert state.succeeded == 1
        assert state.failed == []

    def test_records_failure(self):
        """State records failed handover."""
        from handover_utils import OrchestratorState
        state = OrchestratorState()

        result = {
            "status": "failed",
            "error": "Could not parse file",
            "files_modified": [],
            "commit_message": None,
            "new_handovers_created": 0
        }
        state.record_result("005B_broken.md", result)

        assert state.processed == 1
        assert state.succeeded == 0
        assert state.failed == ["005B_broken.md"]

    def test_tracks_new_handovers(self):
        """State tracks new handovers created by subagents."""
        from handover_utils import OrchestratorState
        state = OrchestratorState()

        result = {
            "status": "success",
            "files_modified": ["src/feature.py"],
            "commit_message": "feat: add feature",
            "new_handovers_created": 2
        }
        state.record_result("005A_task.md", result)

        assert state.new_handovers == 2

    def test_generates_summary(self):
        """State generates human-readable summary."""
        from handover_utils import OrchestratorState
        state = OrchestratorState()

        state.record_result("005A_ok.md", {"status": "success", "files_modified": [], "new_handovers_created": 0})
        state.record_result("005B_bad.md", {"status": "failed", "error": "oops", "files_modified": [], "new_handovers_created": 0})
        state.record_result("005C_ok.md", {"status": "success", "files_modified": [], "new_handovers_created": 1})

        summary = state.get_summary()

        assert "3" in summary  # processed
        assert "2" in summary  # succeeded
        assert "1" in summary or "005B_bad.md" in summary  # failed
