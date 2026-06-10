"""
Tests for Git Stash Workflow Recovery task.

Validates the final git state and output file after the agent completes the task.
All tests run against /app where the git repository should exist.
"""

import os
import subprocess

REPO_DIR = "/app"
REPORT_FILE = os.path.join(REPO_DIR, "stash_report.txt")
README_FILE = os.path.join(REPO_DIR, "README.md")


def run_git(args, cwd=REPO_DIR):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ============================================================
# stash_report.txt — existence and format
# ============================================================

def test_report_file_exists():
    """stash_report.txt must exist at /app/stash_report.txt."""
    assert os.path.isfile(REPORT_FILE), (
        f"stash_report.txt not found at {REPORT_FILE}"
    )


def test_report_file_has_three_lines():
    """stash_report.txt must have exactly 3 non-empty lines."""
    with open(REPORT_FILE) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(lines) == 3, (
        f"Expected 3 lines in stash_report.txt, got {len(lines)}: {lines}"
    )


def test_report_line1_stash_count():
    """Line 1 of stash_report.txt must be '3' (total stash count)."""
    with open(REPORT_FILE) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(lines) >= 1, "stash_report.txt is empty"
    assert lines[0] == "3", (
        f"Expected stash count '3' on line 1, got '{lines[0]}'"
    )


def test_report_line2_stash_ref():
    """Line 2 must be 'stash@{1}' — the applied stash reference."""
    with open(REPORT_FILE) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(lines) >= 2, "stash_report.txt has fewer than 2 lines"
    assert lines[1] == "stash@{1}", (
        f"Expected 'stash@{1}' on line 2, got '{lines[1]}'"
    )


def test_report_line3_branch_name():
    """Line 3 must be 'feature/user-auth' — the current branch."""
    with open(REPORT_FILE) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(lines) >= 3, "stash_report.txt has fewer than 3 lines"
    assert lines[2] == "feature/user-auth", (
        f"Expected 'feature/user-auth' on line 3, got '{lines[2]}'"
    )


# ============================================================
# Git repository state — branch
# ============================================================

def test_repo_is_git_directory():
    """The /app directory must be a valid git repository."""
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), (
        "/app is not a git repository (no .git directory)"
    )


def test_current_branch_is_feature_user_auth():
    """HEAD must point to feature/user-auth."""
    stdout, _, rc = run_git(["branch", "--show-current"])
    assert rc == 0, "git branch --show-current failed"
    assert stdout == "feature/user-auth", (
        f"Expected current branch 'feature/user-auth', got '{stdout}'"
    )


# ============================================================
# Git repository state — commits
# ============================================================

def test_latest_commit_message():
    """The most recent commit on feature/user-auth must be
    'Add user authentication feature'."""
    stdout, _, rc = run_git(["log", "-1", "--format=%s"])
    assert rc == 0, "git log failed"
    assert stdout == "Add user authentication feature", (
        f"Expected commit message 'Add user authentication feature', "
        f"got '{stdout}'"
    )


def test_initial_commit_exists():
    """There must be a commit with message 'Initial commit' in history."""
    stdout, _, rc = run_git(["log", "--all", "--format=%s"])
    assert rc == 0, "git log failed"
    messages = [m.strip() for m in stdout.splitlines()]
    assert "Initial commit" in messages, (
        f"'Initial commit' not found in commit history: {messages}"
    )


def test_feature_branch_has_two_commits():
    """feature/user-auth should have exactly 2 commits
    (Initial commit + Add user authentication feature)."""
    stdout, _, rc = run_git(["rev-list", "--count", "feature/user-auth"])
    assert rc == 0, "git rev-list failed"
    count = int(stdout)
    assert count == 2, (
        f"Expected 2 commits on feature/user-auth, got {count}"
    )


# ============================================================
# Git repository state — README.md content
# ============================================================

def test_readme_exists():
    """README.md must exist in /app."""
    assert os.path.isfile(README_FILE), (
        f"README.md not found at {README_FILE}"
    )


def test_readme_has_user_auth_section():
    """README.md must contain the '## User Authentication' section."""
    with open(README_FILE) as f:
        content = f.read()
    assert "## User Authentication" in content, (
        "README.md does not contain '## User Authentication' heading"
    )


