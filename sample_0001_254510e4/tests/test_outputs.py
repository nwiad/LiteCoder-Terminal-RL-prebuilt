"""
Tests for Git History Recovery task.

Validates that:
1. critical_data.txt has been recovered to disk with exact original content
2. No new commits were created (commit count remains 4)
3. Sibling files (readme.txt, notes.txt) are unchanged
4. Git history integrity is preserved
"""

import os
import subprocess

REPO_DIR = "/app/repo"

EXPECTED_CRITICAL_DATA = "version=1.0\nstatus=active\ndata=important_record_001\n"

EXPECTED_README = "Project README\nUpdated with more info.\n"

EXPECTED_NOTES = "Some development notes.\n"

EXPECTED_COMMIT_MESSAGES = [
    "Add notes",
    "Remove critical data",
    "Update readme",
    "Initial commit",
]


def run_git(args, cwd=REPO_DIR):
    """Helper to run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


# ── Test 1: File existence ──────────────────────────────────────────

def test_critical_data_file_exists():
    """critical_data.txt must exist on disk at /app/repo/critical_data.txt."""
    path = os.path.join(REPO_DIR, "critical_data.txt")
    assert os.path.isfile(path), (
        f"critical_data.txt not found at {path}. "
        "The file must be recovered from git history."
    )


# ── Test 2: File is not empty ───────────────────────────────────────

def test_critical_data_not_empty():
    """Recovered file must not be empty (catches lazy empty-file creation)."""
    path = os.path.join(REPO_DIR, "critical_data.txt")
    assert os.path.isfile(path), "critical_data.txt does not exist"
    size = os.path.getsize(path)
    assert size > 0, "critical_data.txt exists but is empty (0 bytes)"


# ── Test 3: Exact content match ─────────────────────────────────────

def test_critical_data_exact_content():
    """Recovered file content must match the original byte-for-byte."""
    path = os.path.join(REPO_DIR, "critical_data.txt")
    assert os.path.isfile(path), "critical_data.txt does not exist"
    with open(path, "r") as f:
        content = f.read()
    assert content == EXPECTED_CRITICAL_DATA, (
        f"Content mismatch.\n"
        f"Expected:\n{repr(EXPECTED_CRITICAL_DATA)}\n"
        f"Got:\n{repr(content)}"
    )


# ── Test 4: Line-by-line content validation ─────────────────────────

def test_critical_data_individual_lines():
    """Each line of critical_data.txt must match exactly."""
    path = os.path.join(REPO_DIR, "critical_data.txt")
    assert os.path.isfile(path), "critical_data.txt does not exist"
    with open(path, "r") as f:
        lines = f.read().splitlines()

    expected_lines = ["version=1.0", "status=active", "data=important_record_001"]
    assert len(lines) == len(expected_lines), (
        f"Expected {len(expected_lines)} lines, got {len(lines)}: {lines}"
    )
    for i, (got, expected) in enumerate(zip(lines, expected_lines)):
        assert got == expected, (
            f"Line {i+1} mismatch: expected {repr(expected)}, got {repr(got)}"
        )


# ── Test 5: Commit count must remain exactly 4 ─────────────────────

def test_commit_count_is_four():
    """No new commits should be created during recovery. Total must be 4."""
    stdout, rc = run_git(["rev-list", "--count", "HEAD"])
    assert rc == 0, "git rev-list failed"
    count = int(stdout)
    assert count == 4, (
        f"Expected exactly 4 commits, found {count}. "
        "Recovery must not create new commits."
    )


# ── Test 6: Git history commit messages are intact ──────────────────

def test_commit_messages_intact():
    """The 4 original commit messages must be preserved in order."""
    stdout, rc = run_git(["log", "--format=%s"])
    assert rc == 0, "git log failed"
    messages = stdout.strip().splitlines()
    assert len(messages) == 4, (
        f"Expected 4 commit messages, got {len(messages)}: {messages}"
    )
    for i, (got, expected) in enumerate(zip(messages, EXPECTED_COMMIT_MESSAGES)):
        assert got.strip() == expected, (
            f"Commit message {i+1} mismatch: expected {repr(expected)}, got {repr(got)}"
        )


# ── Test 7: readme.txt unchanged ────────────────────────────────────

def test_readme_unchanged():
    """readme.txt must remain unchanged after recovery."""
    path = os.path.join(REPO_DIR, "readme.txt")
    assert os.path.isfile(path), "readme.txt is missing"
    with open(path, "r") as f:
        content = f.read()
    assert content == EXPECTED_README, (
        f"readme.txt was modified.\n"
        f"Expected:\n{repr(EXPECTED_README)}\n"
        f"Got:\n{repr(content)}"
    )


# ── Test 8: notes.txt unchanged ─────────────────────────────────────

def test_notes_unchanged():
    """notes.txt must remain unchanged after recovery."""
    path = os.path.join(REPO_DIR, "notes.txt")
    assert os.path.isfile(path), "notes.txt is missing"
    with open(path, "r") as f:
        content = f.read()
    assert content == EXPECTED_NOTES, (
        f"notes.txt was modified.\n"
        f"Expected:\n{repr(EXPECTED_NOTES)}\n"
        f"Got:\n{repr(content)}"
    )


# ── Test 9: Repository is still valid ───────────────────────────────

def test_git_repo_valid():
    """The git repository must still be in a valid state."""
    stdout, rc = run_git(["status", "--porcelain"])
    assert rc == 0, "git status failed — repository may be corrupted"


# ── Test 10: No merge or rebase artifacts ───────────────────────────

def test_no_rebase_or_merge_in_progress():
    """Recovery should not leave the repo in a rebase/merge state."""
    git_dir = os.path.join(REPO_DIR, ".git")
    for artifact in ["MERGE_HEAD", "REBASE_HEAD", "rebase-merge", "rebase-apply"]:
        artifact_path = os.path.join(git_dir, artifact)
        assert not os.path.exists(artifact_path), (
            f"Found {artifact} in .git/ — repo is in an unfinished "
            f"merge/rebase state"
        )
