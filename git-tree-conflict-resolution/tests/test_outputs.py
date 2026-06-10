"""
Tests for Git Tree Manipulation & Conflict Resolution task.

Validates the final state of /app/repo and /app/graph.txt
after the agent has completed all steps.
"""

import os
import subprocess

REPO_DIR = "/app/repo"
GRAPH_FILE = "/app/graph.txt"


def run_git(args, cwd=REPO_DIR):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ─── Repository existence ───────────────────────────────────────────────

def test_repo_exists():
    """The repository directory must exist."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"


def test_repo_is_git():
    """The repository must be a valid git repo."""
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), \
        f"{REPO_DIR} is not a git repository"


# ─── Current branch ─────────────────────────────────────────────────────

def test_current_branch_is_main():
    """After all operations the active branch must be main."""
    stdout, _, rc = run_git(["branch", "--show-current"])
    assert rc == 0, "git branch --show-current failed"
    assert stdout == "main", f"Expected current branch 'main', got '{stdout}'"


# ─── Branch existence ───────────────────────────────────────────────────

def _get_branches():
    stdout, _, _ = run_git(["branch", "--list"])
    # git branch output prefixes current branch with "* "
    branches = []
    for b in stdout.splitlines():
        name = b.strip()
        if name.startswith("* "):
            name = name[2:]
        branches.append(name)
    return branches


def test_branch_main_exists():
    assert "main" in _get_branches()


def test_branch_feature_a_exists():
    assert "feature-a" in _get_branches()


def test_branch_feature_b_exists():
    assert "feature-b" in _get_branches()


def test_branch_hotfix_exists():
    assert "hotfix" in _get_branches()


def test_branch_cleanup_exists():
    assert "cleanup" in _get_branches()


# ─── File content on main ────────────────────────────────────────────────

def _read_file_on_branch(branch, filepath):
    """Read a file's content from a specific branch using git show."""
    stdout, stderr, rc = run_git(["show", f"{branch}:{filepath}"])
    return stdout, rc


def test_readme_content():
    """README.md on main must have the exact final content."""
    expected = (
        "# Project Alpha\n"
        "## Version 1.0\n"
        "Stable release.\n"
        "Contributors: dev"
    )
    content, rc = _read_file_on_branch("main", "README.md")
    assert rc == 0, "Could not read README.md from main"
    assert content.strip() == expected.strip(), \
        f"README.md content mismatch.\nExpected:\n{expected}\nGot:\n{content}"


def test_app_py_content():
    """app.py on main must contain the merged conflict resolution."""
    expected = (
        'def greet():\n'
        '    return "hello from both features"'
    )
    content, rc = _read_file_on_branch("main", "app.py")
    assert rc == 0, "Could not read app.py from main"
    assert content.strip() == expected.strip(), \
        f"app.py content mismatch.\nExpected:\n{expected}\nGot:\n{content}"


def test_utils_py_content():
    """utils.py on main must have feature-a additions."""
    expected = (
        'def helper():\n'
        '    return 2\n'
        '\n'
        'def feature_a_util():\n'
        '    return "a"'
    )
    content, rc = _read_file_on_branch("main", "utils.py")
    assert rc == 0, "Could not read utils.py from main"
    assert content.strip() == expected.strip(), \
        f"utils.py content mismatch.\nExpected:\n{expected}\nGot:\n{content}"


def test_config_py_content():
    """config.py on main must have the hotfix values."""
    expected = (
        'SETTING = "off"\n'
        'DEBUG = True'
    )
    content, rc = _read_file_on_branch("main", "config.py")
    assert rc == 0, "Could not read config.py from main"
    assert content.strip() == expected.strip(), \
        f"config.py content mismatch.\nExpected:\n{expected}\nGot:\n{content}"


def test_fix_py_not_on_main():
    """fix.py must NOT exist on main (cherry-pick was selective)."""
    _, rc = _read_file_on_branch("main", "fix.py")
    assert rc != 0, "fix.py should NOT exist on main branch"


# ─── Hotfix branch state ────────────────────────────────────────────────

def test_fix_py_exists_on_hotfix():
    """fix.py must exist on the hotfix branch (was not cherry-picked)."""
    content, rc = _read_file_on_branch("hotfix", "fix.py")
    assert rc == 0, "fix.py should exist on hotfix branch"
    assert "patched" in content, \
        "fix.py on hotfix should contain 'patched'"


# ─── Commit message verification on main ────────────────────────────────

def _get_log_messages(branch="main"):
    """Return list of commit messages on a branch."""
    stdout, _, rc = run_git(["log", branch, "--format=%s"])
    assert rc == 0, f"git log on {branch} failed"
    return stdout.splitlines()


def test_initial_commit_exists():
    msgs = _get_log_messages()
    assert any("Initial commit" in m for m in msgs), \
        "'Initial commit' not found in main history"


def test_add_app_module_commit():
    msgs = _get_log_messages()
    assert any("Add app module" in m for m in msgs), \
        "'Add app module' not found in main history"


def test_add_utils_module_commit():
    msgs = _get_log_messages()
    assert any("Add utils module" in m for m in msgs), \
        "'Add utils module' not found in main history"


