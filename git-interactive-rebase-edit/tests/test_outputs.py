"""
Tests for Git Interactive Rebase with Historical Edit task.

Validates that:
- Repository at /app/repo exists with exactly 3 commits on main
- Commit messages are correct and in the right order
- File contents at HEAD match expected values
- History was rewritten (old commit message gone)
- Bare remote at /app/remote.git exists and is in sync
"""

import os
import subprocess


REPO_PATH = "/app/repo"
REMOTE_PATH = "/app/remote.git"


def run_git(args, cwd=REPO_PATH):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ── Repository existence ──────────────────────────────────────────


def test_repo_directory_exists():
    """The local repository directory must exist."""
    assert os.path.isdir(REPO_PATH), f"Repository directory {REPO_PATH} does not exist"


def test_repo_is_git_repo():
    """The local repository must be a valid git repository."""
    git_dir = os.path.join(REPO_PATH, ".git")
    assert os.path.isdir(git_dir), f"{REPO_PATH} is not a git repository (no .git directory)"


# ── Branch ────────────────────────────────────────────────────────


def test_current_branch_is_main():
    """The current branch must be 'main'."""
    stdout, _, rc = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    assert rc == 0, "Failed to get current branch"
    assert stdout == "main", f"Expected branch 'main', got '{stdout}'"


# ── Commit count ──────────────────────────────────────────────────


def test_exactly_three_commits():
    """
    There must be exactly 3 commits on main.
    This catches agents that append a 4th commit instead of rewriting history.
    """
    stdout, _, rc = run_git(["rev-list", "--count", "main"])
    assert rc == 0, "Failed to count commits"
    assert int(stdout) == 3, (
        f"Expected exactly 3 commits on main, got {stdout}. "
        "History must be rewritten via rebase, not by adding new commits."
    )


# ── Commit messages (chronological order) ─────────────────────────


def _get_commit_messages_oldest_first():
    """Return list of commit messages from oldest to newest."""
    stdout, _, rc = run_git(["log", "--reverse", "--format=%s"])
    assert rc == 0, "Failed to read commit log"
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def test_commit_message_order():
    """Commit messages in chronological order must match exactly."""
    messages = _get_commit_messages_oldest_first()
    expected = [
        "Initial commit",
        "Add verified production data",
        "Add config file",
    ]
    assert messages == expected, (
        f"Commit messages mismatch.\n"
        f"  Expected: {expected}\n"
        f"  Got:      {messages}"
    )


def test_old_placeholder_message_absent():
    """
    The original commit message 'Add placeholder data' must NOT appear
    anywhere in the history. This ensures the rebase actually rewrote it.
    """
    stdout, _, rc = run_git(["log", "--format=%s"])
    assert rc == 0, "Failed to read commit log"
    messages = stdout.splitlines()
    for msg in messages:
        assert msg.strip() != "Add placeholder data", (
            "Old commit message 'Add placeholder data' still exists in history. "
            "The rebase did not rewrite the commit message."
        )


# ── File contents at HEAD ─────────────────────────────────────────


def _read_file_at_head(filename):
    """Read a file's content from the HEAD commit via git show."""
    stdout, stderr, rc = run_git(["show", f"HEAD:{filename}"])
    assert rc == 0, f"Failed to read {filename} at HEAD: {stderr}"
    return stdout


def test_data_txt_content():
    """data.txt at HEAD must contain exactly 'verified production data'."""
    content = _read_file_at_head("data.txt")
    assert content == "verified production data", (
        f"data.txt content mismatch.\n"
        f"  Expected: 'verified production data'\n"
        f"  Got:      '{content}'"
    )


def test_readme_content():
    """README.md at HEAD must contain exactly '# My Project'."""
    content = _read_file_at_head("README.md")
    assert content == "# My Project", (
        f"README.md content mismatch.\n"
        f"  Expected: '# My Project'\n"
        f"  Got:      '{content}'"
    )


def test_config_content():
    """config.txt at HEAD must contain exactly 'version=1.0'."""
    content = _read_file_at_head("config.txt")
    assert content == "version=1.0", (
        f"config.txt content mismatch.\n"
        f"  Expected: 'version=1.0'\n"
        f"  Got:      '{content}'"
    )


# ── File existence on disk ────────────────────────────────────────


def test_data_txt_exists_on_disk():
    """data.txt must exist in the working tree."""
    path = os.path.join(REPO_PATH, "data.txt")
    assert os.path.isfile(path), f"data.txt not found at {path}"


def test_readme_exists_on_disk():
    """README.md must exist in the working tree."""
    path = os.path.join(REPO_PATH, "README.md")
    assert os.path.isfile(path), f"README.md not found at {path}"


