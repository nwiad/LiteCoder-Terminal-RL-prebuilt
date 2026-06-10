"""
Tests for Git Repository Recovery and Advanced Manipulation task.

Validates that the agent correctly:
1. Created a valid git repository at /app/data-analytics-recovery
2. Created required files with proper content
3. Recovered a lost commit via a recovery branch
4. Merged the recovery branch into main
5. Tagged the recovery point
6. Generated a recovery report
"""

import os
import subprocess

REPO_PATH = "/app/data-analytics-recovery"


def run_git(args, cwd=REPO_PATH):
    """Helper to run git commands in the repository."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


# ──────────────────────────────────────────────
# 1. Repository existence and validity
# ──────────────────────────────────────────────

def test_repo_directory_exists():
    """The repository directory must exist."""
    assert os.path.isdir(REPO_PATH), f"Repository directory {REPO_PATH} does not exist"


def test_repo_is_valid_git_repo():
    """The directory must be a valid Git repository."""
    git_dir = os.path.join(REPO_PATH, ".git")
    assert os.path.isdir(git_dir), f"{REPO_PATH} is not a valid Git repository (no .git directory)"
    # Double-check with git rev-parse
    result = run_git(["rev-parse", "--is-inside-work-tree"])
    assert result.returncode == 0, "git rev-parse failed — not a valid git repo"
    assert result.stdout.strip() == "true"


# ──────────────────────────────────────────────
# 2. Required directories
# ──────────────────────────────────────────────

def test_scripts_directory_exists():
    assert os.path.isdir(os.path.join(REPO_PATH, "scripts")), "scripts/ directory missing"


def test_docs_directory_exists():
    assert os.path.isdir(os.path.join(REPO_PATH, "docs")), "docs/ directory missing"


# ──────────────────────────────────────────────
# 3. Required script files exist
# ──────────────────────────────────────────────

def test_analysis_v1_exists():
    path = os.path.join(REPO_PATH, "scripts", "analysis_v1.py")
    assert os.path.isfile(path), "scripts/analysis_v1.py does not exist"


def test_analysis_v2_exists():
    path = os.path.join(REPO_PATH, "scripts", "analysis_v2.py")
    assert os.path.isfile(path), "scripts/analysis_v2.py does not exist"


def test_critical_analysis_exists():
    """critical_analysis.py must exist after recovery merge."""
    path = os.path.join(REPO_PATH, "scripts", "critical_analysis.py")
    assert os.path.isfile(path), (
        "scripts/critical_analysis.py does not exist — recovery may have failed"
    )


# ──────────────────────────────────────────────
# 4. File content validation
# ──────────────────────────────────────────────

def test_critical_analysis_contains_marker():
    """critical_analysis.py must contain the CRITICAL_DATA_MARKER string."""
    path = os.path.join(REPO_PATH, "scripts", "critical_analysis.py")
    assert os.path.isfile(path), "scripts/critical_analysis.py missing"
    content = open(path, "r").read()
    assert "CRITICAL_DATA_MARKER" in content, (
        "scripts/critical_analysis.py does not contain CRITICAL_DATA_MARKER"
    )


def test_analysis_v1_has_function_definition():
    """analysis_v1.py must contain at least one function definition."""
    path = os.path.join(REPO_PATH, "scripts", "analysis_v1.py")
    assert os.path.isfile(path), "scripts/analysis_v1.py missing"
    content = open(path, "r").read()
    assert "def " in content, (
        "scripts/analysis_v1.py does not contain a function definition"
    )


def test_analysis_v2_has_function_definition():
    """analysis_v2.py must contain at least one function definition."""
    path = os.path.join(REPO_PATH, "scripts", "analysis_v2.py")
    assert os.path.isfile(path), "scripts/analysis_v2.py missing"
    content = open(path, "r").read()
    assert "def " in content, (
        "scripts/analysis_v2.py does not contain a function definition"
    )


def test_critical_analysis_has_function_definition():
    """critical_analysis.py must contain at least one function definition."""
    path = os.path.join(REPO_PATH, "scripts", "critical_analysis.py")
    assert os.path.isfile(path), "scripts/critical_analysis.py missing"
    content = open(path, "r").read()
    assert "def " in content, (
        "scripts/critical_analysis.py does not contain a function definition"
    )


# ──────────────────────────────────────────────
# 5. Git branch checks
# ──────────────────────────────────────────────

def _get_default_branch():
    """Detect whether the default branch is main or master."""
    result = run_git(["branch", "--list", "main"])
    if result.returncode == 0 and "main" in result.stdout:
        return "main"
    result = run_git(["branch", "--list", "master"])
    if result.returncode == 0 and "master" in result.stdout:
        return "master"
    # Fallback: check symbolic-ref
    result = run_git(["symbolic-ref", "--short", "HEAD"])
    if result.returncode == 0:
        return result.stdout.strip()
    return "main"


def test_recovery_branch_exists():
    """A branch named 'recovery' must exist."""
    result = run_git(["branch", "--list", "recovery"])
    assert result.returncode == 0, "git branch --list recovery failed"
    assert "recovery" in result.stdout, "Branch 'recovery' does not exist"


def test_main_branch_exists():
    """The default branch (main or master) must exist."""
    branch = _get_default_branch()
    result = run_git(["branch", "--list", branch])
    assert branch in result.stdout, f"Default branch '{branch}' does not exist"


# ──────────────────────────────────────────────
# 6. Git tag check
# ──────────────────────────────────────────────

def test_recovery_complete_tag_exists():
    """A tag named 'recovery-complete' must exist."""
    result = run_git(["tag", "--list", "recovery-complete"])
    assert result.returncode == 0, "git tag --list failed"
    assert "recovery-complete" in result.stdout, "Tag 'recovery-complete' does not exist"


def test_recovery_complete_tag_on_main_branch():
    """The recovery-complete tag should be reachable from the main branch."""
    branch = _get_default_branch()
    # Get the commit the tag points to
    tag_result = run_git(["rev-list", "-n", "1", "recovery-complete"])
    assert tag_result.returncode == 0, "Could not resolve recovery-complete tag"
    tag_sha = tag_result.stdout.strip()

    # Check if this commit is an ancestor of the main branch
    result = run_git(["merge-base", "--is-ancestor", tag_sha, branch])
    assert result.returncode == 0, (
        f"Tag 'recovery-complete' is not reachable from '{branch}' branch"
    )


# ──────────────────────────────────────────────
# 7. Commit count and history
# ──────────────────────────────────────────────

def test_main_branch_has_at_least_4_commits():
    """The main branch must have at least 4 commits."""
    branch = _get_default_branch()
    result = run_git(["rev-list", "--count", branch])
    assert result.returncode == 0, "git rev-list --count failed"
    count = int(result.stdout.strip())
    assert count >= 4, (
        f"Main branch has only {count} commits, expected at least 4"
    )


def test_commits_have_distinct_messages():
    """The first 3 non-merge commits must have distinct, non-empty messages."""
    branch = _get_default_branch()
    result = run_git(["log", "--format=%s", branch])
    assert result.returncode == 0, "git log failed"
    messages = [m.strip() for m in result.stdout.strip().splitlines() if m.strip()]
    # Must have at least 3 non-empty messages
    assert len(messages) >= 3, (
        f"Expected at least 3 commit messages, found {len(messages)}"
    )
    # Check that at least 3 are distinct (allowing merge commits to duplicate)
    unique_messages = set(messages)
    assert len(unique_messages) >= 3, (
        f"Expected at least 3 distinct commit messages, found {len(unique_messages)}: {unique_messages}"
    )


# ──────────────────────────────────────────────
# 8. Recovery branch points to the critical commit
# ──────────────────────────────────────────────

def test_recovery_branch_contains_critical_file():
    """The recovery branch must contain scripts/critical_analysis.py."""
    result = run_git(["ls-tree", "-r", "--name-only", "recovery"])
    assert result.returncode == 0, "git ls-tree on recovery branch failed"
    files = result.stdout.strip().splitlines()
    assert "scripts/critical_analysis.py" in files, (
        "Recovery branch does not contain scripts/critical_analysis.py"
    )


def test_recovery_branch_critical_file_has_marker():
    """The critical_analysis.py on the recovery branch must contain CRITICAL_DATA_MARKER."""
    result = run_git(["show", "recovery:scripts/critical_analysis.py"])
    assert result.returncode == 0, "Could not read critical_analysis.py from recovery branch"
    assert "CRITICAL_DATA_MARKER" in result.stdout, (
        "critical_analysis.py on recovery branch does not contain CRITICAL_DATA_MARKER"
    )


# ──────────────────────────────────────────────
# 9. Recovery report validation
# ──────────────────────────────────────────────

def test_recovery_report_exists():
    """docs/recovery_report.txt must exist."""
    path = os.path.join(REPO_PATH, "docs", "recovery_report.txt")
    assert os.path.isfile(path), "docs/recovery_report.txt does not exist"


def test_recovery_report_has_at_least_4_lines():
    """docs/recovery_report.txt must have at least 4 lines of content."""
    path = os.path.join(REPO_PATH, "docs", "recovery_report.txt")
    assert os.path.isfile(path), "docs/recovery_report.txt does not exist"
    with open(path, "r") as f:
        lines = [line for line in f.readlines() if line.strip()]
    assert len(lines) >= 4, (
        f"recovery_report.txt has only {len(lines)} non-empty lines, expected at least 4"
    )


def test_recovery_report_contains_git_log_output():
    """The report should contain git log --oneline style output (short SHAs)."""
    path = os.path.join(REPO_PATH, "docs", "recovery_report.txt")
    assert os.path.isfile(path), "docs/recovery_report.txt does not exist"
    content = open(path, "r").read()
    # A git log --oneline entry looks like a 7+ char hex SHA followed by text
    import re
    sha_pattern = re.compile(r"[0-9a-f]{7,}")
    matches = sha_pattern.findall(content)
    assert len(matches) >= 3, (
        f"recovery_report.txt should contain git log output with commit SHAs, "
        f"found only {len(matches)} SHA-like strings"
    )


# ──────────────────────────────────────────────
# 10. Merge verification — critical file on main
# ──────────────────────────────────────────────

def test_critical_file_tracked_on_main():
    """critical_analysis.py must be tracked (not just in working tree) on the main branch."""
    branch = _get_default_branch()
    result = run_git(["ls-tree", "-r", "--name-only", branch])
    assert result.returncode == 0, "git ls-tree on main branch failed"
    files = result.stdout.strip().splitlines()
    assert "scripts/critical_analysis.py" in files, (
        "scripts/critical_analysis.py is not tracked on the main branch — merge may have failed"
    )


def test_recovery_branch_is_ancestor_of_main():
    """The recovery branch should be an ancestor of (or merged into) the main branch."""
    branch = _get_default_branch()
    # Get recovery branch tip
    rec_result = run_git(["rev-parse", "recovery"])
    assert rec_result.returncode == 0, "Could not resolve recovery branch"
    recovery_sha = rec_result.stdout.strip()

    # Check if recovery is ancestor of main (true if merged or cherry-picked the same commit)
    result = run_git(["merge-base", "--is-ancestor", recovery_sha, branch])
    assert result.returncode == 0, (
        "Recovery branch has not been merged into the main branch"
    )
