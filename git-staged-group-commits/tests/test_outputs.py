"""
Tests for git-staged-group-commits task.

Verifies that the agent correctly:
1. Initialized a git repo at /app/project/
2. Created exactly 3 commits in the correct order (docs → feature → build)
3. Each commit message contains the required keyword
4. Each commit contains exactly the correct files
5. No untracked files remain
"""

import os
import subprocess

REPO_DIR = "/app/project"

# Expected file groups (sorted for stable comparison)
DOCS_FILES = sorted(["CONTRIBUTING.md", "README.md", "docs/usage.md"])
FEATURE_FILES = sorted(["src/app.py", "src/utils.py", "tests/test_app.py"])
BUILD_FILES = sorted([".github/workflows/ci.yml", "Dockerfile", "Makefile"])
ALL_FILES = sorted(DOCS_FILES + FEATURE_FILES + BUILD_FILES)


def run_git(*args):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ── Test 1: Repository exists ──────────────────────────────────────

def test_git_repo_exists():
    """The .git directory must exist at /app/project/."""
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), (
        f"Expected a .git directory at {git_dir}, but it does not exist. "
        "The agent must initialize a git repository in /app/project/."
    )


# ── Test 2: Exactly 3 commits ─────────────────────────────────────

def test_exactly_three_commits():
    """The repository must contain exactly 3 commits."""
    stdout, _, rc = run_git("rev-list", "--count", "HEAD")
    assert rc == 0, "Failed to run git rev-list. Is the repo initialized with commits?"
    count = int(stdout)
    assert count == 3, (
        f"Expected exactly 3 commits, but found {count}. "
        "The agent must create exactly 3 commits: docs, feature, build."
    )


# ── Test 3: Commit order — oldest to newest: docs → feature → build

def _get_commits_oldest_first():
    """Return list of (sha, message) from oldest to newest."""
    stdout, _, rc = run_git("log", "--reverse", "--format=%H %s")
    assert rc == 0, "Failed to read git log."
    lines = [l for l in stdout.splitlines() if l.strip()]
    commits = []
    for line in lines:
        parts = line.split(" ", 1)
        sha = parts[0]
        msg = parts[1] if len(parts) > 1 else ""
        commits.append((sha, msg))
    return commits


def test_commit_1_message_contains_docs():
    """The oldest commit message must contain the word 'docs' (case-insensitive)."""
    commits = _get_commits_oldest_first()
    assert len(commits) >= 1, "No commits found."
    _, msg = commits[0]
    assert "docs" in msg.lower(), (
        f"Commit 1 (oldest) message does not contain 'docs'. "
        f"Got: '{msg}'"
    )


def test_commit_2_message_contains_feature():
    """The middle commit message must contain the word 'feature' (case-insensitive)."""
    commits = _get_commits_oldest_first()
    assert len(commits) >= 2, "Fewer than 2 commits found."
    _, msg = commits[1]
    assert "feature" in msg.lower(), (
        f"Commit 2 (middle) message does not contain 'feature'. "
        f"Got: '{msg}'"
    )


def test_commit_3_message_contains_build():
    """The newest commit (HEAD) message must contain the word 'build' (case-insensitive)."""
    commits = _get_commits_oldest_first()
    assert len(commits) >= 3, "Fewer than 3 commits found."
    _, msg = commits[2]
    assert "build" in msg.lower(), (
        f"Commit 3 (newest/HEAD) message does not contain 'build'. "
        f"Got: '{msg}'"
    )


# ── Test 4: Each commit contains exactly the right files ──────────

def _get_commit_files(sha):
    """Return sorted list of files changed in a given commit."""
    stdout, _, rc = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", sha)
    assert rc == 0, f"Failed to get files for commit {sha}."
    files = sorted([f.strip() for f in stdout.splitlines() if f.strip()])
    return files


def test_commit_1_contains_only_docs_files():
    """Commit 1 (oldest) must contain exactly the 3 documentation files."""
    commits = _get_commits_oldest_first()
    assert len(commits) >= 1, "No commits found."
    sha, _ = commits[0]
    files = _get_commit_files(sha)
    assert files == DOCS_FILES, (
        f"Commit 1 (docs) should contain exactly {DOCS_FILES}, "
        f"but found {files}."
    )


