import os
import subprocess


def test_upstream_repository_exists():
    """Verify upstream repository exists and is a valid git repo"""
    assert os.path.isdir("/app/upstream"), "Upstream repository directory does not exist"
    assert os.path.isdir("/app/upstream/.git"), "Upstream is not a git repository"


def test_fork_repository_exists():
    """Verify fork repository exists and is a valid git repo"""
    assert os.path.isdir("/app/fork"), "Fork repository directory does not exist"
    assert os.path.isdir("/app/fork/.git"), "Fork is not a git repository"


def test_config_file_exists():
    """Verify config.txt exists in fork repository"""
    config_path = "/app/fork/config.txt"
    assert os.path.isfile(config_path), "config.txt does not exist in fork repository"


def test_config_final_content():
    """Verify config.txt has the correct final content after conflict resolution"""
    config_path = "/app/fork/config.txt"
    with open(config_path, 'r') as f:
        content = f.read().strip()

    assert content == "version=3.0", f"Expected 'version=3.0' but got '{content}'"


def test_no_unresolved_conflicts():
    """Verify there are no unresolved merge conflicts"""
    config_path = "/app/fork/config.txt"
    with open(config_path, 'r') as f:
        content = f.read()

    # Check for git conflict markers
    conflict_markers = ['<<<<<<<', '=======', '>>>>>>>']
    for marker in conflict_markers:
        assert marker not in content, f"Unresolved conflict marker '{marker}' found in config.txt"


def test_git_status_clean():
    """Verify git status is clean (no uncommitted changes)"""
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Git status command failed"
    assert result.stdout.strip() == "", f"Repository has uncommitted changes: {result.stdout}"


def test_upstream_remote_configured():
    """Verify upstream remote is configured in fork"""
    result = subprocess.run(
        ['git', 'remote', '-v'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Git remote command failed"
    assert 'upstream' in result.stdout, "Upstream remote not configured"
    assert '/app/upstream' in result.stdout, "Upstream remote does not point to /app/upstream"


def test_commit_history_completeness():
    """Verify all required commits exist in fork history"""
    result = subprocess.run(
        ['git', 'log', '--all', '--oneline'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Git log command failed"
    log_output = result.stdout.lower()

    # Check for key commits (case-insensitive partial matching)
    assert 'initial commit' in log_output, "Initial commit not found in history"
    assert '2.0' in log_output, "Commit for version 2.0 not found"
    assert '2.5' in log_output, "Commit for version 2.5 not found"
    assert '3.0' in log_output, "Commit for version 3.0 not found"


def test_merge_commit_exists():
    """Verify a merge commit exists that resolved the conflict"""
    # Get commits with their parent count
    result = subprocess.run(
        ['git', 'log', '--all', '--pretty=format:%H %P'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Git log command failed"

    # A merge commit has 2 or more parents
    merge_commits = []
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) >= 3:  # commit hash + at least 2 parent hashes
            merge_commits.append(parts[0])

    assert len(merge_commits) > 0, "No merge commit found in history"


def test_conflict_resolution_correctness():
    """Verify the conflict was resolved with the correct version (3.0 from upstream)"""
    # Get the content at the merge commit
    result = subprocess.run(
        ['git', 'log', '--all', '--pretty=format:%H %P'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    # Find merge commit
    merge_commit = None
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) >= 3:
            merge_commit = parts[0]
            break

    assert merge_commit is not None, "No merge commit found"

    # Check content at merge commit
    result = subprocess.run(
        ['git', 'show', f'{merge_commit}:config.txt'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Failed to read config.txt at merge commit"
    content = result.stdout.strip()
    assert content == "version=3.0", f"Merge commit has wrong content: '{content}' (expected 'version=3.0')"


def test_git_config_set():
    """Verify git user configuration is set"""
    result_name = subprocess.run(
        ['git', 'config', 'user.name'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    result_email = subprocess.run(
        ['git', 'config', 'user.email'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result_name.returncode == 0, "Git user.name not configured"
    assert result_email.returncode == 0, "Git user.email not configured"
    assert result_name.stdout.strip() != "", "Git user.name is empty"
    assert result_email.stdout.strip() != "", "Git user.email is empty"


def test_fork_has_upstream_commits():
    """Verify fork contains commits from upstream (proper merge, not just file copy)"""
    # Get commit hashes from upstream
    result_upstream = subprocess.run(
        ['git', 'log', '--all', '--pretty=format:%H'],
        cwd='/app/upstream',
        capture_output=True,
        text=True
    )

    assert result_upstream.returncode == 0, "Failed to get upstream commits"
    upstream_commits = set(result_upstream.stdout.strip().split('\n'))

    # Get commit hashes from fork
    result_fork = subprocess.run(
        ['git', 'log', '--all', '--pretty=format:%H'],
        cwd='/app/fork',
        capture_output=True,
        text=True
    )

    assert result_fork.returncode == 0, "Failed to get fork commits"
    fork_commits = set(result_fork.stdout.strip().split('\n'))

    # Fork should contain at least some upstream commits (from initial clone and merges)
    common_commits = upstream_commits.intersection(fork_commits)
    assert len(common_commits) > 0, "Fork does not share any commits with upstream (not properly cloned/merged)"


def test_config_file_not_empty():
    """Verify config.txt is not empty (catch lazy empty file creation)"""
    config_path = "/app/fork/config.txt"
    assert os.path.getsize(config_path) > 0, "config.txt is empty"


def test_repositories_are_separate():
    """Verify upstream and fork are separate repositories (not symlinks or same directory)"""
    upstream_real = os.path.realpath("/app/upstream")
    fork_real = os.path.realpath("/app/fork")

    assert upstream_real != fork_real, "Upstream and fork point to the same directory"
