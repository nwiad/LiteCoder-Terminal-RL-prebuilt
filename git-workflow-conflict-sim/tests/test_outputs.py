"""
Tests for Git Workflow Simulator with Conflict Resolution.

Validates:
- /app/output.json existence, structure, and content
- /app/repo/ is a valid git repository with correct state
- Branch existence and naming
- File contents on main after all merges
- Commit history (count and key messages)
- Merge operations were actually performed
"""

import os
import json
import subprocess

REPO_DIR = "/app/repo"
OUTPUT_FILE = "/app/output.json"


def run_git(args, cwd=REPO_DIR):
    """Helper to run git commands in the repo directory."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


# ==============================================================
# output.json — existence and structure
# ==============================================================

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"


def test_output_json_is_valid_json():
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "output.json is empty or trivially small"
    data = json.loads(content)  # will raise on invalid JSON
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_json_has_required_keys():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    required_keys = {"branches", "total_commits_on_main", "conflict_files", "final_files", "merge_count"}
    missing = required_keys - set(data.keys())
    assert not missing, f"output.json missing keys: {missing}"


# ==============================================================
# output.json — content validation
# ==============================================================

def test_output_branches():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    branches = data["branches"]
    assert isinstance(branches, list), "branches must be a list"
    # Normalize to sorted list of stripped strings
    branches_clean = sorted([b.strip() for b in branches])
    expected = ["feature/login", "feature/math", "main"]
    assert branches_clean == expected, f"Expected branches {expected}, got {branches_clean}"


def test_output_total_commits_on_main():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    count = data["total_commits_on_main"]
    assert isinstance(count, int), "total_commits_on_main must be an integer"
    # 5 commits if feature/math is fast-forwarded, 6 if a merge commit is created
    assert count in (5, 6), f"Expected 5 or 6 commits on main, got {count}"


def test_output_conflict_files():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    conflict_files = data["conflict_files"]
    assert isinstance(conflict_files, list), "conflict_files must be a list"
    cleaned = [f.strip() for f in conflict_files]
    assert "src/app.py" in cleaned, "src/app.py must be listed as a conflict file"


def test_output_final_files():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    final_files = data["final_files"]
    assert isinstance(final_files, list), "final_files must be a list"
    cleaned = sorted([f.strip() for f in final_files])
    expected = ["README.md", "src/app.py", "src/utils.py"]
    assert cleaned == expected, f"Expected final_files {expected}, got {cleaned}"


def test_output_merge_count():
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    mc = data["merge_count"]
    assert isinstance(mc, int), "merge_count must be an integer"
    assert mc == 2, f"Expected merge_count 2, got {mc}"


# ==============================================================
# Git repository — existence and validity
# ==============================================================

def test_repo_exists():
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} directory does not exist"


def test_repo_is_git_repo():
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a git repository (no .git)"


def test_repo_has_main_branch():
    result = run_git(["branch", "--list", "main"])
    assert result.returncode == 0, "git branch command failed"
    branches = result.stdout.strip()
    assert "main" in branches, "main branch does not exist"


# ==============================================================
# Branch verification
# ==============================================================

def test_all_three_branches_exist():
    result = run_git(["branch", "--format=%(refname:short)"])
    assert result.returncode == 0, "git branch command failed"
    branches = sorted([b.strip() for b in result.stdout.strip().splitlines()])
    assert "main" in branches, "main branch missing"
    assert "feature/login" in branches, "feature/login branch missing"
    assert "feature/math" in branches, "feature/math branch missing"


def test_current_branch_is_main():
    """After all operations, HEAD should be on main."""
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    assert result.returncode == 0, "git rev-parse failed"
    assert result.stdout.strip() == "main", f"Expected HEAD on main, got {result.stdout.strip()}"


# ==============================================================
# File content verification on main
# ==============================================================

def test_readme_content():
    readme_path = os.path.join(REPO_DIR, "README.md")
    assert os.path.isfile(readme_path), "README.md not found in repo"
    with open(readme_path, "r") as f:
        content = f.read().strip()
    assert content == "# Project Alpha", f"README.md content mismatch: {content!r}"


def test_app_py_greet_function():
    """Verify the resolved greet function in src/app.py."""
    app_path = os.path.join(REPO_DIR, "src", "app.py")
    assert os.path.isfile(app_path), "src/app.py not found"
    with open(app_path, "r") as f:
        content = f.read()
    # Must contain the resolved greeting
    assert 'Welcome, {name}! Welcome to Project Alpha.' in content, \
        "src/app.py missing resolved greet: 'Welcome, {name}! Welcome to Project Alpha.'"


def test_app_py_login_function():
    """Verify the login function exists in src/app.py after merge."""
    app_path = os.path.join(REPO_DIR, "src", "app.py")
    assert os.path.isfile(app_path), "src/app.py not found"
    with open(app_path, "r") as f:
        content = f.read()
    assert "def login(user):" in content, "src/app.py missing login function"
    assert "logged in" in content, "src/app.py login function missing 'logged in' text"


def test_app_py_no_conflict_markers():
    """Ensure no leftover conflict markers in src/app.py."""
    app_path = os.path.join(REPO_DIR, "src", "app.py")
    assert os.path.isfile(app_path), "src/app.py not found"
    with open(app_path, "r") as f:
        content = f.read()
    for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
        assert marker not in content, f"Conflict marker {marker!r} found in src/app.py"


def test_utils_py_add_function():
    utils_path = os.path.join(REPO_DIR, "src", "utils.py")
    assert os.path.isfile(utils_path), "src/utils.py not found"
    with open(utils_path, "r") as f:
        content = f.read()
    assert "def add(a, b):" in content, "src/utils.py missing add function"


def test_utils_py_multiply_function():
    """Verify multiply was added from feature/math."""
    utils_path = os.path.join(REPO_DIR, "src", "utils.py")
    assert os.path.isfile(utils_path), "src/utils.py not found"
    with open(utils_path, "r") as f:
        content = f.read()
    assert "def multiply(a, b):" in content, "src/utils.py missing multiply function"
    assert "a * b" in content, "src/utils.py multiply function missing 'a * b'"


# ==============================================================
# Commit history verification
# ==============================================================

def test_commit_count_on_main():
    """Verify total commits reachable from main (5 if ff, 6 if merge commit for feature/math)."""
    result = run_git(["rev-list", "--count", "main"])
    assert result.returncode == 0, "git rev-list --count main failed"
    count = int(result.stdout.strip())
    assert count in (5, 6), f"Expected 5 or 6 commits on main, got {count}"


def test_initial_commit_message_exists():
    result = run_git(["log", "--oneline", "--all"])
    assert result.returncode == 0, "git log failed"
    log = result.stdout.lower()
    assert "initial commit" in log, "Missing 'Initial commit' in git history"


def test_login_feature_commit_exists():
    result = run_git(["log", "--oneline", "--all"])
    assert result.returncode == 0, "git log failed"
    log = result.stdout.lower()
    assert "login" in log, "Missing login-related commit in git history"


def test_update_greeting_commit_exists():
    result = run_git(["log", "--oneline", "--all"])
    assert result.returncode == 0, "git log failed"
    log = result.stdout.lower()
    assert "greeting" in log or "greet" in log or "update" in log, \
        "Missing greeting update commit in git history"


def test_merge_commit_for_login_exists():
    """Verify a merge commit for feature/login exists on main."""
    result = run_git(["log", "--oneline", "--merges", "main"])
    assert result.returncode == 0, "git log --merges failed"
    log = result.stdout.lower()
    # The merge for feature/login should produce a merge commit (it was conflicting)
    assert "merge" in log or "login" in log, \
        "No merge commit found for feature/login on main"


def test_multiply_commit_exists():
    result = run_git(["log", "--oneline", "--all"])
    assert result.returncode == 0, "git log failed"
    log = result.stdout.lower()
    assert "multiply" in log, "Missing 'multiply' commit in git history"


# ==============================================================
# Git config verification
# ==============================================================

def test_git_user_config():
    """Verify git user was configured (any commits should have an author)."""
    result = run_git(["log", "-1", "--format=%an <%ae>", "main"])
    assert result.returncode == 0, "git log for author failed"
    author = result.stdout.strip()
    # Just verify it's not empty — the task specifies Dev Team / dev@example.com
    assert len(author) > 0, "No author configured for commits"


# ==============================================================
# Tracked files on main
# ==============================================================

def test_tracked_files_on_main():
    """Verify the exact set of tracked files on main."""
    result = run_git(["ls-tree", "-r", "--name-only", "main"])
    assert result.returncode == 0, "git ls-tree failed"
    files = sorted([f.strip() for f in result.stdout.strip().splitlines()])
    expected = ["README.md", "src/app.py", "src/utils.py"]
    assert files == expected, f"Expected tracked files {expected}, got {files}"


# ==============================================================
# Cross-validation: output.json vs actual git state
# ==============================================================

def test_output_branches_match_actual():
    """Verify output.json branches match actual git branches."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    reported = sorted([b.strip() for b in data["branches"]])

    result = run_git(["branch", "--format=%(refname:short)"])
    assert result.returncode == 0
    actual = sorted([b.strip() for b in result.stdout.strip().splitlines()])

    assert reported == actual, f"output.json branches {reported} != actual {actual}"


def test_output_commit_count_matches_actual():
    """Verify output.json commit count matches actual git state."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    reported = data["total_commits_on_main"]

    result = run_git(["rev-list", "--count", "main"])
    assert result.returncode == 0
    actual = int(result.stdout.strip())

    assert reported == actual, \
        f"output.json total_commits_on_main={reported} != actual={actual}"


def test_output_final_files_match_actual():
    """Verify output.json final_files match actual tracked files."""
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    reported = sorted([f.strip() for f in data["final_files"]])

    result = run_git(["ls-tree", "-r", "--name-only", "main"])
    assert result.returncode == 0
    actual = sorted([f.strip() for f in result.stdout.strip().splitlines()])

    assert reported == actual, \
        f"output.json final_files {reported} != actual {actual}"
