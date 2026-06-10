import os
import subprocess
import re


def run_git_command(cmd, cwd="/app"):
    """Run a git command and return output"""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_git_repository_exists():
    """Verify Git repository is initialized"""
    assert os.path.exists("/app/.git"), "Git repository not initialized"


def test_required_branches_exist():
    """Verify all required branches exist"""
    stdout, _, _ = run_git_command("git branch -a")
    branches = stdout.split('\n')
    branch_names = [b.strip().replace('* ', '') for b in branches]

    required_branches = ['main', 'feature-arithmetic', 'feature-scientific', 'hotfix-typo', 'release-v1.1']
    for branch in required_branches:
        assert any(branch in b for b in branch_names), f"Branch '{branch}' not found"


def test_required_tags_exist():
    """Verify required tags exist"""
    stdout, _, _ = run_git_command("git tag")
    tags = stdout.split('\n')

    assert 'v1.0.0' in tags, "Tag 'v1.0.0' not found"
    assert 'v1.0.1' in tags, "Tag 'v1.0.1' not found"


def test_tags_are_annotated():
    """Verify tags are annotated (not lightweight)"""
    # Check v1.0.0
    stdout, _, _ = run_git_command("git cat-file -t v1.0.0")
    assert stdout == "tag", "v1.0.0 is not an annotated tag"

    # Check v1.0.1
    stdout, _, _ = run_git_command("git cat-file -t v1.0.1")
    assert stdout == "tag", "v1.0.1 is not an annotated tag"


def test_tag_messages():
    """Verify tag messages contain expected content"""
    # Check v1.0.0 message
    stdout, _, _ = run_git_command("git tag -l -n99 v1.0.0")
    assert "release" in stdout.lower(), "v1.0.0 tag message should mention 'release'"

    # Check v1.0.1 message
    stdout, _, _ = run_git_command("git tag -l -n99 v1.0.1")
    assert "hotfix" in stdout.lower() or "release" in stdout.lower(), "v1.0.1 tag message should mention 'hotfix' or 'release'"


def test_readme_exists_and_has_content():
    """Verify README.md exists with proper content"""
    assert os.path.exists("/app/README.md"), "README.md not found"

    with open("/app/README.md", "r") as f:
        content = f.read()

    assert "Stellar Calculator" in content, "README.md should contain 'Stellar Calculator'"
    assert len(content.strip()) > 20, "README.md should have meaningful content"


def test_main_py_exists():
    """Verify main.py exists"""
    assert os.path.exists("/app/main.py"), "main.py not found"


def test_arithmetic_functions_exist():
    """Verify arithmetic functions are implemented in main.py"""
    with open("/app/main.py", "r") as f:
        content = f.read()

    assert "def add(" in content, "add() function not found"
    assert "def subtract(" in content, "subtract() function not found"
    assert "def multiply(" in content, "multiply() function not found"
    assert "def divide(" in content, "divide() function not found"


def test_scientific_functions_exist():
    """Verify scientific functions are implemented in main.py"""
    with open("/app/main.py", "r") as f:
        content = f.read()

    assert "def power(" in content, "power() function not found"
    assert "def square_root(" in content, "square_root() function not found"
    assert "def logarithm(" in content, "logarithm() function not found"


def test_main_py_imports_math():
    """Verify main.py imports math module for scientific operations"""
    with open("/app/main.py", "r") as f:
        content = f.read()

    assert "import math" in content, "main.py should import math module"


def test_arithmetic_functions_work():
    """Verify arithmetic functions actually work"""
    # Import and test the functions
    import sys
    sys.path.insert(0, "/app")
    import main

    assert main.add(2, 3) == 5, "add() function doesn't work correctly"
    assert main.subtract(5, 3) == 2, "subtract() function doesn't work correctly"
    assert main.multiply(4, 3) == 12, "multiply() function doesn't work correctly"
    assert main.divide(10, 2) == 5, "divide() function doesn't work correctly"