def test_merge_feature_b_commit():
    """The merge commit for feature-b with conflict resolution must exist."""
    msgs = _get_log_messages()
    assert any("Merge feature-b" in m and "conflict resolution" in m.lower()
               for m in msgs), \
        "Merge commit for feature-b with conflict resolution not found"


def test_hotfix_config_cherry_picked():
    """'Hotfix config' must appear in main's history (cherry-picked)."""
    msgs = _get_log_messages()
    assert any("Hotfix config" in m for m in msgs), \
        "'Hotfix config' not found in main history (cherry-pick missing)"


def test_add_patch_fix_not_on_main():
    """'Add patch fix' must NOT appear in main's first-parent history."""
    # Use first-parent to avoid seeing it through merge paths
    stdout, _, rc = run_git(["log", "main", "--first-parent", "--format=%s"])
    assert rc == 0
    msgs = stdout.splitlines()
    assert not any("Add patch fix" in m for m in msgs), \
        "'Add patch fix' should not be in main's first-parent history"


def test_squashed_commit_on_main():
    """The squashed commit 'Update readme to v1.0' must be in main history."""
    msgs = _get_log_messages()
    assert any("Update readme to v1.0" in m for m in msgs), \
        "'Update readme to v1.0' not found in main history"


# ─── Squash verification ────────────────────────────────────────────────

def test_individual_cleanup_commits_not_on_cleanup():
    """The 3 individual cleanup commits should have been squashed.
    'Update readme v1' (without the '.0') should not appear as a
    standalone commit on the cleanup branch."""
    stdout, _, rc = run_git(["log", "cleanup", "--format=%s"])
    assert rc == 0
    msgs = stdout.splitlines()
    # The squashed commit should exist
    assert any("Update readme to v1.0" in m for m in msgs), \
        "Squashed commit 'Update readme to v1.0' not on cleanup"
    # The individual pre-squash commits should NOT exist
    individual = [
        "Update readme v1 - add note",
        "Update readme v1 - add contributors",
    ]
    for ind_msg in individual:
        assert not any(ind_msg == m for m in msgs), \
            f"Individual commit '{ind_msg}' still exists on cleanup (not squashed)"


# ─── Merge structure verification ───────────────────────────────────────

def test_feature_b_merge_is_merge_commit():
    """The feature-b merge should be a merge commit (2 parents)."""
    # Find the merge commit
    stdout, _, rc = run_git([
        "log", "main", "--format=%H %P %s"
    ])
    assert rc == 0
    for line in stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) >= 3 and "Merge feature-b" in parts[2]:
            # parts[1] contains parent hashes separated by space
            # A merge commit has at least 2 parents
            commit_hash = parts[0]
            parent_stdout, _, _ = run_git(["cat-file", "-p", commit_hash])
            parent_count = parent_stdout.count("parent ")
            assert parent_count >= 2, \
                "feature-b merge should be a merge commit with 2+ parents"
            return
    # If we get here, we didn't find the merge commit at all
    # (already tested elsewhere, so just pass)


# ─── Graph output file ──────────────────────────────────────────────────

def test_graph_file_exists():
    """/app/graph.txt must exist."""
    assert os.path.isfile(GRAPH_FILE), f"{GRAPH_FILE} does not exist"


def test_graph_file_not_empty():
    """/app/graph.txt must not be empty."""
    assert os.path.isfile(GRAPH_FILE), f"{GRAPH_FILE} does not exist"
    size = os.path.getsize(GRAPH_FILE)
    assert size > 0, f"{GRAPH_FILE} is empty"


def test_graph_file_has_branch_refs():
    """The graph should reference branch names."""
    assert os.path.isfile(GRAPH_FILE)
    with open(GRAPH_FILE, "r") as f:
        content = f.read()
    # At minimum, main and hotfix should appear in the decorated graph
    assert "main" in content, "'main' not found in graph.txt"
    assert "hotfix" in content, "'hotfix' not found in graph.txt"


def test_graph_file_has_graph_characters():
    """The graph output should contain graph drawing characters."""
    assert os.path.isfile(GRAPH_FILE)
    with open(GRAPH_FILE, "r") as f:
        content = f.read()
    # git log --graph uses *, |, /, \ characters
    assert "*" in content, "No '*' found in graph — not a graph output"


# ─── Git config ──────────────────────────────────────────────────────────

def test_git_user_name():
    """Git user.name should be 'dev'."""
    stdout, _, rc = run_git(["config", "user.name"])
    assert rc == 0, "git config user.name not set"
    assert stdout.strip() == "dev", \
        f"Expected user.name 'dev', got '{stdout.strip()}'"


def test_git_user_email():
    """Git user.email should be 'dev@example.com'."""
    stdout, _, rc = run_git(["config", "user.email"])
    assert rc == 0, "git config user.email not set"
    assert stdout.strip() == "dev@example.com", \
        f"Expected user.email 'dev@example.com', got '{stdout.strip()}'"


# ─── Feature branch content verification ────────────────────────────────

def test_feature_a_app_py():
    """app.py on feature-a should have feature-a's version."""
    content, rc = _read_file_on_branch("feature-a", "app.py")
    assert rc == 0
    assert "hello from feature-a" in content


def test_feature_b_config_py():
    """config.py on feature-b should have the original config."""
    content, rc = _read_file_on_branch("feature-b", "config.py")
    assert rc == 0
    assert 'SETTING = "on"' in content

