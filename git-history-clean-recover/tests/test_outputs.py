"""
Tests for Git History Clean & Recover task.

Validates:
1. Sensitive files removed from ALL history (not just working tree)
2. Non-sensitive files and commit messages preserved
3. Force-push recovery successful (HEAD matches saved hash)
4. output.json correctness cross-checked against actual repo state
"""

import os
import json
import subprocess

REPO_DIR = "/app/repo"
OUTPUT_JSON = "/app/output.json"
PRE_FORCEPUSH_HEAD = "/app/pre_forcepush_head.txt"

SENSITIVE_FILES = ["secrets/api_keys.json", ".env"]
EXPECTED_PRESERVED_FILES = sorted(["README.md", "app.py", "config.yaml", "feature.py"])
EXPECTED_COMMIT_MESSAGES = [
    "Initial project setup",
    "Add configuration",
    "Add feature module",
    "Add credentials file",
    "Update app",
]
EXPECTED_TOTAL_COMMITS = 5


def git(args, cwd=REPO_DIR):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout.strip(), result.returncode


# ──────────────────────────────────────────────
# File existence tests
# ──────────────────────────────────────────────

def test_repo_exists():
    """The repo directory must exist and be a git repo."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), f"{REPO_DIR} is not a git repo"


def test_output_json_exists():
    """output.json must exist and be valid JSON."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 10, "output.json appears empty or too small"
    data = json.loads(content)  # will raise if invalid JSON
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_pre_forcepush_head_exists():
    """pre_forcepush_head.txt must exist and contain a 40-char hex hash."""
    assert os.path.isfile(PRE_FORCEPUSH_HEAD), f"{PRE_FORCEPUSH_HEAD} does not exist"
    with open(PRE_FORCEPUSH_HEAD, "r") as f:
        content = f.read().strip()
    assert len(content) == 40, f"Expected 40-char hash, got {len(content)} chars"
    assert all(c in "0123456789abcdef" for c in content), "Hash contains non-hex characters"


# ──────────────────────────────────────────────
# Part 1: Sensitive files removed from ALL history
# ──────────────────────────────────────────────

def test_sensitive_files_not_in_working_tree():
    """Sensitive files must not exist in the working directory."""
    for sf in SENSITIVE_FILES:
        full_path = os.path.join(REPO_DIR, sf)
        assert not os.path.exists(full_path), f"Sensitive file {sf} still exists in working tree"


def test_sensitive_files_not_in_any_commit():
    """
    Sensitive files must not appear in ANY commit's tree across the entire history.
    This is the critical test — catches agents that only delete from HEAD but not history.
    """
    # Get all commit hashes
    commits_out, rc = git(["rev-list", "--all"])
    assert rc == 0, "git rev-list --all failed"
    commit_hashes = [h for h in commits_out.split("\n") if h.strip()]
    assert len(commit_hashes) > 0, "No commits found in repo"

    for commit_hash in commit_hashes:
        # List all files in this commit's tree
        ls_out, rc2 = git(["ls-tree", "-r", "--name-only", commit_hash])
        if rc2 != 0:
            continue
        files_in_commit = [f.strip() for f in ls_out.split("\n") if f.strip()]
        for sf in SENSITIVE_FILES:
            assert sf not in files_in_commit, (
                f"Sensitive file '{sf}' found in commit {commit_hash[:8]}. "
                f"History was not fully cleaned."
            )


def test_sensitive_files_not_in_git_log_diff():
    """
    Double-check: git log --all --diff-filter=A should not show sensitive files
    being added in any commit. This catches edge cases where ls-tree might miss
    files in merge commits.
    """
    for sf in SENSITIVE_FILES:
        out, rc = git(["log", "--all", "--pretty=format:%H", "--", sf])
        assert rc == 0
        commits_touching = [h for h in out.split("\n") if h.strip()]
        assert len(commits_touching) == 0, (
            f"Sensitive file '{sf}' still referenced in git log history "
            f"(commits: {commits_touching[:3]})"
        )


# ──────────────────────────────────────────────
# Part 1 continued: Preserved files and commits
# ──────────────────────────────────────────────

def test_preserved_files_in_working_tree():
    """All non-sensitive files must exist in the final working tree."""
    ls_out, rc = git(["ls-files"])
    assert rc == 0, "git ls-files failed"
    tracked_files = sorted([f.strip() for f in ls_out.split("\n") if f.strip()])
    for pf in EXPECTED_PRESERVED_FILES:
        assert pf in tracked_files, f"Expected preserved file '{pf}' not found in working tree"


