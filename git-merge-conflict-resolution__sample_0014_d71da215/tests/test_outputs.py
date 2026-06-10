"""
Test suite for Git merge conflict resolution task.

This test validates that the agent correctly:
1. Created all required branches and files
2. Performed proper Git workflow with commits and merges
3. Resolved merge conflicts correctly
4. Integrated all modules into the final main branch
"""

import os
import subprocess
import re


def run_git_command(cmd, cwd="/app"):
    """Run a git command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_git_repository_exists():
    """Test that /app is a valid git repository."""
    stdout, stderr, code = run_git_command("git rev-parse --git-dir")
    assert code == 0, "Git repository not initialized"
    assert ".git" in stdout, "Invalid git directory"


def test_charlie_git_config():
    """Test that git user is configured as Charlie."""
    name, _, _ = run_git_command("git config user.name")
    email, _, _ = run_git_command("git config user.email")

    assert name == "Charlie", f"Expected user.name 'Charlie', got '{name}'"
    assert email == "charlie@tinygraph.dev", f"Expected email 'charlie@tinygraph.dev', got '{email}'"


def test_all_branches_exist():
    """Test that all required branches were created."""
    stdout, _, code = run_git_command("git branch -a")
    assert code == 0, "Failed to list branches"

    branches = stdout.lower()
    required_branches = ["charlie/optimise", "alice/io", "bob/algos"]

    for branch in required_branches:
        assert branch in branches, f"Branch '{branch}' not found in repository"


def test_main_branch_is_current():
    """Test that the final state is on main branch."""
    stdout, _, code = run_git_command("git branch --show-current")
    assert code == 0, "Failed to get current branch"
    assert stdout == "main", f"Expected to be on 'main' branch, currently on '{stdout}'"


def test_all_module_files_exist():
    """Test that all required Python module files exist in /app/tinygraph/."""
    required_files = [
        "/app/tinygraph/__init__.py",
        "/app/tinygraph/graph.py",
        "/app/tinygraph/optim.py",
        "/app/tinygraph/io.py",
        "/app/tinygraph/algos.py"
    ]

    for filepath in required_files:
        assert os.path.exists(filepath), f"Required file '{filepath}' does not exist"
        assert os.path.isfile(filepath), f"'{filepath}' is not a file"


def test_optim_module_content():
    """Test that optim.py contains at least one function."""
    with open("/app/tinygraph/optim.py", "r") as f:
        content = f.read()

    assert len(content) > 0, "optim.py is empty"
    assert "def " in content, "optim.py does not contain any function definitions"


def test_io_module_functions():
    """Test that io.py contains save_graph and load_graph functions."""
    with open("/app/tinygraph/io.py", "r") as f:
        content = f.read()

    assert "def save_graph" in content, "io.py missing save_graph() function"
    assert "def load_graph" in content, "io.py missing load_graph() function"


def test_algos_module_functions():
    """Test that algos.py contains dijkstra and kruskal functions."""
    with open("/app/tinygraph/algos.py", "r") as f:
        content = f.read()

    assert "def dijkstra" in content, "algos.py missing dijkstra() function"
    assert "def kruskal" in content, "algos.py missing kruskal() function"


def test_init_imports_all_modules():
    """Test that __init__.py imports from all three new modules."""
    with open("/app/tinygraph/__init__.py", "r") as f:
        content = f.read()

    # Check for imports from all modules
    assert "from tinygraph.optim import" in content or "from .optim import" in content, \
        "__init__.py does not import from optim module"
    assert "from tinygraph.io import" in content or "from .io import" in content, \
        "__init__.py does not import from io module"
    assert "from tinygraph.algos import" in content or "from .algos import" in content, \
        "__init__.py does not import from algos module"

    # Verify specific function imports
    assert "save_graph" in content and "load_graph" in content, \
        "__init__.py missing save_graph or load_graph imports"
    assert "dijkstra" in content and "kruskal" in content, \
        "__init__.py missing dijkstra or kruskal imports"


def test_commit_messages_exist():
    """Test that required commit messages are present in git history."""
    stdout, _, code = run_git_command("git log --all --oneline")
    assert code == 0, "Failed to retrieve git log"

    log_lower = stdout.lower()

    required_messages = [
        "add optimization module",
        "add i/o module",
        "add algorithms module",
        "import optimization module",
        "merge main into charlie/optimise"
    ]

    for msg in required_messages:
        assert msg in log_lower, f"Commit message '{msg}' not found in git history"


def test_merge_commits_exist():
    """Test that merge commits were created."""
    stdout, _, code = run_git_command("git log --all --merges --oneline")
    assert code == 0, "Failed to retrieve merge commits"

    # Should have at least 3 merges: alice/io -> main, bob/algos -> main, charlie/optimise -> main
    # Plus the merge of main into charlie/optimise
    merge_count = len(stdout.strip().split("\n")) if stdout.strip() else 0
    assert merge_count >= 3, f"Expected at least 3 merge commits, found {merge_count}"


def test_charlie_branch_has_optim_commit():
    """Test that charlie/optimise branch contains the optim.py commit."""
    stdout, _, code = run_git_command("git log charlie/optimise --oneline")
    assert code == 0, "Failed to get charlie/optimise branch log"

    log_lower = stdout.lower()
    assert "add optimization module" in log_lower, \
        "charlie/optimise branch missing 'Add optimization module' commit"


def test_alice_branch_has_io_commit():
    """Test that alice/io branch contains the io.py commit."""
    stdout, _, code = run_git_command("git log alice/io --oneline")
    assert code == 0, "Failed to get alice/io branch log"

    log_lower = stdout.lower()
    assert "add i/o module" in log_lower, \
        "alice/io branch missing 'Add I/O module' commit"


def test_bob_branch_has_algos_commit():
    """Test that bob/algos branch contains the algos.py commit."""
    stdout, _, code = run_git_command("git log bob/algos --oneline")
    assert code == 0, "Failed to get bob/algos branch log"

    log_lower = stdout.lower()
    assert "add algorithms module" in log_lower, \
        "bob/algos branch missing 'Add algorithms module' commit"


def test_main_branch_has_all_modules():
    """Test that main branch contains all integrated modules."""
    # Switch to main and verify files exist
    run_git_command("git checkout main")

    required_files = [
        "/app/tinygraph/optim.py",
        "/app/tinygraph/io.py",
        "/app/tinygraph/algos.py"
    ]

    for filepath in required_files:
        assert os.path.exists(filepath), \
            f"Main branch missing required file '{filepath}'"


def test_conflict_was_resolved():
    """Test that merge conflict in __init__.py was properly resolved."""
    # Check that the final __init__.py has all imports integrated
    with open("/app/tinygraph/__init__.py", "r") as f:
        content = f.read()

    # All three module imports should coexist
    has_optim = "optim" in content
    has_io = "io" in content or "save_graph" in content
    has_algos = "algos" in content or "dijkstra" in content

    assert has_optim and has_io and has_algos, \
        "Merge conflict not properly resolved: __init__.py missing imports from all modules"

    # Should not contain conflict markers
    conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]
    for marker in conflict_markers:
        assert marker not in content, \
            f"Conflict marker '{marker}' still present in __init__.py"


def test_git_history_shows_proper_workflow():
    """Test that git history reflects proper branching and merging workflow."""
    # Get full git log with graph
    stdout, _, code = run_git_command("git log --all --graph --oneline")
    assert code == 0, "Failed to retrieve git graph"

    # Should show branching structure (contains asterisks and branch indicators)
    assert "*" in stdout, "Git history does not show proper branching structure"

    # Verify that commits exist from different branches
    log_output, _, _ = run_git_command("git log --all --pretty=format:'%s'")
    assert len(log_output.split("\n")) >= 8, \
        "Expected at least 8 commits in total history (initial + 3 feature branches + merges)"


def test_no_uncommitted_changes():
    """Test that there are no uncommitted changes in the working directory."""
    stdout, _, code = run_git_command("git status --porcelain")
    assert code == 0, "Failed to check git status"
    assert stdout == "", f"Uncommitted changes detected: {stdout}"


def test_modules_are_importable():
    """Test that all modules can be imported without errors."""
    import sys
    sys.path.insert(0, "/app")

    try:
        from tinygraph import graph
        from tinygraph import optim
        from tinygraph import io
        from tinygraph import algos
    except ImportError as e:
        assert False, f"Failed to import modules: {e}"

    # Verify that the imported modules have expected attributes
    assert hasattr(graph, "Graph"), "graph module missing Graph class"
    assert hasattr(io, "save_graph"), "io module missing save_graph function"
    assert hasattr(io, "load_graph"), "io module missing load_graph function"
    assert hasattr(algos, "dijkstra"), "algos module missing dijkstra function"
    assert hasattr(algos, "kruskal"), "algos module missing kruskal function"
