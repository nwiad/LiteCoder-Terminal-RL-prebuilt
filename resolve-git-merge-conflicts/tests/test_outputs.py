"""
Tests for the multi-branch Git repository management with merge conflicts task.

Validates:
- Git repository structure at /app/repo/
- Branch existence and current branch state
- Commit history on main
- main.py validity (syntax, no conflict markers)
- Feature presence (authentication + logging)
- Runtime execution correctness
"""

import os
import subprocess
import ast
import re

REPO_DIR = "/app/repo"
MAIN_PY = os.path.join(REPO_DIR, "main.py")


def run_git(*args, cwd=REPO_DIR):
    """Helper to run git commands in the repo directory."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


# ── Repository structure ──────────────────────────────────────


def test_repo_directory_exists():
    """The repo directory must exist."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"


def test_repo_is_git_repository():
    """The repo must be a valid git repository."""
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a git repository (no .git)"
    result = run_git("rev-parse", "--is-inside-work-tree")
    assert result.returncode == 0
    assert result.stdout.strip() == "true"


# ── Branch checks ────────────────────────────────────────────


def test_current_branch_is_main():
    """After all merges, the current branch must be main."""
    result = run_git("branch", "--show-current")
    assert result.returncode == 0
    branch = result.stdout.strip()
    assert branch == "main", f"Expected current branch 'main', got '{branch}'"


def test_feature_user_auth_branch_exists():
    """Branch feature-user-auth must exist."""
    result = run_git("branch", "--list", "feature-user-auth")
    assert result.returncode == 0
    branches = result.stdout.strip()
    assert "feature-user-auth" in branches, "Branch 'feature-user-auth' not found"


def test_feature_logging_branch_exists():
    """Branch feature-logging must exist."""
    result = run_git("branch", "--list", "feature-logging")
    assert result.returncode == 0
    branches = result.stdout.strip()
    assert "feature-logging" in branches, "Branch 'feature-logging' not found"


# ── Commit history ───────────────────────────────────────────


def test_minimum_commit_count():
    """main branch must have at least 4 commits."""
    result = run_git("rev-list", "--count", "main")
    assert result.returncode == 0
    count = int(result.stdout.strip())
    assert count >= 4, f"Expected at least 4 commits on main, got {count}"


def test_commit_messages_present():
    """Key commit messages must appear in the log."""
    result = run_git("log", "--oneline", "--all")
    assert result.returncode == 0
    log_output = result.stdout.lower()

    # Check for the initial commit
    assert "initial commit" in log_output, "Missing 'Initial commit' in git log"

    # Check for authentication commit
    assert "user auth" in log_output or "authentication" in log_output, (
        "Missing authentication-related commit message in git log"
    )

    # Check for logging commit
    assert "logging" in log_output, (
        "Missing logging-related commit message in git log"
    )

def test_merge_commit_exists():
    """There must be at least one merge commit on main."""
    # Merge commits have more than one parent
    result = run_git("log", "--merges", "--oneline", "main")
    assert result.returncode == 0
    merge_lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(merge_lines) >= 1, "No merge commits found on main branch"


# ── main.py file checks ─────────────────────────────────────


def test_main_py_exists():
    """main.py must exist in the repo."""
    assert os.path.isfile(MAIN_PY), f"{MAIN_PY} does not exist"


def test_main_py_not_empty():
    """main.py must not be empty."""
    assert os.path.getsize(MAIN_PY) > 0, "main.py is empty"


def test_main_py_valid_python_syntax():
    """main.py must be valid Python (parseable by ast)."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"main.py has a syntax error: {e}")


def test_no_conflict_markers():
    """main.py must not contain any git conflict markers."""
    with open(MAIN_PY, "r") as f:
        content = f.read()
    conflict_patterns = [
        r"^<{7}",
        r"^={7}",
        r"^>{7}",
    ]
    for pattern in conflict_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        assert len(matches) == 0, (
            f"Conflict marker found in main.py: {pattern}"
        )


# ── Feature: logging ────────────────────────────────────────


def test_import_logging():
    """main.py must import the logging module."""
    with open(MAIN_PY, "r") as f:
        content = f.read()
    assert "import logging" in content, "Missing 'import logging' in main.py"


def test_logging_basic_config():
    """main.py must call logging.basicConfig."""
    with open(MAIN_PY, "r") as f:
        content = f.read()
    assert "basicConfig" in content, "Missing 'logging.basicConfig' in main.py"


def test_logging_get_logger():
    """main.py must call logging.getLogger."""
    with open(MAIN_PY, "r") as f:
        content = f.read()
    assert "getLogger" in content, "Missing 'logging.getLogger' in main.py"


def test_logger_info_usage():
    """main.py must use logger.info at least once."""
    with open(MAIN_PY, "r") as f:
        content = f.read()
    assert "logger.info" in content, "Missing 'logger.info' call in main.py"


# ── Feature: authentication ──────────────────────────────────


def test_authenticate_function_defined():
    """main.py must define an 'authenticate' function."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    func_names = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]
    assert "authenticate" in func_names, (
        f"Function 'authenticate' not found. Found: {func_names}"
    )


