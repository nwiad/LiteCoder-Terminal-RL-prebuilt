"""
Tests for Git Stash and Merge Conflict Resolution task.
Validates the final state of /app/repo after all git operations.
"""

import os
import subprocess

REPO_DIR = "/app/repo"


def run_git(*args):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ── Test 1: Repository exists and is valid ──────────────────────────────────

def test_repo_exists():
    """The repository directory must exist."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"


def test_repo_is_git_repo():
    """The directory must be a valid git repository."""
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a git repository"


# ── Test 2: Current branch is 'feature' ─────────────────────────────────────

def test_current_branch_is_feature():
    """HEAD must point to the 'feature' branch."""
    stdout, _, rc = run_git("branch", "--show-current")
    assert rc == 0, "git branch --show-current failed"
    assert stdout == "feature", f"Expected branch 'feature', got '{stdout}'"


# ── Test 3: app.py content (conflict resolution) ────────────────────────────

def test_app_py_exists():
    """app.py must exist in the working tree."""
    path = os.path.join(REPO_DIR, "app.py")
    assert os.path.isfile(path), "app.py does not exist"


def test_app_py_greet_returns_hi_there():
    """greet() must return 'hi there' (main's version kept during conflict resolution)."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    assert '"hi there"' in content or "'hi there'" in content, (
        f"app.py greet() should return 'hi there', got:\n{content}"
    )


def test_app_py_farewell_returns_see_you_later():
    """farewell() must return 'see you later' (stash's version kept during conflict resolution)."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    assert '"see you later"' in content or "'see you later'" in content, (
        f"app.py farewell() should return 'see you later', got:\n{content}"
    )


def test_app_py_no_conflict_markers():
    """app.py must not contain unresolved conflict markers."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
        assert marker not in content, (
            f"app.py contains unresolved conflict marker: {marker}"
        )


def test_app_py_has_greet_function():
    """app.py must define a greet() function."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    assert "def greet()" in content, "app.py missing greet() function definition"


def test_app_py_has_farewell_function():
    """app.py must define a farewell() function."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    assert "def farewell()" in content, "app.py missing farewell() function definition"


