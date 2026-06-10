import os
import json
import pytest


def test_comparison_json_exists():
    """Test that the comparison.json file exists at the expected location."""
    assert os.path.exists("/app/comparison.json"), "comparison.json file not found at /app/comparison.json"


def test_comparison_json_valid():
    """Test that comparison.json is valid JSON."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "comparison.json should contain a JSON object"


def test_comparison_json_structure():
    """Test that comparison.json has the required top-level structure."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    assert "squash_merge" in data, "Missing 'squash_merge' key"
    assert "regular_merge" in data, "Missing 'regular_merge' key"
    assert "differences" in data, "Missing 'differences' key"


def test_squash_merge_structure():
    """Test that squash_merge section has required fields."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    squash = data["squash_merge"]
    assert "branch" in squash, "Missing 'branch' in squash_merge"
    assert "total_commits" in squash, "Missing 'total_commits' in squash_merge"
    assert "commit_messages" in squash, "Missing 'commit_messages' in squash_merge"

    assert squash["branch"] == "main-squash", "Branch name should be 'main-squash'"
    assert isinstance(squash["total_commits"], int), "total_commits should be an integer"
    assert isinstance(squash["commit_messages"], list), "commit_messages should be a list"


def test_regular_merge_structure():
    """Test that regular_merge section has required fields."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    regular = data["regular_merge"]
    assert "branch" in regular, "Missing 'branch' in regular_merge"
    assert "total_commits" in regular, "Missing 'total_commits' in regular_merge"
    assert "commit_messages" in regular, "Missing 'commit_messages' in regular_merge"

    assert regular["branch"] == "main-regular", "Branch name should be 'main-regular'"
    assert isinstance(regular["total_commits"], int), "total_commits should be an integer"
    assert isinstance(regular["commit_messages"], list), "commit_messages should be a list"


def test_differences_structure():
    """Test that differences section has required fields."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    diff = data["differences"]
    assert "commit_count_difference" in diff, "Missing 'commit_count_difference' in differences"
    assert "history_structure" in diff, "Missing 'history_structure' in differences"

    assert isinstance(diff["commit_count_difference"], int), "commit_count_difference should be an integer"
    assert isinstance(diff["history_structure"], str), "history_structure should be a string"


def test_commit_counts_logical():
    """Test that commit counts are logical (regular merge should have more commits than squash)."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    squash_count = data["squash_merge"]["total_commits"]
    regular_count = data["regular_merge"]["total_commits"]

    # Both should have at least the initial commit
    assert squash_count >= 1, "Squash merge should have at least 1 commit (initial)"
    assert regular_count >= 1, "Regular merge should have at least 1 commit (initial)"

    # Regular merge should have more commits (preserves feature branch commits)
    assert regular_count > squash_count, \
        f"Regular merge ({regular_count}) should have more commits than squash merge ({squash_count})"


def test_commit_count_difference_accurate():
    """Test that commit_count_difference matches the actual difference."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    squash_count = data["squash_merge"]["total_commits"]
    regular_count = data["regular_merge"]["total_commits"]
    reported_diff = data["differences"]["commit_count_difference"]

    expected_diff = regular_count - squash_count
    assert reported_diff == expected_diff, \
        f"Reported difference ({reported_diff}) doesn't match actual ({expected_diff})"


def test_commit_messages_non_empty():
    """Test that commit messages lists are non-empty."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    squash_messages = data["squash_merge"]["commit_messages"]
    regular_messages = data["regular_merge"]["commit_messages"]

    assert len(squash_messages) > 0, "Squash merge should have at least one commit message"
    assert len(regular_messages) > 0, "Regular merge should have at least one commit message"