def test_greet_function_defined():
    """main.py must define a 'greet' function."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    func_names = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]
    assert "greet" in func_names, (
        f"Function 'greet' not found. Found: {func_names}"
    )


def test_main_function_defined():
    """main.py must define a 'main' function."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    func_names = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]
    assert "main" in func_names, (
        f"Function 'main' not found. Found: {func_names}"
    )


def test_authenticate_function_has_two_params():
    """authenticate must accept (user, password) parameters."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "authenticate":
            arg_names = [a.arg for a in node.args.args]
            assert len(arg_names) == 2, (
                f"authenticate should have 2 params, got {len(arg_names)}: {arg_names}"
            )
            return
    raise AssertionError("authenticate function not found")


def test_greet_function_has_name_param():
    """greet must accept a 'name' parameter."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "greet":
            arg_names = [a.arg for a in node.args.args]
            assert "name" in arg_names, (
                f"greet should have a 'name' param, got: {arg_names}"
            )
            return
    raise AssertionError("greet function not found")


# ── Runtime execution ────────────────────────────────────────


def test_main_py_executes_without_error():
    """Running main.py must not raise any exceptions."""
    result = subprocess.run(
        ["python3", MAIN_PY],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"main.py exited with code {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )


def test_main_py_output_contains_greeting():
    """Running main.py should print the greeting."""
    result = subprocess.run(
        ["python3", MAIN_PY],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert "Hello" in result.stdout, (
        f"Expected 'Hello' in output, got: {result.stdout}"
    )


def test_main_py_output_contains_auth_result():
    """Running main.py should print authentication result."""
    result = subprocess.run(
        ["python3", MAIN_PY],
        capture_output=True,
        text=True,
        timeout=10,
    )
    stdout_lower = result.stdout.lower()
    assert "authentication" in stdout_lower or "auth" in stdout_lower, (
        f"Expected authentication output, got: {result.stdout}"
    )


# ── Functional correctness via import ────────────────────────


def test_authenticate_returns_true_for_valid_creds():
    """authenticate('admin', 'secret') should return True."""
    result = subprocess.run(
        [
            "python3", "-c",
            "import sys; sys.path.insert(0, '/app/repo'); "
            "from main import authenticate; "
            "assert authenticate('admin', 'secret') == True, "
            "'authenticate(admin, secret) should be True'"
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"authenticate('admin','secret') did not return True.\n"
        f"stderr: {result.stderr}"
    )


def test_authenticate_returns_false_for_invalid_creds():
    """authenticate('admin', 'wrong') should return False."""
    result = subprocess.run(
        [
            "python3", "-c",
            "import sys; sys.path.insert(0, '/app/repo'); "
            "from main import authenticate; "
            "assert authenticate('admin', 'wrong') == False, "
            "'authenticate(admin, wrong) should be False'"
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"authenticate('admin','wrong') did not return False.\n"
        f"stderr: {result.stderr}"
    )


def test_greet_returns_hello_string():
    """greet('World') should return 'Hello, World!'."""
    result = subprocess.run(
        [
            "python3", "-c",
            "import sys; sys.path.insert(0, '/app/repo'); "
            "from main import greet; "
            "r = greet('World'); "
            "assert r == 'Hello, World!', f'Expected Hello, World! got {r}'"
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"greet('World') did not return 'Hello, World!'.\n"
        f"stderr: {result.stderr}"
    )


# ── main() calls both features ──────────────────────────────


def test_main_function_calls_authenticate():
    """The main() function body must reference authenticate."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            # Get the source segment for main()
            main_src = ast.get_source_segment(source, node)
            if main_src is None:
                # Fallback: check raw text between function boundaries
                lines = source.splitlines()
                main_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            assert "authenticate" in main_src, (
                "main() does not call authenticate()"
            )
            return
    raise AssertionError("main function not found")


def test_main_function_calls_greet():
    """The main() function body must reference greet."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_src = ast.get_source_segment(source, node)
            if main_src is None:
                lines = source.splitlines()
                main_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            assert "greet" in main_src, "main() does not call greet()"
            return
    raise AssertionError("main function not found")


def test_main_function_uses_logger():
    """The main() function body must use logger.info."""
    with open(MAIN_PY, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_src = ast.get_source_segment(source, node)
            if main_src is None:
                lines = source.splitlines()
                main_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            assert "logger" in main_src, "main() does not use logger"
            return
    raise AssertionError("main function not found")
