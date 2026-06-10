"""
Tests for git-bisect-automation-script task.

Validates:
- /app/result.json exists with correct structure and values
- /app/repo is a valid git repository with exactly 20 commits
- Commit 11 is correctly identified as the first bad commit
- The hash in result.json matches the actual commit 11 hash in the repo
- Repository is in a clean state (no active bisect session)
- Required files exist in the repo
- bisect_script.sh uses git bisect run (automation, not manual)
- The good/bad boundary is correct (test passes at commit 10, fails at commit 11)
"""

import json
import os
import re
import subprocess


RESULT_PATH = "/app/result.json"
REPO_PATH = "/app/repo"


# ─── Helpers ───────────────────────────────────────────────────────────────

def load_result():
    """Load and return the result.json content."""
    with open(RESULT_PATH, "r") as f:
        return json.load(f)


def git(cmd, cwd=REPO_PATH):
    """Run a git command in the repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def get_all_commit_messages():
    """Return list of commit messages in chronological order (oldest first)."""
    stdout, _, _ = git(["log", "--reverse", "--format=%s"])
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def get_commit_hash_for_message(message):
    """Return the full SHA for the commit with the given message."""
    stdout, _, _ = git(["log", "--all", "--reverse", "--format=%H %s"])
    for line in stdout.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) == 2 and parts[1] == message:
            return parts[0]
    return None


# ─── Test: result.json existence and validity ──────────────────────────────

def test_result_file_exists():
    """result.json must exist at /app/result.json."""
    assert os.path.isfile(RESULT_PATH), f"{RESULT_PATH} does not exist"


def test_result_file_is_valid_json():
    """result.json must be parseable JSON."""
    assert os.path.isfile(RESULT_PATH), f"{RESULT_PATH} does not exist"
    with open(RESULT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "result.json is empty"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"result.json is not valid JSON: {e}"


def test_result_file_not_empty_object():
    """result.json must not be an empty object or array."""
    data = load_result()
    assert isinstance(data, dict), "result.json should be a JSON object"
    assert len(data) > 0, "result.json is an empty object"


# ─── Test: result.json required fields ─────────────────────────────────────

def test_result_has_all_required_fields():
    """result.json must contain all 5 required fields."""
    data = load_result()
    required = [
        "first_bad_commit_hash",
        "first_bad_commit_message",
        "total_commits",
        "good_commits",
        "bad_commits",
    ]
    for field in required:
        assert field in data, f"Missing required field: '{field}'"


def test_total_commits_value():
    """total_commits must be 20."""
    data = load_result()
    assert data["total_commits"] == 20, (
        f"Expected total_commits=20, got {data['total_commits']}"
    )


def test_good_commits_value():
    """good_commits must be 10."""
    data = load_result()
    assert data["good_commits"] == 10, (
        f"Expected good_commits=10, got {data['good_commits']}"
    )


def test_bad_commits_value():
    """bad_commits must be 10."""
    data = load_result()
    assert data["bad_commits"] == 10, (
        f"Expected bad_commits=10, got {data['bad_commits']}"
    )


def test_first_bad_commit_message():
    """first_bad_commit_message must be exactly 'Commit 11'."""
    data = load_result()
    msg = data["first_bad_commit_message"]
    assert isinstance(msg, str), "first_bad_commit_message must be a string"
    assert msg.strip() == "Commit 11", (
        f"Expected first_bad_commit_message='Commit 11', got '{msg}'"
    )


def test_first_bad_commit_hash_format():
    """first_bad_commit_hash must be a 40-character lowercase hex string (SHA-1)."""
    data = load_result()
    h = data["first_bad_commit_hash"]
    assert isinstance(h, str), "first_bad_commit_hash must be a string"
    assert re.fullmatch(r"[0-9a-f]{40}", h.strip()), (
        f"first_bad_commit_hash is not a valid 40-char SHA-1 hex: '{h}'"
    )


# ─── Test: cross-validate hash against actual repo ────────────────────────

def test_first_bad_commit_hash_matches_repo():
    """The hash in result.json must match the actual 'Commit 11' hash in the repo."""
    data = load_result()
    reported_hash = data["first_bad_commit_hash"].strip()

    actual_hash = get_commit_hash_for_message("Commit 11")
    assert actual_hash is not None, (
        "Could not find a commit with message 'Commit 11' in the repo"
    )
    assert reported_hash == actual_hash, (
        f"Hash mismatch: result.json has '{reported_hash}', "
        f"but actual 'Commit 11' hash is '{actual_hash}'"
    )


# ─── Test: git repository structure ───────────────────────────────────────

def test_repo_exists():
    """/app/repo must be a git repository."""
    assert os.path.isdir(REPO_PATH), f"{REPO_PATH} does not exist"
    assert os.path.isdir(os.path.join(REPO_PATH, ".git")), (
        f"{REPO_PATH} is not a git repository (no .git directory)"
    )


def test_repo_has_exactly_20_commits():
    """The repository must have exactly 20 commits."""
    stdout, _, rc = git(["rev-list", "--count", "HEAD"])
    assert rc == 0, "Failed to count commits"
    count = int(stdout.strip())
    assert count == 20, f"Expected 20 commits, found {count}"


def test_commit_messages_format():
    """All 20 commits must have messages in 'Commit N' format (N=1..20)."""
    messages = get_all_commit_messages()
    assert len(messages) == 20, f"Expected 20 commit messages, got {len(messages)}"
    for i, msg in enumerate(messages, start=1):
        expected = f"Commit {i}"
        assert msg == expected, (
            f"Commit {i} has message '{msg}', expected '{expected}'"
        )


# ─── Test: repo clean state ──────────────────────────────────────────────

def test_repo_not_in_bisect_state():
    """After execution, the repo must not be in an active bisect session."""
    bisect_log_path = os.path.join(REPO_PATH, ".git", "BISECT_LOG")
    # If BISECT_LOG exists, bisect is still active
    assert not os.path.isfile(bisect_log_path), (
        "Repository is still in a bisect session (BISECT_LOG exists)"
    )


def test_repo_head_is_on_branch():
    """HEAD should be on a branch (not detached) after bisect reset."""
    stdout, _, rc = git(["symbolic-ref", "HEAD"])
    assert rc == 0, (
        "HEAD is detached — repo should be on a branch after bisect reset"
    )
    assert "refs/heads/" in stdout, (
        f"HEAD does not point to a branch: '{stdout}'"
    )


# ─── Test: required files in repo ────────────────────────────────────────

def test_auth_py_exists():
    """auth.py must exist in /app/repo."""
    assert os.path.isfile(os.path.join(REPO_PATH, "auth.py")), (
        "auth.py not found in /app/repo"
    )


def test_test_auth_py_exists():
    """test_auth.py must exist in /app/repo."""
    assert os.path.isfile(os.path.join(REPO_PATH, "test_auth.py")), (
        "test_auth.py not found in /app/repo"
    )


def test_bisect_script_exists():
    """bisect_script.sh must exist in /app/repo."""
    assert os.path.isfile(os.path.join(REPO_PATH, "bisect_script.sh")), (
        "bisect_script.sh not found in /app/repo"
    )


# ─── Test: bisect_script.sh uses git bisect run ─────────────────────────

def test_bisect_script_uses_bisect_run():
    """bisect_script.sh must use 'git bisect run' for automation."""
    script_path = os.path.join(REPO_PATH, "bisect_script.sh")
    if not os.path.isfile(script_path):
        assert False, "bisect_script.sh not found"
    with open(script_path, "r") as f:
        content = f.read()
    assert "git bisect run" in content, (
        "bisect_script.sh does not contain 'git bisect run' — "
        "must use automated bisect, not manual steps"
    )


def test_bisect_script_is_executable():
    """bisect_script.sh must be executable."""
    script_path = os.path.join(REPO_PATH, "bisect_script.sh")
    if not os.path.isfile(script_path):
        assert False, "bisect_script.sh not found"
    assert os.access(script_path, os.X_OK), (
        "bisect_script.sh is not executable"
    )


# ─── Test: test_auth.py uses correct class name ─────────────────────────

def test_test_auth_has_correct_class():
    """test_auth.py must define a class named TestAuth."""
    path = os.path.join(REPO_PATH, "test_auth.py")
    if not os.path.isfile(path):
        assert False, "test_auth.py not found"
    with open(path, "r") as f:
        content = f.read()
    assert "class TestAuth" in content, (
        "test_auth.py does not contain 'class TestAuth'"
    )


def test_test_auth_uses_unittest():
    """test_auth.py must use the unittest module."""
    path = os.path.join(REPO_PATH, "test_auth.py")
    if not os.path.isfile(path):
        assert False, "test_auth.py not found"
    with open(path, "r") as f:
        content = f.read()
    assert "import unittest" in content or "from unittest" in content, (
        "test_auth.py does not import unittest"
    )


# ─── Test: good/bad boundary is correct in the actual repo ──────────────

def test_commit_10_is_good():
    """At commit 10, the test should pass (authenticate_user returns True)."""
    # Get hash of commit 10
    commit_10_hash = get_commit_hash_for_message("Commit 10")
    assert commit_10_hash is not None, "Could not find 'Commit 10' in repo"

    # Checkout commit 10, run the test, then go back
    git(["checkout", commit_10_hash])
    result = subprocess.run(
        ["python3", "-m", "unittest", "test_auth.TestAuth.test_user_authentication"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Go back to main branch
    git(["checkout", "main"])

    assert result.returncode == 0, (
        f"Test should PASS at Commit 10 (good commit), but it failed. "
        f"stderr: {result.stderr[:500]}"
    )


def test_commit_11_is_bad():
    """At commit 11, the test should fail (authenticate_user returns False)."""
    commit_11_hash = get_commit_hash_for_message("Commit 11")
    assert commit_11_hash is not None, "Could not find 'Commit 11' in repo"

    git(["checkout", commit_11_hash])
    result = subprocess.run(
        ["python3", "-m", "unittest", "test_auth.TestAuth.test_user_authentication"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        timeout=30,
    )
    git(["checkout", "main"])

    assert result.returncode != 0, (
        "Test should FAIL at Commit 11 (first bad commit), but it passed"
    )
