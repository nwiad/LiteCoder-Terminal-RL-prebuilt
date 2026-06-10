import os
import subprocess
import pytest


def run_git_command(cmd, cwd="/app"):
    """Helper to run git commands and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_git_repository_exists():
    """Verify that /app is a valid Git repository."""
    assert os.path.exists("/app/.git"), "Git repository not initialized in /app"


def test_main_branch_exists():
    """Verify that main branch exists with initial commit."""
    stdout, stderr, returncode = run_git_command("git rev-parse --verify main")
    assert returncode == 0, f"Main branch does not exist: {stderr}"


def test_feature_branch_exists():
    """Verify that feature/user-auth branch exists."""
    stdout, stderr, returncode = run_git_command("git rev-parse --verify feature/user-auth")
    assert returncode == 0, f"feature/user-auth branch does not exist: {stderr}"


def test_exactly_two_commits_ahead():
    """Verify feature/user-auth is exactly 2 commits ahead of main."""
    stdout, stderr, returncode = run_git_command("git rev-list --count main..feature/user-auth")
    assert returncode == 0, f"Failed to count commits: {stderr}"

    commit_count = int(stdout)
    assert commit_count == 2, f"Expected exactly 2 commits ahead of main, got {commit_count}"


def test_commit_messages():
    """Verify the two commit messages are exactly as specified."""
    stdout, stderr, returncode = run_git_command(
        "git log --format=%s main..feature/user-auth"
    )
    assert returncode == 0, f"Failed to get commit messages: {stderr}"

    messages = stdout.strip().split('\n')
    assert len(messages) == 2, f"Expected 2 commit messages, got {len(messages)}"

    # Messages are in reverse chronological order (newest first)
    assert messages[1] == "Implement authentication logic", \
        f"First commit message incorrect. Expected 'Implement authentication logic', got '{messages[1]}'"
    assert messages[0] == "Add tests and documentation", \
        f"Second commit message incorrect. Expected 'Add tests and documentation', got '{messages[0]}'"


def test_all_files_exist():
    """Verify all three required files exist in /app."""
    assert os.path.exists("/app/auth.py"), "auth.py file not found"
    assert os.path.exists("/app/test_auth.py"), "test_auth.py file not found"
    assert os.path.exists("/app/AUTH.md"), "AUTH.md file not found"
    assert os.path.exists("/app/README.md"), "README.md file not found (should be from initial commit)"


def test_auth_py_content():
    """Verify auth.py contains all three functions."""
    with open("/app/auth.py", "r") as f:
        content = f.read()

    assert "def login():" in content, "login() function not found in auth.py"
    assert "def logout():" in content, "logout() function not found in auth.py"
    assert "def validate():" in content, "validate() function not found in auth.py"

    # Verify it's not empty or just comments
    assert "pass" in content, "Functions should have 'pass' statements"


def test_test_auth_py_content():
    """Verify test_auth.py has expected content."""
    with open("/app/test_auth.py", "r") as f:
        content = f.read()

    assert "# tests" in content, "test_auth.py should contain '# tests'"


def test_auth_md_content():
    """Verify AUTH.md has expected content."""
    with open("/app/AUTH.md", "r") as f:
        content = f.read()

    assert "# Authentication" in content, "AUTH.md should contain '# Authentication'"


def test_readme_content():
    """Verify README.md from initial commit is preserved."""
    with open("/app/README.md", "r") as f:
        content = f.read()

    assert "# Project" in content, "README.md should contain '# Project' from initial commit"


def test_files_tracked_in_git():
    """Verify all files are tracked in Git, not just present in filesystem."""
    stdout, stderr, returncode = run_git_command("git ls-tree -r feature/user-auth --name-only")
    assert returncode == 0, f"Failed to list tracked files: {stderr}"

    tracked_files = stdout.strip().split('\n')
    assert "auth.py" in tracked_files, "auth.py not tracked in Git"
    assert "test_auth.py" in tracked_files, "test_auth.py not tracked in Git"
    assert "AUTH.md" in tracked_files, "AUTH.md not tracked in Git"
    assert "README.md" in tracked_files, "README.md not tracked in Git"


def test_commit_chronology():
    """Verify commits are in correct chronological order."""
    # Get commit hashes in chronological order (oldest to newest)
    stdout, stderr, returncode = run_git_command(
        "git log --reverse --format=%H main..feature/user-auth"
    )
    assert returncode == 0, f"Failed to get commit hashes: {stderr}"

    commits = stdout.strip().split('\n')
    assert len(commits) == 2, f"Expected 2 commits, got {len(commits)}"

    # First commit should contain auth.py
    stdout, _, _ = run_git_command(f"git show --name-only --format= {commits[0]}")
    first_commit_files = stdout.strip().split('\n')
    assert "auth.py" in first_commit_files, \
        "First commit should contain auth.py (authentication logic)"

    # Second commit should contain test_auth.py and AUTH.md
    stdout, _, _ = run_git_command(f"git show --name-only --format= {commits[1]}")
    second_commit_files = stdout.strip().split('\n')
    assert "test_auth.py" in second_commit_files or "AUTH.md" in second_commit_files, \
        "Second commit should contain test_auth.py or AUTH.md (tests/documentation)"


def test_first_commit_has_complete_auth():
    """Verify first commit contains complete auth.py with all functions."""
    # Get the first commit hash
    stdout, stderr, returncode = run_git_command(
        "git log --reverse --format=%H main..feature/user-auth"
    )
    assert returncode == 0, f"Failed to get commit hashes: {stderr}"

    first_commit = stdout.strip().split('\n')[0]

    # Get auth.py content from first commit
    stdout, stderr, returncode = run_git_command(f"git show {first_commit}:auth.py")
    assert returncode == 0, f"Failed to get auth.py from first commit: {stderr}"

    content = stdout
    assert "def login():" in content, "First commit should have login() function"
    assert "def logout():" in content, "First commit should have logout() function"
    assert "def validate():" in content, "First commit should have validate() function"


def test_no_extra_commits():
    """Verify there are no extra commits beyond the required 2."""
    stdout, stderr, returncode = run_git_command("git rev-list --count main..feature/user-auth")
    assert returncode == 0, f"Failed to count commits: {stderr}"

    commit_count = int(stdout)
    assert commit_count == 2, f"Should have exactly 2 commits, not more. Found {commit_count}"


def test_branch_divergence():
    """Verify feature/user-auth properly diverges from main."""
    # Check that main and feature/user-auth have different HEAD commits
    stdout_main, _, _ = run_git_command("git rev-parse main")
    stdout_feature, _, _ = run_git_command("git rev-parse feature/user-auth")

    assert stdout_main != stdout_feature, \
        "feature/user-auth should have different HEAD than main"

    # Verify main is an ancestor of feature/user-auth
    _, _, returncode = run_git_command(
        f"git merge-base --is-ancestor main feature/user-auth"
    )
    assert returncode == 0, "main should be an ancestor of feature/user-auth"


def test_no_merge_commits():
    """Verify there are no merge commits (rebase should create linear history)."""
    stdout, stderr, returncode = run_git_command(
        "git log --format=%p main..feature/user-auth"
    )
    assert returncode == 0, f"Failed to get parent commits: {stderr}"

    parent_lines = stdout.strip().split('\n')
    for line in parent_lines:
        # Each commit should have exactly one parent (no merge commits)
        parents = line.strip().split()
        assert len(parents) == 1, \
            f"Found merge commit with {len(parents)} parents. Rebase should create linear history."


def test_git_config():
    """Verify Git is configured with correct user information."""
    stdout_name, _, returncode_name = run_git_command("git config user.name")
    stdout_email, _, returncode_email = run_git_command("git config user.email")

    assert returncode_name == 0, "Git user.name not configured"
    assert returncode_email == 0, "Git user.email not configured"

    assert stdout_name == "Test User", f"Expected user.name 'Test User', got '{stdout_name}'"
    assert stdout_email == "test@example.com", f"Expected user.email 'test@example.com', got '{stdout_email}'"
