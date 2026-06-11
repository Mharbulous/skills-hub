#!/usr/bin/env python3
"""Unit tests for commit_ingestion.py — tests parsing and classification logic."""

import os
import sys

# Add scripts directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from unittest.mock import patch, MagicMock

from commit_ingestion import (
    is_trivial, get_areas_touched, parse_git_log,
    count_commits_since, get_recent_cursor, init_cursor,
)


def test_is_trivial():
    """Test trivial commit detection."""
    # Trivial cases
    assert is_trivial("style: fix formatting") is True
    assert is_trivial("style(auth): reformat imports") is True
    assert is_trivial("fix typo in readme") is True
    assert is_trivial("Fix Typo in config") is True
    assert is_trivial("formatting fixes") is True
    assert is_trivial("whitespace cleanup") is True

    # Non-trivial cases
    assert is_trivial("feat: add user authentication") is False
    assert is_trivial("fix: resolve login bug") is False
    assert is_trivial("refactor: reorganize utils") is False
    assert is_trivial("docs: update API reference") is False
    assert is_trivial("chore: update dependencies") is False
    assert is_trivial("test: add unit tests") is False
    assert is_trivial("perf: optimize query") is False
    assert is_trivial("ci: update workflow") is False
    assert is_trivial("build: update webpack config") is False


def test_get_areas_touched():
    """Test area extraction from file paths."""
    # Basic directory extraction
    assert get_areas_touched(["src/auth/login.py"]) == ["src/auth/"]
    assert get_areas_touched(["src/auth/login.py", "src/auth/middleware.py"]) == ["src/auth/"]

    # Multiple directories
    result = get_areas_touched([
        "src/auth/login.py",
        "src/auth/middleware.py",
        "tests/test_auth.py",
    ])
    assert result == ["src/auth/", "tests/"]

    # Root-level file
    assert get_areas_touched(["README.md"]) == [""]
    assert get_areas_touched(["CHANGELOG.md"]) == [""]

    # Mixed root and nested
    result = get_areas_touched(["README.md", "src/config.py"])
    assert result == ["", "src/"]

    # Deep nesting — extracts immediate parent
    assert get_areas_touched(["src/components/auth/forms/login/LoginForm.vue"]) == [
        "src/components/auth/forms/login/"
    ]

    # Deduplication
    result = get_areas_touched([
        "src/utils/helpers.py",
        "src/utils/formatters.py",
        "src/core/config.py",
    ])
    assert result == ["src/core/", "src/utils/"]

    # Sorted output
    result = get_areas_touched([
        "tests/test_upload.py",
        "src/upload/handler.py",
        "src/workers/hash_worker.py",
    ])
    assert result == ["src/upload/", "src/workers/", "tests/"]


def test_parse_git_log():
    """Test git log parsing with the baseline scenario."""
    raw_output = """COMMIT:bbb2222222222222222222222222222222222222|feat: add user authentication

src/auth/login.py
src/auth/middleware.py
tests/test_auth.py
COMMIT:ccc3333333333333333333333333333333333333|fix typo in readme

README.md
COMMIT:ddd4444444444444444444444444444444444444|refactor: reorganize utils and helpers

src/utils/helpers.py
src/utils/formatters.py
src/core/config.py
COMMIT:eee5555555555555555555555555555555555555|style: fix formatting

src/auth/login.py
COMMIT:fff6666666666666666666666666666666666666|feat: add file upload with hashing

src/upload/handler.py
src/upload/hasher.py
src/workers/hash_worker.py
tests/test_upload.py"""

    commits = parse_git_log(raw_output)

    assert len(commits) == 5

    # Commit 1: feat: add user authentication
    c1 = commits[0]
    assert c1["hash"] == "bbb2222222222222222222222222222222222222"
    assert c1["msg"] == "feat: add user authentication"
    assert c1["files"] == ["src/auth/login.py", "src/auth/middleware.py", "tests/test_auth.py"]
    assert c1["areas_touched"] == ["src/auth/", "tests/"]
    assert c1["trivial"] is False

    # Commit 2: fix typo in readme (trivial)
    c2 = commits[1]
    assert c2["hash"] == "ccc3333333333333333333333333333333333333"
    assert c2["msg"] == "fix typo in readme"
    assert c2["files"] == ["README.md"]
    assert c2["areas_touched"] == [""]
    assert c2["trivial"] is True

    # Commit 3: refactor
    c3 = commits[2]
    assert c3["hash"] == "ddd4444444444444444444444444444444444444"
    assert c3["msg"] == "refactor: reorganize utils and helpers"
    assert c3["files"] == ["src/utils/helpers.py", "src/utils/formatters.py", "src/core/config.py"]
    assert c3["areas_touched"] == ["src/core/", "src/utils/"]
    assert c3["trivial"] is False

    # Commit 4: style (trivial)
    c4 = commits[3]
    assert c4["hash"] == "eee5555555555555555555555555555555555555"
    assert c4["msg"] == "style: fix formatting"
    assert c4["files"] == ["src/auth/login.py"]
    assert c4["areas_touched"] == ["src/auth/"]
    assert c4["trivial"] is True

    # Commit 5: feat
    c5 = commits[4]
    assert c5["hash"] == "fff6666666666666666666666666666666666666"
    assert c5["msg"] == "feat: add file upload with hashing"
    assert c5["files"] == [
        "src/upload/handler.py", "src/upload/hasher.py",
        "src/workers/hash_worker.py", "tests/test_upload.py"
    ]
    assert c5["areas_touched"] == ["src/upload/", "src/workers/", "tests/"]
    assert c5["trivial"] is False