def test_commit_2_contains_only_feature_files():
    """Commit 2 (middle) must contain exactly the 3 feature files."""
    commits = _get_commits_oldest_first()
    assert len(commits) >= 2, "Fewer than 2 commits found."
    sha, _ = commits[1]
    files = _get_commit_files(sha)
    assert files == FEATURE_FILES, (
        f"Commit 2 (feature) should contain exactly {FEATURE_FILES}, "
        f"but found {files}."
    )


def test_commit_3_contains_only_build_files():
    """Commit 3 (newest/HEAD) must contain exactly the 3 build files."""
    commits = _get_commits_oldest_first()
    assert len(commits) >= 3, "Fewer than 3 commits found."
    sha, _ = commits[2]
    files = _get_commit_files(sha)
    assert files == BUILD_FILES, (
        f"Commit 3 (build) should contain exactly {BUILD_FILES}, "
        f"but found {files}."
    )


# ── Test 5: No untracked files remain ─────────────────────────────

def test_no_untracked_files():
    """After all commits, git status should show no untracked files."""
    stdout, _, rc = run_git("status", "--porcelain")
    assert rc == 0, "Failed to run git status."
    untracked = [
        line for line in stdout.splitlines()
        if line.strip().startswith("??")
    ]
    assert len(untracked) == 0, (
        f"Found untracked files: {untracked}. "
        "All files created by setup.sh must be committed."
    )


# ── Test 6: Working tree is clean ─────────────────────────────────

def test_working_tree_clean():
    """The working tree should be clean — no modified, staged, or deleted files."""
    stdout, _, rc = run_git("status", "--porcelain")
    assert rc == 0, "Failed to run git status."
    dirty = [line for line in stdout.splitlines() if line.strip()]
    assert len(dirty) == 0, (
        f"Working tree is not clean. Dirty entries: {dirty}"
    )


# ── Test 7: All 9 expected files are tracked ──────────────────────

def test_all_files_tracked():
    """All 9 files from the setup script must be tracked in the repository."""
    stdout, _, rc = run_git("ls-files")
    assert rc == 0, "Failed to run git ls-files."
    tracked = sorted([f.strip() for f in stdout.splitlines() if f.strip()])
    assert tracked == ALL_FILES, (
        f"Expected tracked files: {ALL_FILES}, "
        f"but found: {tracked}."
    )


# ── Test 8: HEAD points to the build commit ───────────────────────

def test_head_is_build_commit():
    """HEAD must be the build commit (the newest one)."""
    stdout, _, rc = run_git("log", "-1", "--format=%s")
    assert rc == 0, "Failed to read HEAD commit message."
    msg = stdout.strip()
    assert "build" in msg.lower(), (
        f"HEAD commit message should contain 'build', but got: '{msg}'. "
        "The build commit must be the newest (HEAD)."
    )


# ── Test 9: No merge commits ──────────────────────────────────────

def test_no_merge_commits():
    """All commits should be simple (non-merge) commits."""
    stdout, _, rc = run_git("log", "--format=%H %P")
    assert rc == 0, "Failed to read git log."
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split()
        # First element is the commit SHA, rest are parent SHAs
        parents = parts[1:]
        assert len(parents) <= 1, (
            f"Commit {parts[0]} has {len(parents)} parents — "
            "merge commits are not expected."
        )


# ── Test 10: File contents are intact ─────────────────────────────

def test_readme_content_intact():
    """README.md should contain expected content from setup script."""
    readme_path = os.path.join(REPO_DIR, "README.md")
    assert os.path.isfile(readme_path), "README.md does not exist."
    content = open(readme_path).read()
    assert "# My Project" in content, (
        "README.md does not contain expected header '# My Project'."
    )


def test_app_py_content_intact():
    """src/app.py should contain expected content from setup script."""
    app_path = os.path.join(REPO_DIR, "src", "app.py")
    assert os.path.isfile(app_path), "src/app.py does not exist."
    content = open(app_path).read()
    assert "def add(a, b):" in content, (
        "src/app.py does not contain expected function 'def add(a, b):'."
    )
    assert "def main():" in content, (
        "src/app.py does not contain expected function 'def main():'."
    )


def test_ci_yml_content_intact():
    """.github/workflows/ci.yml should contain expected CI content."""
    ci_path = os.path.join(REPO_DIR, ".github", "workflows", "ci.yml")
    assert os.path.isfile(ci_path), ".github/workflows/ci.yml does not exist."
    content = open(ci_path).read()
    assert "name: CI" in content, (
        "ci.yml does not contain expected 'name: CI'."
    )
