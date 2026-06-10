import os
import re

# All output files should be in /app directory
OUTPUT_DIR = "/app"

def test_all_output_files_exist():
    """Verify all 7 required output files exist in /app directory."""
    required_files = [
        "oneline_log.txt",
        "detailed_log.txt",
        "graph_log.txt",
        "author_log.txt",
        "pretty_log.txt",
        "file_log.txt",
        "stats.txt"
    ]

    for filename in required_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        assert os.path.exists(filepath), f"Missing required file: {filename}"
        assert os.path.isfile(filepath), f"{filename} is not a file"


def test_files_not_empty():
    """Verify all output files contain actual content (not empty)."""
    required_files = [
        "oneline_log.txt",
        "detailed_log.txt",
        "graph_log.txt",
        "author_log.txt",
        "pretty_log.txt",
        "file_log.txt",
        "stats.txt"
    ]

    for filename in required_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'r') as f:
            content = f.read().strip()
        assert len(content) > 0, f"{filename} is empty"


def test_oneline_log_format():
    """Verify oneline_log.txt has correct format: short hash followed by commit message."""
    filepath = os.path.join(OUTPUT_DIR, "oneline_log.txt")
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    # Should have 5 commits
    assert len(lines) == 5, f"Expected 5 commits, found {len(lines)}"

    # Each line should start with a short hash (7 chars) followed by space and message
    for line in lines:
        # Git oneline format: <short-hash> <message>
        assert re.match(r'^[0-9a-f]{7}\s+.+', line), f"Invalid oneline format: {line}"


def test_detailed_log_has_stats():
    """Verify detailed_log.txt contains diff statistics."""
    filepath = os.path.join(OUTPUT_DIR, "detailed_log.txt")
    with open(filepath, 'r') as f:
        content = f.read()

    # Should contain commit information
    assert "commit " in content.lower(), "Missing commit information"
    assert "Author:" in content or "author:" in content.lower(), "Missing author information"

    # Should contain file change statistics (insertions/deletions or file changed info)
    # Git --stat shows lines like "1 file changed" or "files changed"
    assert "file" in content.lower() and "changed" in content.lower(), "Missing diff statistics"


def test_graph_log_has_graph():
    """Verify graph_log.txt contains graph visualization characters."""
    filepath = os.path.join(OUTPUT_DIR, "graph_log.txt")
    with open(filepath, 'r') as f:
        content = f.read()

    # Graph output should contain asterisks or other graph characters
    # Git graph uses *, |, /, \ characters
    assert "*" in content, "Missing graph visualization"
    assert "commit " in content.lower(), "Missing commit information"


def test_author_log_filtered():
    """Verify author_log.txt is filtered by 'Test User'."""
    filepath = os.path.join(OUTPUT_DIR, "author_log.txt")
    with open(filepath, 'r') as f:
        content = f.read()

    # Should contain commits
    assert "commit " in content.lower(), "Missing commit information"

    # Should contain author information with "Test User"
    assert "Test User" in content, "Missing 'Test User' in author log"


def test_pretty_log_custom_format():
    """Verify pretty_log.txt has custom pipe-delimited format."""
    filepath = os.path.join(OUTPUT_DIR, "pretty_log.txt")
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    # Should have 5 commits
    assert len(lines) == 5, f"Expected 5 commits, found {len(lines)}"

    # Each line should match format: hash | author | date | message
    for line in lines:
        parts = line.split(" | ")
        assert len(parts) == 4, f"Expected 4 pipe-delimited parts, found {len(parts)} in: {line}"

        # Part 0: short hash (7 chars)
        assert re.match(r'^[0-9a-f]{7}$', parts[0]), f"Invalid hash format: {parts[0]}"

        # Part 1: author name (should be "Test User")
        assert len(parts[1]) > 0, "Author name is empty"

        # Part 2: ISO date format (YYYY-MM-DDTHH:MM:SS+TZ)
        assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', parts[2]), \
            f"Invalid ISO date format: {parts[2]}"

        # Part 3: commit message
        assert len(parts[3]) > 0, "Commit message is empty"


