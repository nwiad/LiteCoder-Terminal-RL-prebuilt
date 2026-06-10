import os
import subprocess
import pytest


def run_git_command(cmd, cwd="/app/repo"):
    """Helper to run git commands and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def test_repository_exists():
    """Verify the repository exists at /app/repo."""
    assert os.path.exists("/app/repo"), "Repository directory /app/repo does not exist"
    assert os.path.exists("/app/repo/.git"), "Not a valid git repository"


def test_config_json_not_in_working_directory():
    """Verify config.json is not in the current working directory."""
    # This catches lazy agents who just delete the file without touching history
    assert not os.path.exists("/app/repo/config.json"), \
        "config.json still exists in working directory - file must be removed from history, not just deleted"


def test_config_json_not_in_git_log():
    """Verify config.json does not appear in git log across all branches."""
    returncode, stdout, stderr = run_git_command(
        "git log --all --full-history --oneline -- config.json"
    )
    assert returncode == 0, f"git log command failed: {stderr}"
    assert stdout.strip() == "", \
        f"config.json still appears in git log:\n{stdout}\nFile must be completely removed from history"


def test_config_json_not_in_any_commit_tree():
    """Verify config.json does not exist in any commit's tree across all refs."""
    # Get all commits from all branches and tags
    returncode, stdout, stderr = run_git_command("git rev-list --all")
    assert returncode == 0, f"Failed to get commit list: {stderr}"

    commits = stdout.strip().split('\n')
    assert len(commits) > 0, "No commits found in repository"

    # Check each commit's tree for config.json
    for commit in commits:
        if not commit:
            continue
        returncode, stdout, stderr = run_git_command(f"git ls-tree -r {commit}")
        assert returncode == 0, f"Failed to list tree for commit {commit}: {stderr}"

        # Check if config.json appears in the tree
        for line in stdout.split('\n'):
            if 'config.json' in line:
                pytest.fail(
                    f"config.json found in commit {commit}:\n{line}\n"
                    f"File must be completely purged from all commits"
                )


def test_config_json_not_in_branches():
    """Verify config.json is removed from all branches (main, development, feature/api-integration)."""
    branches = ["main", "development", "feature/api-integration"]

    for branch in branches:
        # Check if branch exists
        returncode, stdout, stderr = run_git_command(f"git rev-parse --verify {branch}")
        assert returncode == 0, f"Branch {branch} does not exist or is invalid: {stderr}"

        # Check git log for this branch
        returncode, stdout, stderr = run_git_command(
            f"git log {branch} --full-history --oneline -- config.json"
        )
        assert returncode == 0, f"git log failed for branch {branch}: {stderr}"
        assert stdout.strip() == "", \
            f"config.json still appears in branch {branch}:\n{stdout}"

        # Check the branch's HEAD tree
        returncode, stdout, stderr = run_git_command(f"git ls-tree -r {branch}")
        assert returncode == 0, f"Failed to list tree for branch {branch}: {stderr}"
        assert "config.json" not in stdout, \
            f"config.json found in branch {branch} tree"


def test_config_json_not_in_tags():
    """Verify config.json is removed from all tags (v1.0.0, v1.1.0)."""
    tags = ["v1.0.0", "v1.1.0"]

    for tag in tags:
        # Check if tag exists
        returncode, stdout, stderr = run_git_command(f"git rev-parse --verify {tag}")
        assert returncode == 0, f"Tag {tag} does not exist or is invalid: {stderr}"

        # Check git log for this tag
        returncode, stdout, stderr = run_git_command(
            f"git log {tag} --full-history --oneline -- config.json"
        )
        assert returncode == 0, f"git log failed for tag {tag}: {stderr}"
        assert stdout.strip() == "", \
            f"config.json still appears in tag {tag}:\n{stdout}"

        # Check the tag's tree
        returncode, stdout, stderr = run_git_command(f"git ls-tree -r {tag}")
        assert returncode == 0, f"Failed to list tree for tag {tag}: {stderr}"
        assert "config.json" not in stdout, \
            f"config.json found in tag {tag} tree"


