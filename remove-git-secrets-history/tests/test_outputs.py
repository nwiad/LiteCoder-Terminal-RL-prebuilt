import os
import subprocess
import re


def test_cleanup_report_exists():
    """Verify cleanup_report.txt exists."""
    assert os.path.exists("/app/cleanup_report.txt"), "cleanup_report.txt not found"


def test_gitignore_exists():
    """Verify .gitignore exists."""
    assert os.path.exists("/app/.gitignore"), ".gitignore not found"


def test_gitignore_content():
    """Verify .gitignore contains required patterns."""
    with open("/app/.gitignore", "r") as f:
        content = f.read()

    assert "config.json" in content, ".gitignore missing config.json"
    assert "*.env" in content, ".gitignore missing *.env pattern"
    assert "secrets/" in content, ".gitignore missing secrets/ directory"


def test_config_not_in_working_directory():
    """Verify config.json is not in the working directory."""
    assert not os.path.exists("/app/config.json"), "config.json still exists in working directory"


def test_git_repository_exists():
    """Verify git repository is initialized."""
    assert os.path.exists("/app/.git"), "Git repository not initialized"


def test_three_commits_exist():
    """Verify exactly 3 commits exist after cleanup."""
    result = subprocess.run(
        ["git", "-C", "/app", "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True
    )
    commit_count = int(result.stdout.strip())
    assert commit_count == 3, f"Expected 3 commits, found {commit_count}"


def test_config_not_in_git_history():
    """Verify config.json does not appear in any commit in git history."""
    # Check if config.json appears in any commit
    result = subprocess.run(
        ["git", "-C", "/app", "log", "--all", "--full-history", "--", "config.json"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "", "config.json still exists in git history"

    # Double-check by searching all commits for the file
    result = subprocess.run(
        ["git", "-C", "/app", "rev-list", "--all"],
        capture_output=True,
        text=True
    )
    commits = result.stdout.strip().split("\n")

    for commit in commits:
        result = subprocess.run(
            ["git", "-C", "/app", "ls-tree", "-r", commit, "--name-only"],
            capture_output=True,
            text=True
        )
        files = result.stdout.strip().split("\n")
        assert "config.json" not in files, f"config.json found in commit {commit}"


def test_sensitive_data_not_in_history():
    """Verify sensitive data strings don't appear in git history."""
    # Search for the actual sensitive strings in all commits
    result = subprocess.run(
        ["git", "-C", "/app", "log", "--all", "-p"],
        capture_output=True,
        text=True
    )
    git_log = result.stdout

    assert "sk_live_abc123xyz" not in git_log, "API key found in git history"
    assert "secret_token_456" not in git_log, "Secret token found in git history"


def test_required_files_exist():
    """Verify required files exist in the repository."""
    assert os.path.exists("/app/src/main.py"), "src/main.py not found"
    assert os.path.exists("/app/README.md"), "README.md not found"


def test_remote_repository_exists():
    """Verify remote repository exists."""
    result = subprocess.run(
        ["git", "-C", "/app", "remote", "-v"],
        capture_output=True,
        text=True
    )
    assert "origin" in result.stdout, "Remote 'origin' not configured"


def test_remote_repository_cleaned():
    """Verify remote repository does not contain config.json in history."""
    # Get remote URL
    result = subprocess.run(
        ["git", "-C", "/app", "remote", "get-url", "origin"],
        capture_output=True,
        text=True
    )
    remote_url = result.stdout.strip()

    # Clone remote to temporary location
    temp_dir = "/tmp/test_remote_verify"
    subprocess.run(["rm", "-rf", temp_dir], capture_output=True)

    result = subprocess.run(
        ["git", "clone", remote_url, temp_dir],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Failed to clone remote repository"

    # Check if config.json exists in remote history
    result = subprocess.run(
        ["git", "-C", temp_dir, "log", "--all", "--full-history", "--", "config.json"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "", "config.json found in remote repository history"

    # Verify commit count in remote
    result = subprocess.run(
        ["git", "-C", temp_dir, "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True
    )
    remote_commit_count = int(result.stdout.strip())
    assert remote_commit_count == 3, f"Remote has {remote_commit_count} commits, expected 3"


def test_cleanup_report_structure():
    """Verify cleanup_report.txt contains required information."""
    with open("/app/cleanup_report.txt", "r") as f:
        content = f.read()

    # Check for key sections
    assert "config.json" in content.lower(), "Report doesn't mention config.json"
    assert "removed" in content.lower() or "success" in content.lower(), "Report doesn't confirm removal"

    # Check for commit statistics
    assert re.search(r"commits?\s+(before|after)", content.lower()), "Report missing commit statistics"

    # Check for file listing
    assert "main.py" in content or "src/main.py" in content, "Report doesn't list main.py"
    assert "README.md" in content, "Report doesn't list README.md"

    # Verify config.json is NOT listed in remaining files
    lines = content.split("\n")
    in_file_list = False
    for line in lines:
        if "remaining files" in line.lower():
            in_file_list = True
        if in_file_list and "config.json" in line.lower():
            assert False, "config.json listed in remaining files"

    # Check for remote verification
    assert "remote" in content.lower(), "Report doesn't mention remote repository"


def test_cleanup_report_commit_counts():
    """Verify cleanup report shows correct commit counts."""
    with open("/app/cleanup_report.txt", "r") as f:
        content = f.read()

    # Extract commit counts from report
    before_match = re.search(r"before.*?:\s*(\d+)", content, re.IGNORECASE)
    after_match = re.search(r"after.*?:\s*(\d+)", content, re.IGNORECASE)

    assert before_match, "Report doesn't contain 'commits before' count"
    assert after_match, "Report doesn't contain 'commits after' count"

    commits_before = int(before_match.group(1))
    commits_after = int(after_match.group(1))

    assert commits_before == 3, f"Report shows {commits_before} commits before, expected 3"
    assert commits_after == 3, f"Report shows {commits_after} commits after, expected 3"


def test_no_hardcoded_dummy_report():
    """Ensure report is not just a hardcoded dummy file."""
    with open("/app/cleanup_report.txt", "r") as f:
        content = f.read()

    # Report should be substantial (not just a few lines)
    lines = [line for line in content.split("\n") if line.strip()]
    assert len(lines) >= 10, "Report appears to be a dummy file (too short)"

    # Report should contain actual file listings
    assert "src/main.py" in content or "main.py" in content, "Report doesn't contain actual file listings"


def test_git_commits_have_correct_structure():
    """Verify the three commits exist with proper structure."""
    # Get commit messages
    result = subprocess.run(
        ["git", "-C", "/app", "log", "--format=%s", "--reverse"],
        capture_output=True,
        text=True
    )
    messages = result.stdout.strip().split("\n")

    assert len(messages) == 3, f"Expected 3 commit messages, found {len(messages)}"

    # First commit should mention initial/config (but not contain config.json file)
    result = subprocess.run(
        ["git", "-C", "/app", "rev-list", "--reverse", "HEAD"],
        capture_output=True,
        text=True
    )
    first_commit = result.stdout.strip().split("\n")[0]

    # Verify first commit does NOT contain config.json
    result = subprocess.run(
        ["git", "-C", "/app", "ls-tree", "-r", first_commit, "--name-only"],
        capture_output=True,
        text=True
    )
    files_in_first_commit = result.stdout.strip().split("\n")
    assert "config.json" not in files_in_first_commit, "config.json still in first commit"

    # Verify main.py exists in first commit
    assert any("main.py" in f for f in files_in_first_commit), "main.py not in first commit"