def test_total_commits_on_main():
    """There must be exactly 5 commits on main."""
    log_out, rc = git(["log", "--oneline", "--first-parent", "main"])
    assert rc == 0, "git log on main failed"
    commits = [line for line in log_out.split("\n") if line.strip()]
    assert len(commits) == EXPECTED_TOTAL_COMMITS, (
        f"Expected {EXPECTED_TOTAL_COMMITS} commits, found {len(commits)}"
    )


def test_commit_messages_preserved():
    """All 5 original commit messages must be preserved in order (oldest first)."""
    msg_out, rc = git(["log", "--reverse", "--format=%s", "main"])
    assert rc == 0, "git log --format=%s failed"
    actual_messages = [m.strip() for m in msg_out.split("\n") if m.strip()]
    assert len(actual_messages) == len(EXPECTED_COMMIT_MESSAGES), (
        f"Expected {len(EXPECTED_COMMIT_MESSAGES)} commit messages, "
        f"got {len(actual_messages)}: {actual_messages}"
    )
    for i, (expected, actual) in enumerate(zip(EXPECTED_COMMIT_MESSAGES, actual_messages)):
        assert actual == expected, (
            f"Commit {i+1} message mismatch: expected '{expected}', got '{actual}'"
        )


# ──────────────────────────────────────────────
# Part 1 continued: File content verification
# ──────────────────────────────────────────────

def test_readme_content():
    """README.md must have the expected content."""
    path = os.path.join(REPO_DIR, "README.md")
    assert os.path.isfile(path), "README.md missing"
    with open(path, "r") as f:
        content = f.read()
    assert "# MyProject" in content, "README.md missing '# MyProject' header"
    assert "A sample project." in content, "README.md missing 'A sample project.' line"


def test_app_py_content():
    """app.py must have the final (Commit 5) content."""
    path = os.path.join(REPO_DIR, "app.py")
    assert os.path.isfile(path), "app.py missing"
    with open(path, "r") as f:
        content = f.read()
    assert "from feature import run" in content, "app.py missing 'from feature import run'"
    assert "print(run())" in content, "app.py missing 'print(run())'"


def test_config_yaml_content():
    """config.yaml must have the expected content."""
    path = os.path.join(REPO_DIR, "config.yaml")
    assert os.path.isfile(path), "config.yaml missing"
    with open(path, "r") as f:
        content = f.read()
    assert "db_host: localhost" in content
    assert "db_port: 5432" in content


def test_feature_py_content():
    """feature.py must have the expected content."""
    path = os.path.join(REPO_DIR, "feature.py")
    assert os.path.isfile(path), "feature.py missing"
    with open(path, "r") as f:
        content = f.read()
    assert "def run():" in content
    assert "return True" in content


# ──────────────────────────────────────────────
# Part 2: Force-push recovery
# ──────────────────────────────────────────────

def test_recovery_head_matches_saved_hash():
    """
    The current HEAD of main must match the hash saved in pre_forcepush_head.txt.
    This verifies the force-push recovery was successful.
    """
    with open(PRE_FORCEPUSH_HEAD, "r") as f:
        saved_hash = f.read().strip()

    current_head, rc = git(["rev-parse", "HEAD"])
    assert rc == 0, "git rev-parse HEAD failed"
    assert current_head == saved_hash, (
        f"Recovery failed: HEAD is {current_head[:8]} but saved hash is {saved_hash[:8]}"
    )


def test_saved_hash_is_valid_commit():
    """The hash in pre_forcepush_head.txt must be a valid commit object in the repo."""
    with open(PRE_FORCEPUSH_HEAD, "r") as f:
        saved_hash = f.read().strip()

    obj_type, rc = git(["cat-file", "-t", saved_hash])
    assert rc == 0, f"Hash {saved_hash[:8]} is not a valid git object"
    assert obj_type == "commit", f"Hash {saved_hash[:8]} is type '{obj_type}', expected 'commit'"


# ──────────────────────────────────────────────
# Part 3: output.json cross-validation
# ──────────────────────────────────────────────

def _load_output():
    """Helper to load and return output.json as dict."""
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def test_output_json_has_required_keys():
    """output.json must contain all required keys."""
    data = _load_output()
    required_keys = [
        "total_commits",
        "sensitive_files_removed",
        "preserved_files",
        "commit_messages",
        "recovery_successful",
    ]
    for key in required_keys:
        assert key in data, f"output.json missing required key: '{key}'"