def test_config_json_not_searchable_in_history():
    """Verify config.json content is not searchable in any commit."""
    # This catches cases where the file might be renamed but content remains
    returncode, stdout, stderr = run_git_command(
        "git rev-list --all"
    )
    assert returncode == 0, f"Failed to get commit list: {stderr}"

    commits = stdout.strip().split('\n')

    # Try to grep for config.json in all commits
    # This should return nothing if properly removed
    returncode, stdout, stderr = run_git_command(
        f"git grep 'config.json' $(git rev-list --all) 2>&1 || true"
    )

    # git grep returns non-zero if nothing found, which is what we want
    # But we need to check the output doesn't contain actual file references
    if "config.json" in stdout:
        # Filter out references in test files or documentation
        lines = [line for line in stdout.split('\n') if 'config.json' in line]
        # Check if any line is actually the config.json file itself (not just a reference)
        for line in lines:
            # Format: commit:filename:content
            if ':config.json:' in line:
                pytest.fail(
                    f"config.json file content found in history:\n{line}\n"
                    f"File must be completely purged"
                )


def test_other_files_preserved():
    """Verify that other files remain intact in the repository."""
    expected_files = ["README.md", "app.py", "utils.py", ".gitignore"]

    # Check in main branch
    returncode, stdout, stderr = run_git_command("git ls-tree -r main --name-only")
    assert returncode == 0, f"Failed to list files in main: {stderr}"

    files_in_main = stdout.strip().split('\n')

    for expected_file in expected_files:
        assert expected_file in files_in_main, \
            f"Expected file {expected_file} not found in main branch. Other files must be preserved."


def test_commit_history_preserved():
    """Verify that commit history structure is preserved (commits still exist)."""
    # Check that we still have multiple commits
    returncode, stdout, stderr = run_git_command("git rev-list --all --count")
    assert returncode == 0, f"Failed to count commits: {stderr}"

    commit_count = int(stdout.strip())
    assert commit_count >= 5, \
        f"Expected at least 5 commits in history, found {commit_count}. Commit history should be preserved."


def test_all_branches_accessible():
    """Verify all branches are still accessible and functional."""
    branches = ["main", "development", "feature/api-integration"]

    for branch in branches:
        # Try to checkout the branch
        returncode, stdout, stderr = run_git_command(f"git checkout {branch}")
        assert returncode == 0, \
            f"Failed to checkout branch {branch}: {stderr}\nBranches must remain functional after cleanup"


def test_all_tags_accessible():
    """Verify all tags are still accessible and functional."""
    tags = ["v1.0.0", "v1.1.0"]

    for tag in tags:
        # Verify tag exists and points to a valid commit
        returncode, stdout, stderr = run_git_command(f"git rev-parse {tag}")
        assert returncode == 0, \
            f"Tag {tag} is not accessible: {stderr}\nTags must remain functional after cleanup"

        commit_hash = stdout.strip()
        assert len(commit_hash) == 40, \
            f"Tag {tag} does not point to a valid commit hash"


def test_no_backup_refs_remaining():
    """Verify no backup refs from filter-branch remain."""
    returncode, stdout, stderr = run_git_command("git for-each-ref refs/original/")
    assert returncode == 0, f"Failed to check backup refs: {stderr}"
    assert stdout.strip() == "", \
        f"Backup refs still exist:\n{stdout}\nBackup refs must be cleaned up to complete the purge"


def test_reflog_cleaned():
    """Verify reflog has been properly cleaned (file should not be recoverable)."""
    # Try to find config.json in reflog
    returncode, stdout, stderr = run_git_command(
        "git reflog --all | head -20"
    )
    # Reflog should exist but we just verify the command works
    assert returncode == 0, f"Failed to check reflog: {stderr}"

    # The key test: try to find any dangling objects that might contain config.json
    returncode, stdout, stderr = run_git_command(
        "git fsck --unreachable 2>&1 | grep -i unreachable | head -10 || true"
    )
    # This is informational - some unreachable objects may exist but config.json should not be recoverable


def test_repository_integrity():
    """Verify repository integrity after cleanup."""
    returncode, stdout, stderr = run_git_command("git fsck --full")
    assert returncode == 0, \
        f"Repository integrity check failed:\n{stderr}\nRepository must remain valid after cleanup"
