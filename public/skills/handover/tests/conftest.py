"""Pytest configuration for handover skill tests."""
import pytest
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

@pytest.fixture
def handover_skill_dir():
    """Return path to handover skill directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def mock_queued_dir(tmp_path):
    """Create mock queued handover directory."""
    queued = tmp_path / ".handovers" / "queued"
    queued.mkdir(parents=True)
    return queued

@pytest.fixture
def mock_wip_dir(tmp_path):
    """Create mock WIP directory."""
    wip = tmp_path / ".handovers" / "WIP"
    wip.mkdir(parents=True)
    return wip

@pytest.fixture
def mock_completed_dir(tmp_path):
    """Create mock completed directory."""
    completed = tmp_path / ".handovers" / "completed"
    completed.mkdir(parents=True)
    return completed

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: integration tests")
