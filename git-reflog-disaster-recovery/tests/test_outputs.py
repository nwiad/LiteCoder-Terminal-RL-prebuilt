"""
Tests for Git Reflog Disaster Recovery task.

Validates that the agent correctly:
1. Found the lost commit (Refs #1883) and wrote its SHA
2. Created the recovery-1883 branch
3. Extracted the correct patch
4. Extracted the correct file contents at the lost commit
"""

import os
import re
import subprocess


# ── Paths ──────────────────────────────────────────────────────
REPO_DIR = "/app/recovered-repo"
COMMIT_SHA_FILE = "/app/commit_sha.txt"
PATCH_FILE = "/app/patch.diff"
BRANCHES_FILE = "/app/branches.txt"
BUGGY_FILE = "/app/buggy_file.txt"


# ── Helpers ────────────────────────────────────────────────────
def read_file(path):
    """Read file contents, return None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def git(args, cwd=REPO_DIR):
    """Run a git command inside the recovered repo."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


# ══════════════════════════════════════════════════════════════
#  1. commit_sha.txt
# ══════════════════════════════════════════════════════════════

def test_commit_sha_file_exists():
    """commit_sha.txt must exist."""
    assert os.path.isfile(COMMIT_SHA_FILE), (
        f"{COMMIT_SHA_FILE} does not exist"
    )


def test_commit_sha_is_40_hex_chars():
    """SHA must be exactly 40 lowercase hex characters."""
    content = read_file(COMMIT_SHA_FILE)
    assert content is not None, "commit_sha.txt missing"
    sha = content.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", sha), (
        f"Expected 40-char hex SHA, got: '{sha}'"
    )

def test_commit_sha_is_valid_git_object():
    """The SHA in commit_sha.txt must be a valid commit object in the repo."""
    content = read_file(COMMIT_SHA_FILE)
    assert content is not None, "commit_sha.txt missing"
    sha = content.strip()
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    result = git(["cat-file", "-t", sha])
    assert result.returncode == 0, (
        f"SHA {sha} is not a valid git object: {result.stderr}"
    )
    assert result.stdout.strip() == "commit", (
        f"SHA {sha} is type '{result.stdout.strip()}', expected 'commit'"
    )


def test_commit_sha_message_contains_refs_1883():
    """The commit pointed to by the SHA must have 'Refs #1883' in its message."""
    content = read_file(COMMIT_SHA_FILE)
    assert content is not None, "commit_sha.txt missing"
    sha = content.strip()
    result = git(["log", "--format=%s", "-1", sha])
    assert result.returncode == 0, f"Cannot read commit message: {result.stderr}"
    msg = result.stdout.strip()
    assert "Refs #1883" in msg, (
        f"Commit message does not contain 'Refs #1883'. Got: '{msg}'"
    )


# ══════════════════════════════════════════════════════════════
#  2. recovered-repo existence and structure
# ══════════════════════════════════════════════════════════════

def test_recovered_repo_exists():
    """The cloned working repo must exist at /app/recovered-repo."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), (
        f"{REPO_DIR} is not a git repository"
    )


# ══════════════════════════════════════════════════════════════
#  3. branches.txt — recovery-1883 branch
# ══════════════════════════════════════════════════════════════

def test_branches_file_exists():
    """branches.txt must exist."""
    assert os.path.isfile(BRANCHES_FILE), f"{BRANCHES_FILE} does not exist"


def test_branches_file_not_empty():
    """branches.txt must not be empty."""
    content = read_file(BRANCHES_FILE)
    assert content is not None, "branches.txt missing"
    assert len(content.strip()) > 0, "branches.txt is empty"


def test_branches_contains_recovery_1883():
    """branches.txt must list the recovery-1883 branch."""
    content = read_file(BRANCHES_FILE)
    assert content is not None, "branches.txt missing"
    # git branch output has lines like "  recovery-1883" or "* master"
    branch_names = [line.strip().lstrip("* ") for line in content.strip().splitlines()]
    assert "recovery-1883" in branch_names, (
        f"'recovery-1883' not found in branches. Found: {branch_names}"
    )


def test_recovery_branch_exists_in_repo():
    """The recovery-1883 branch must actually exist in the git repo."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    result = git(["rev-parse", "--verify", "recovery-1883"])
    assert result.returncode == 0, (
        f"Branch 'recovery-1883' does not exist in repo: {result.stderr}"
    )