def test_output_total_commits():
    """output.json total_commits must match actual repo commit count."""
    data = _load_output()
    assert isinstance(data["total_commits"], int), "total_commits must be an integer"
    assert data["total_commits"] == EXPECTED_TOTAL_COMMITS, (
        f"total_commits is {data['total_commits']}, expected {EXPECTED_TOTAL_COMMITS}"
    )
    # Cross-check against actual repo
    log_out, rc = git(["log", "--oneline", "--first-parent", "main"])
    assert rc == 0
    actual_count = len([l for l in log_out.split("\n") if l.strip()])
    assert data["total_commits"] == actual_count, (
        f"total_commits ({data['total_commits']}) doesn't match actual repo ({actual_count})"
    )


def test_output_sensitive_files_removed():
    """output.json sensitive_files_removed must list the two sensitive files."""
    data = _load_output()
    removed = data["sensitive_files_removed"]
    assert isinstance(removed, list), "sensitive_files_removed must be a list"
    assert sorted(removed) == sorted(SENSITIVE_FILES), (
        f"sensitive_files_removed is {removed}, expected {SENSITIVE_FILES}"
    )


def test_output_preserved_files():
    """output.json preserved_files must match actual non-sensitive tracked files."""
    data = _load_output()
    preserved = data["preserved_files"]
    assert isinstance(preserved, list), "preserved_files must be a list"
    assert sorted(preserved) == EXPECTED_PRESERVED_FILES, (
        f"preserved_files is {sorted(preserved)}, expected {EXPECTED_PRESERVED_FILES}"
    )
    # Cross-check: these files must actually exist in the working tree
    ls_out, rc = git(["ls-files"])
    assert rc == 0
    actual_files = sorted([f.strip() for f in ls_out.split("\n") if f.strip()])
    for pf in preserved:
        assert pf in actual_files, (
            f"output.json claims '{pf}' is preserved but it's not in git ls-files"
        )


def test_output_commit_messages():
    """output.json commit_messages must match actual repo messages in order."""
    data = _load_output()
    messages = data["commit_messages"]
    assert isinstance(messages, list), "commit_messages must be a list"
    assert messages == EXPECTED_COMMIT_MESSAGES, (
        f"commit_messages mismatch.\nExpected: {EXPECTED_COMMIT_MESSAGES}\nGot: {messages}"
    )
    # Cross-check against actual repo
    msg_out, rc = git(["log", "--reverse", "--format=%s", "main"])
    assert rc == 0
    actual_messages = [m.strip() for m in msg_out.split("\n") if m.strip()]
    assert messages == actual_messages, (
        f"output.json commit_messages don't match actual repo.\n"
        f"output.json: {messages}\nActual repo: {actual_messages}"
    )


def test_output_recovery_successful():
    """output.json recovery_successful must be true and match actual state."""
    data = _load_output()
    assert data["recovery_successful"] is True, (
        f"recovery_successful is {data['recovery_successful']}, expected true"
    )
    # Cross-check: HEAD must actually match saved hash
    with open(PRE_FORCEPUSH_HEAD, "r") as f:
        saved_hash = f.read().strip()
    current_head, rc = git(["rev-parse", "HEAD"])
    assert rc == 0
    assert current_head == saved_hash, (
        "output.json says recovery_successful=true but HEAD doesn't match saved hash"
    )


# ──────────────────────────────────────────────
# Anti-cheat: verify repo is not a shallow clone or trivial fake
# ──────────────────────────────────────────────

def test_repo_has_real_history():
    """
    Verify the repo has real commit history with parent relationships,
    not just a single squashed commit.
    """
    # First commit should have no parent
    log_out, rc = git(["log", "--reverse", "--format=%H %P", "main"])
    assert rc == 0
    lines = [l.strip() for l in log_out.split("\n") if l.strip()]
    assert len(lines) == EXPECTED_TOTAL_COMMITS, (
        f"Expected {EXPECTED_TOTAL_COMMITS} commits in history, got {len(lines)}"
    )
    # First commit has no parent (only hash, no space-separated parent)
    first_parts = lines[0].split()
    assert len(first_parts) == 1, "First commit should have no parent (root commit)"
    # All subsequent commits should have exactly one parent
    for i, line in enumerate(lines[1:], start=2):
        parts = line.split()
        assert len(parts) == 2, (
            f"Commit {i} should have exactly one parent, got {len(parts)-1}"
        )

