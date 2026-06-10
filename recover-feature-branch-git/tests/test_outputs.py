"""
Tests for the Git repository restoration and feature recovery task.

Validates the final state of /app/repo/ after the agent has completed
all steps: init, feature branch, simulated disaster, reflog recovery,
and merge.
"""

import os
import subprocess

REPO_DIR = "/app/repo"


def run_git(*args, cwd=REPO_DIR):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


def git_output(*args):
    """Run a git command and return stripped stdout, asserting success."""
    result = run_git(*args)
    assert result.returncode == 0, (
        f"git {' '.join(args)} failed: {result.stderr}"
    )
    return result.stdout.strip()


# ── Test 1: Repository exists and is a valid git repo ──


def test_repo_directory_exists():
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"


def test_repo_is_git_repo():
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a git repository"


# ── Test 2: Branch structure ──


def test_main_branch_exists():
    result = run_git("rev-parse", "--verify", "main")
    assert result.returncode == 0, "Branch 'main' does not exist"


def test_feature_auth_branch_exists():
    result = run_git("rev-parse", "--verify", "feature/auth")
    assert result.returncode == 0, "Branch 'feature/auth' does not exist"


def test_current_branch_is_main():
    """After the merge, HEAD should be on main."""
    head_ref = git_output("symbolic-ref", "--short", "HEAD")
    assert head_ref == "main", f"Expected HEAD on 'main', got '{head_ref}'"


# ── Test 3: File existence on main ──


def test_readme_exists():
    path = os.path.join(REPO_DIR, "README.md")
    assert os.path.isfile(path), "README.md missing on main"


def test_config_exists():
    path = os.path.join(REPO_DIR, "config.txt")
    assert os.path.isfile(path), "config.txt missing on main"


def test_auth_py_exists():
    path = os.path.join(REPO_DIR, "auth.py")
    assert os.path.isfile(path), "auth.py missing on main"


def test_auth_test_py_exists():
    path = os.path.join(REPO_DIR, "auth_test.py")
    assert os.path.isfile(path), "auth_test.py missing on main"


# ── Test 4: File contents on main ──


def test_readme_content():
    path = os.path.join(REPO_DIR, "README.md")
    content = open(path).read().strip()
    assert content == "# Auth Project", (
        f"README.md content wrong: {content!r}"
    )


def test_config_content():
    path = os.path.join(REPO_DIR, "config.txt")
    content = open(path).read().strip()
    assert content == "version=1.0", (
        f"config.txt content wrong: {content!r}"
    )


def test_auth_py_has_login():
    path = os.path.join(REPO_DIR, "auth.py")
    content = open(path).read()
    assert "def login(user): pass" in content, (
        "auth.py missing 'def login(user): pass'"
    )


def test_auth_py_has_logout():
    path = os.path.join(REPO_DIR, "auth.py")
    content = open(path).read()
    assert "def logout(user): pass" in content, (
        "auth.py missing 'def logout(user): pass'"
    )


def test_auth_test_content():
    path = os.path.join(REPO_DIR, "auth_test.py")
    content = open(path).read()
    assert "assert login is not None" in content, (
        "auth_test.py missing 'assert login is not None'"
    )


# ── Test 5: Commit history on main ──


def test_main_log_has_minimum_commits():
    """main should have at least 5 commits (merge + 3 feature + config + initial)."""
    log = git_output("log", "--oneline", "main")
    lines = [l for l in log.splitlines() if l.strip()]
    assert len(lines) >= 5, (
        f"Expected at least 5 commits on main, got {len(lines)}:\n{log}"
    )


def test_main_log_has_initial_commit():
    log = git_output("log", "--oneline", "main")
    assert "Initial commit" in log, (
        f"'Initial commit' not found in main log:\n{log}"
    )


def test_main_log_has_add_config():
    log = git_output("log", "--oneline", "main")
    assert "Add config" in log, (
        f"'Add config' not found in main log:\n{log}"
    )


def test_main_log_has_add_login():
    log = git_output("log", "--oneline", "main")
    assert "Add login function" in log, (
        f"'Add login function' not found in main log:\n{log}"
    )


def test_main_log_has_add_logout():
    log = git_output("log", "--oneline", "main")
    assert "Add logout function" in log, (
        f"'Add logout function' not found in main log:\n{log}"
    )


def test_main_log_has_add_auth_tests():
    log = git_output("log", "--oneline", "main")
    assert "Add auth tests" in log, (
        f"'Add auth tests' not found in main log:\n{log}"
    )


def test_main_log_has_merge_commit_message():
    log = git_output("log", "--oneline", "main")
    assert "Merge feature/auth into main" in log, (
        f"'Merge feature/auth into main' not found in main log:\n{log}"
    )


# ── Test 6: feature/auth branch history ──


