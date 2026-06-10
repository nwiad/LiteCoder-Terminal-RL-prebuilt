"""
Tests for the git-restore-deleted-file benchmark task.

Validates:
- Git repository structure and commit history
- analysis.txt correctness (cross-referenced with git log)
- restoration_summary.txt correctness
- utils/data_cleaner.py: 4 functions with docstrings, type hints, raise statements
- Functional correctness of the restored functions
- Commit message conventions (refactor, restore)
- Clean working tree
"""

import os
import re
import ast
import subprocess

APP_DIR = "/app"


def run_git(args, cwd=APP_DIR):
    """Helper to run git commands and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ============================================================
# 1. Git repository validity
# ============================================================

def test_app_is_git_repo():
    """The /app directory must be a valid git repository."""
    assert os.path.isdir(os.path.join(APP_DIR, ".git")), \
        "/app is not a git repository (no .git directory)"


def test_minimum_commit_count():
    """Repository must have at least 8 commits."""
    stdout, _, rc = run_git(["rev-list", "--count", "HEAD"])
    assert rc == 0, "Failed to count commits"
    count = int(stdout)
    assert count >= 8, f"Expected at least 8 commits, got {count}"


def test_clean_working_tree():
    """Working tree must be clean (no uncommitted changes)."""
    stdout, _, rc = run_git(["status", "--porcelain"])
    assert rc == 0, "git status failed"
    assert stdout == "", f"Working tree is not clean:\n{stdout}"


# ============================================================
# 2. Project structure
# ============================================================

REQUIRED_FILES = [
    "README.md",
    "setup.py",
    "dataforge/__init__.py",
    "dataforge/core.py",
    "utils/__init__.py",
    "utils/data_cleaner.py",
    "tests/__init__.py",
]


def test_required_files_exist():
    """All required project files must exist."""
    for rel_path in REQUIRED_FILES:
        full = os.path.join(APP_DIR, rel_path)
        assert os.path.isfile(full), f"Missing required file: {rel_path}"


def test_readme_contains_dataforge():
    """README.md must contain the text 'DataForge'."""
    readme = os.path.join(APP_DIR, "README.md")
    assert os.path.isfile(readme), "README.md missing"
    content = open(readme).read()
    assert "DataForge" in content, "README.md does not contain 'DataForge'"


# ============================================================
# 3. analysis.txt validation
# ============================================================

def _parse_analysis():
    """Parse analysis.txt and return (deletion_hash, addition_hash)."""
    path = os.path.join(APP_DIR, "analysis.txt")
    assert os.path.isfile(path), "analysis.txt missing"
    content = open(path).read().strip()
    lines = content.splitlines()
    assert len(lines) >= 2, f"analysis.txt must have at least 2 lines, got {len(lines)}"

    deletion_line = lines[0].strip()
    addition_line = lines[1].strip()

    # Parse "deletion_commit: <hash>"
    m_del = re.match(r"deletion_commit:\s*([0-9a-f]{40})", deletion_line)
    assert m_del, f"Line 1 of analysis.txt doesn't match expected format: {deletion_line}"

    m_add = re.match(r"addition_commit:\s*([0-9a-f]{40})", addition_line)
    assert m_add, f"Line 2 of analysis.txt doesn't match expected format: {addition_line}"

    return m_del.group(1), m_add.group(1)


def test_analysis_txt_exists_and_format():
    """analysis.txt must exist with correct format."""
    _parse_analysis()


def test_analysis_deletion_commit_is_valid():
    """The deletion commit hash in analysis.txt must be a real commit."""
    del_hash, _ = _parse_analysis()
    stdout, _, rc = run_git(["cat-file", "-t", del_hash])
    assert rc == 0 and stdout == "commit", \
        f"Deletion hash {del_hash} is not a valid commit"


def test_analysis_addition_commit_is_valid():
    """The addition commit hash in analysis.txt must be a real commit."""
    _, add_hash = _parse_analysis()
    stdout, _, rc = run_git(["cat-file", "-t", add_hash])
    assert rc == 0 and stdout == "commit", \
        f"Addition hash {add_hash} is not a valid commit"


def test_analysis_deletion_commit_actually_deleted_file():
    """The deletion commit must actually delete utils/data_cleaner.py."""
    del_hash, _ = _parse_analysis()
    # Check that data_cleaner.py appears as deleted (D) in this commit
    stdout, _, rc = run_git(["diff-tree", "--no-commit-id", "-r", "--diff-filter=D",
                             "--name-only", del_hash])
    assert rc == 0, "git diff-tree failed"
    deleted_files = stdout.splitlines()
    assert any("data_cleaner.py" in f for f in deleted_files), \
        f"Commit {del_hash} did not delete data_cleaner.py. Deleted files: {deleted_files}"


def test_analysis_addition_commit_actually_added_file():
    """The addition commit must actually add utils/data_cleaner.py."""
    _, add_hash = _parse_analysis()
    # Check that data_cleaner.py appears as added (A) in this commit
    stdout, _, rc = run_git(["diff-tree", "--no-commit-id", "-r", "--diff-filter=A",
                             "--name-only", add_hash])
    assert rc == 0, "git diff-tree failed"
    added_files = stdout.splitlines()
    assert any("data_cleaner.py" in f for f in added_files), \
        f"Commit {add_hash} did not add data_cleaner.py. Added files: {added_files}"


# ============================================================
# 4. restoration_summary.txt validation
# ============================================================

def _parse_restoration_summary():
    """Parse restoration_summary.txt and return (del_hash, add_hash, total_count)."""
    path = os.path.join(APP_DIR, "restoration_summary.txt")
    assert os.path.isfile(path), "restoration_summary.txt missing"
    content = open(path).read().strip()
    lines = content.splitlines()
    assert len(lines) >= 3, \
        f"restoration_summary.txt must have at least 3 lines, got {len(lines)}"

    del_hash = lines[0].strip()
    add_hash = lines[1].strip()
    count_str = lines[2].strip()

    assert re.fullmatch(r"[0-9a-f]{40}", del_hash), \
        f"Line 1 is not a valid 40-char hex hash: {del_hash}"
    assert re.fullmatch(r"[0-9a-f]{40}", add_hash), \
        f"Line 2 is not a valid 40-char hex hash: {add_hash}"
    assert count_str.isdigit(), \
        f"Line 3 is not an integer: {count_str}"

    return del_hash, add_hash, int(count_str)


def test_restoration_summary_exists_and_format():
    """restoration_summary.txt must exist with correct 3-line format."""
    _parse_restoration_summary()


def test_restoration_summary_hashes_match_analysis():
    """Hashes in restoration_summary.txt must match analysis.txt."""
    analysis_del, analysis_add = _parse_analysis()
    summary_del, summary_add, _ = _parse_restoration_summary()
    assert summary_del == analysis_del, \
        f"Deletion hash mismatch: analysis={analysis_del}, summary={summary_del}"
    assert summary_add == analysis_add, \
        f"Addition hash mismatch: analysis={analysis_add}, summary={summary_add}"


def test_restoration_summary_commit_count():
    """Total commit count in restoration_summary.txt must match git rev-list --count HEAD."""
    _, _, reported_count = _parse_restoration_summary()
    stdout, _, rc = run_git(["rev-list", "--count", "HEAD"])
    assert rc == 0, "git rev-list --count HEAD failed"
    actual_count = int(stdout)
    assert reported_count == actual_count, \
        f"Commit count mismatch: summary says {reported_count}, actual is {actual_count}"


# ============================================================
# 5. Commit message conventions
# ============================================================

def test_refactor_commit_exists():
    """There must be a commit whose message contains 'refactor' (case-insensitive)."""
    stdout, _, rc = run_git(["log", "--all", "--format=%s"])
    assert rc == 0, "git log failed"
    messages = stdout.splitlines()
    assert any("refactor" in m.lower() for m in messages), \
        "No commit message contains the word 'refactor'"


def test_restore_commit_exists():
    """There must be a commit whose message contains 'restore' (case-insensitive)."""
    stdout, _, rc = run_git(["log", "--all", "--format=%s"])
    assert rc == 0, "git log failed"
    messages = stdout.splitlines()
    assert any("restore" in m.lower() for m in messages), \
        "No commit message contains the word 'restore'"


def test_initial_commit_message():
    """The first commit message must contain 'Initial commit'."""
    # Get the root commit
    stdout, _, rc = run_git(["rev-list", "--max-parents=0", "HEAD"])
    assert rc == 0, "Failed to find root commit"
    root_hash = stdout.splitlines()[0].strip()
    msg_out, _, rc2 = run_git(["log", "--format=%s", "-1", root_hash])
    assert rc2 == 0, "Failed to get root commit message"
    assert "initial commit" in msg_out.lower(), \
        f"First commit message does not contain 'Initial commit': {msg_out}"


# ============================================================
# 6. utils/data_cleaner.py — AST-based code quality checks
# ============================================================

REQUIRED_FUNCTIONS = [
    "remove_duplicates",
    "normalize_whitespace",
    "convert_dates",
    "fill_missing_values",
]


def _load_data_cleaner_ast():
    """Parse utils/data_cleaner.py and return the AST module."""
    path = os.path.join(APP_DIR, "utils", "data_cleaner.py")
    assert os.path.isfile(path), "utils/data_cleaner.py missing"
    source = open(path).read()
    assert len(source.strip()) > 0, "utils/data_cleaner.py is empty"
    tree = ast.parse(source, filename=path)
    return tree


def _get_function_nodes(tree):
    """Return a dict of {function_name: FunctionDef node} for top-level functions."""
    funcs = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs[node.name] = node
    return funcs


def test_data_cleaner_has_all_four_functions():
    """utils/data_cleaner.py must contain all 4 required functions."""
    tree = _load_data_cleaner_ast()
    funcs = _get_function_nodes(tree)
    for fname in REQUIRED_FUNCTIONS:
        assert fname in funcs, f"Function '{fname}' not found in data_cleaner.py"


def test_all_functions_have_docstrings():
    """Every required function must have a docstring."""
    tree = _load_data_cleaner_ast()
    funcs = _get_function_nodes(tree)
    for fname in REQUIRED_FUNCTIONS:
        assert fname in funcs, f"Function '{fname}' not found"
        node = funcs[fname]
        docstring = ast.get_docstring(node)
        assert docstring is not None and len(docstring.strip()) > 0, \
            f"Function '{fname}' is missing a docstring"


def test_all_functions_have_return_type_hint():
    """Every required function must have a return type annotation."""
    tree = _load_data_cleaner_ast()
    funcs = _get_function_nodes(tree)
    for fname in REQUIRED_FUNCTIONS:
        assert fname in funcs, f"Function '{fname}' not found"
        node = funcs[fname]
        assert node.returns is not None, \
            f"Function '{fname}' is missing a return type hint"


def test_all_functions_have_parameter_type_hints():
    """Every parameter of every required function must have a type annotation."""
    tree = _load_data_cleaner_ast()
    funcs = _get_function_nodes(tree)
    for fname in REQUIRED_FUNCTIONS:
        assert fname in funcs, f"Function '{fname}' not found"
        node = funcs[fname]
        for arg in node.args.args:
            if arg.arg == "self":
                continue
            assert arg.annotation is not None, \
                f"Function '{fname}' parameter '{arg.arg}' is missing a type hint"


def test_all_functions_have_raise_statement():
    """Every required function must contain at least one raise statement."""
    tree = _load_data_cleaner_ast()
    funcs = _get_function_nodes(tree)
    for fname in REQUIRED_FUNCTIONS:
        assert fname in funcs, f"Function '{fname}' not found"
        node = funcs[fname]
        has_raise = False
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                has_raise = True
                break
        assert has_raise, \
            f"Function '{fname}' does not contain a raise statement for input validation"


# ============================================================
# 7. Functional correctness of restored functions
# ============================================================

def _import_data_cleaner():
    """Import data_cleaner module dynamically."""
    import importlib.util
    path = os.path.join(APP_DIR, "utils", "data_cleaner.py")
    spec = importlib.util.spec_from_file_location("data_cleaner", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_remove_duplicates_basic():
    """remove_duplicates should remove duplicates preserving order."""
    mod = _import_data_cleaner()
    result = mod.remove_duplicates([1, 2, 3, 2, 1, 4])
    assert result == [1, 2, 3, 4], f"Expected [1, 2, 3, 4], got {result}"


def test_remove_duplicates_empty():
    """remove_duplicates on empty list returns empty list."""
    mod = _import_data_cleaner()
    result = mod.remove_duplicates([])
    assert result == [], f"Expected [], got {result}"


def test_remove_duplicates_raises_on_invalid_input():
    """remove_duplicates should raise on non-list input."""
    mod = _import_data_cleaner()
    raised = False
    try:
        mod.remove_duplicates("not a list")
    except (TypeError, ValueError):
        raised = True
    assert raised, "remove_duplicates did not raise on invalid input"


def test_normalize_whitespace_basic():
    """normalize_whitespace should collapse whitespace and strip."""
    mod = _import_data_cleaner()
    result = mod.normalize_whitespace("  hello   world  ")
    assert result == "hello world", f"Expected 'hello world', got '{result}'"


def test_normalize_whitespace_tabs_and_newlines():
    """normalize_whitespace should handle tabs and newlines."""
    mod = _import_data_cleaner()
    result = mod.normalize_whitespace("hello\t\n  world")
    assert result == "hello world", f"Expected 'hello world', got '{result}'"


def test_normalize_whitespace_raises_on_invalid_input():
    """normalize_whitespace should raise on non-string input."""
    mod = _import_data_cleaner()
    raised = False
    try:
        mod.normalize_whitespace(12345)
    except (TypeError, ValueError):
        raised = True
    assert raised, "normalize_whitespace did not raise on invalid input"


def test_convert_dates_basic():
    """convert_dates should convert between date formats."""
    mod = _import_data_cleaner()
    result = mod.convert_dates("2023-01-15", "%Y-%m-%d", "%d/%m/%Y")
    assert result == "15/01/2023", f"Expected '15/01/2023', got '{result}'"


def test_convert_dates_different_format():
    """convert_dates should handle another format pair."""
    mod = _import_data_cleaner()
    result = mod.convert_dates("12/25/2020", "%m/%d/%Y", "%Y-%m-%d")
    assert result == "2020-12-25", f"Expected '2020-12-25', got '{result}'"


def test_convert_dates_raises_on_invalid_input():
    """convert_dates should raise on invalid input."""
    mod = _import_data_cleaner()
    raised = False
    try:
        mod.convert_dates(12345, "%Y-%m-%d", "%d/%m/%Y")
    except (TypeError, ValueError):
        raised = True
    assert raised, "convert_dates did not raise on non-string input"


def test_fill_missing_values_basic():
    """fill_missing_values should fill missing keys from defaults."""
    mod = _import_data_cleaner()
    data = {"a": 1, "b": 2}
    defaults = {"b": 99, "c": 3}
    result = mod.fill_missing_values(data, defaults)
    assert result == {"a": 1, "b": 2, "c": 3}, f"Unexpected result: {result}"


def test_fill_missing_values_no_overlap():
    """fill_missing_values with no overlap adds all defaults."""
    mod = _import_data_cleaner()
    result = mod.fill_missing_values({"x": 1}, {"y": 2, "z": 3})
    assert result == {"x": 1, "y": 2, "z": 3}, f"Unexpected result: {result}"


def test_fill_missing_values_does_not_mutate_original():
    """fill_missing_values should return a new dict, not mutate the original."""
    mod = _import_data_cleaner()
    data = {"a": 1}
    defaults = {"b": 2}
    result = mod.fill_missing_values(data, defaults)
    assert "b" not in data, "Original data dict was mutated"
    assert result == {"a": 1, "b": 2}


def test_fill_missing_values_raises_on_invalid_input():
    """fill_missing_values should raise on non-dict input."""
    mod = _import_data_cleaner()
    raised = False
    try:
        mod.fill_missing_values("not a dict", {})
    except (TypeError, ValueError):
        raised = True
    assert raised, "fill_missing_values did not raise on invalid input"


# ============================================================
# 8. Git history integrity — deletion happened before restore
# ============================================================

def test_deletion_commit_is_ancestor_of_restore():
    """The refactor (deletion) commit must come before the restore commit in history."""
    del_hash, _ = _parse_analysis()
    # Find the restore commit
    stdout, _, rc = run_git(["log", "--all", "--format=%H %s"])
    assert rc == 0
    restore_hash = None
    for line in stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and "restore" in parts[1].lower():
            restore_hash = parts[0]
            break
    assert restore_hash is not None, "No restore commit found"
    # Check that deletion is an ancestor of restore
    _, _, rc = run_git(["merge-base", "--is-ancestor", del_hash, restore_hash])
    assert rc == 0, \
        "Deletion commit is not an ancestor of the restore commit"


def test_at_least_one_commit_after_deletion_before_analysis():
    """There must be at least 1 commit between the deletion and the analysis/restore."""
    del_hash, _ = _parse_analysis()
    # Count commits after deletion up to HEAD
    stdout, _, rc = run_git(["rev-list", "--count", f"{del_hash}..HEAD"])
    assert rc == 0
    commits_after = int(stdout)
    # At least 1 post-deletion commit + analysis + restore + summary = at least 4
    # But instruction only requires at least 1 more commit after deletion
    assert commits_after >= 1, \
        f"Expected at least 1 commit after deletion, got {commits_after}"