def test_recovery_branch_points_to_correct_commit():
    """recovery-1883 must point to the same SHA as commit_sha.txt."""
    content = read_file(COMMIT_SHA_FILE)
    assert content is not None, "commit_sha.txt missing"
    expected_sha = content.strip()
    result = git(["rev-parse", "recovery-1883"])
    assert result.returncode == 0, f"Cannot resolve recovery-1883: {result.stderr}"
    actual_sha = result.stdout.strip()
    assert actual_sha == expected_sha, (
        f"recovery-1883 points to {actual_sha}, expected {expected_sha}"
    )


# ══════════════════════════════════════════════════════════════
#  4. patch.diff — the diff introduced by the lost commit
# ══════════════════════════════════════════════════════════════

def test_patch_file_exists():
    """patch.diff must exist."""
    assert os.path.isfile(PATCH_FILE), f"{PATCH_FILE} does not exist"


def test_patch_file_not_empty():
    """patch.diff must not be empty."""
    content = read_file(PATCH_FILE)
    assert content is not None, "patch.diff missing"
    assert len(content.strip()) > 0, "patch.diff is empty"


def test_patch_is_valid_diff():
    """patch.diff must look like a unified diff (contain diff markers)."""
    content = read_file(PATCH_FILE)
    assert content is not None, "patch.diff missing"
    assert "diff --git" in content, (
        "patch.diff does not contain 'diff --git' header"
    )
    assert "@@" in content, "patch.diff does not contain any @@ hunk headers"


def test_patch_no_commit_metadata():
    """patch.diff should not contain commit metadata (Author:, Date:, commit lines)."""
    content = read_file(PATCH_FILE)
    assert content is not None, "patch.diff missing"
    lines = content.strip().splitlines()
    # The first non-empty line should start with 'diff' not 'commit' or 'Author:'
    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break
    assert not first_line.startswith("commit "), (
        "patch.diff should not start with commit metadata"
    )
    assert not first_line.startswith("Author:"), (
        "patch.diff should not contain Author: header"
    )


def test_patch_modifies_tracker_py():
    """The patch must modify tracker.py (the file changed by the lost commit)."""
    content = read_file(PATCH_FILE)
    assert content is not None, "patch.diff missing"
    assert "tracker.py" in content, (
        "patch.diff does not reference tracker.py"
    )


def test_patch_contains_close_issue_addition():
    """The patch must add the close_issue method (core change of the lost commit)."""
    content = read_file(PATCH_FILE)
    assert content is not None, "patch.diff missing"
    assert "close_issue" in content, (
        "patch.diff does not contain 'close_issue' — the key method added by the lost commit"
    )


def test_patch_contains_priority_addition():
    """The patch must add the priority parameter (part of the lost commit's changes)."""
    content = read_file(PATCH_FILE)
    assert content is not None, "patch.diff missing"
    assert "priority" in content, (
        "patch.diff does not contain 'priority' — the parameter added by the lost commit"
    )


def test_patch_matches_git_show():
    """patch.diff must match what git show produces for the lost commit."""
    sha_content = read_file(COMMIT_SHA_FILE)
    if sha_content is None:
        assert False, "commit_sha.txt missing, cannot cross-validate patch"
    sha = sha_content.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        assert False, f"Invalid SHA in commit_sha.txt: {sha}"

    result = git(["show", sha, "--format=", "--patch"])
    if result.returncode != 0:
        assert False, f"git show failed: {result.stderr}"

    expected_patch = result.stdout
    actual_patch = read_file(PATCH_FILE)
    assert actual_patch is not None, "patch.diff missing"

    # Normalize whitespace for comparison
    expected_lines = [l.rstrip() for l in expected_patch.strip().splitlines()]
    actual_lines = [l.rstrip() for l in actual_patch.strip().splitlines()]
    assert actual_lines == expected_lines, (
        "patch.diff content does not match 'git show <SHA> --format= --patch' output"
    )


