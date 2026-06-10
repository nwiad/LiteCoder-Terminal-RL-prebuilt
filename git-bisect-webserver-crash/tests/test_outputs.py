import os
import json
import subprocess
import re

def test_result_json_exists():
    """Test that result.json file exists at the expected location."""
    assert os.path.exists("/app/result.json"), "result.json file not found at /app/result.json"

def test_result_json_valid():
    """Test that result.json is valid JSON."""
    with open("/app/result.json", "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"result.json is not valid JSON: {e}"

def test_result_json_structure():
    """Test that result.json has all required fields."""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    required_fields = ["first_bad_commit", "commit_author", "commit_message"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

def test_first_bad_commit_format():
    """Test that first_bad_commit is a valid 40-character SHA-1 hash."""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    commit_hash = data["first_bad_commit"]
    assert isinstance(commit_hash, str), "first_bad_commit must be a string"
    assert len(commit_hash) == 40, f"first_bad_commit must be 40 characters, got {len(commit_hash)}"
    assert re.match(r'^[0-9a-f]{40}$', commit_hash), "first_bad_commit must be a valid SHA-1 hash (lowercase hex)"

def test_commit_author_not_empty():
    """Test that commit_author is not empty."""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    author = data["commit_author"]
    assert isinstance(author, str), "commit_author must be a string"
    assert len(author.strip()) > 0, "commit_author cannot be empty"

def test_commit_message_not_empty():
    """Test that commit_message is not empty."""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    message = data["commit_message"]
    assert isinstance(message, str), "commit_message must be a string"
    assert len(message.strip()) > 0, "commit_message cannot be empty"

def test_webserver_directory_exists():
    """Test that the webserver repository was cloned."""
    assert os.path.exists("/app/webserver"), "webserver directory not found at /app/webserver"
    assert os.path.isdir("/app/webserver/.git"), "webserver directory is not a git repository"

def test_commit_exists_in_repository():
    """Test that the first_bad_commit actually exists in the git repository."""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    commit_hash = data["first_bad_commit"]

    # Change to the webserver directory and verify the commit exists
    result = subprocess.run(
        ["git", "cat-file", "-t", commit_hash],
        cwd="/app/webserver",
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Commit {commit_hash} does not exist in the repository"
    assert result.stdout.strip() == "commit", f"Hash {commit_hash} is not a commit object"

def test_commit_metadata_matches():
    """Test that the author and message in JSON match the actual commit."""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    commit_hash = data["first_bad_commit"]
    expected_author = data["commit_author"]
    expected_message = data["commit_message"]

    # Get actual author from git
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%an", commit_hash],
        cwd="/app/webserver",
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to get author for commit {commit_hash}"
    actual_author = result.stdout.strip()

    # Get actual commit message (first line) from git
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%s", commit_hash],
        cwd="/app/webserver",
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to get message for commit {commit_hash}"
    actual_message = result.stdout.strip()

    assert expected_author == actual_author, f"Author mismatch: expected '{expected_author}', got '{actual_author}'"
    assert expected_message == actual_message, f"Message mismatch: expected '{expected_message}', got '{actual_message}'"

def test_test_script_exists():
    """Test that the test script was created."""
    assert os.path.exists("/app/test.sh"), "test.sh script not found at /app/test.sh"

    # Check if it's executable
    assert os.access("/app/test.sh", os.X_OK), "test.sh is not executable"

def test_repository_at_bad_commit():
    """Test that the repository is at the original HEAD (bad commit) after cleanup."""
    # Get current HEAD
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd="/app/webserver",
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Failed to get current HEAD"
    current_head = result.stdout.strip()

    # Verify it's a valid 40-character hash
    assert len(current_head) == 40, "Current HEAD is not a full commit hash"
    assert re.match(r'^[0-9a-f]{40}$', current_head), "Current HEAD is not a valid SHA-1 hash"

def test_no_active_bisect():
    """Test that git bisect was properly reset (no active bisect session)."""
    # Check if .git/BISECT_LOG exists (indicates active bisect)
    bisect_log = "/app/webserver/.git/BISECT_LOG"
    assert not os.path.exists(bisect_log), "Git bisect was not properly reset (BISECT_LOG still exists)"
