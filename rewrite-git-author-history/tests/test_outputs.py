import os
import subprocess
import json


def run_git_command(repo_path, command):
    """Helper to run git commands in a repository."""
    full_command = f"git -C {repo_path} {command}"
    result = subprocess.run(
        full_command,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_target_repo_exists():
    """Test that the target bare repository exists."""
    target_repo = "/app/target-repo.git"
    assert os.path.exists(target_repo), f"Target repository not found at {target_repo}"
    assert os.path.isdir(target_repo), f"Target repository path is not a directory"

    # Check if it's a valid git repository
    stdout, stderr, returncode = run_git_command(target_repo, "rev-parse --git-dir")
    assert returncode == 0, f"Target repository is not a valid git repository: {stderr}"


def test_target_repo_is_bare():
    """Test that the target repository is a bare repository."""
    target_repo = "/app/target-repo.git"
    stdout, stderr, returncode = run_git_command(target_repo, "rev-parse --is-bare-repository")
    assert returncode == 0, f"Failed to check if repository is bare: {stderr}"
    assert stdout == "true", f"Target repository is not bare (expected 'true', got '{stdout}')"


def test_all_commits_have_correct_author():
    """Test that all commits have author set to CorpX <legal@corpx.example>."""
    target_repo = "/app/target-repo.git"

    # Get all commit authors
    stdout, stderr, returncode = run_git_command(
        target_repo,
        "log --all --format='%an|%ae'"
    )
    assert returncode == 0, f"Failed to get commit authors: {stderr}"

    authors = stdout.split('\n') if stdout else []
    assert len(authors) > 0, "No commits found in target repository"

    # Check each commit has the correct author
    for author_line in authors:
        if not author_line:
            continue
        name, email = author_line.split('|')
        assert name == "CorpX", f"Author name is '{name}', expected 'CorpX'"
        assert email == "legal@corpx.example", f"Author email is '{email}', expected 'legal@corpx.example'"


def test_all_commits_have_correct_committer():
    """Test that all commits have committer set to CorpX <legal@corpx.example>."""
    target_repo = "/app/target-repo.git"

    # Get all commit committers
    stdout, stderr, returncode = run_git_command(
        target_repo,
        "log --all --format='%cn|%ce'"
    )
    assert returncode == 0, f"Failed to get commit committers: {stderr}"

    committers = stdout.split('\n') if stdout else []
    assert len(committers) > 0, "No commits found in target repository"

    # Check each commit has the correct committer
    for committer_line in committers:
        if not committer_line:
            continue
        name, email = committer_line.split('|')
        assert name == "CorpX", f"Committer name is '{name}', expected 'CorpX'"
        assert email == "legal@corpx.example", f"Committer email is '{email}', expected 'legal@corpx.example'"


def test_commit_count_matches():
    """Test that the target repository has the same number of commits as the original."""
    source_repo = "/app/test-repo"
    target_repo = "/app/target-repo.git"

    # Get commit count from source
    stdout_src, stderr_src, returncode_src = run_git_command(
        source_repo,
        "rev-list --all --count"
    )
    assert returncode_src == 0, f"Failed to count commits in source repo: {stderr_src}"
    source_count = int(stdout_src)

    # Get commit count from target
    stdout_tgt, stderr_tgt, returncode_tgt = run_git_command(
        target_repo,
        "rev-list --all --count"
    )
    assert returncode_tgt == 0, f"Failed to count commits in target repo: {stderr_tgt}"
    target_count = int(stdout_tgt)

    assert target_count == source_count, f"Commit count mismatch: source has {source_count}, target has {target_count}"
    assert target_count >= 3, f"Expected at least 3 commits, found {target_count}"


def test_commit_messages_preserved():
    """Test that commit messages are preserved from the original repository."""
    source_repo = "/app/test-repo"
    target_repo = "/app/target-repo.git"

    # Get commit messages from source
    stdout_src, stderr_src, returncode_src = run_git_command(
        source_repo,
        "log --all --format='%H|%s' --reverse"
    )
    assert returncode_src == 0, f"Failed to get commit messages from source: {stderr_src}"

    # Get commit messages from target
    stdout_tgt, stderr_tgt, returncode_tgt = run_git_command(
        target_repo,
        "log --all --format='%H|%s' --reverse"
    )
    assert returncode_tgt == 0, f"Failed to get commit messages from target: {stderr_tgt}"

    source_messages = [line.split('|', 1)[1] for line in stdout_src.split('\n') if line]
    target_messages = [line.split('|', 1)[1] for line in stdout_tgt.split('\n') if line]

    assert len(source_messages) == len(target_messages), "Number of commits doesn't match"

    # Messages should be identical (order matters)
    for i, (src_msg, tgt_msg) in enumerate(zip(source_messages, target_messages)):
        assert src_msg == tgt_msg, f"Commit {i} message mismatch: '{src_msg}' vs '{tgt_msg}'"


def test_commit_timestamps_preserved():
    """Test that commit timestamps (author date and commit date) are preserved."""
    source_repo = "/app/test-repo"
    target_repo = "/app/target-repo.git"

    # Get timestamps from source (author date and commit date)
    stdout_src, stderr_src, returncode_src = run_git_command(
        source_repo,
        "log --all --format='%H|%aI|%cI' --reverse"
    )
    assert returncode_src == 0, f"Failed to get timestamps from source: {stderr_src}"

    # Get timestamps from target
    stdout_tgt, stderr_tgt, returncode_tgt = run_git_command(
        target_repo,
        "log --all --format='%H|%aI|%cI' --reverse"
    )
    assert returncode_tgt == 0, f"Failed to get timestamps from target: {stderr_tgt}"

    source_timestamps = [line.split('|')[1:] for line in stdout_src.split('\n') if line]
    target_timestamps = [line.split('|')[1:] for line in stdout_tgt.split('\n') if line]

    assert len(source_timestamps) == len(target_timestamps), "Number of commits doesn't match"

    # Timestamps should be identical
    for i, (src_ts, tgt_ts) in enumerate(zip(source_timestamps, target_timestamps)):
        assert src_ts[0] == tgt_ts[0], f"Commit {i} author date mismatch: '{src_ts[0]}' vs '{tgt_ts[0]}'"
        assert src_ts[1] == tgt_ts[1], f"Commit {i} commit date mismatch: '{src_ts[1]}' vs '{tgt_ts[1]}'"


def test_file_contents_preserved():
    """Test that file contents at each commit are preserved."""
    source_repo = "/app/test-repo"
    target_repo = "/app/target-repo.git"

    # Get list of all commits from source
    stdout_src, stderr_src, returncode_src = run_git_command(
        source_repo,
        "log --all --format='%H' --reverse"
    )
    assert returncode_src == 0, f"Failed to get commits from source: {stderr_src}"
    source_commits = [line for line in stdout_src.split('\n') if line]

    # Get list of all commits from target
    stdout_tgt, stderr_tgt, returncode_tgt = run_git_command(
        target_repo,
        "log --all --format='%H' --reverse"
    )
    assert returncode_tgt == 0, f"Failed to get commits from target: {stderr_tgt}"
    target_commits = [line for line in stdout_tgt.split('\n') if line]

    assert len(source_commits) == len(target_commits), "Number of commits doesn't match"

    # For each commit, compare the tree hash (which represents file contents)
    for i, (src_commit, tgt_commit) in enumerate(zip(source_commits, target_commits)):
        # Get tree hash from source commit
        stdout_src_tree, _, returncode_src_tree = run_git_command(
            source_repo,
            f"rev-parse {src_commit}^{{tree}}"
        )
        assert returncode_src_tree == 0, f"Failed to get tree hash for source commit {src_commit}"

        # Get tree hash from target commit
        stdout_tgt_tree, _, returncode_tgt_tree = run_git_command(
            target_repo,
            f"rev-parse {tgt_commit}^{{tree}}"
        )
        assert returncode_tgt_tree == 0, f"Failed to get tree hash for target commit {tgt_commit}"

        assert stdout_src_tree == stdout_tgt_tree, \
            f"Commit {i} tree hash mismatch: source {stdout_src_tree} vs target {stdout_tgt_tree}"


def test_multiple_authors_in_original():
    """Test that the original repository had multiple authors (requirement verification)."""
    source_repo = "/app/test-repo"

    # Get unique authors from source
    stdout, stderr, returncode = run_git_command(
        source_repo,
        "log --all --format='%an|%ae' | sort -u"
    )
    assert returncode == 0, f"Failed to get authors from source: {stderr}"

    unique_authors = [line for line in stdout.split('\n') if line]
    assert len(unique_authors) >= 2, \
        f"Original repository should have at least 2 different authors, found {len(unique_authors)}"


def test_no_lazy_empty_repo():
    """Test that the target repository is not just an empty initialized repo."""
    target_repo = "/app/target-repo.git"

    # Check that there are actual commits
    stdout, stderr, returncode = run_git_command(
        target_repo,
        "rev-list --all --count"
    )
    assert returncode == 0, f"Failed to count commits: {stderr}"
    commit_count = int(stdout)
    assert commit_count > 0, "Target repository has no commits (lazy empty repo)"

    # Check that there are actual refs (branches)
    stdout, stderr, returncode = run_git_command(
        target_repo,
        "show-ref"
    )
    assert returncode == 0, f"Target repository has no refs: {stderr}"
    assert len(stdout) > 0, "Target repository has no branches or tags"


def test_commit_graph_topology_preserved():
    """Test that the commit graph topology (parent relationships) is preserved."""
    source_repo = "/app/test-repo"
    target_repo = "/app/target-repo.git"

    # Get commit graph from source (commit hash and parent count)
    stdout_src, stderr_src, returncode_src = run_git_command(
        source_repo,
        "log --all --format='%H|%P' --reverse"
    )
    assert returncode_src == 0, f"Failed to get commit graph from source: {stderr_src}"

    # Get commit graph from target
    stdout_tgt, stderr_tgt, returncode_tgt = run_git_command(
        target_repo,
        "log --all --format='%H|%P' --reverse"
    )
    assert returncode_tgt == 0, f"Failed to get commit graph from target: {stderr_tgt}"

    source_graph = [line.split('|') for line in stdout_src.split('\n') if line]
    target_graph = [line.split('|') for line in stdout_tgt.split('\n') if line]

    assert len(source_graph) == len(target_graph), "Number of commits doesn't match"

    # Check that parent count matches for each commit
    for i, (src_entry, tgt_entry) in enumerate(zip(source_graph, target_graph)):
        src_parents = src_entry[1].split() if len(src_entry) > 1 and src_entry[1] else []
        tgt_parents = tgt_entry[1].split() if len(tgt_entry) > 1 and tgt_entry[1] else []

        assert len(src_parents) == len(tgt_parents), \
            f"Commit {i} parent count mismatch: source has {len(src_parents)}, target has {len(tgt_parents)}"
