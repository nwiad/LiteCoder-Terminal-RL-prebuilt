"""
Tests for the Git repository recovery task.

Validates that the agent correctly recovered lost commits from reflog,
created the recovery branch, restored main, cleaned up, and documented
the recovery process.
"""

import os
import subprocess

REPO_DIR = "/app"


def run_git(*args):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


# ============================================================
# 1. Current branch must be 'main'
# ============================================================

def test_current_branch_is_main():
    """The checked-out branch must be 'main'."""
    result = run_git("branch", "--show-current")
    assert result.returncode == 0, f"git branch --show-current failed: {result.stderr}"
    branch = result.stdout.strip()
    assert branch == "main", f"Expected current branch 'main', got '{branch}'"


# ============================================================
# 2. Recovery branch exists
# ============================================================

def test_recovery_branch_exists():
    """A branch named 'recovery' must exist."""
    result = run_git("branch", "--list", "recovery")
    assert result.returncode == 0, f"git branch --list failed: {result.stderr}"
    branches = result.stdout.strip()
    assert "recovery" in branches, "Branch 'recovery' does not exist"


# ============================================================
# 3. Commit count on main (at least 8)
# ============================================================

def test_main_has_at_least_8_commits():
    """git log --oneline main must show at least 8 commits."""
    result = run_git("log", "--oneline", "main")
    assert result.returncode == 0, f"git log failed: {result.stderr}"
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(lines) >= 8, (
        f"Expected at least 8 commits on main, found {len(lines)}. "
        f"Commits: {result.stdout.strip()}"
    )


# ============================================================
# 4. All 9 required files exist and are non-empty
# ============================================================

REQUIRED_FILES = [
    "README.md",
    "src/config.py",
    "src/utils.py",
    "app.py",
    "models/database.py",
    "api/routes.py",
    "requirements.txt",
    "tests/__init__.py",
    "tests/test_utils.py",
]


def test_all_required_files_exist():
    """All 9 files listed in the instructions must exist in the working tree."""
    missing = []
    for f in REQUIRED_FILES:
        full_path = os.path.join(REPO_DIR, f)
        if not os.path.isfile(full_path):
            missing.append(f)
    assert not missing, f"Missing files: {missing}"


def test_required_files_are_not_empty():
    """Key recovered files must have actual content (not just touched empty)."""
    # __init__.py files can legitimately be empty, skip them
    content_files = [f for f in REQUIRED_FILES if "__init__" not in f]
    empty = []
    for f in content_files:
        full_path = os.path.join(REPO_DIR, f)
        if os.path.isfile(full_path) and os.path.getsize(full_path) == 0:
            empty.append(f)
    assert not empty, f"These files exist but are empty (likely not recovered): {empty}"


# ============================================================
# 5. Specific file content checks (anti-fake guard)
# ============================================================

def test_config_py_has_expected_content():
    """src/config.py must contain the Config class from the original commits."""
    path = os.path.join(REPO_DIR, "src/config.py")
    if not os.path.isfile(path):
        assert False, "src/config.py does not exist"
    content = open(path).read()
    assert "DATABASE_URL" in content, "src/config.py missing DATABASE_URL"
    assert "SECRET_KEY" in content, "src/config.py missing SECRET_KEY"
    assert "class Config" in content, "src/config.py missing class Config"


def test_utils_py_has_expected_content():
    """src/utils.py must contain the utility functions from the original commits."""
    path = os.path.join(REPO_DIR, "src/utils.py")
    if not os.path.isfile(path):
        assert False, "src/utils.py does not exist"
    content = open(path).read()
    assert "hash_password" in content, "src/utils.py missing hash_password"
    assert "format_timestamp" in content, "src/utils.py missing format_timestamp"


def test_app_py_has_expected_content():
    """app.py must contain the create_app function."""
    path = os.path.join(REPO_DIR, "app.py")
    if not os.path.isfile(path):
        assert False, "app.py does not exist"
    content = open(path).read()
    assert "create_app" in content, "app.py missing create_app function"


def test_database_py_has_expected_content():
    """models/database.py must contain the Database class."""
    path = os.path.join(REPO_DIR, "models/database.py")
    if not os.path.isfile(path):
        assert False, "models/database.py does not exist"
    content = open(path).read()
    assert "class Database" in content, "models/database.py missing class Database"


def test_routes_py_has_expected_content():
    """api/routes.py must contain route definitions."""
    path = os.path.join(REPO_DIR, "api/routes.py")
    if not os.path.isfile(path):
        assert False, "api/routes.py does not exist"
    content = open(path).read()
    assert "ROUTES" in content, "api/routes.py missing ROUTES"
    assert "get_health" in content, "api/routes.py missing get_health"


def test_test_utils_has_expected_content():
    """tests/test_utils.py must contain the original test class."""
    path = os.path.join(REPO_DIR, "tests/test_utils.py")
    if not os.path.isfile(path):
        assert False, "tests/test_utils.py does not exist"
    content = open(path).read()
    assert "TestUtils" in content or "test_hash_password" in content, (
        "tests/test_utils.py missing expected test content"
    )


