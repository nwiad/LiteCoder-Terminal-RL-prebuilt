import os
import subprocess
import re

def test_verification_file_exists():
    """Test that verification.txt exists at the expected location."""
    assert os.path.exists("/app/verification.txt"), "verification.txt not found at /app/verification.txt"

def test_verification_file_not_empty():
    """Test that verification.txt is not empty."""
    with open("/app/verification.txt", "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "verification.txt is empty"

def test_monorepo_exists():
    """Test that the monorepo directory exists."""
    assert os.path.exists("/app/monorepo"), "Monorepo directory not found at /app/monorepo"
    assert os.path.isdir("/app/monorepo/.git"), "Monorepo is not a valid Git repository"

def test_target_files_exist():
    """Test that migrated files exist at the correct paths."""
    calculator_path = "/app/monorepo/libs/python/legacy-lib/calculator.py"
    readme_path = "/app/monorepo/libs/python/legacy-lib/README.md"

    assert os.path.exists(calculator_path), f"calculator.py not found at {calculator_path}"
    assert os.path.exists(readme_path), f"README.md not found at {readme_path}"

def test_calculator_content():
    """Test that calculator.py contains expected functions."""
    calculator_path = "/app/monorepo/libs/python/legacy-lib/calculator.py"
    with open(calculator_path, "r") as f:
        content = f.read()

    # Check for all four functions
    assert "def add" in content, "add function not found in calculator.py"
    assert "def subtract" in content, "subtract function not found in calculator.py"
    assert "def multiply" in content, "multiply function not found in calculator.py"
    assert "def divide" in content, "divide function not found in calculator.py"

def test_readme_content():
    """Test that README.md has meaningful content."""
    readme_path = "/app/monorepo/libs/python/legacy-lib/README.md"
    with open(readme_path, "r") as f:
        content = f.read()

    assert len(content.strip()) > 50, "README.md appears to be too short or empty"
    assert "calculator" in content.lower() or "library" in content.lower(), "README.md doesn't mention calculator or library"

def test_commit_count():
    """Test that the monorepo has the expected number of commits."""
    os.chdir("/app/monorepo")
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=True
    )
    commit_count = int(result.stdout.strip())

    # Should have at least 5 commits:
    # 1 initial monorepo + 3 SVN commits + 1 merge commit
    assert commit_count >= 5, f"Expected at least 5 commits, but found {commit_count}"

def test_verification_commit_count():
    """Test that verification.txt contains the correct commit count."""
    with open("/app/verification.txt", "r") as f:
        content = f.read()

    # Extract commit count from verification file
    match = re.search(r"Total commit count:\s*(\d+)", content)
    assert match, "Could not find 'Total commit count:' in verification.txt"

    stated_count = int(match.group(1))

    # Get actual commit count from the repository
    os.chdir("/app/monorepo")
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=True
    )
    actual_count = int(result.stdout.strip())

    assert stated_count == actual_count, f"Verification file states {stated_count} commits, but repository has {actual_count}"

def test_svn_commits_in_history():
    """Test that SVN commit messages are preserved in Git history."""
    os.chdir("/app/monorepo")
    result = subprocess.run(
        ["git", "log", "--format=%s"],
        capture_output=True,
        text=True,
        check=True
    )
    commit_messages = result.stdout.lower()

    # Check for key SVN commit messages
    assert "add" in commit_messages and "subtract" in commit_messages, "Initial SVN commit not found in history"
    assert "multiply" in commit_messages and "divide" in commit_messages, "Second SVN commit not found in history"
    assert "readme" in commit_messages or "documentation" in commit_messages, "Third SVN commit not found in history"

def test_verification_lists_commit_messages():
    """Test that verification.txt lists commit messages."""
    with open("/app/verification.txt", "r") as f:
        content = f.read()

    # Should contain "Commit messages:" section
    assert "Commit messages:" in content, "verification.txt missing 'Commit messages:' section"

    # Should list multiple commit messages (at least 3 lines after the header)
    lines = content.split("\n")
    commit_section_started = False
    commit_lines = []

    for line in lines:
        if "Commit messages:" in line:
            commit_section_started = True
            continue
        if commit_section_started and line.strip() and not line.startswith("Files exist"):
            commit_lines.append(line)

    assert len(commit_lines) >= 3, f"Expected at least 3 commit messages, found {len(commit_lines)}"