def test_config_exists_on_disk():
    """config.txt must exist in the working tree."""
    path = os.path.join(REPO_PATH, "config.txt")
    assert os.path.isfile(path), f"config.txt not found at {path}"


# ── Working tree file contents ────────────────────────────────────


def test_data_txt_working_tree():
    """data.txt on disk must match the committed content."""
    path = os.path.join(REPO_PATH, "data.txt")
    with open(path, "r") as f:
        content = f.read().strip()
    assert content == "verified production data", (
        f"data.txt on-disk content mismatch: '{content}'"
    )


# ── Remote repository ────────────────────────────────────────────


def test_remote_bare_repo_exists():
    """A bare git repository must exist at /app/remote.git."""
    assert os.path.isdir(REMOTE_PATH), (
        f"Remote bare repository directory {REMOTE_PATH} does not exist"
    )
    # A bare repo has HEAD directly in the directory (no .git subdirectory)
    head_file = os.path.join(REMOTE_PATH, "HEAD")
    assert os.path.isfile(head_file), (
        f"{REMOTE_PATH} does not appear to be a bare git repository (no HEAD file)"
    )


def test_origin_remote_configured():
    """The local repo must have a remote named 'origin'."""
    stdout, _, rc = run_git(["remote"])
    assert rc == 0, "Failed to list remotes"
    remotes = [r.strip() for r in stdout.splitlines()]
    assert "origin" in remotes, (
        f"Remote 'origin' not found. Configured remotes: {remotes}"
    )


def test_origin_points_to_remote_git():
    """The 'origin' remote URL must point to /app/remote.git."""
    stdout, _, rc = run_git(["remote", "get-url", "origin"])
    assert rc == 0, "Failed to get origin URL"
    assert stdout.rstrip("/") == REMOTE_PATH, (
        f"Origin URL mismatch. Expected '{REMOTE_PATH}', got '{stdout}'"
    )


def test_remote_head_matches_local():
    """
    The remote's main branch HEAD must match the local main HEAD.
    This verifies the push was successful.
    """
    local_head, _, rc1 = run_git(["rev-parse", "main"])
    assert rc1 == 0, "Failed to get local main HEAD"

    remote_head, _, rc2 = run_git(
        ["rev-parse", "main"], cwd=REMOTE_PATH
    )
    assert rc2 == 0, "Failed to get remote main HEAD"

    assert local_head == remote_head, (
        f"Remote HEAD does not match local HEAD.\n"
        f"  Local:  {local_head}\n"
        f"  Remote: {remote_head}"
    )


def test_remote_has_three_commits():
    """The remote must also have exactly 3 commits (consistent with local)."""
    stdout, _, rc = run_git(["rev-list", "--count", "main"], cwd=REMOTE_PATH)
    assert rc == 0, "Failed to count commits in remote"
    assert int(stdout) == 3, (
        f"Remote has {stdout} commits, expected 3"
    )


# ── Author identity ──────────────────────────────────────────────


def test_author_identity():
    """All commits should use the specified author identity."""
    stdout, _, rc = run_git(["log", "--format=%an <%ae>"])
    assert rc == 0, "Failed to read author info"
    authors = [line.strip() for line in stdout.splitlines() if line.strip()]
    for author in authors:
        assert author == "Developer <dev@example.com>", (
            f"Unexpected author: '{author}'. "
            f"Expected 'Developer <dev@example.com>'"
        )


# ── History integrity ─────────────────────────────────────────────


def test_commit2_introduces_data_txt():
    """
    The second commit (chronologically) must be the one that introduces data.txt.
    This verifies the rebase preserved the correct commit structure.
    """
    # Get commit hashes oldest-first
    stdout, _, rc = run_git(["log", "--reverse", "--format=%H"])
    assert rc == 0, "Failed to get commit hashes"
    hashes = [h.strip() for h in stdout.splitlines() if h.strip()]
    assert len(hashes) == 3, f"Expected 3 commits, got {len(hashes)}"

    # Check what files commit 2 changed
    second_hash = hashes[1]
    stdout2, _, rc2 = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", second_hash])
    assert rc2 == 0, "Failed to inspect second commit"
    files_changed = [f.strip() for f in stdout2.splitlines() if f.strip()]
    assert "data.txt" in files_changed, (
        f"Second commit should modify data.txt, but changed: {files_changed}"
    )


def test_no_rebase_in_progress():
    """There must be no ongoing rebase (the rebase must have completed cleanly)."""
    rebase_dir = os.path.join(REPO_PATH, ".git", "rebase-merge")
    rebase_apply = os.path.join(REPO_PATH, ".git", "rebase-apply")
    assert not os.path.isdir(rebase_dir), "rebase-merge directory exists — rebase not completed"
    assert not os.path.isdir(rebase_apply), "rebase-apply directory exists — rebase not completed"
