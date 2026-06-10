"""
Tests for the recover-deleted-branch-merge task.

Validates:
1. Git repository state (branch exists, main checked out, merge done)
2. Output JSON structure and correctness
3. Actual file content on main after merge
4. Commit hash validity against real git objects
"""

import json
import os
import subprocess
import re

REPO_DIR = "/app/repo"
OUTPUT_FILE = "/app/output.json"

EXPECTED_BRANCH_NAME = "feature/user-auth"
EXPECTED_NUM_COMMITS = 3
EXPECTED_FILES = ["auth.py", "config.yaml", "tests/test_auth.py"]


def run_git(args, cwd=REPO_DIR):
    """Run a git command in the repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ──────────────────────────────────────────────
# Section 1: Git repository state checks
# ──────────────────────────────────────────────

def test_repo_exists():
    """The git repository at /app/repo must exist."""
    assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), f"{REPO_DIR} is not a git repository"


def test_main_is_checked_out():
    """HEAD must be on the main branch at the end."""
    stdout, _, rc = run_git(["branch", "--show-current"])
    assert rc == 0, "Failed to get current branch"
    assert stdout == "main", f"Expected current branch 'main', got '{stdout}'"


def test_feature_branch_exists():
    """The recovered branch feature/user-auth must exist."""
    stdout, _, rc = run_git(["branch", "--list", EXPECTED_BRANCH_NAME])
    assert rc == 0
    # git branch --list output has leading whitespace/asterisk
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines() if b.strip()]
    assert EXPECTED_BRANCH_NAME in branches, (
        f"Branch '{EXPECTED_BRANCH_NAME}' not found. Existing branches: {branches}"
    )


def test_feature_branch_has_correct_commit_count():
    """feature/user-auth must have exactly 3 commits not on original main (first commit)."""
    # Get the initial commit (root) — main's original single commit
    stdout, _, rc = run_git(["rev-list", "--max-parents=0", "HEAD"])
    assert rc == 0, "Failed to find root commit"
    root_commit = stdout.splitlines()[0].strip()

    # Count commits on feature branch that are not the root
    stdout, _, rc = run_git(["rev-list", "--count", f"{root_commit}..{EXPECTED_BRANCH_NAME}"])
    assert rc == 0, "Failed to count commits on feature branch"
    count = int(stdout)
    assert count == EXPECTED_NUM_COMMITS, (
        f"Expected {EXPECTED_NUM_COMMITS} commits on feature branch, got {count}"
    )


def test_merge_completed():
    """main must contain all commits from feature/user-auth (i.e., feature is ancestor of main)."""
    # feature/user-auth tip must be an ancestor of (or equal to) main
    _, _, rc = run_git(["merge-base", "--is-ancestor", EXPECTED_BRANCH_NAME, "main"])
    assert rc == 0, (
        "feature/user-auth is not an ancestor of main — merge was not completed"
    )


def test_feature_files_exist_on_main():
    """All files introduced by the feature branch must exist on main after merge."""
    for filepath in EXPECTED_FILES:
        full_path = os.path.join(REPO_DIR, filepath)
        assert os.path.isfile(full_path), (
            f"Expected file '{filepath}' to exist on main after merge, but it's missing"
        )


def test_auth_py_has_content():
    """auth.py must have meaningful content (not empty or dummy)."""
    auth_path = os.path.join(REPO_DIR, "auth.py")
    assert os.path.isfile(auth_path), "auth.py does not exist"
    content = open(auth_path).read()
    assert len(content) > 50, "auth.py appears to be empty or trivially small"
    assert "def login" in content, "auth.py should contain a login function"
    assert "def logout" in content, "auth.py should contain a logout function"


# ──────────────────────────────────────────────
# Section 2: Output JSON existence and structure
# ──────────────────────────────────────────────

def _load_output():
    """Helper to load and return the output JSON."""
    assert os.path.isfile(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE) as f:
        content = f.read().strip()
    assert len(content) > 10, "Output file appears empty or trivially small"
    data = json.loads(content)
    return data


def test_output_file_exists():
    """output.json must exist and be valid JSON."""
    data = _load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_has_required_keys():
    """output.json must contain all required keys."""
    data = _load_output()
    required_keys = [
        "recovered_branch",
        "tip_commit_hash",
        "num_commits_on_feature",
        "merge_commit_hash",
        "files_from_feature",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in output.json"


# ──────────────────────────────────────────────
# Section 3: Output JSON value correctness
# ──────────────────────────────────────────────

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def test_recovered_branch_name():
    """recovered_branch must be exactly 'feature/user-auth'."""
    data = _load_output()
    assert data["recovered_branch"] == EXPECTED_BRANCH_NAME, (
        f"Expected recovered_branch='{EXPECTED_BRANCH_NAME}', got '{data['recovered_branch']}'"
    )


def test_tip_commit_hash_format():
    """tip_commit_hash must be a valid 40-char lowercase hex SHA."""
    data = _load_output()
    h = data["tip_commit_hash"]
    assert isinstance(h, str), "tip_commit_hash must be a string"
    assert SHA_PATTERN.match(h), (
        f"tip_commit_hash '{h}' is not a valid 40-char lowercase hex SHA"
    )


def test_tip_commit_hash_exists_in_repo():
    """tip_commit_hash must reference a real commit object in the repo."""
    data = _load_output()
    h = data["tip_commit_hash"]
    stdout, _, rc = run_git(["cat-file", "-t", h])
    assert rc == 0 and stdout == "commit", (
        f"tip_commit_hash '{h}' does not reference a valid commit in the repo"
    )


def test_tip_commit_matches_feature_branch():
    """tip_commit_hash must match the actual tip of feature/user-auth."""
    data = _load_output()
    stdout, _, rc = run_git(["rev-parse", EXPECTED_BRANCH_NAME])
    assert rc == 0, "Failed to resolve feature/user-auth"
    actual_tip = stdout.strip()
    assert data["tip_commit_hash"] == actual_tip, (
        f"tip_commit_hash mismatch: output says '{data['tip_commit_hash']}', "
        f"but feature/user-auth actually points to '{actual_tip}'"
    )


def test_num_commits_on_feature():
    """num_commits_on_feature must be the integer 3."""
    data = _load_output()
    val = data["num_commits_on_feature"]
    assert isinstance(val, int), f"num_commits_on_feature must be an integer, got {type(val).__name__}"
    assert val == EXPECTED_NUM_COMMITS, (
        f"Expected num_commits_on_feature={EXPECTED_NUM_COMMITS}, got {val}"
    )


def test_merge_commit_hash_format():
    """merge_commit_hash must be a valid 40-char lowercase hex SHA."""
    data = _load_output()
    h = data["merge_commit_hash"]
    assert isinstance(h, str), "merge_commit_hash must be a string"
    assert SHA_PATTERN.match(h), (
        f"merge_commit_hash '{h}' is not a valid 40-char lowercase hex SHA"
    )


def test_merge_commit_hash_exists_in_repo():
    """merge_commit_hash must reference a real commit in the repo."""
    data = _load_output()
    h = data["merge_commit_hash"]
    stdout, _, rc = run_git(["cat-file", "-t", h])
    assert rc == 0 and stdout == "commit", (
        f"merge_commit_hash '{h}' does not reference a valid commit in the repo"
    )


def test_merge_commit_is_on_main():
    """merge_commit_hash must be reachable from main (i.e., an ancestor of or equal to HEAD)."""
    data = _load_output()
    h = data["merge_commit_hash"]
    # Check that the reported merge hash is an ancestor of (or equal to) current main HEAD
    _, _, rc = run_git(["merge-base", "--is-ancestor", h, "main"])
    assert rc == 0, (
        f"merge_commit_hash '{h}' is not reachable from main"
    )


def test_merge_commit_contains_feature_changes():
    """
    The merge_commit_hash (or main HEAD) must contain the feature branch.
    Whether it's a fast-forward or a real merge commit, the feature tip
    must be an ancestor of (or equal to) the merge result.
    """
    data = _load_output()
    merge_h = data["merge_commit_hash"]
    tip_h = data["tip_commit_hash"]
    # The feature tip must be ancestor-of-or-equal-to the merge result
    _, _, rc = run_git(["merge-base", "--is-ancestor", tip_h, merge_h])
    assert rc == 0, (
        f"Feature tip '{tip_h}' is not an ancestor of merge result '{merge_h}'. "
        "The merge did not incorporate the feature branch."
    )


def test_files_from_feature_value():
    """files_from_feature must be a sorted list matching the expected files."""
    data = _load_output()
    files = data["files_from_feature"]
    assert isinstance(files, list), "files_from_feature must be a list"
    # Normalize: strip whitespace from each entry
    files_clean = sorted([f.strip() for f in files if f.strip()])
    expected_sorted = sorted(EXPECTED_FILES)
    assert files_clean == expected_sorted, (
        f"Expected files_from_feature={expected_sorted}, got {files_clean}"
    )


def test_files_from_feature_no_duplicates():
    """files_from_feature must not contain duplicate entries."""
    data = _load_output()
    files = data["files_from_feature"]
    assert len(files) == len(set(files)), (
        f"files_from_feature contains duplicates: {files}"
    )


def test_files_from_feature_is_sorted():
    """files_from_feature must be sorted alphabetically."""
    data = _load_output()
    files = data["files_from_feature"]
    assert files == sorted(files), (
        f"files_from_feature is not sorted. Got: {files}, expected: {sorted(files)}"
    )


# ──────────────────────────────────────────────
# Section 4: Cross-validation (git state vs JSON)
# ──────────────────────────────────────────────

def test_main_head_matches_or_descends_merge_hash():
    """
    Current main HEAD must equal or descend from merge_commit_hash.
    (Agent might have made additional commits after merge, which is acceptable.)
    """
    data = _load_output()
    merge_h = data["merge_commit_hash"]
    stdout, _, rc = run_git(["rev-parse", "HEAD"])
    assert rc == 0
    head = stdout.strip()
    # merge_h must be ancestor-of-or-equal-to HEAD
    _, _, rc = run_git(["merge-base", "--is-ancestor", merge_h, head])
    assert rc == 0, (
        f"merge_commit_hash '{merge_h}' is not an ancestor of current HEAD '{head}'"
    )


def test_feature_files_tracked_by_git():
    """All expected feature files must be tracked by git on main."""
    stdout, _, rc = run_git(["ls-files"])
    assert rc == 0
    tracked = set(stdout.splitlines())
    for f in EXPECTED_FILES:
        assert f in tracked, (
            f"File '{f}' is not tracked by git on main. Tracked files: {tracked}"
        )