def test_file_log_readme_only():
    """Verify file_log.txt contains only README.md commit history."""
    filepath = os.path.join(OUTPUT_DIR, "file_log.txt")
    with open(filepath, 'r') as f:
        content = f.read()

    # Should contain commit information
    assert "commit " in content.lower(), "Missing commit information"

    # Should have commits related to README.md (commits 1 and 4)
    # We can't check exact count without parsing, but should have at least 2 commits
    commit_count = content.lower().count("commit ")
    assert commit_count >= 2, f"Expected at least 2 commits for README.md, found {commit_count}"

    # Should NOT mention other files in commit messages if properly filtered
    # (This is a soft check - git log -- file shows commits that touched that file)


def test_stats_format_and_values():
    """Verify stats.txt has correct format and reasonable values."""
    filepath = os.path.join(OUTPUT_DIR, "stats.txt")
    with open(filepath, 'r') as f:
        content = f.read().strip()

    lines = content.split('\n')
    assert len(lines) == 2, f"Expected 2 lines in stats.txt, found {len(lines)}"

    # Line 1: Total commits: X
    assert lines[0].startswith("Total commits: "), f"Invalid format for line 1: {lines[0]}"
    total_commits = int(lines[0].split(": ")[1])
    assert total_commits == 5, f"Expected 5 total commits, found {total_commits}"

    # Line 2: Files in latest commit: Y
    assert lines[1].startswith("Files in latest commit: "), f"Invalid format for line 2: {lines[1]}"
    files_count = int(lines[1].split(": ")[1])
    # Latest commit should have 4 files: README.md, file1.txt, file2.py, file3.js
    assert files_count == 4, f"Expected 4 files in latest commit, found {files_count}"


def test_git_repository_exists():
    """Verify that a git repository was actually created at /app/repo."""
    repo_path = "/app/repo"
    git_dir = os.path.join(repo_path, ".git")

    assert os.path.exists(repo_path), "Repository directory /app/repo does not exist"
    assert os.path.isdir(repo_path), "/app/repo is not a directory"
    assert os.path.exists(git_dir), "Git repository not initialized (missing .git directory)"
    assert os.path.isdir(git_dir), ".git is not a directory"


def test_commit_messages_present():
    """Verify that actual commit messages are present in logs (not hardcoded dummy data)."""
    # Check oneline log for reasonable commit messages
    filepath = os.path.join(OUTPUT_DIR, "oneline_log.txt")
    with open(filepath, 'r') as f:
        content = f.read().lower()

    # Should contain keywords from actual commits
    # We check for generic terms that should appear in git commit messages
    assert len(content) > 100, "Oneline log suspiciously short"

    # Verify it's not just dummy text by checking for git hash patterns
    assert re.search(r'[0-9a-f]{7}', content), "Missing git commit hashes"


def test_pretty_log_author_is_test_user():
    """Verify all commits in pretty_log.txt are by 'Test User'."""
    filepath = os.path.join(OUTPUT_DIR, "pretty_log.txt")
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        parts = line.split(" | ")
        author = parts[1]
        assert author == "Test User", f"Expected author 'Test User', found '{author}'"


def test_output_files_in_app_not_repo():
    """Verify output files are in /app, not in /app/repo."""
    required_files = [
        "oneline_log.txt",
        "detailed_log.txt",
        "graph_log.txt",
        "author_log.txt",
        "pretty_log.txt",
        "file_log.txt",
        "stats.txt"
    ]

    for filename in required_files:
        # Should exist in /app
        app_path = os.path.join(OUTPUT_DIR, filename)
        assert os.path.exists(app_path), f"{filename} not found in /app"

        # Should NOT exist in /app/repo
        repo_path = os.path.join("/app/repo", filename)
        assert not os.path.exists(repo_path), f"{filename} incorrectly placed in /app/repo"
