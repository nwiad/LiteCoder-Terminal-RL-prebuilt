import os
import subprocess
import re


def test_result_file_exists():
    """Test that the result file exists at the expected location."""
    assert os.path.exists("/app/result.txt"), "Result file /app/result.txt does not exist"


def test_result_file_not_empty():
    """Test that the result file is not empty."""
    with open("/app/result.txt", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "Result file is empty"


def test_result_is_valid_sha():
    """Test that the result contains a valid 40-character hexadecimal SHA."""
    with open("/app/result.txt", "r") as f:
        content = f.read().strip()

    # Check if it's a valid 40-character hex string
    sha_pattern = re.compile(r'^[0-9a-f]{40}$')
    assert sha_pattern.match(content), f"Result '{content}' is not a valid 40-character SHA"


def test_commit_exists_in_repo():
    """Test that the commit SHA exists in the repository."""
    with open("/app/result.txt", "r") as f:
        commit_sha = f.read().strip()

    # Check if the repository was cloned
    repo_path = "/app/test-git-bisect"
    assert os.path.exists(repo_path), f"Repository not found at {repo_path}"

    # Verify the commit exists
    result = subprocess.run(
        ["git", "cat-file", "-t", commit_sha],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Commit {commit_sha} does not exist in the repository"
    assert result.stdout.strip() == "commit", f"SHA {commit_sha} is not a commit object"


def test_identified_commit_is_bad():
    """Test that the identified commit has the broken add_numbers function."""
    with open("/app/result.txt", "r") as f:
        commit_sha = f.read().strip()

    repo_path = "/app/test-git-bisect"

    # Checkout the identified commit
    subprocess.run(
        ["git", "checkout", "-f", commit_sha],
        cwd=repo_path,
        capture_output=True,
        check=True
    )

    # Find and test the add_numbers function
    result = subprocess.run(
        ["python3", "-c", """
import sys
import os
import glob
import importlib.util

sys.path.insert(0, '/app/test-git-bisect')

# Search for add_numbers function
possible_files = ['main.py', 'app.py', 'solution.py', 'add_numbers.py', 'calculator.py']
module = None

for filename in possible_files:
    filepath = f'/app/test-git-bisect/{filename}'
    if os.path.exists(filepath):
        spec = importlib.util.spec_from_file_location("module", filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'add_numbers'):
                break

if module is None or not hasattr(module, 'add_numbers'):
    for filepath in glob.glob('/app/test-git-bisect/**/*.py', recursive=True):
        try:
            spec = importlib.util.spec_from_file_location("module", filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'add_numbers'):
                    break
        except:
            continue

if module is None or not hasattr(module, 'add_numbers'):
    sys.exit(2)  # Function not found

result = module.add_numbers(2, 3)
if result == 5:
    sys.exit(0)  # Good
else:
    sys.exit(1)  # Bad
"""],
        cwd=repo_path,
        capture_output=True
    )

    assert result.returncode != 2, "add_numbers function not found in the repository"
    assert result.returncode == 1, f"Commit {commit_sha} does not have a broken add_numbers function (test passed when it should fail)"


def test_parent_commit_is_good():
    """Test that the parent of the identified commit has a working add_numbers function."""
    with open("/app/result.txt", "r") as f:
        commit_sha = f.read().strip()

    repo_path = "/app/test-git-bisect"

    # Get the parent commit
    result = subprocess.run(
        ["git", "rev-parse", f"{commit_sha}^"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    # If there's no parent (first commit), skip this test
    if result.returncode != 0:
        return

    parent_sha = result.stdout.strip()

    # Checkout the parent commit
    subprocess.run(
        ["git", "checkout", "-f", parent_sha],
        cwd=repo_path,
        capture_output=True,
        check=True
    )

    # Test the add_numbers function at parent commit
    result = subprocess.run(
        ["python3", "-c", """
import sys
import os
import glob
import importlib.util

sys.path.insert(0, '/app/test-git-bisect')

# Search for add_numbers function
possible_files = ['main.py', 'app.py', 'solution.py', 'add_numbers.py', 'calculator.py']
module = None

for filename in possible_files:
    filepath = f'/app/test-git-bisect/{filename}'
    if os.path.exists(filepath):
        spec = importlib.util.spec_from_file_location("module", filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'add_numbers'):
                break

if module is None or not hasattr(module, 'add_numbers'):
    for filepath in glob.glob('/app/test-git-bisect/**/*.py', recursive=True):
        try:
            spec = importlib.util.spec_from_file_location("module", filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'add_numbers'):
                    break
        except:
            continue

if module is None or not hasattr(module, 'add_numbers'):
    sys.exit(2)  # Function not found

result = module.add_numbers(2, 3)
if result == 5:
    sys.exit(0)  # Good
else:
    sys.exit(1)  # Bad
"""],
        cwd=repo_path,
        capture_output=True
    )

    assert result.returncode == 0, f"Parent commit {parent_sha} should have a working add_numbers function, but it's broken"