def test_verification_confirms_files_exist():
    """Test that verification.txt confirms files exist."""
    with open("/app/verification.txt", "r") as f:
        content = f.read()

    # Check for confirmation of calculator.py
    assert "libs/python/legacy-lib/calculator.py" in content, "verification.txt doesn't mention calculator.py"
    assert "YES" in content or "yes" in content or "exist" in content.lower(), "verification.txt doesn't confirm files exist"

def test_monorepo_structure_preserved():
    """Test that original monorepo structure is preserved."""
    # The libs/ directory should exist
    assert os.path.exists("/app/monorepo/libs"), "libs/ directory not found"

    # The original monorepo README should exist
    assert os.path.exists("/app/monorepo/README.md"), "Original monorepo README.md not found"

def test_git_history_accessible():
    """Test that Git history is accessible and valid."""
    os.chdir("/app/monorepo")

    # Test that git log works
    result = subprocess.run(
        ["git", "log", "--oneline"],
        capture_output=True,
        text=True,
        check=True
    )

    assert len(result.stdout.strip()) > 0, "Git log is empty"

def test_subtree_path_in_history():
    """Test that files are tracked under the correct subtree path."""
    os.chdir("/app/monorepo")

    # Check that calculator.py appears in git log with the correct path
    result = subprocess.run(
        ["git", "log", "--all", "--name-only", "--format="],
        capture_output=True,
        text=True,
        check=True
    )

    files_in_history = result.stdout
    assert "libs/python/legacy-lib/calculator.py" in files_in_history, "calculator.py not found in correct path in Git history"
    assert "libs/python/legacy-lib/README.md" in files_in_history, "README.md not found in correct path in Git history"

def test_no_hardcoded_verification():
    """Test that verification isn't just a hardcoded file without actual migration."""
    # If the monorepo doesn't exist but verification.txt does, it's hardcoded
    if os.path.exists("/app/verification.txt"):
        assert os.path.exists("/app/monorepo"), "verification.txt exists but monorepo doesn't - likely hardcoded"
        assert os.path.exists("/app/monorepo/libs/python/legacy-lib/calculator.py"), "verification.txt exists but files don't - likely hardcoded"

def test_calculator_has_all_functions():
    """Test that the final calculator.py has all four arithmetic functions."""
    calculator_path = "/app/monorepo/libs/python/legacy-lib/calculator.py"
    with open(calculator_path, "r") as f:
        content = f.read()

    # The final version should have all four functions (from commit 2)
    functions = ["add", "subtract", "multiply", "divide"]
    for func in functions:
        assert f"def {func}" in content, f"Function '{func}' not found in calculator.py"

def test_merge_commit_exists():
    """Test that a merge commit exists showing integration."""
    os.chdir("/app/monorepo")
    result = subprocess.run(
        ["git", "log", "--format=%s", "--all"],
        capture_output=True,
        text=True,
        check=True
    )

    commit_messages = result.stdout.lower()
    # Should have a merge or integration commit
    assert "merge" in commit_messages or "legacy" in commit_messages, "No merge/integration commit found"

def test_verification_format():
    """Test that verification.txt follows the expected format."""
    with open("/app/verification.txt", "r") as f:
        content = f.read()

    # Check for required sections
    assert "Total commit count:" in content, "Missing 'Total commit count:' in verification.txt"
    assert "Commit messages:" in content, "Missing 'Commit messages:' section in verification.txt"
    assert "libs/python/legacy-lib/calculator.py" in content, "Missing calculator.py confirmation in verification.txt"
    assert "libs/python/legacy-lib/README.md" in content, "Missing README.md confirmation in verification.txt"