def test_parse_git_log_empty():
    """Test parsing empty git log output."""
    commits = parse_git_log("")
    assert commits == []

    commits = parse_git_log("\n\n")
    assert commits == []


def test_parse_git_log_single_commit():
    """Test parsing a single commit."""
    raw = "COMMIT:abc123|fix: resolve bug\nsrc/main.py"
    commits = parse_git_log(raw)
    assert len(commits) == 1
    assert commits[0]["hash"] == "abc123"
    assert commits[0]["msg"] == "fix: resolve bug"
    assert commits[0]["files"] == ["src/main.py"]


def test_parse_git_log_no_files():
    """Test commit with no files (empty commit)."""
    raw = "COMMIT:abc123|chore: empty commit"
    commits = parse_git_log(raw)
    assert len(commits) == 1
    assert commits[0]["files"] == []
    assert commits[0]["areas_touched"] == []


def test_parse_git_log_pipe_in_message():
    """Test message containing pipe character."""
    raw = "COMMIT:abc123|feat: add x | y support\nsrc/main.py"
    commits = parse_git_log(raw)
    assert commits[0]["msg"] == "feat: add x | y support"


@patch("commit_ingestion.subprocess.run")
def test_count_commits_since(mock_run):
    """Test counting commits between cursor and HEAD."""
    mock_run.return_value = MagicMock(returncode=0, stdout="350\n")
    assert count_commits_since("/repo", "abc123") == 350
    mock_run.assert_called_once_with(
        ["git", "rev-list", "--count", "abc123..HEAD"],
        capture_output=True, text=True, encoding="utf-8", cwd="/repo",
    )


@patch("commit_ingestion.subprocess.run")
def test_count_commits_since_error(mock_run):
    """Test count_commits_since returns 0 on git failure."""
    mock_run.return_value = MagicMock(returncode=128, stdout="")
    assert count_commits_since("/repo", "badref") == 0


@patch("commit_ingestion.subprocess.run")
def test_get_recent_cursor_normal(mock_run):
    """Test get_recent_cursor returns hash for HEAD~n."""
    mock_run.return_value = MagicMock(returncode=0, stdout="def456\n")
    assert get_recent_cursor("/repo", 100) == "def456"
    mock_run.assert_called_once_with(
        ["git", "rev-list", "-1", "HEAD~100"],
        capture_output=True, text=True, encoding="utf-8", cwd="/repo",
    )


@patch("commit_ingestion.subprocess.run")
def test_get_recent_cursor_small_repo(mock_run):
    """Test get_recent_cursor falls back to earliest commit for small repos."""
    # First call (HEAD~100) fails, second call (rev-list --reverse) succeeds
    mock_run.side_effect = [
        MagicMock(returncode=128, stdout=""),
        MagicMock(returncode=0, stdout="aaa111\nbbb222\nccc333\n"),
    ]
    assert get_recent_cursor("/repo", 100) == "aaa111"
    assert mock_run.call_count == 2


@patch("commit_ingestion.get_recent_cursor", return_value="abc100")
def test_init_cursor(mock_get_recent):
    """Test init_cursor writes cursor to database."""
    import sqlite3
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Create schema
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE repo_cursors ("
            "repo TEXT PRIMARY KEY, last_commit_hash TEXT NOT NULL, "
            "last_commit_timestamp TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()
        conn.close()

        result = init_cursor(db_path, "test-repo", "/repo")

        assert result == {"cursor": "abc100", "repo": "test-repo"}
        mock_get_recent.assert_called_once_with("/repo", 100)

        # Verify database was written
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT last_commit_hash FROM repo_cursors WHERE repo = ?",
            ("test-repo",),
        ).fetchone()
        conn.close()
        assert row[0] == "abc100"
    finally:
        os.unlink(db_path)


@patch("commit_ingestion.get_recent_cursor", return_value="")
def test_init_cursor_no_commits(mock_get_recent):
    """Test init_cursor returns error when repo has no commits."""
    result = init_cursor("/fake.db", "test-repo", "/repo")
    assert "error" in result


if __name__ == "__main__":
    test_is_trivial()
    test_get_areas_touched()
    test_parse_git_log()
    test_parse_git_log_empty()
    test_parse_git_log_single_commit()
    test_parse_git_log_no_files()
    test_parse_git_log_pipe_in_message()
    test_count_commits_since(MagicMock())
    test_count_commits_since_error(MagicMock())
    test_get_recent_cursor_normal(MagicMock())
    test_get_recent_cursor_small_repo(MagicMock())
    test_init_cursor(MagicMock())
    test_init_cursor_no_commits(MagicMock())
    print("All tests passed!")