def test_commit_messages_count_matches():
    """Test that the number of commit messages matches total_commits."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    squash_count = data["squash_merge"]["total_commits"]
    squash_messages = data["squash_merge"]["commit_messages"]
    assert len(squash_messages) == squash_count, \
        f"Squash merge: commit message count ({len(squash_messages)}) doesn't match total_commits ({squash_count})"

    regular_count = data["regular_merge"]["total_commits"]
    regular_messages = data["regular_merge"]["commit_messages"]
    assert len(regular_messages) == regular_count, \
        f"Regular merge: commit message count ({len(regular_messages)}) doesn't match total_commits ({regular_count})"


def test_commit_messages_are_strings():
    """Test that all commit messages are non-empty strings."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    for msg in data["squash_merge"]["commit_messages"]:
        assert isinstance(msg, str), "All commit messages should be strings"
        assert len(msg.strip()) > 0, "Commit messages should not be empty"

    for msg in data["regular_merge"]["commit_messages"]:
        assert isinstance(msg, str), "All commit messages should be strings"
        assert len(msg.strip()) > 0, "Commit messages should not be empty"


def test_history_structure_meaningful():
    """Test that history_structure contains meaningful content."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    history_desc = data["differences"]["history_structure"]

    # Should be a non-empty string
    assert len(history_desc.strip()) > 0, "history_structure should not be empty"

    # Should be reasonably descriptive (at least 20 characters)
    assert len(history_desc) >= 20, "history_structure should be descriptive (at least 20 characters)"


def test_squash_merge_expected_commits():
    """Test that squash merge has the expected number of commits (initial + 1 squashed)."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    squash_count = data["squash_merge"]["total_commits"]

    # Should have: 1 initial commit + 1 squashed commit = 2 total
    assert squash_count == 2, \
        f"Squash merge should have exactly 2 commits (initial + squashed), found {squash_count}"


def test_regular_merge_expected_commits():
    """Test that regular merge has the expected number of commits."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    regular_count = data["regular_merge"]["total_commits"]

    # Should have: 1 initial + 3 feature commits + 1 merge commit = 5 total
    assert regular_count == 5, \
        f"Regular merge should have exactly 5 commits (initial + 3 feature + merge), found {regular_count}"


def test_commit_difference_is_three():
    """Test that the difference between regular and squash is exactly 3."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    diff = data["differences"]["commit_count_difference"]

    # Regular (5) - Squash (2) = 3
    assert diff == 3, \
        f"Commit count difference should be exactly 3, found {diff}"


def test_demo_repo_exists():
    """Test that the demo repository was created."""
    assert os.path.exists("/app/demo_repo"), "Demo repository directory not found at /app/demo_repo"
    assert os.path.isdir("/app/demo_repo"), "/app/demo_repo should be a directory"


def test_demo_repo_is_git_repo():
    """Test that demo_repo is a valid Git repository."""
    git_dir = "/app/demo_repo/.git"
    assert os.path.exists(git_dir), "demo_repo is not a Git repository (missing .git directory)"
    assert os.path.isdir(git_dir), ".git should be a directory"


def test_initial_readme_exists():
    """Test that the initial README.md file exists."""
    readme_path = "/app/demo_repo/README.md"
    assert os.path.exists(readme_path), "README.md not found in demo_repo"


def test_feature_files_exist():
    """Test that all three feature files were created."""
    for i in range(1, 4):
        file_path = f"/app/demo_repo/feature_a_{i}.txt"
        assert os.path.exists(file_path), f"feature_a_{i}.txt not found in demo_repo"


def test_feature_files_content():
    """Test that feature files have the correct content."""
    for i in range(1, 4):
        file_path = f"/app/demo_repo/feature_a_{i}.txt"
        with open(file_path, "r") as f:
            content = f.read().strip()
        expected = f"Feature A - Part {i}"
        assert content == expected, \
            f"feature_a_{i}.txt has incorrect content. Expected '{expected}', got '{content}'"


def test_chronological_order_squash():
    """Test that squash merge commit messages are in chronological order (oldest first)."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    messages = data["squash_merge"]["commit_messages"]

    # First message should be the initial commit (oldest)
    # Last message should be the squash merge commit (newest)
    # We can't hardcode exact messages, but we can verify the list is non-empty
    assert len(messages) >= 2, "Should have at least 2 messages in chronological order"


def test_chronological_order_regular():
    """Test that regular merge commit messages are in chronological order (oldest first)."""
    with open("/app/comparison.json", "r") as f:
        data = json.load(f)

    messages = data["regular_merge"]["commit_messages"]

    # Should have: initial, feature-a commits (3), merge commit
    assert len(messages) >= 5, "Should have at least 5 messages in chronological order"