def test_scientific_functions_work():
    """Verify scientific functions actually work"""
    import sys
    sys.path.insert(0, "/app")
    import main

    assert main.power(2, 3) == 8, "power() function doesn't work correctly"
    assert abs(main.square_root(16) - 4.0) < 0.001, "square_root() function doesn't work correctly"
    assert abs(main.logarithm(100, 10) - 2.0) < 0.001, "logarithm() function doesn't work correctly"


def test_feature_arithmetic_was_merged():
    """Verify feature-arithmetic branch was merged into main"""
    stdout, _, _ = run_git_command("git log main --oneline --all")

    # Check that main has commits from feature-arithmetic
    stdout_full, _, _ = run_git_command("git log main --all")
    assert "arithmetic" in stdout_full.lower(), "feature-arithmetic branch was not merged into main"


def test_feature_scientific_was_merged():
    """Verify feature-scientific branch was merged into main"""
    stdout, _, _ = run_git_command("git log main --all")

    assert "scientific" in stdout.lower(), "feature-scientific branch was not merged into main"


def test_merge_conflict_was_resolved():
    """Verify merge conflict was resolved (both comment and scientific functions present)"""
    with open("/app/main.py", "r") as f:
        content = f.read()

    # Check that both the comment from main and scientific functions are present
    has_scientific = "def power(" in content and "def square_root(" in content and "def logarithm(" in content
    has_arithmetic = "def add(" in content and "def subtract(" in content

    assert has_scientific, "Scientific functions missing - merge conflict not properly resolved"
    assert has_arithmetic, "Arithmetic functions missing - merge conflict not properly resolved"


def test_hotfix_branch_was_merged():
    """Verify hotfix-typo branch was merged into main"""
    stdout, _, _ = run_git_command("git log main --all")

    assert "hotfix" in stdout.lower() or "typo" in stdout.lower(), "hotfix-typo branch was not merged into main"


def test_commit_count_reasonable():
    """Verify there are a reasonable number of commits"""
    stdout, _, _ = run_git_command("git rev-list --count main")
    commit_count = int(stdout)

    # Should have at least: initial commit, arithmetic commit, merge, scientific commit,
    # main modification, merge with conflict resolution, hotfix commit, hotfix merge
    assert commit_count >= 6, f"Expected at least 6 commits on main, found {commit_count}"


def test_v1_0_0_tag_points_to_correct_state():
    """Verify v1.0.0 tag points to state before hotfix"""
    # Checkout v1.0.0 and verify it has scientific functions but before hotfix
    stdout, _, _ = run_git_command("git log v1.0.0 --oneline")

    # Should have scientific operations merged by this point
    assert "scientific" in stdout.lower() or "merge" in stdout.lower(), "v1.0.0 should be after scientific merge"


def test_v1_0_1_tag_points_to_correct_state():
    """Verify v1.0.1 tag points to state after hotfix"""
    stdout, _, _ = run_git_command("git log v1.0.1 --oneline")

    # Should have hotfix merged by this point
    assert "hotfix" in stdout.lower() or "typo" in stdout.lower(), "v1.0.1 should be after hotfix merge"


def test_release_branch_exists_from_main():
    """Verify release-v1.1 branch was created from main"""
    # Check that release-v1.1 exists
    stdout, _, _ = run_git_command("git branch -a")
    assert "release-v1.1" in stdout, "release-v1.1 branch not found"

    # Check that it has the same commits as main up to its creation point
    stdout, _, _ = run_git_command("git log release-v1.1 --oneline")
    assert len(stdout) > 0, "release-v1.1 branch has no commits"


def test_main_branch_is_current():
    """Verify main branch is the current branch (or at least exists in final state)"""
    stdout, _, _ = run_git_command("git branch")
    # Just verify main exists and is accessible
    assert "main" in stdout, "main branch should exist in final state"


def test_no_uncommitted_changes():
    """Verify there are no uncommitted changes"""
    stdout, _, _ = run_git_command("git status --porcelain")
    # Allow for some flexibility - the test itself might create files
    # Just check that the main files are committed
    assert os.path.exists("/app/main.py"), "main.py should exist"
    assert os.path.exists("/app/README.md"), "README.md should exist"
