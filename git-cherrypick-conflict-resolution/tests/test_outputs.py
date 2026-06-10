"""
Tests for Git Cherry-Pick and Conflict Resolution task.

Validates:
1. Git repository structure (branches, checked-out branch)
2. File contents on production branch (app.py, config.txt)
3. Commit history on production branch
4. /app/result.json correctness (cross-validated against actual git state)
"""

import os
import json
import subprocess


REPO_DIR = "/app/repo"
RESULT_JSON = "/app/result.json"


def run_git(args, cwd=REPO_DIR):
    """Run a git command in the repo directory and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ──────────────────────────────────────────────────────────────────────
# 1. Repository existence and validity
# ──────────────────────────────────────────────────────────────────────

def test_repo_exists():
    """The git repository directory must exist."""
    assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"


def test_repo_is_valid_git():
    """The directory must be a valid git repository."""
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), \
        f"{REPO_DIR} is not a valid git repository (no .git directory)"


# ──────────────────────────────────────────────────────────────────────
# 2. Branch structure
# ──────────────────────────────────────────────────────────────────────

def test_all_branches_exist():
    """All four required branches must exist."""
    stdout, _, rc = run_git(["branch", "--list"])
    assert rc == 0, "git branch failed"
    branches = sorted([b.strip().lstrip("* ") for b in stdout.splitlines()])
    for expected in ["feature-x", "feature-y", "main", "production"]:
        assert expected in branches, \
            f"Branch '{expected}' not found. Existing branches: {branches}"


def test_production_is_checked_out():
    """The production branch must be the currently checked-out branch."""
    stdout, _, rc = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    assert rc == 0, "git rev-parse failed"
    assert stdout == "production", \
        f"Expected 'production' to be checked out, but HEAD is on '{stdout}'"


# ──────────────────────────────────────────────────────────────────────
# 3. File contents on production branch
# ──────────────────────────────────────────────────────────────────────

EXPECTED_APP_PY = '''\
def greet(name):
    return "Hey, " + name + "!"

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def subtract(a, b):
    return a - b

def version():
    return "1.0.0"'''

EXPECTED_CONFIG_TXT = '''\
mode=production
debug=true
log_level=debug
feature_x=enabled
feature_y=enabled'''


def test_app_py_exists():
    """app.py must exist on the production branch."""
    path = os.path.join(REPO_DIR, "app.py")
    assert os.path.isfile(path), "app.py not found in repository"


def test_app_py_content():
    """app.py must have the exact expected content after conflict resolution."""
    path = os.path.join(REPO_DIR, "app.py")
    assert os.path.isfile(path), "app.py not found"
    content = open(path).read().strip()
    assert content == EXPECTED_APP_PY.strip(), (
        f"app.py content mismatch.\n"
        f"--- EXPECTED ---\n{EXPECTED_APP_PY.strip()}\n"
        f"--- ACTUAL ---\n{content}"
    )


def test_app_py_no_conflict_markers():
    """app.py must not contain any unresolved conflict markers."""
    path = os.path.join(REPO_DIR, "app.py")
    if not os.path.isfile(path):
        return  # covered by existence test
    content = open(path).read()
    for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
        assert marker not in content, \
            f"app.py contains unresolved conflict marker: {marker}"


def test_config_txt_exists():
    """config.txt must exist on the production branch."""
    path = os.path.join(REPO_DIR, "config.txt")
    assert os.path.isfile(path), "config.txt not found in repository"


def test_config_txt_content():
    """config.txt must have the exact expected content after conflict resolution."""
    path = os.path.join(REPO_DIR, "config.txt")
    assert os.path.isfile(path), "config.txt not found"
    content = open(path).read().strip()
    assert content == EXPECTED_CONFIG_TXT.strip(), (
        f"config.txt content mismatch.\n"
        f"--- EXPECTED ---\n{EXPECTED_CONFIG_TXT.strip()}\n"
        f"--- ACTUAL ---\n{content}"
    )


def test_config_txt_no_conflict_markers():
    """config.txt must not contain any unresolved conflict markers."""
    path = os.path.join(REPO_DIR, "config.txt")
    if not os.path.isfile(path):
        return
    content = open(path).read()
    for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
        assert marker not in content, \
            f"config.txt contains unresolved conflict marker: {marker}"


def test_app_py_greet_function():
    """The greet function must return the feature-y version."""
    path = os.path.join(REPO_DIR, "app.py")
    assert os.path.isfile(path), "app.py not found"
    content = open(path).read()
    assert 'return "Hey, " + name + "!"' in content, \
        "greet() must return 'Hey, ' + name + '!' (feature-y version)"
    # Must NOT contain the feature-x or original versions
    assert 'return "Hi, " + name + "!"' not in content, \
        "greet() should not contain feature-x version ('Hi, ')"
    assert 'return "Hello, " + name' not in content, \
        "greet() should not contain original version ('Hello, ')"


def test_app_py_has_all_functions():
    """app.py must contain greet, add, multiply, subtract, and version functions."""
    path = os.path.join(REPO_DIR, "app.py")
    assert os.path.isfile(path), "app.py not found"
    content = open(path).read()
    for func in ["def greet(", "def add(", "def multiply(", "def subtract(", "def version("]:
        assert func in content, f"app.py missing function: {func}"


def test_config_has_both_feature_flags():
    """config.txt must contain both feature_x=enabled and feature_y=enabled."""
    path = os.path.join(REPO_DIR, "config.txt")
    assert os.path.isfile(path), "config.txt not found"
    content = open(path).read()
    assert "feature_x=enabled" in content, "config.txt missing feature_x=enabled"
    assert "feature_y=enabled" in content, "config.txt missing feature_y=enabled"


def test_config_has_merged_values():
    """config.txt must have debug=true and log_level=debug (merged from both features)."""
    path = os.path.join(REPO_DIR, "config.txt")
    assert os.path.isfile(path), "config.txt not found"
    content = open(path).read()
    assert "debug=true" in content, "config.txt should have debug=true"
    assert "log_level=debug" in content, "config.txt should have log_level=debug"
    assert "debug=false" not in content, "config.txt should not have debug=false"
    assert "log_level=info" not in content, "config.txt should not have log_level=info"


# ──────────────────────────────────────────────────────────────────────
# 4. Commit history on production branch
# ──────────────────────────────────────────────────────────────────────

def test_production_commit_count():
    """Production branch must have exactly 5 commits (1 initial + 4 cherry-picks)."""
    stdout, _, rc = run_git(["rev-list", "--count", "production"])
    assert rc == 0, "git rev-list failed"
    count = int(stdout)
    assert count == 5, f"Expected 5 commits on production, got {count}"


def test_production_cherry_pick_messages():
    """Production branch must contain the 4 cherry-picked commit messages."""
    stdout, _, rc = run_git(["log", "--format=%s", "production"])
    assert rc == 0, "git log failed"
    messages = stdout.splitlines()
    expected_messages = [
        "feature-x: update greet and add multiply",
        "feature-y: update greet and add subtract",
        "feature-x: update config",
        "feature-y: update config",
    ]
    for msg in expected_messages:
        assert msg in messages, \
            f"Cherry-pick commit message not found: '{msg}'. Messages: {messages}"


def test_production_commit_order():
    """Cherry-picked commits must appear in the correct order on production."""
    stdout, _, rc = run_git(["log", "--format=%s", "--reverse", "production"])
    assert rc == 0, "git log failed"
    messages = stdout.splitlines()
    # First commit is the initial commit, then 4 cherry-picks in order
    assert len(messages) >= 5, f"Expected at least 5 commits, got {len(messages)}"
    # The cherry-picks should be in this order (indices 1-4)
    cherry_picks = messages[1:]
    expected_order = [
        "feature-x: update greet and add multiply",
        "feature-y: update greet and add subtract",
        "feature-x: update config",
        "feature-y: update config",
    ]
    for i, expected_msg in enumerate(expected_order):
        assert cherry_picks[i] == expected_msg, (
            f"Commit at position {i+1} should be '{expected_msg}', "
            f"got '{cherry_picks[i]}'"
        )


def test_no_pending_cherry_pick():
    """There must be no in-progress cherry-pick (all conflicts resolved)."""
    cherry_pick_head = os.path.join(REPO_DIR, ".git", "CHERRY_PICK_HEAD")
    assert not os.path.exists(cherry_pick_head), \
        "CHERRY_PICK_HEAD exists — there is an unfinished cherry-pick"


def test_clean_working_tree():
    """The working tree must be clean (no uncommitted changes)."""
    stdout, _, rc = run_git(["status", "--porcelain"])
    assert rc == 0, "git status failed"
    # Filter out untracked files that aren't part of the task (like result.json)
    tracked_changes = [
        line for line in stdout.splitlines()
        if not line.strip().startswith("??")
    ]
    assert len(tracked_changes) == 0, \
        f"Working tree has uncommitted tracked changes: {tracked_changes}"


# ──────────────────────────────────────────────────────────────────────
# 5. Tracked files on production
# ──────────────────────────────────────────────────────────────────────

def test_tracked_files_on_production():
    """Production branch must track exactly app.py and config.txt."""
    stdout, _, rc = run_git(["ls-files"])
    assert rc == 0, "git ls-files failed"
    files = sorted([f.strip() for f in stdout.splitlines() if f.strip()])
    assert files == ["app.py", "config.txt"], \
        f"Expected tracked files ['app.py', 'config.txt'], got {files}"


# ──────────────────────────────────────────────────────────────────────
# 6. result.json validation
# ──────────────────────────────────────────────────────────────────────

def test_result_json_exists():
    """result.json must exist at /app/result.json."""
    assert os.path.isfile(RESULT_JSON), f"{RESULT_JSON} does not exist"


def test_result_json_is_valid():
    """result.json must be valid JSON."""
    assert os.path.isfile(RESULT_JSON), f"{RESULT_JSON} does not exist"
    with open(RESULT_JSON) as f:
        content = f.read().strip()
    assert len(content) > 0, "result.json is empty"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"result.json is not valid JSON: {e}"


def _load_result():
    with open(RESULT_JSON) as f:
        return json.load(f)


def test_result_branches():
    """result.json branches must list all 4 branches sorted alphabetically."""
    data = _load_result()
    assert "branches" in data, "result.json missing 'branches' key"
    assert sorted(data["branches"]) == ["feature-x", "feature-y", "main", "production"], \
        f"Expected branches ['feature-x','feature-y','main','production'], got {data['branches']}"


def test_result_production_commit_count():
    """result.json production_commit_count must be 5."""
    data = _load_result()
    assert "production_commit_count" in data, \
        "result.json missing 'production_commit_count' key"
    assert data["production_commit_count"] == 5, \
        f"Expected production_commit_count=5, got {data['production_commit_count']}"


def test_result_cherry_picked_commits():
    """result.json cherry_picked_commits must list the 4 commit messages in order."""
    data = _load_result()
    assert "cherry_picked_commits" in data, \
        "result.json missing 'cherry_picked_commits' key"
    expected = [
        "feature-x: update greet and add multiply",
        "feature-y: update greet and add subtract",
        "feature-x: update config",
        "feature-y: update config",
    ]
    assert data["cherry_picked_commits"] == expected, (
        f"cherry_picked_commits mismatch.\n"
        f"Expected: {expected}\n"
        f"Got: {data['cherry_picked_commits']}"
    )


def test_result_conflicts_resolved():
    """result.json conflicts_resolved must be 2."""
    data = _load_result()
    assert "conflicts_resolved" in data, \
        "result.json missing 'conflicts_resolved' key"
    assert data["conflicts_resolved"] == 2, \
        f"Expected conflicts_resolved=2, got {data['conflicts_resolved']}"


def test_result_final_files():
    """result.json final_files must list app.py and config.txt sorted."""
    data = _load_result()
    assert "final_files" in data, "result.json missing 'final_files' key"
    assert sorted(data["final_files"]) == ["app.py", "config.txt"], \
        f"Expected final_files ['app.py','config.txt'], got {data['final_files']}"


# ──────────────────────────────────────────────────────────────────────
# 7. Cross-validation: result.json vs actual git state
# ──────────────────────────────────────────────────────────────────────

def test_cross_validate_commit_count():
    """result.json commit count must match actual git commit count on production."""
    data = _load_result()
    stdout, _, rc = run_git(["rev-list", "--count", "production"])
    assert rc == 0
    actual_count = int(stdout)
    reported_count = data.get("production_commit_count", -1)
    assert reported_count == actual_count, (
        f"result.json says {reported_count} commits but git shows {actual_count}"
    )


def test_cross_validate_branches():
    """result.json branches must match actual git branches."""
    data = _load_result()
    stdout, _, rc = run_git(["branch", "--list"])
    assert rc == 0
    actual_branches = sorted([b.strip().lstrip("* ") for b in stdout.splitlines()])
    reported_branches = sorted(data.get("branches", []))
    assert reported_branches == actual_branches, (
        f"result.json branches {reported_branches} != actual {actual_branches}"
    )


def test_cross_validate_tracked_files():
    """result.json final_files must match actual tracked files on production."""
    data = _load_result()
    stdout, _, rc = run_git(["ls-files"])
    assert rc == 0
    actual_files = sorted([f.strip() for f in stdout.splitlines() if f.strip()])
    reported_files = sorted(data.get("final_files", []))
    assert reported_files == actual_files, (
        f"result.json final_files {reported_files} != actual {actual_files}"
    )
