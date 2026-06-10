import os
import subprocess
import re


def test_result_file_exists():
    """Test that result.txt file exists."""
    assert os.path.exists("/app/result.txt"), "result.txt file does not exist at /app/result.txt"


def test_result_file_not_empty():
    """Test that result.txt is not empty."""
    with open("/app/result.txt", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "result.txt is empty"


def test_result_contains_valid_commit_hash():
    """Test that result.txt contains a valid 40-character SHA-1 hash."""
    with open("/app/result.txt", "r") as f:
        content = f.read().strip()

    # Check if it's a valid 40-character hexadecimal string
    assert len(content) == 40, f"Commit hash should be 40 characters, got {len(content)}"
    assert re.match(r'^[0-9a-f]{40}$', content), f"Invalid commit hash format: {content}"


def test_result_is_single_line():
    """Test that result.txt contains only a single line (no extra text)."""
    with open("/app/result.txt", "r") as f:
        lines = f.readlines()

    assert len(lines) == 1, f"result.txt should contain exactly one line, got {len(lines)} lines"


def test_commit_hash_exists_in_repo():
    """Test that the commit hash in result.txt actually exists in the git repository."""
    with open("/app/result.txt", "r") as f:
        commit_hash = f.read().strip()

    # Verify the commit exists in the repository
    result = subprocess.run(
        ["git", "-C", "/app", "cat-file", "-t", commit_hash],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Commit {commit_hash} does not exist in the repository"
    assert result.stdout.strip() == "commit", f"Hash {commit_hash} is not a commit object"


def test_commit_is_the_first_bad_commit():
    """Test that the identified commit is actually the first commit where the test fails."""
    with open("/app/result.txt", "r") as f:
        bad_commit = f.read().strip()

    # Test that this commit fails the test
    result = subprocess.run(
        ["git", "-C", "/app", "checkout", bad_commit],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to checkout commit {bad_commit}"

    test_result = subprocess.run(["/app/test.sh"], capture_output=True)
    assert test_result.returncode != 0, f"Commit {bad_commit} should fail the test but it passed"

    # Get the parent commit
    parent_result = subprocess.run(
        ["git", "-C", "/app", "rev-parse", f"{bad_commit}^"],
        capture_output=True,
        text=True
    )

    if parent_result.returncode == 0:
        parent_commit = parent_result.stdout.strip()

        # Checkout parent and verify it passes
        subprocess.run(
            ["git", "-C", "/app", "checkout", parent_commit],
            capture_output=True
        )

        parent_test_result = subprocess.run(["/app/test.sh"], capture_output=True)
        assert parent_test_result.returncode == 0, \
            f"Parent commit {parent_commit} should pass the test but it failed. " \
            f"This means {bad_commit} is not the first bad commit."

    # Restore HEAD
    subprocess.run(["git", "-C", "/app", "checkout", "HEAD"], capture_output=True)


def test_no_extra_whitespace_or_formatting():
    """Test that result.txt contains only the hash with no extra whitespace or formatting."""
    with open("/app/result.txt", "r") as f:
        content = f.read()

    stripped = content.strip()

    # Should be exactly the hash plus a newline (or just the hash)
    assert content == stripped + "\n" or content == stripped, \
        "result.txt should contain only the commit hash with at most one trailing newline"


def test_not_hardcoded_dummy_hash():
    """Test that the result is not a dummy/placeholder hash."""
    with open("/app/result.txt", "r") as f:
        commit_hash = f.read().strip()

    # Check for common dummy patterns
    dummy_patterns = [
        "0" * 40,
        "1" * 40,
        "a" * 40,
        "f" * 40,
        "1234567890" * 4,
    ]

    assert commit_hash not in dummy_patterns, \
        f"Commit hash appears to be a dummy/placeholder value: {commit_hash}"


def test_bisect_automate_script_exists():
    """Test that the bisect_automate.sh script was created."""
    assert os.path.exists("/app/bisect_automate.sh"), \
        "bisect_automate.sh script does not exist at /app/bisect_automate.sh"


def test_bisect_automate_script_is_executable():
    """Test that bisect_automate.sh is executable."""
    assert os.access("/app/bisect_automate.sh", os.X_OK), \
        "bisect_automate.sh is not executable"


def test_git_bisect_was_reset():
    """Test that git bisect was properly reset (no active bisect session)."""
    result = subprocess.run(
        ["git", "-C", "/app", "bisect", "log"],
        capture_output=True,
        text=True
    )

    # If bisect was properly reset, this command should fail or return empty
    assert result.returncode != 0 or len(result.stdout.strip()) == 0, \
        "Git bisect session was not properly reset"