# ============================================================
# 6. recovery.log existence, tracking, and content
# ============================================================

def test_recovery_log_exists():
    """recovery.log must exist at /app/recovery.log."""
    path = os.path.join(REPO_DIR, "recovery.log")
    assert os.path.isfile(path), "recovery.log does not exist"


def test_recovery_log_is_tracked_by_git():
    """recovery.log must be committed (tracked) in the repository."""
    result = run_git("ls-files", "recovery.log")
    assert result.returncode == 0, f"git ls-files failed: {result.stderr}"
    tracked = result.stdout.strip()
    assert "recovery.log" in tracked, (
        "recovery.log exists but is not tracked by git"
    )


def test_recovery_log_contains_reflog_keyword():
    """recovery.log must mention 'reflog'."""
    path = os.path.join(REPO_DIR, "recovery.log")
    if not os.path.isfile(path):
        assert False, "recovery.log does not exist"
    content = open(path).read().lower()
    assert "reflog" in content, "recovery.log missing keyword 'reflog'"


def test_recovery_log_contains_recovery_keyword():
    """recovery.log must mention 'recovery'."""
    path = os.path.join(REPO_DIR, "recovery.log")
    if not os.path.isfile(path):
        assert False, "recovery.log does not exist"
    content = open(path).read().lower()
    assert "recovery" in content, "recovery.log missing keyword 'recovery'"


def test_recovery_log_contains_merge_or_reset_keyword():
    """recovery.log must mention 'merge' or 'reset'."""
    path = os.path.join(REPO_DIR, "recovery.log")
    if not os.path.isfile(path):
        assert False, "recovery.log does not exist"
    content = open(path).read().lower()
    assert "merge" in content or "reset" in content, (
        "recovery.log missing keyword 'merge' or 'reset'"
    )


def test_recovery_log_has_at_least_3_lines():
    """recovery.log must have at least 3 lines of content."""
    path = os.path.join(REPO_DIR, "recovery.log")
    if not os.path.isfile(path):
        assert False, "recovery.log does not exist"
    content = open(path).read()
    # Count non-empty lines
    lines = [l for l in content.splitlines() if l.strip()]
    assert len(lines) >= 3, (
        f"recovery.log has only {len(lines)} non-empty lines, need at least 3"
    )


# ============================================================
# 7. Clean working tree (no uncommitted changes)
# ============================================================

def test_working_tree_is_clean():
    """git status must show a clean working tree (no uncommitted changes)."""
    result = run_git("status", "--porcelain")
    assert result.returncode == 0, f"git status failed: {result.stderr}"
    status = result.stdout.strip()
    assert status == "", (
        f"Working tree is not clean. Uncommitted changes:\n{status}"
    )


# ============================================================
# 8. Recovery branch points to correct history
# ============================================================

def test_recovery_branch_has_lost_commits():
    """The recovery branch must contain the 7 recovered commits."""
    result = run_git("log", "--oneline", "recovery")
    assert result.returncode == 0, f"git log recovery failed: {result.stderr}"
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    # recovery branch should have at least 7 commits (the original 8 minus
    # possibly the initial, but really all 8 should be there)
    assert len(lines) >= 7, (
        f"Expected at least 7 commits on recovery branch, found {len(lines)}"
    )


# ============================================================
# 9. Commit history integrity — original commit messages present
# ============================================================

def test_original_commit_messages_present():
    """Key original commit messages should appear in main's log."""
    result = run_git("log", "--oneline", "main")
    assert result.returncode == 0, f"git log failed: {result.stderr}"
    log_text = result.stdout.lower()
    # The setup script created commits with these keywords in messages.
    # We check for a subset to be method-agnostic (merge vs reset).
    expected_keywords = ["readme", "config", "util", "app", "database", "route", "test"]
    found = [kw for kw in expected_keywords if kw in log_text]
    assert len(found) >= 5, (
        f"Expected at least 5 of {expected_keywords} in commit log, "
        f"found only {found}. Log:\n{result.stdout}"
    )


# ============================================================
# 10. The repo is a valid git repository
# ============================================================

def test_repo_is_valid_git_repo():
    """The /app directory must be a valid git repository."""
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), (
        "/app/.git directory does not exist — not a git repository"
    )
    result = run_git("rev-parse", "--is-inside-work-tree")
    assert result.returncode == 0, f"Not inside a git work tree: {result.stderr}"
    assert result.stdout.strip() == "true"


# ============================================================
# 11. README.md content check (the only file present after reset)
# ============================================================

def test_readme_has_expected_content():
    """README.md must contain project description from original commit."""
    path = os.path.join(REPO_DIR, "README.md")
    if not os.path.isfile(path):
        assert False, "README.md does not exist"
    content = open(path).read()
    assert "Project App" in content or "web application" in content.lower(), (
        "README.md does not contain expected project description"
    )