def test_feature_auth_has_login_commit():
    log = git_output("log", "--oneline", "feature/auth")
    assert "Add login function" in log, (
        f"'Add login function' not in feature/auth log:\n{log}"
    )


def test_feature_auth_has_logout_commit():
    log = git_output("log", "--oneline", "feature/auth")
    assert "Add logout function" in log, (
        f"'Add logout function' not in feature/auth log:\n{log}"
    )


def test_feature_auth_has_auth_tests_commit():
    log = git_output("log", "--oneline", "feature/auth")
    assert "Add auth tests" in log, (
        f"'Add auth tests' not in feature/auth log:\n{log}"
    )


def test_feature_auth_has_initial_commit():
    log = git_output("log", "--oneline", "feature/auth")
    assert "Initial commit" in log, (
        f"'Initial commit' not in feature/auth log:\n{log}"
    )


# ── Test 7: Merge commit has exactly 2 parents ──


def test_merge_commit_has_two_parents():
    """The top commit on main should be a merge commit with 2 parents."""
    # Get the hash of the tip of main
    tip_hash = git_output("rev-parse", "main")

    # Use cat-file to inspect the commit object
    cat_output = git_output("cat-file", "-p", tip_hash)

    # Count lines starting with "parent "
    parent_lines = [
        line for line in cat_output.splitlines()
        if line.startswith("parent ")
    ]
    assert len(parent_lines) == 2, (
        f"Merge commit should have exactly 2 parents, "
        f"found {len(parent_lines)}.\nCommit object:\n{cat_output}"
    )


def test_merge_commit_message_in_cat_file():
    """Verify the merge commit message via cat-file."""
    tip_hash = git_output("rev-parse", "main")
    cat_output = git_output("cat-file", "-p", tip_hash)
    assert "Merge feature/auth into main" in cat_output, (
        f"Merge commit message not found in commit object:\n{cat_output}"
    )


# ── Test 8: git log --all --oneline has all expected messages ──


def test_all_log_has_all_commit_messages():
    """git log --all --oneline must include all 6 expected commit messages."""
    log = git_output("log", "--all", "--oneline")
    expected_messages = [
        "Initial commit",
        "Add config",
        "Add login function",
        "Add logout function",
        "Add auth tests",
        "Merge feature/auth into main",
    ]
    for msg in expected_messages:
        assert msg in log, (
            f"'{msg}' not found in git log --all --oneline:\n{log}"
        )


# ── Test 9: feature/auth is an ancestor of main (merged) ──


def test_feature_auth_is_merged_into_main():
    """feature/auth tip should be reachable from main."""
    result = run_git("merge-base", "--is-ancestor", "feature/auth", "main")
    assert result.returncode == 0, (
        "feature/auth is not an ancestor of main — merge may not have happened"
    )


# ── Test 10: Files tracked by git on main (not just on disk) ──


def test_files_tracked_on_main():
    """All 4 required files should be tracked by git on main."""
    ls_output = git_output("ls-tree", "--name-only", "main")
    tracked_files = ls_output.splitlines()
    for fname in ["README.md", "config.txt", "auth.py", "auth_test.py"]:
        assert fname in tracked_files, (
            f"'{fname}' not tracked in git on main. "
            f"Tracked files: {tracked_files}"
        )


# ── Test 11: Commit ordering sanity ──


def test_initial_commit_is_root():
    """The 'Initial commit' should be a root commit (no parents)."""
    # Find the commit with message "Initial commit"
    log_lines = git_output(
        "log", "--all", "--oneline", "--format=%H %s"
    ).splitlines()
    initial_hash = None
    for line in log_lines:
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1] == "Initial commit":
            initial_hash = parts[0]
            break
    assert initial_hash is not None, "Could not find 'Initial commit' hash"

    # Check it has no parents
    cat_output = git_output("cat-file", "-p", initial_hash)
    parent_lines = [
        l for l in cat_output.splitlines() if l.startswith("parent ")
    ]
    assert len(parent_lines) == 0, (
        f"'Initial commit' should be a root commit with 0 parents, "
        f"found {len(parent_lines)}"
    )


# ── Test 12: Merge parents are correct branches ──


def test_merge_parent_includes_feature_auth_tip():
    """One of the merge commit's parents should be the tip of feature/auth."""
    tip_hash = git_output("rev-parse", "main")
    cat_output = git_output("cat-file", "-p", tip_hash)
    parent_hashes = [
        line.split()[1]
        for line in cat_output.splitlines()
        if line.startswith("parent ")
    ]

    feature_tip = git_output("rev-parse", "feature/auth")
    assert feature_tip in parent_hashes, (
        f"feature/auth tip ({feature_tip}) is not a parent of the merge commit. "
        f"Parents: {parent_hashes}"
    )