# Verify greet does NOT return old values
def test_app_py_greet_not_hello():
    """greet() must NOT return the original 'hello' — it was changed on main."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    # Extract what greet returns by looking at lines near def greet
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "def greet" in line:
            # Check the next few lines for the return value
            for j in range(i + 1, min(i + 4, len(lines))):
                if "return" in lines[j]:
                    return_line = lines[j].strip()
                    # Must not be the original "hello" (without "world")
                    assert "hello" not in return_line.lower(), (
                        f"greet() still returns original value: {return_line}"
                    )
                    break
            break


def test_app_py_farewell_not_goodbye():
    """farewell() must NOT return 'goodbye' — stash version was kept."""
    path = os.path.join(REPO_DIR, "app.py")
    content = open(path).read()
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "def farewell" in line:
            for j in range(i + 1, min(i + 4, len(lines))):
                if "return" in lines[j]:
                    return_line = lines[j].strip()
                    assert "goodbye" not in return_line.lower(), (
                        f"farewell() still returns original value: {return_line}"
                    )
                    break
            break


# ── Test 4: utils.py exists and is committed ────────────────────────────────

def test_utils_py_exists():
    """utils.py must exist in the working tree."""
    path = os.path.join(REPO_DIR, "utils.py")
    assert os.path.isfile(path), "utils.py does not exist"


def test_utils_py_content():
    """utils.py must contain the add function."""
    path = os.path.join(REPO_DIR, "utils.py")
    content = open(path).read()
    assert "def add" in content, "utils.py missing add() function"
    assert "return a + b" in content or "return a+b" in content, (
        "utils.py add() should return a + b"
    )


def test_utils_py_is_tracked():
    """utils.py must be tracked (committed) in git."""
    stdout, _, rc = run_git("ls-files", "utils.py")
    assert rc == 0
    assert "utils.py" in stdout, "utils.py is not tracked by git"


# ── Test 5: config.py must NOT exist in working tree ────────────────────────

def test_config_py_not_in_working_tree():
    """config.py must NOT exist in the working tree (only in stash)."""
    path = os.path.join(REPO_DIR, "config.py")
    assert not os.path.exists(path), (
        "config.py should NOT exist in the working tree"
    )


def test_config_py_not_tracked():
    """config.py must not be a tracked file."""
    stdout, _, rc = run_git("ls-files", "config.py")
    assert "config.py" not in stdout, "config.py should not be tracked by git"


# ── Test 6: Stash list validation ───────────────────────────────────────────

def test_stash_list_contains_config_wip():
    """The stash list must contain the 'config-wip' entry."""
    stdout, _, rc = run_git("stash", "list")
    assert rc == 0, "git stash list failed"
    assert "config-wip" in stdout, (
        f"Stash list missing 'config-wip'. Stash list:\n{stdout}"
    )


def test_stash_list_does_not_contain_utils_wip():
    """The 'utils-wip' stash must have been dropped after committing utils.py."""
    stdout, _, rc = run_git("stash", "list")
    assert rc == 0, "git stash list failed"
    assert "utils-wip" not in stdout, (
        f"Stash list still contains 'utils-wip' (should have been dropped). "
        f"Stash list:\n{stdout}"
    )


def test_stash_list_not_empty():
    """Stash list must not be empty — at least config-wip should remain."""
    stdout, _, rc = run_git("stash", "list")
    assert rc == 0
    assert len(stdout.strip()) > 0, "Stash list is empty"


# ── Test 7: Clean working tree ──────────────────────────────────────────────

def test_clean_working_tree():
    """git status must show a clean working tree (nothing to commit)."""
    stdout, _, rc = run_git("status", "--porcelain")
    assert rc == 0, "git status failed"
    assert stdout == "", (
        f"Working tree is not clean. git status --porcelain output:\n{stdout}"
    )


# ── Test 8: Commit history validation ───────────────────────────────────────

def test_commit_initial_commit_exists():
    """The 'Initial commit' must exist in the log."""
    stdout, _, rc = run_git("log", "--all", "--oneline", "--format=%s")
    assert rc == 0
    messages = stdout.splitlines()
    assert any("Initial commit" in m for m in messages), (
        f"'Initial commit' not found in git log. Messages:\n{stdout}"
    )


def test_commit_update_greet_on_main_exists():
    """The 'Update greet on main' commit must exist."""
    stdout, _, rc = run_git("log", "--all", "--oneline", "--format=%s")
    assert rc == 0
    messages = stdout.splitlines()
    assert any("Update greet on main" in m for m in messages), (
        f"'Update greet on main' not found in git log. Messages:\n{stdout}"
    )


def test_commit_resolve_stash_conflict_exists():
    """The 'Resolve stash conflict' commit must exist on feature branch."""
    stdout, _, rc = run_git("log", "--oneline", "--format=%s")
    assert rc == 0
    messages = stdout.splitlines()
    assert any("Resolve stash conflict" in m for m in messages), (
        f"'Resolve stash conflict' not found in feature branch log. Messages:\n{stdout}"
    )


def test_commit_add_utils_exists():
    """The 'Add utils' commit must exist on feature branch."""
    stdout, _, rc = run_git("log", "--oneline", "--format=%s")
    assert rc == 0
    messages = stdout.splitlines()
    assert any("Add utils" in m for m in messages), (
        f"'Add utils' not found in feature branch log. Messages:\n{stdout}"
    )


# ── Test 9: Branch 'main' exists ────────────────────────────────────────────

def test_main_branch_exists():
    """The 'main' branch must exist."""
    stdout, _, rc = run_git("branch", "--list", "main")
    assert rc == 0
    assert "main" in stdout, "Branch 'main' does not exist"


def test_feature_branch_exists():
    """The 'feature' branch must exist."""
    stdout, _, rc = run_git("branch", "--list", "feature")
    assert rc == 0
    assert "feature" in stdout, "Branch 'feature' does not exist"


# ── Test 10: Commit count sanity check ──────────────────────────────────────

def test_minimum_commit_count():
    """Feature branch should have at least 4 commits."""
    stdout, _, rc = run_git("rev-list", "--count", "HEAD")
    assert rc == 0
    count = int(stdout.strip())
    assert count >= 4, (
        f"Expected at least 4 commits on feature, got {count}"
    )


# ── Test 11: Verify merge happened ─────────────────────────────────────────

def test_main_is_ancestor_of_feature():
    """main must be an ancestor of feature (merge happened)."""
    _, _, rc = run_git("merge-base", "--is-ancestor", "main", "feature")
    assert rc == 0, "main is not an ancestor of feature — merge did not happen"
