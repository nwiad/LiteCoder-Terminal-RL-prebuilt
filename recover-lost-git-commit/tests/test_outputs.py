import os
import subprocess
import pytest


def run_git_command(cmd, cwd="/app/workspace"):
    """Helper to run git commands and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode


def test_workspace_exists():
    """Verify the repository was cloned to /app/workspace."""
    assert os.path.exists("/app/workspace"), "Workspace directory /app/workspace does not exist"
    assert os.path.isdir("/app/workspace/.git"), "Workspace is not a Git repository"


def test_feature_file_exists():
    """Verify the lost commit's feature.py file was recovered."""
    feature_path = "/app/workspace/feature.py"
    assert os.path.exists(feature_path), "feature.py was not recovered"

    with open(feature_path, 'r') as f:
        content = f.read()

    # Verify it contains the calculation functions (not just an empty/dummy file)
    assert "calculate_sum" in content, "feature.py missing calculate_sum function"
    assert "calculate_product" in content, "feature.py missing calculate_product function"
    assert "return a + b" in content, "calculate_sum implementation missing"
    assert "return a * b" in content, "calculate_product implementation missing"


def test_recovery_branch_created():
    """Verify the recover-lost-commit branch was created."""
    stdout, _, returncode = run_git_command("git branch --list recover-lost-commit")
    assert returncode == 0, "Failed to list branches"
    assert "recover-lost-commit" in stdout, "Branch 'recover-lost-commit' was not created"


def test_lost_commit_in_main_history():
    """Verify the lost commit is now in main branch history."""
    # Check that feature.py exists on main branch
    stdout, _, returncode = run_git_command("git checkout main")
    assert returncode == 0, "Failed to checkout main branch"

    stdout, _, returncode = run_git_command("git ls-files")
    assert "feature.py" in stdout, "feature.py not in main branch"

    # Verify the commit message appears in main's history
    stdout, _, returncode = run_git_command("git log --all --oneline")
    assert returncode == 0, "Failed to get git log"
    assert "critical feature" in stdout.lower() or "calculation" in stdout.lower(), \
        "Lost commit message not found in history"


def test_merge_commit_exists():
    """Verify a merge was performed (not just a fast-forward or cherry-pick)."""
    stdout, _, returncode = run_git_command("git log --oneline --graph --all")
    assert returncode == 0, "Failed to get git log"

    # Check for merge indicators in the log
    # The recovery should show up in the history
    stdout_lower = stdout.lower()
    assert "recover" in stdout_lower or "merge" in stdout_lower, \
        "No evidence of merge/recovery in git history"


def test_changes_pushed_to_remote():
    """Verify changes were pushed to the remote repository."""
    # Check that local main and origin/main are in sync
    stdout, _, returncode = run_git_command("git status")
    assert returncode == 0, "Failed to get git status"

    # Should not say "ahead of" or "behind" - should be up to date
    assert "ahead of" not in stdout.lower() or "up to date" in stdout.lower() or "up-to-date" in stdout.lower(), \
        "Local main branch not pushed to remote"

    # Verify remote has the feature.py file by checking remote refs
    stdout, _, returncode = run_git_command("git ls-tree origin/main --name-only")
    assert returncode == 0, "Failed to list remote files"
    assert "feature.py" in stdout, "feature.py not in remote repository"


def test_remote_repository_integrity():
    """Verify the remote repository contains the recovered commit."""
    # Clone the remote repo to a temp location to verify it independently
    temp_clone = "/tmp/verify_clone"

    # Clean up any previous test runs
    subprocess.run(f"rm -rf {temp_clone}", shell=True)

    stdout, stderr, returncode = run_git_command(
        f"git clone /app/remote_repo.git {temp_clone}",
        cwd="/tmp"
    )
    assert returncode == 0, f"Failed to clone remote repository: {stderr}"

    # Verify feature.py exists in the fresh clone
    assert os.path.exists(f"{temp_clone}/feature.py"), \
        "feature.py not found in fresh clone of remote repository"

    # Verify content
    with open(f"{temp_clone}/feature.py", 'r') as f:
        content = f.read()

    assert "calculate_sum" in content and "calculate_product" in content, \
        "Remote repository missing correct feature.py content"

    # Clean up
    subprocess.run(f"rm -rf {temp_clone}", shell=True)


def test_not_just_hardcoded_file():
    """Verify the solution actually used Git recovery, not just created a hardcoded file."""
    # Check that the recovery branch points to a real commit with the feature
    stdout, _, returncode = run_git_command("git log recover-lost-commit --oneline")
    assert returncode == 0, "Recovery branch doesn't exist or has no commits"

    # The recovery branch should have at least 2 commits (initial + feature)
    commit_count = len(stdout.strip().split('\n'))
    assert commit_count >= 2, \
        f"Recovery branch has only {commit_count} commit(s), expected at least 2"

    # Verify the feature commit is actually in the recovery branch
    stdout, _, returncode = run_git_command("git log recover-lost-commit --all --grep='feature' -i")
    assert returncode == 0, "Failed to search commit history"
    # Should find at least one commit mentioning feature/calculation
    assert len(stdout.strip()) > 0, "No feature-related commit found in recovery branch"


def test_main_branch_has_all_commits():
    """Verify main branch contains both initial and recovered commits."""
    stdout, _, returncode = run_git_command("git log main --oneline")
    assert returncode == 0, "Failed to get main branch log"

    # Should have at least 3 commits: initial, lost commit, and merge commit
    commit_count = len(stdout.strip().split('\n'))
    assert commit_count >= 3, \
        f"Main branch has only {commit_count} commit(s), expected at least 3 (initial + recovered + merge)"


def test_readme_still_exists():
    """Verify the initial commit's README.md still exists (no data loss)."""
    readme_path = "/app/workspace/README.md"
    assert os.path.exists(readme_path), "README.md was lost during recovery"

    with open(readme_path, 'r') as f:
        content = f.read()

    assert "Project README" in content or "initial" in content.lower(), \
        "README.md content was corrupted"
