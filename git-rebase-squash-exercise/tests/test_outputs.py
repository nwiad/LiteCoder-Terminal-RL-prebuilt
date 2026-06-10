"""
Tests for git-rebase-squash-exercise.

Verifies that 8 commits on feature-branch were squashed into a single commit
with the correct message, correct file contents, and main branch untouched.
"""

import os
import subprocess

REPO_PATH = "/app/repo"


def run_git(*args, cwd=REPO_PATH):
    """Run a git command in the repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ── Test 1: Repository exists and is a valid git repo ──

def test_repo_exists():
    """The repository directory must exist at /app/repo."""
    assert os.path.isdir(REPO_PATH), f"Repository directory {REPO_PATH} does not exist"


def test_repo_is_git():
    """The directory must be a valid git repository."""
    git_dir = os.path.join(REPO_PATH, ".git")
    assert os.path.isdir(git_dir), f"{REPO_PATH} is not a git repository (no .git directory)"


# ── Test 2: Branch structure ──

def test_feature_branch_exists():
    """feature-branch must exist in the repository."""
    stdout, _, rc = run_git("branch", "--list", "feature-branch")
    assert rc == 0, "git branch command failed"
    assert "feature-branch" in stdout, "feature-branch does not exist"


def test_main_branch_exists():
    """main branch must exist in the repository."""
    stdout, _, rc = run_git("branch", "--list", "main")
    assert rc == 0, "git branch command failed"
    assert "main" in stdout, "main branch does not exist"


# ── Test 3: Exactly 1 commit ahead of main ──

def test_commit_count_ahead_of_main():
    """feature-branch must have exactly 1 commit ahead of main."""
    stdout, stderr, rc = run_git("rev-list", "main..feature-branch", "--count")
    assert rc == 0, f"git rev-list failed: {stderr}"
    count = int(stdout)
    assert count == 1, (
        f"feature-branch should have exactly 1 commit ahead of main, "
        f"but has {count}"
    )


# ── Test 4: Squashed commit message ──

def test_squashed_commit_message():
    """The single squashed commit message must be exactly correct."""
    # First checkout feature-branch to ensure HEAD is there
    run_git("checkout", "feature-branch")
    stdout, stderr, rc = run_git("log", "-1", "--format=%s", "feature-branch")
    assert rc == 0, f"git log failed: {stderr}"
    expected = "Add complete feature with tests and config"
    assert stdout == expected, (
        f"Commit message mismatch.\n"
        f"Expected: '{expected}'\n"
        f"Got:      '{stdout}'"
    )


def test_commit_message_is_single_line_subject():
    """The commit subject line must match exactly (no extra lines in subject)."""
    stdout, _, rc = run_git("log", "-1", "--format=%s", "feature-branch")
    assert rc == 0
    # Subject should not contain newlines
    assert "\n" not in stdout, "Commit subject should be a single line"


# ── Test 5: All required files exist on feature-branch ──

def test_feature_py_exists():
    """feature.py must exist on feature-branch."""
    run_git("checkout", "feature-branch")
    filepath = os.path.join(REPO_PATH, "feature.py")
    assert os.path.isfile(filepath), "feature.py does not exist on feature-branch"


def test_tests_py_exists():
    """tests.py must exist on feature-branch."""
    run_git("checkout", "feature-branch")
    filepath = os.path.join(REPO_PATH, "tests.py")
    assert os.path.isfile(filepath), "tests.py does not exist on feature-branch"


def test_config_txt_exists():
    """config.txt must exist on feature-branch."""
    run_git("checkout", "feature-branch")
    filepath = os.path.join(REPO_PATH, "config.txt")
    assert os.path.isfile(filepath), "config.txt does not exist on feature-branch"


def test_readme_exists():
    """README.md must still exist on feature-branch (inherited from main)."""
    run_git("checkout", "feature-branch")
    filepath = os.path.join(REPO_PATH, "README.md")
    assert os.path.isfile(filepath), "README.md does not exist on feature-branch"


# ── Test 6: File contents on feature-branch ──

def _read_file(filename):
    """Read a file from the repo after checking out feature-branch."""
    run_git("checkout", "feature-branch")
    filepath = os.path.join(REPO_PATH, filename)
    with open(filepath, "r") as f:
        return f.read()


def test_feature_py_contains_hello():
    """feature.py must contain the hello() function."""
    content = _read_file("feature.py")
    assert "def hello():" in content, "feature.py missing def hello()"
    assert 'return "hello"' in content, 'feature.py missing return "hello"'


def test_feature_py_contains_world():
    """feature.py must contain the world() function."""
    content = _read_file("feature.py")
    assert "def world():" in content, "feature.py missing def world()"
    assert 'return "world"' in content, 'feature.py missing return "world"'


def test_feature_py_contains_greet():
    """feature.py must contain the greet() function."""
    content = _read_file("feature.py")
    assert "def greet(name):" in content, "feature.py missing def greet(name)"
    assert 'return f"hello {name}"' in content, 'feature.py missing return f"hello {name}"'


def test_feature_py_contains_farewell():
    """feature.py must contain the farewell() function."""
    content = _read_file("feature.py")
    assert "def farewell():" in content, "feature.py missing def farewell()"
    assert 'return "goodbye"' in content, 'feature.py missing return "goodbye"'


def test_feature_py_has_all_four_functions():
    """feature.py must contain exactly the 4 expected function definitions."""
    content = _read_file("feature.py")
    expected_funcs = ["def hello():", "def world():", "def greet(name):", "def farewell():"]
    for func in expected_funcs:
        assert func in content, f"feature.py missing {func}"


def test_tests_py_contains_test_hello():
    """tests.py must contain test_hello."""
    content = _read_file("tests.py")
    assert "def test_hello():" in content, "tests.py missing def test_hello()"
    assert 'assert hello() == "hello"' in content, 'tests.py missing hello assertion'


def test_tests_py_contains_test_greet():
    """tests.py must contain test_greet."""
    content = _read_file("tests.py")
    assert "def test_greet():" in content, "tests.py missing def test_greet()"
    assert 'assert greet("alice") == "hello alice"' in content, (
        "tests.py missing greet assertion"
    )


def test_tests_py_contains_test_farewell():
    """tests.py must contain test_farewell."""
    content = _read_file("tests.py")
    assert "def test_farewell():" in content, "tests.py missing def test_farewell()"
    assert 'assert farewell() == "goodbye"' in content, (
        "tests.py missing farewell assertion"
    )


def test_config_txt_content():
    """config.txt must contain version=1.0."""
    content = _read_file("config.txt")
    assert "version=1.0" in content, "config.txt missing 'version=1.0'"


# ── Test 7: Main branch integrity ──

def test_main_branch_commit_count():
    """main branch must have exactly 1 commit (the initial commit)."""
    stdout, stderr, rc = run_git("rev-list", "--count", "main")
    assert rc == 0, f"git rev-list failed: {stderr}"
    count = int(stdout)
    assert count == 1, (
        f"main branch should have exactly 1 commit, but has {count}"
    )


def test_main_branch_only_has_readme():
    """main branch should only contain README.md."""
    stdout, stderr, rc = run_git("ls-tree", "--name-only", "main")
    assert rc == 0, f"git ls-tree failed: {stderr}"
    files = [f.strip() for f in stdout.split("\n") if f.strip()]
    assert files == ["README.md"], (
        f"main branch should only contain README.md, but contains: {files}"
    )


def test_main_branch_readme_content():
    """README.md on main must contain '# My Project'."""
    stdout, stderr, rc = run_git("show", "main:README.md")
    assert rc == 0, f"git show failed: {stderr}"
    assert "# My Project" in stdout, (
        f"README.md on main should contain '# My Project', got: '{stdout}'"
    )


# ── Test 8: The squashed commit contains all file changes ──

def test_squashed_commit_diff_has_all_files():
    """The single squashed commit must touch feature.py, tests.py, and config.txt."""
    stdout, stderr, rc = run_git(
        "diff", "--name-only", "main..feature-branch"
    )
    assert rc == 0, f"git diff failed: {stderr}"
    changed_files = set(f.strip() for f in stdout.split("\n") if f.strip())
    expected_files = {"feature.py", "tests.py", "config.txt"}
    assert expected_files.issubset(changed_files), (
        f"Squashed commit should include changes to {expected_files}, "
        f"but only found: {changed_files}"
    )


# ── Test 9: HEAD of feature-branch points to the squashed commit ──

def test_head_points_to_squashed_commit():
    """HEAD of feature-branch must point to the single squashed commit."""
    # Get the commit that feature-branch points to
    head_stdout, _, rc1 = run_git("rev-parse", "feature-branch")
    assert rc1 == 0

    # Get the single commit ahead of main
    commits_stdout, _, rc2 = run_git("rev-list", "main..feature-branch")
    assert rc2 == 0

    commits = [c.strip() for c in commits_stdout.split("\n") if c.strip()]
    assert len(commits) == 1, f"Expected 1 commit ahead of main, got {len(commits)}"
    assert head_stdout == commits[0], (
        "feature-branch HEAD does not point to the squashed commit"
    )


# ── Test 10: No merge commits ──

def test_no_merge_commits_on_feature_branch():
    """The squashed commit should not be a merge commit."""
    stdout, stderr, rc = run_git(
        "log", "--merges", "--oneline", "main..feature-branch"
    )
    assert rc == 0, f"git log failed: {stderr}"
    assert stdout == "", (
        f"feature-branch should have no merge commits, but found: {stdout}"
    )