def test_readme_has_login_endpoint_bullet():
    """README.md must contain '- Add login endpoint'."""
    with open(README_FILE) as f:
        content = f.read()
    assert "- Add login endpoint" in content, (
        "README.md missing '- Add login endpoint'"
    )


def test_readme_has_session_management_bullet():
    """README.md must contain '- Add session management'."""
    with open(README_FILE) as f:
        content = f.read()
    assert "- Add session management" in content, (
        "README.md missing '- Add session management'"
    )


def test_readme_does_not_have_bugfix_section():
    """README.md must NOT contain the bugfix stash content."""
    with open(README_FILE) as f:
        content = f.read()
    assert "## Bug Fixes" not in content, (
        "README.md incorrectly contains '## Bug Fixes' — wrong stash applied"
    )


def test_readme_does_not_have_experiment_section():
    """README.md must NOT contain the experiment stash content."""
    with open(README_FILE) as f:
        content = f.read()
    assert "## Experiment" not in content, (
        "README.md incorrectly contains '## Experiment' — wrong stash applied"
    )


# ============================================================
# Git repository state — stashes
# ============================================================

def test_stash_count_is_three():
    """All 3 stashes must still exist (apply was used, not pop)."""
    stdout, _, rc = run_git(["stash", "list"])
    assert rc == 0, "git stash list failed"
    stash_lines = [l for l in stdout.splitlines() if l.strip()]
    assert len(stash_lines) == 3, (
        f"Expected 3 stashes, got {len(stash_lines)}. "
        f"If fewer, 'pop' may have been used instead of 'apply'. "
        f"Stash list: {stash_lines}"
    )


def test_stash_messages_present():
    """The three stash messages must include the expected keywords."""
    stdout, _, rc = run_git(["stash", "list"])
    assert rc == 0, "git stash list failed"
    expected_keywords = ["bugfix notes", "user-auth feature", "random experiment"]
    for kw in expected_keywords:
        assert kw in stdout, (
            f"Stash message containing '{kw}' not found in stash list:\n{stdout}"
        )


def test_stash_order():
    """Stash ordering: stash@{0} should be 'random experiment',
    stash@{1} should be 'user-auth feature',
    stash@{2} should be 'bugfix notes'."""
    stdout, _, rc = run_git(["stash", "list"])
    assert rc == 0, "git stash list failed"
    lines = [l.strip() for l in stdout.splitlines() if l.strip()]
    assert len(lines) == 3, f"Expected 3 stash entries, got {len(lines)}"

    assert "random experiment" in lines[0], (
        f"stash@{{0}} should contain 'random experiment', got: {lines[0]}"
    )
    assert "user-auth feature" in lines[1], (
        f"stash@{{1}} should contain 'user-auth feature', got: {lines[1]}"
    )
    assert "bugfix notes" in lines[2], (
        f"stash@{{2}} should contain 'bugfix notes', got: {lines[2]}"
    )


# ============================================================
# Git repository state — clean working directory
# ============================================================

def test_working_directory_clean():
    """There should be no uncommitted changes (staged or unstaged)
    in tracked files."""
    stdout, _, rc = run_git(["status", "--porcelain"])
    assert rc == 0, "git status failed"
    # Filter out untracked files (lines starting with '??') since
    # stash_report.txt may be untracked and that's acceptable
    dirty_lines = [
        l for l in stdout.splitlines()
        if l.strip() and not l.startswith("??")
    ]
    assert len(dirty_lines) == 0, (
        f"Working directory has uncommitted changes:\n"
        + "\n".join(dirty_lines)
    )


# ============================================================
# Cross-validation: report matches actual git state
# ============================================================

def test_report_stash_count_matches_git():
    """The stash count in stash_report.txt must match actual git stash count."""
    with open(REPORT_FILE) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    reported_count = int(lines[0])

    stdout, _, rc = run_git(["stash", "list"])
    assert rc == 0
    actual_count = len([l for l in stdout.splitlines() if l.strip()])

    assert reported_count == actual_count, (
        f"Report says {reported_count} stashes but git has {actual_count}"
    )


def test_report_branch_matches_git():
    """The branch in stash_report.txt must match actual current branch."""
    with open(REPORT_FILE) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    reported_branch = lines[2]

    stdout, _, rc = run_git(["branch", "--show-current"])
    assert rc == 0
    assert reported_branch == stdout, (
        f"Report says branch '{reported_branch}' but git says '{stdout}'"
    )