# ══════════════════════════════════════════════════════════════
#  5. buggy_file.txt — file contents at the lost commit
# ══════════════════════════════════════════════════════════════

def test_buggy_file_exists():
    """buggy_file.txt must exist."""
    assert os.path.isfile(BUGGY_FILE), f"{BUGGY_FILE} does not exist"


def test_buggy_file_not_empty():
    """buggy_file.txt must not be empty."""
    content = read_file(BUGGY_FILE)
    assert content is not None, "buggy_file.txt missing"
    assert len(content.strip()) > 0, "buggy_file.txt is empty"


def test_buggy_file_contains_close_issue_method():
    """buggy_file.txt must contain the close_issue method definition."""
    content = read_file(BUGGY_FILE)
    assert content is not None, "buggy_file.txt missing"
    assert "def close_issue" in content, (
        "buggy_file.txt does not contain 'def close_issue' method"
    )


def test_buggy_file_contains_priority_param():
    """buggy_file.txt must contain the priority parameter in add_issue."""
    content = read_file(BUGGY_FILE)
    assert content is not None, "buggy_file.txt missing"
    assert "priority" in content, (
        "buggy_file.txt does not contain 'priority' parameter"
    )


def test_buggy_file_contains_bugtracker_class():
    """buggy_file.txt must contain the BugTracker class."""
    content = read_file(BUGGY_FILE)
    assert content is not None, "buggy_file.txt missing"
    assert "class BugTracker" in content, (
        "buggy_file.txt does not contain 'class BugTracker'"
    )


def test_buggy_file_is_valid_python():
    """buggy_file.txt must be valid Python (it's tracker.py at the lost commit)."""
    content = read_file(BUGGY_FILE)
    assert content is not None, "buggy_file.txt missing"
    try:
        compile(content, "buggy_file.txt", "exec")
    except SyntaxError as e:
        assert False, f"buggy_file.txt is not valid Python: {e}"


def test_buggy_file_matches_git_show():
    """buggy_file.txt must match git show <SHA>:tracker.py."""
    sha_content = read_file(COMMIT_SHA_FILE)
    if sha_content is None:
        assert False, "commit_sha.txt missing, cannot cross-validate buggy_file"
    sha = sha_content.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        assert False, f"Invalid SHA in commit_sha.txt: {sha}"

    result = git(["show", f"{sha}:tracker.py"])
    if result.returncode != 0:
        assert False, f"git show {sha}:tracker.py failed: {result.stderr}"

    expected = result.stdout
    actual = read_file(BUGGY_FILE)
    assert actual is not None, "buggy_file.txt missing"

    # Normalize trailing whitespace
    expected_lines = [l.rstrip() for l in expected.strip().splitlines()]
    actual_lines = [l.rstrip() for l in actual.strip().splitlines()]
    assert actual_lines == expected_lines, (
        "buggy_file.txt does not match 'git show <SHA>:tracker.py' output"
    )


# ══════════════════════════════════════════════════════════════
#  6. Cross-validation: consistency between all outputs
# ══════════════════════════════════════════════════════════════

def test_commit_is_not_on_main_branch():
    """The lost commit should NOT be an ancestor of the main branch
    (it was dropped by the simulated disaster)."""
    sha_content = read_file(COMMIT_SHA_FILE)
    if sha_content is None:
        assert False, "commit_sha.txt missing"
    sha = sha_content.strip()

    # Determine the main branch name (master or main)
    result = git(["branch", "--list", "master", "main"])
    if result.returncode != 0:
        return  # skip if we can't determine
    branches = [b.strip().lstrip("* ") for b in result.stdout.strip().splitlines()]
    main_branch = None
    for b in ["master", "main"]:
        if b in branches:
            main_branch = b
            break
    if main_branch is None:
        return  # skip

    result = git(["merge-base", "--is-ancestor", sha, main_branch])
    assert result.returncode != 0, (
        f"The lost commit {sha} is still an ancestor of {main_branch} — "
        "it should have been dropped by the disaster"
    )
